from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegmentCreate(BaseModel):
    speaker: str = Field(min_length=1, max_length=30)
    text: str = Field(min_length=1)
    started_at: float | None = None
    ended_at: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class TranscriptCreate(BaseModel):
    language: str | None = Field(default=None, max_length=10)
    segments: list[TranscriptSegmentCreate] = Field(min_length=1, max_length=5000)


class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    call_id: UUID
    language: str | None
    status: str


class CallIntelligenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    call_id: UUID
    summary: str
    intent: str | None
    outcome: str | None
    sentiment: str | None
    follow_up_required: bool
    next_action: str | None
