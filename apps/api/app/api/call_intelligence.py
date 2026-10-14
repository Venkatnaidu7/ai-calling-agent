from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import tenant_id
from app.db.session import get_db
from app.models import Call, Transcript, TranscriptSegment, CallSummary
from app.schemas.call_intelligence import TranscriptCreate, TranscriptOut, CallIntelligenceOut
from app.services.call_intelligence import IntelligenceError, analyze_call

router = APIRouter(prefix='/calls', tags=['call-intelligence'])


@router.get('/{call_id}/transcript', response_model=TranscriptOut)
async def get_transcript(call_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    transcript = await db.scalar(select(Transcript).where(Transcript.call_id == call_id, Transcript.tenant_id == UUID(t)))
    if not transcript:
        raise HTTPException(404, 'Transcript not found')
    return transcript


@router.post('/{call_id}/transcript', response_model=TranscriptOut)
async def upsert_transcript(call_id: UUID, body: TranscriptCreate, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    tid = UUID(t)
    call = await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == tid))
    if not call:
        raise HTTPException(404, 'Call not found')
    transcript = await db.scalar(select(Transcript).where(Transcript.call_id == call_id, Transcript.tenant_id == tid))
    if transcript:
        await db.execute(TranscriptSegment.__table__.delete().where(TranscriptSegment.transcript_id == transcript.id, TranscriptSegment.tenant_id == tid))
        transcript.language = body.language
        transcript.status = 'PROCESSING'
    else:
        transcript = Transcript(tenant_id=tid, call_id=call_id, language=body.language, status='PROCESSING')
        db.add(transcript)
        await db.flush()
    for segment in body.segments:
        db.add(TranscriptSegment(tenant_id=tid, transcript_id=transcript.id, speaker=segment.speaker, text=segment.text, started_at=segment.started_at, ended_at=segment.ended_at, confidence=segment.confidence))
    await db.commit()
    await db.refresh(transcript)
    return transcript


@router.get('/{call_id}/intelligence', response_model=CallIntelligenceOut)
async def get_intelligence(call_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    result = await db.scalar(select(CallSummary).where(CallSummary.call_id == call_id, CallSummary.tenant_id == UUID(t)))
    if not result:
        raise HTTPException(404, 'Call intelligence not found')
    return result


@router.post('/{call_id}/intelligence', response_model=CallIntelligenceOut)
async def generate_intelligence(call_id: UUID, t=Depends(tenant_id), db: AsyncSession = Depends(get_db)):
    try:
        return await analyze_call(db, UUID(t), call_id)
    except IntelligenceError as exc:
        code = str(exc)
        status = 404 if code in {'CALL_NOT_FOUND', 'TRANSCRIPT_NOT_FOUND'} else 409 if code == 'TRANSCRIPT_EMPTY' else 503 if code == 'OPENAI_API_KEY_NOT_CONFIGURED' else 502
        raise HTTPException(status, code)
