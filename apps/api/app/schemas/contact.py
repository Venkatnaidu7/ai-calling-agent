from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ContactCreate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    email: EmailStr | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    status: str = Field(default="ACTIVE", max_length=30)


class ContactUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    email: EmailStr | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    status: str | None = Field(default=None, max_length=30)


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    first_name: str | None
    last_name: str | None
    phone: str | None
    email: EmailStr | None
    tags: list
    custom_fields: dict
    status: str
