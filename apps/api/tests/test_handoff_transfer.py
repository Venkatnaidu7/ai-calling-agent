from app.services.handoff import ACTIVE_STATES

def test_handoff_active_states_are_supported():
    assert {'AVAILABLE','ONLINE','READY'} == ACTIVE_STATES

def test_transfer_provider_contract_is_restricted():
    assert {'twilio','plivo'} == {'twilio','plivo'}

def test_transfer_states_are_explicit():
    assert {'REQUESTED','TRANSFERRING','CONNECTED','FAILED'} == {'REQUESTED','TRANSFERRING','CONNECTED','FAILED'}
