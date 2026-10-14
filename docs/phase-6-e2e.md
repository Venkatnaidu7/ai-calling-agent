# Phase 6 — Realtime Voice E2E Test

This verifies the real call path:

`Phone ↔ Twilio ↔ HTTPS/WSS FastAPI ↔ OpenAI Realtime`

## 1. Configure the API

Set these values in `apps/api/.env` (never commit real secrets):

```env
APP_ENV=production
SECRET_KEY=<strong-random-secret>
PUBLIC_BASE_URL=https://<public-api-host>
TWILIO_ACCOUNT_SID=<twilio-account-sid>
TWILIO_AUTH_TOKEN=<twilio-auth-token>
OPENAI_API_KEY=<openai-api-key>
OPENAI_REALTIME_MODEL=gpt-realtime-2.1
OUTBOUND_ENABLED=true
```

`PUBLIC_BASE_URL` must be HTTPS. Twilio will connect to the corresponding WSS stream URL.

## 2. Start the stack with Podman

Start PostgreSQL, Redis, API, and web services using the repository's Podman setup. Run migrations before testing:

```bash
alembic upgrade head
```

Then verify the API health endpoint and that the API is reachable from the public hostname.

## 3. Configure Twilio

For the Twilio number assigned to the AI agent, configure the Voice webhook to:

```text
https://<public-api-host>/api/v1/voice/twilio/inbound
```

Use HTTP POST. Configure the status callback as:

```text
https://<public-api-host>/api/v1/voice/twilio/status
```

For local development, expose the API through an HTTPS tunnel and use that public HTTPS URL; plain localhost cannot receive Twilio webhooks.

## 4. Prepare an agent

1. Create an AI agent.
2. Create/publish an agent version with system instructions.
3. Assign the published agent to a Twilio phone number.
4. Confirm the number has inbound calling enabled.

## 5. Inbound E2E test

Call the Twilio number from a test phone.

Expected sequence:

1. Twilio sends `/twilio/inbound`.
2. The API creates an `IN_PROGRESS` call bound to the published agent version.
3. The API returns TwiML containing a signed WSS Media Stream URL.
4. Twilio opens the WebSocket.
5. The API connects to OpenAI Realtime.
6. The agent produces an initial greeting.
7. Caller audio is forwarded to Realtime as G.711 μ-law/PCMU.
8. Realtime audio deltas are returned to Twilio as media messages.
9. Caller interruption cancels the active response.
10. Ending the call closes the stream and records completion.

## 6. Outbound E2E test

Create a test contact with a valid phone number and the required voice consent. From the Calling Console, select the contact, assigned AI agent, and Twilio number, then choose **Call Now**.

Expected sequence:

1. API passes outbound compliance checks.
2. API creates a `QUEUED` call bound to the published agent version.
3. Twilio creates the outbound call.
4. Twilio requests `/twilio/outbound/{call_id}`.
5. API returns the signed WSS Media Stream TwiML.
6. OpenAI Realtime connects and greets the callee.
7. Two-way audio works.
8. Twilio status callbacks update the call lifecycle.

## 7. Acceptance criteria

Phase 6 E2E is accepted only when all of these pass on a real test call:

- [ ] Inbound call connects.
- [ ] AI greeting is audible.
- [ ] Caller speech reaches the model.
- [ ] AI speech reaches the caller.
- [ ] Interruption/barge-in works.
- [ ] Call completion is persisted.
- [ ] Outbound call connects.
- [ ] Published agent version is used.
- [ ] Twilio signatures are validated.
- [ ] Invalid stream token is rejected.
- [ ] No provider/API secrets are committed.

## 8. Troubleshooting

- **Twilio cannot reach webhook:** check public DNS, HTTPS certificate, firewall, and `PUBLIC_BASE_URL`.
- **WebSocket rejected:** verify the public URL, Twilio signature validation, and stream token generation.
- **No AI audio:** verify `OPENAI_API_KEY`, Realtime model configuration, and API logs.
- **Outbound blocked:** verify `OUTBOUND_ENABLED=true`, phone capabilities, agent publication, and contact voice consent.
- **Call exists but no audio:** verify Twilio Media Streams and that the WebSocket remains connected while the call is active.
