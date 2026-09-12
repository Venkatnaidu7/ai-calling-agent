import json
import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.models import Call, CallActionItem, CallIntelligenceJob, CallSummary, Transcript, TranscriptSegment

class IntelligenceError(RuntimeError):
    pass

def build_transcript_text(segments: list[TranscriptSegment]) -> str:
    return "\n".join(f"{s.speaker}: {s.text}" for s in segments if s.text)

async def ensure_job(db: AsyncSession, tenant_id, call_id):
    """Get-or-create the single intelligence job for a call, safely under callback races."""
    job = await db.scalar(select(CallIntelligenceJob).where(CallIntelligenceJob.call_id == call_id, CallIntelligenceJob.tenant_id == tenant_id))
    if job:
        return job
    job = CallIntelligenceJob(tenant_id=tenant_id, call_id=call_id, status='QUEUED')
    db.add(job)
    try:
        await db.flush()
        return job
    except IntegrityError:
        await db.rollback()
        job = await db.scalar(select(CallIntelligenceJob).where(CallIntelligenceJob.call_id == call_id, CallIntelligenceJob.tenant_id == tenant_id))
        if not job:
            raise
        return job

async def analyze_call(db: AsyncSession, tenant_id, call_id):
    settings = get_settings()
    call = await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == tenant_id))
    if not call: raise IntelligenceError('CALL_NOT_FOUND')
    transcript = await db.scalar(select(Transcript).where(Transcript.call_id == call_id, Transcript.tenant_id == tenant_id))
    if not transcript: raise IntelligenceError('TRANSCRIPT_NOT_FOUND')
    segments = (await db.scalars(select(TranscriptSegment).where(TranscriptSegment.transcript_id == transcript.id, TranscriptSegment.tenant_id == tenant_id).order_by(TranscriptSegment.started_at.asc().nulls_last(), TranscriptSegment.id.asc()))).all()
    text = build_transcript_text(segments)
    if not text.strip(): raise IntelligenceError('TRANSCRIPT_EMPTY')
    if not settings.openai_api_key: raise IntelligenceError('OPENAI_API_KEY_NOT_CONFIGURED')
    schema = {'type':'object','properties':{'summary':{'type':'string'},'intent':{'type':'string'},'outcome':{'type':'string'},'sentiment':{'type':'string','enum':['POSITIVE','NEUTRAL','NEGATIVE','MIXED','UNKNOWN']},'follow_up_required':{'type':'boolean'},'next_action':{'type':'string'},'action_items':{'type':'array','items':{'type':'object','properties':{'description':{'type':'string'},'owner':{'type':'string'},'due_date':{'type':'string'}},'required':['description','owner','due_date'],'additionalProperties':False}}},'required':['summary','intent','outcome','sentiment','follow_up_required','next_action','action_items'],'additionalProperties':False}
    payload = {'model':settings.openai_intelligence_model,'store':False,'input':[{'role':'system','content':'Analyze a customer phone call transcript. Return concise, factual call intelligence. Never invent facts. Use UNKNOWN or an empty action_items array when unsupported.'},{'role':'user','content':text[:120000]}],'text':{'format':{'type':'json_schema','name':'call_intelligence','strict':True,'schema':schema}}}
    headers = {'Authorization':f'Bearer {settings.openai_api_key}','Content-Type':'application/json'}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = await client.post('https://api.openai.com/v1/responses',headers=headers,json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc: raise IntelligenceError(f'OPENAI_ERROR_{exc.response.status_code}') from exc
    except httpx.HTTPError as exc: raise IntelligenceError('OPENAI_REQUEST_FAILED') from exc
    data = response.json(); output_text = data.get('output_text')
    if not output_text:
        for item in data.get('output',[]):
            for content in item.get('content',[]):
                if content.get('type') in {'output_text','text'} and content.get('text'): output_text = content['text']; break
            if output_text: break
    if not output_text: raise IntelligenceError('OPENAI_EMPTY_RESPONSE')
    try: result = json.loads(output_text)
    except json.JSONDecodeError as exc: raise IntelligenceError('OPENAI_INVALID_JSON') from exc
    summary = await db.scalar(select(CallSummary).where(CallSummary.call_id == call_id, CallSummary.tenant_id == tenant_id))
    if not summary: summary = CallSummary(tenant_id=tenant_id, call_id=call_id, summary=result['summary']); db.add(summary)
    summary.summary=result['summary']; summary.intent=result['intent']; summary.outcome=result['outcome']; summary.sentiment=result['sentiment']; summary.follow_up_required=result['follow_up_required']; summary.next_action=result['next_action']
    await db.execute(delete(CallActionItem).where(CallActionItem.call_id == call_id, CallActionItem.tenant_id == tenant_id))
    for item in result.get('action_items',[]):
        if item['description'].strip(): db.add(CallActionItem(tenant_id=tenant_id,call_id=call_id,description=item['description'][:4000],owner=item['owner'][:100] or None,due_date=item['due_date'][:50] or None))
    transcript.status='COMPLETED'; job=await ensure_job(db,tenant_id,call_id); job.status='COMPLETED'; job.attempts += 1; job.last_error=None
    await db.commit(); await db.refresh(summary); return summary
