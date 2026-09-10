import json

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Call, CallSummary, Transcript, TranscriptSegment


class IntelligenceError(RuntimeError):
    pass


def build_transcript_text(segments: list[TranscriptSegment]) -> str:
    return "\n".join(f"{s.speaker}: {s.text}" for s in segments if s.text)


async def analyze_call(db: AsyncSession, tenant_id, call_id):
    settings = get_settings()
    call = await db.scalar(select(Call).where(Call.id == call_id, Call.tenant_id == tenant_id))
    if not call:
        raise IntelligenceError("CALL_NOT_FOUND")

    transcript = await db.scalar(select(Transcript).where(Transcript.call_id == call_id, Transcript.tenant_id == tenant_id))
    if not transcript:
        raise IntelligenceError("TRANSCRIPT_NOT_FOUND")
    segments = (await db.scalars(select(TranscriptSegment).where(TranscriptSegment.transcript_id == transcript.id, TranscriptSegment.tenant_id == tenant_id).order_by(TranscriptSegment.started_at.asc().nulls_last(), TranscriptSegment.id.asc()))).all()
    text = build_transcript_text(segments)
    if not text.strip():
        raise IntelligenceError("TRANSCRIPT_EMPTY")
    if not settings.openai_api_key:
        raise IntelligenceError("OPENAI_API_KEY_NOT_CONFIGURED")

    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "intent": {"type": ["string", "null"]},
            "outcome": {"type": ["string", "null"]},
            "sentiment": {"type": ["string", "null"]},
            "follow_up_required": {"type": "boolean"},
            "next_action": {"type": ["string", "null"]},
        },
        "required": ["summary", "intent", "outcome", "sentiment", "follow_up_required", "next_action"],
        "additionalProperties": False,
    }
    payload = {
        "model": settings.openai_realtime_model,
        "input": [
            {"role": "system", "content": "Analyze a customer phone call transcript. Return concise, factual call intelligence. Do not invent facts."},
            {"role": "user", "content": text},
        ],
        "text": {"format": {"type": "json_schema", "name": "call_intelligence", "strict": True, "schema": schema}},
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
    if response.status_code >= 400:
        raise IntelligenceError(f"OPENAI_ERROR_{response.status_code}")
    data = response.json()
    output_text = data.get("output_text")
    if not output_text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    output_text = content["text"]
                    break
            if output_text:
                break
    if not output_text:
        raise IntelligenceError("OPENAI_EMPTY_RESPONSE")
    result = json.loads(output_text)
    summary = await db.scalar(select(CallSummary).where(CallSummary.call_id == call_id, CallSummary.tenant_id == tenant_id))
    if summary:
        for key, value in result.items():
            setattr(summary, key, value)
    else:
        summary = CallSummary(tenant_id=tenant_id, call_id=call_id, **result)
        db.add(summary)
    transcript.status = "COMPLETED"
    await db.commit()
    await db.refresh(summary)
    return summary
