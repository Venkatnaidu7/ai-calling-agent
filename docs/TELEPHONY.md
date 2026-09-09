# Telephony

Configure the Twilio number Voice webhook to `POST /api/v1/voice/twilio/inbound` and status callback to `POST /api/v1/voice/twilio/status`.

The inbound endpoint resolves the E.164 number to the tenant and published agent, creates a call, and returns Twilio `<Connect><Stream>` for a bidirectional Media Stream.

Twilio sends base64 G.711 μ-law/8 kHz audio. The realtime bridge uses OpenAI Realtime PCMU so the telephone audio path stays compatible.

Production requires HTTPS/WSS, Twilio signature validation, provider credentials and live staging verification.
