from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone_number_id: UUID
    schedule: dict = Field(default_factory=dict)
    retry_policy: dict = Field(default_factory=lambda: {"max_attempts": 3, "backoff_minutes": 60})
    concurrency: int = Field(default=1, ge=1, le=50)


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone_number_id: UUID | None = None
    schedule: dict | None = None
    retry_policy: dict | None = None
    concurrency: int | None = Field(default=None, ge=1, le=50)


class CampaignContactAdd(BaseModel):
    contact_ids: list[UUID] = Field(min_length=1, max_length=1000)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    status: str
    schedule: dict
    retry_policy: dict
    concurrency: int


class CampaignContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    campaign_id: UUID
    contact_id: UUID
    state: str
    attempts: int


class CampaignStats(BaseModel):
    total: int
    queued: int
    in_progress: int
    completed: int
    failed: int
    retryable: int
