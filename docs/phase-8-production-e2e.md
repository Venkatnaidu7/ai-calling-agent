# Phase 8 — Twilio + Plivo Production E2E Runbook

## Scope

Phase 8 supports exactly two voice providers:

- Twilio
- Plivo

No additional voice provider is part of this architecture.

The production call path is:

`Provider phone number → HTTPS webhook → FastAPI → Call record → WSS media stream → OpenAI Realtime → provider audio → Call Intelligence`

## Preconditions

- `PUBLIC_BASE_URL` is a stable public HTTPS origin.
- `OPENAI_API_KEY` is configured.
- The selected provider credentials are configured.
- PostgreSQL and Redis are healthy.
- API and Celery worker are running.
- At least one AI agent has a published version.
- The provider number is attached to the correct tenant and AI agent.
- Inbound/outbound capability flags match the intended test.

## Plivo setup

Create or use a Plivo Voice Application whose answer URL is:

`POST /api/v1/voice/plivo/inbound`

For outbound calls, the application/call flow uses:

`POST /api/v1/voice/plivo/outbound/{call_id}`

Configure callbacks:

- Ring: `POST /api/v1/voice/plivo/ring`
- Hangup/status: `POST /api/v1/voice/plivo/status`
- Stream status: `POST /api/v1/voice/plivo/stream-status`

The application must be associated with the Plivo number. The number must also exist in the platform database with provider `plivo`.

## Twilio setup

Configure the Twilio number voice webhook to:

`POST /api/v1/voice/twilio/inbound`

Configure status callbacks to:

`POST /api/v1/voice/twilio/status`

For outbound calls the platform generates the call and uses:

`POST /api/v1/voice/twilio/outbound/{call_id}`

## Inbound E2E test

1. Call the configured provider number from an allowed test phone.
2. Confirm the provider reaches the HTTPS inbound webhook.
3. Confirm a `Call` row is created for the correct tenant.
4. Confirm the call is bound to an active AI agent and published version.
5. Confirm the provider opens the WSS media stream.
6. Confirm OpenAI Realtime connects successfully.
7. Confirm the AI greeting is played.
8. Speak a short sentence and confirm customer transcription is persisted.
9. Confirm the assistant response audio is returned to the caller.
10. Hang up and confirm the provider status callback marks the call terminal.
11. Confirm a Call Intelligence job is created exactly once for the terminal call.

## Outbound E2E test

1. Create an allowed contact with a verified test phone number.
2. Ensure the selected platform number has outbound enabled.
3. Start an outbound call from Calling Console.
4. Confirm the call enters `QUEUED`/`RINGING` and receives the provider ID.
5. Answer the call.
6. Confirm the provider answer webhook opens the realtime stream.
7. Confirm AI greeting, two-way audio, interruption handling, and transcription.
8. Hang up.
9. Confirm terminal status and duration are persisted.
10. Confirm Call Intelligence is queued once.

## Failure tests

### Missing OpenAI key

The media stream must fail closed rather than creating an unauthenticated realtime session.

### Invalid stream token

A WSS connection with an invalid call token must be rejected with WebSocket policy code `1008`.

### Invalid provider signature

A forged provider webhook must be rejected with HTTP `403` when provider authentication is configured.

### Disabled capability

A number with inbound or outbound disabled must reject the corresponding operation before starting a call.

### Unpublished agent

A provider webhook for a number without an active published agent must fail safely and must not start an AI session.

### Duplicate callbacks

Provider callbacks may be delivered more than once. Replaying the same terminal callback must not create duplicate Call Intelligence jobs or regress a terminal call back to a non-terminal state.

## Acceptance criteria

Phase 8 is not considered production-complete until both providers pass the live E2E checklist and the failure tests above, using public HTTPS/WSS infrastructure.

CI success alone is not sufficient evidence of provider interoperability.
