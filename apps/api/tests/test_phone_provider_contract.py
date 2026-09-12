import pytest
from fastapi import HTTPException

from app.api.phone_numbers import _provider
from app.schemas.phone import PhoneNumberProvision, PlivoNumberAttach


def test_provider_contract_accepts_only_twilio_and_plivo():
    assert _provider("twilio") == "twilio"
    assert _provider(" PLIVO ") == "plivo"
    with pytest.raises(HTTPException) as exc:
        _provider("telnyx")
    assert exc.value.status_code == 400


def test_phone_provision_defaults_to_twilio():
    payload = PhoneNumberProvision(phone_number="+14155551234")
    assert payload.provider == "twilio"
    assert payload.inbound_enabled is True
    assert payload.outbound_enabled is True


def test_plivo_attach_schema_requires_e164():
    payload = PlivoNumberAttach(phone_number="+919876543210")
    assert payload.phone_number == "+919876543210"
    assert payload.inbound_enabled is True
    assert payload.outbound_enabled is True

    with pytest.raises(ValueError):
        PlivoNumberAttach(phone_number="919876543210")
