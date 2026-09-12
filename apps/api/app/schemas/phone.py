from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhoneNumberCreate(BaseModel):
    e164: str = Field(min_length=7, max_length=32, pattern=r"^\+[1-9]\d{6,30}$")
    provider: str = Field(default="twilio", min_length=2, max_length=30)
    provider_number_id: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=4)
    agent_id: UUID | None = None
    inbound_enabled: bool = True
    outbound_enabled: bool = True


class PhoneNumberUpdate(BaseModel):
    agent_id: UUID | None = None
    inbound_enabled: bool | None = None
    outbound_enabled: bool | None = None
    active: bool | None = None


class PhoneNumberProvision(BaseModel):
    phone_number: str = Field(min_length=7, max_length=32, pattern=r"^\+[1-9]\d{6,30}$")
    agent_id: UUID | None = None
    country: str | None = Field(default=None, min_length=2, max_length=4)
    inbound_enabled: bool = True
    outbound_enabled: bool = True


class PlivoNumberAttach(BaseModel):
    phone_number: str = Field(min_length=7, max_length=32, pattern=r"^\+[1-9]\d{6,30}$")
    agent_id: UUID | None = None
    country: str | None = Field(default=None, min_length=2, max_length=4)
    inbound_enabled: bool = True
    outbound_enabled: bool = True


class PhoneNumberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    e164: str
    provider: str
    provider_number_id: str | None
    country: str | None
    agent_id: str | None
    inbound_enabled: bool
    outbound_enabled: bool
    active: bool
