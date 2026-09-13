from calendar import monthrange
from datetime import datetime, timezone
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import tenant_id
from app.core.config import get_settings
from app.db.session import get_db
from app.models import BillingEvent, Plan, Subscription, UsageRecord

router = APIRouter(prefix='/billing', tags=['billing'])

def configure_stripe() -> None:
    key = get_settings().stripe_secret_key
    if not key:
        raise HTTPException(503, 'Stripe billing is not configured')
    stripe.api_key = key

def current_period() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(day=monthrange(now.year, now.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    return start, end

@router.get('/plans')
async def plans(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Plan).order_by(Plan.name))).all()
    return [{'id': str(p.id), 'name': p.name, 'limits': p.limits or {}, 'stripe_price_id': p.stripe_price_id} for p in rows]

@router.get('/subscription')
async def subscription(t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == UUID(t)))
    if not sub: return {'subscription': None}
    plan = await db.scalar(select(Plan).where(Plan.id == sub.plan_id)) if sub.plan_id else None
    return {'subscription': {'id': str(sub.id), 'status': sub.status, 'plan': plan.name if plan else None, 'stripe_customer_id': sub.stripe_customer_id, 'stripe_subscription_id': sub.stripe_subscription_id}}

@router.get('/usage')
async def usage(t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    tid = UUID(t); start, end = current_period()
    rows = (await db.execute(select(UsageRecord.metric, func.coalesce(func.sum(UsageRecord.quantity), 0)).where(UsageRecord.tenant_id == tid, UsageRecord.period_start == start, UsageRecord.period_end == end).group_by(UsageRecord.metric))).all()
    values = {metric: float(quantity) for metric, quantity in rows}
    sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == tid))
    plan = await db.scalar(select(Plan).where(Plan.id == sub.plan_id)) if sub and sub.plan_id else None
    limit = (plan.limits or {}).get('minutes') if plan else None
    used = values.get('voice_minutes', 0.0)
    return {'period_start': start.isoformat(), 'period_end': end.isoformat(), 'usage': values, 'limits': {'minutes': limit, 'used': used, 'remaining': max(0.0, float(limit) - used) if limit is not None else None}}

@router.post('/checkout')
async def checkout(plan_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    configure_stripe(); tid = UUID(t)
    plan = await db.scalar(select(Plan).where(Plan.id == plan_id))
    if not plan or not plan.stripe_price_id: raise HTTPException(400, 'Selected plan is not configured for Stripe checkout')
    sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == tid))
    customer_id = sub.stripe_customer_id if sub else None
    if not customer_id:
        customer = stripe.Customer.create(metadata={'tenant_id': str(tid)}); customer_id = customer.id
        if not sub: sub = Subscription(tenant_id=tid, plan_id=plan.id, stripe_customer_id=customer_id, status='INCOMPLETE'); db.add(sub)
        else: sub.stripe_customer_id = customer_id
        await db.commit()
    session = stripe.checkout.Session.create(mode='subscription', customer=customer_id, line_items=[{'price': plan.stripe_price_id, 'quantity': 1}], success_url=f"{get_settings().frontend_url.rstrip('/')}/billing?checkout=success", cancel_url=f"{get_settings().frontend_url.rstrip('/')}/billing?checkout=cancelled", metadata={'tenant_id': str(tid), 'plan_id': str(plan.id)}, subscription_data={'metadata': {'tenant_id': str(tid), 'plan_id': str(plan.id)}})
    return {'checkout_url': session.url, 'session_id': session.id}

@router.post('/portal')
async def portal(t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    configure_stripe(); sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == UUID(t)))
    if not sub or not sub.stripe_customer_id: raise HTTPException(409, 'No Stripe customer is configured for this tenant')
    session = stripe.billing_portal.Session.create(customer=sub.stripe_customer_id, return_url=f"{get_settings().frontend_url.rstrip('/')}/billing")
    return {'portal_url': session.url}

@router.post('/stripe/webhook')
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body(); secret = get_settings().stripe_webhook_secret; signature = request.headers.get('Stripe-Signature')
    if not secret or not signature: raise HTTPException(400, 'Stripe webhook signature is required')
    try: event = stripe.Webhook.construct_event(body, signature, secret)
    except ValueError: raise HTTPException(400, 'Invalid webhook payload')
    except stripe.error.SignatureVerificationError: raise HTTPException(400, 'Invalid webhook signature')
    event_id = event['id']; event_type = event['type']
    existing = await db.scalar(select(BillingEvent).where(BillingEvent.stripe_event_id == event_id))
    if existing: return {'received': True, 'event_id': event_id, 'duplicate': True}
    db.add(BillingEvent(stripe_event_id=event_id, event_type=event_type, payload=event))
    obj = event['data']['object']; metadata = obj.get('metadata') or {}; tenant_value = metadata.get('tenant_id'); customer_id = obj.get('customer')
    sub = await db.scalar(select(Subscription).where(Subscription.stripe_customer_id == customer_id)) if customer_id else None
    if not sub and tenant_value:
        try: sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == UUID(tenant_value)))
        except ValueError: sub = None
    if event_type == 'checkout.session.completed' and sub:
        sub.stripe_customer_id = customer_id or sub.stripe_customer_id; sub.stripe_subscription_id = obj.get('subscription') or sub.stripe_subscription_id; sub.status = 'ACTIVE'
        if metadata.get('plan_id'):
            try:
                plan = await db.scalar(select(Plan).where(Plan.id == UUID(metadata['plan_id'])))
                if plan: sub.plan_id = plan.id
            except ValueError: pass
    elif event_type in {'customer.subscription.created', 'customer.subscription.updated', 'customer.subscription.deleted'} and sub:
        sub.stripe_subscription_id = obj.get('id') or sub.stripe_subscription_id; sub.status = str(obj.get('status', 'unknown')).upper()
        price_id = ((obj.get('items') or {}).get('data') or [{}])[0].get('price', {}).get('id')
        if price_id:
            plan = await db.scalar(select(Plan).where(Plan.stripe_price_id == price_id))
            if plan: sub.plan_id = plan.id
    await db.commit(); return {'received': True, 'event_id': event_id, 'duplicate': False}
