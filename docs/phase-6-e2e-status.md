# Phase 6 E2E status

Automated CI verifies the Realtime bridge contract. Real-phone acceptance requires deployment with real Twilio/OpenAI credentials and a public HTTPS/WSS endpoint.

Acceptance path: inbound and outbound call -> Twilio Media Stream -> Realtime PCMU audio -> AI response -> Twilio audio -> persisted call completion.
