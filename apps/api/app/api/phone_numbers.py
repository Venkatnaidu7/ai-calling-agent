from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client

from app.api.deps import tenant_id
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Agent, PhoneNumber
from app.providers.plivo import attach_number as plivo_attach_number
from app.providers.plivo import client as plivo_client
from app.providers.plivo import ensure_voice_application, normalize_number
from app.schemas.phone import (
    PhoneNumberCreate,
    PhoneNumberOut,
    PhoneNumberProvision,
    PhoneNumberUpdate,
    PlivoNumberAttach,
)

router = APIRouter(prefix="/phone-numbers", tags=["phone-numbers"])


def _twilio_client() -> Client:
    s = get_settings()
    if not s.twilio_account_sid or not s.twilio_auth_token:
        raise HTTPException(status_code=503, detail="Twilio is not configured")
    return Client(s.twilio_account_sid, s.twilio_auth_token)


def _voice_url(path: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(status_code=503, detail="public_base_url must use HTTPS for Twilio voice webhooks")
    return f"{base}{path}"


def _provider(value: str) -> str:
    provider = value.strip().lower()
    if provider not in {"twilio", "plivo"}:
        raise HTTPException(status_code=400, detail=f"Unsupported voice provider: {provider}")
    return provider


def _plivo_value(response, name: str, default=None):
    if isinstance(response, dict):
        return response.get(name, default)
    return getattr(response, name, default)


def to_out(phone: PhoneNumber) -> PhoneNumberOut:
    capabilities = phone.capabilities or {}
    return PhoneNumberOut(
        id=str(phone.id),
        tenant_id=str(phone.tenant_id),
        e164=phone.e164,
        provider=phone.provider,
        provider_number_id=phone.provider_number_id,
        country=phone.country,
        agent_id=str(phone.agent_id) if phone.agent_id else None,
        inbound_enabled=bool(capabilities.get("inbound", True)),
        outbound_enabled=bool(capabilities.get("outbound", True)),
        active=bool(phone.active),
    )


async def get_agent(agent_id: UUID | None, tenant: UUID, db: AsyncSession) -> Agent | None:
    if agent_id is None:
        return None
    agent = await db.scalar(select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant))
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not found for this tenant")
    return agent


@router.get("", response_model=list[PhoneNumberOut])
async def list_phone_numbers(tenant: str = Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(PhoneNumber)
            .where(PhoneNumber.tenant_id == UUID(tenant))
            .order_by(PhoneNumber.created_at.desc())
        )
    ).all()
    return [to_out(phone) for phone in rows]


@router.get("/available")
async def search_available_numbers(
    provider: str = Query("twilio", min_length=2, max_length=10),
    country: str = Query("US", min_length=2, max_length=4),
    area_code: str | None = Query(None, min_length=3, max_length=6),
    limit: int = Query(20, ge=1, le=100),
):
    provider = _provider(provider)
    try:
        if provider == "plivo":
            response = plivo_client().numbers.search(
                country_iso=country.upper(),
                pattern=area_code,
                services="voice",
                limit=min(limit, 20),
            )
            objects = _plivo_value(response, "objects", []) or []
            return [
                {
                    "phone_number": f"+{_plivo_value(n, 'number')}",
                    "friendly_name": _plivo_value(n, "region") or _plivo_value(n, "city"),
                    "locality": _plivo_value(n, "city"),
                    "region": _plivo_value(n, "region"),
                    "iso_country": country.upper(),
                    "provider": "plivo",
                    "voice_enabled": bool(_plivo_value(n, "voice_enabled", True)),
                    "monthly_rental_rate": _plivo_value(n, "monthly_rental_rate"),
                }
                for n in objects
            ]
        client = _twilio_client()
        numbers = (
            client.available_phone_numbers(country.upper()).local.list(area_code=area_code, limit=limit)
            if area_code
            else client.available_phone_numbers(country.upper()).local.list(limit=limit)
        )
        return [
            {
                "phone_number": n.phone_number,
                "friendly_name": n.friendly_name,
                "locality": n.locality,
                "region": n.region,
                "iso_country": n.iso_country,
                "provider": "twilio",
            }
            for n in numbers
        ]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to search {provider} numbers: {exc}") from exc


@router.post("/provision", response_model=PhoneNumberOut, status_code=status.HTTP_201_CREATED)
async def provision_phone_number(
    data: PhoneNumberProvision,
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    tid = UUID(tenant)
    provider = _provider(data.provider)
    duplicate = await db.scalar(
        select(PhoneNumber).where(PhoneNumber.tenant_id == tid, PhoneNumber.e164 == data.phone_number)
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Phone number already configured")
    await get_agent(data.agent_id, tid, db)

    if provider == "plivo":
        number = normalize_number(data.phone_number)
        api = plivo_client()
        app_id = ensure_voice_application()
        try:
            result = api.numbers.buy(number=number, app_id=app_id)
            purchased = _plivo_value(result, "numbers", []) or []
            if purchased and isinstance(purchased, list):
                first = purchased[0]
                status_value = _plivo_value(first, "status", "Success")
                if str(status_value).lower() not in {"success", "fulfilled", "created"}:
                    raise RuntimeError(f"Plivo number purchase was not fulfilled: {status_value}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Unable to provision Plivo number: {exc}") from exc
        phone = PhoneNumber(
            tenant_id=tid,
            e164=data.phone_number,
            provider="plivo",
            provider_number_id=number,
            country=data.country,
            agent_id=data.agent_id,
            capabilities={"inbound": data.inbound_enabled, "outbound": data.outbound_enabled},
            active=True,
        )
        db.add(phone)
        try:
            await db.commit()
            await db.refresh(phone)
        except Exception as exc:
            await db.rollback()
            try:
                api.numbers.delete(number=number)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="Number was provisioned but could not be stored") from exc
        return to_out(phone)

    client = _twilio_client()
    voice_url = _voice_url("/api/v1/voice/twilio/inbound")
    status_url = _voice_url("/api/v1/voice/twilio/status")
    try:
        tw = client.incoming_phone_numbers.create(
            phone_number=data.phone_number,
            voice_url=voice_url,
            voice_method="POST",
            status_callback=status_url,
            status_callback_method="POST",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to provision Twilio number: {exc}") from exc
    phone = PhoneNumber(
        tenant_id=tid,
        e164=tw.phone_number,
        provider="twilio",
        provider_number_id=tw.sid,
        country=data.country or getattr(tw, "iso_country", None),
        agent_id=data.agent_id,
        capabilities={"inbound": data.inbound_enabled, "outbound": data.outbound_enabled},
        active=True,
    )
    db.add(phone)
    try:
        await db.commit()
        await db.refresh(phone)
    except Exception:
        await db.rollback()
        try:
            client.incoming_phone_numbers(tw.sid).delete()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Number was provisioned but could not be stored")
    return to_out(phone)


@router.post("/plivo/attach", response_model=PhoneNumberOut, status_code=status.HTTP_201_CREATED)
async def attach_plivo_number(
    data: PlivoNumberAttach,
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    tid = UUID(tenant)
    await get_agent(data.agent_id, tid, db)
    duplicate = await db.scalar(
        select(PhoneNumber).where(PhoneNumber.tenant_id == tid, PhoneNumber.e164 == data.phone_number)
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Phone number already configured")

    number = normalize_number(data.phone_number)
    try:
        details = plivo_client().numbers.get(number=number)
        if not bool(_plivo_value(details, "voice_enabled", True)):
            raise HTTPException(status_code=409, detail="Plivo number is not voice enabled")
        app_id = ensure_voice_application()
        plivo_attach_number(data.phone_number, app_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to attach Plivo number: {exc}") from exc

    phone = PhoneNumber(
        tenant_id=tid,
        e164=data.phone_number,
        provider="plivo",
        provider_number_id=number,
        country=data.country,
        agent_id=data.agent_id,
        capabilities={"inbound": data.inbound_enabled, "outbound": data.outbound_enabled},
        active=True,
    )
    db.add(phone)
    try:
        await db.commit()
        await db.refresh(phone)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Plivo number was attached but could not be stored") from exc
    return to_out(phone)


@router.post("", response_model=PhoneNumberOut, status_code=status.HTTP_201_CREATED)
async def create_phone_number(
    data: PhoneNumberCreate,
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    tid = UUID(tenant)
    provider = _provider(data.provider)
    duplicate = await db.scalar(
        select(PhoneNumber).where(PhoneNumber.tenant_id == tid, PhoneNumber.e164 == data.e164)
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Phone number already configured")
    agent_id = UUID(data.agent_id) if data.agent_id else None
    await get_agent(agent_id, tid, db)
    phone = PhoneNumber(
        tenant_id=tid,
        e164=data.e164,
        provider=provider,
        provider_number_id=data.provider_number_id,
        country=data.country,
        agent_id=agent_id,
        capabilities={"inbound": data.inbound_enabled, "outbound": data.outbound_enabled},
        active=True,
    )
    db.add(phone)
    await db.commit()
    await db.refresh(phone)
    return to_out(phone)


@router.patch("/{phone_id}", response_model=PhoneNumberOut)
async def update_phone_number(
    phone_id: UUID,
    data: PhoneNumberUpdate,
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    tid = UUID(tenant)
    phone = await db.scalar(select(PhoneNumber).where(PhoneNumber.id == phone_id, PhoneNumber.tenant_id == tid))
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    if data.agent_id is not None:
        phone.agent_id = UUID(data.agent_id)
        await get_agent(phone.agent_id, tid, db)
    elif "agent_id" in data.model_fields_set:
        phone.agent_id = None
    capabilities = dict(phone.capabilities or {})
    if data.inbound_enabled is not None:
        capabilities["inbound"] = data.inbound_enabled
    if data.outbound_enabled is not None:
        capabilities["outbound"] = data.outbound_enabled
    phone.capabilities = capabilities
    if data.active is not None:
        phone.active = data.active
    await db.commit()
    await db.refresh(phone)
    return to_out(phone)


@router.delete("/{phone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phone_number(
    phone_id: UUID,
    tenant: str = Depends(tenant_id),
    db: AsyncSession = Depends(get_db),
):
    phone = await db.scalar(
        select(PhoneNumber).where(PhoneNumber.id == phone_id, PhoneNumber.tenant_id == UUID(tenant))
    )
    if not phone:
        raise HTTPException(status_code=404, detail="Phone number not found")
    phone.active = False
    await db.commit()
