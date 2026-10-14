# Phase 6 E2E Voice Runbook

Path: Phone <-> Twilio <-> public HTTPS/WSS FastAPI <-> OpenAI Realtime.

Required environment: PUBLIC_BASE_URL=https://<public-api-host>, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY, OPENAI_REALTIME_MODEL=gpt-realtime-2.1, OUTBOUND_ENABLED=true. Never commit secrets.

Migrations: alembic upgrade head

Twilio inbound POST: https://<public-api-host>/api/v1/voice/twilio/inbound
Twilio status POST: https://<public-api-host>/api/v1/voice/twilio/status

Prepare: create AI agent, publish a version, assign it to the Twilio number, enable inbound. For outbound, create a compliant test contact with required voice consent.

Inbound acceptance: call number; verify signed WSS opens, published version loads, AI greeting is audible, PCMU caller audio reaches Realtime, Realtime audio reaches caller, barge-in works, and completion persists.

Outbound acceptance: Call Now from Calling Console; verify compliance passes, published version is bound, Twilio connects, AI greeting is audible, two-way audio works, and status callbacks update lifecycle.

Security acceptance: Twilio signatures validated; invalid stream tokens rejected; no secrets committed.
