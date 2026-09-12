# Phase 8 Production Acceptance

Phase 8 (Call Intelligence + Twilio/Plivo) is code-complete and CI-validated.

## Acceptance gate

A live provider call must be executed before a deployment is declared production-live:

1. Configure Twilio and/or Plivo credentials without committing secrets.
2. Configure a stable HTTPS `PUBLIC_BASE_URL` and WSS endpoint.
3. Configure an active phone number with a published AI agent.
4. Place an inbound and outbound test call.
5. Verify provider signature validation.
6. Verify bidirectional audio through OpenAI Realtime.
7. Verify customer and assistant transcript segments are persisted.
8. Verify exactly one Call Intelligence job is created for terminal calls.
9. Verify summary, intent, outcome, sentiment and action items persist.
10. Send duplicate terminal callbacks and verify no duplicate intelligence job is created.
11. Verify campaign calls work with both supported providers when configured.
12. Record provider, call ID, timestamps, status transitions and any failure reason.

## Definition of done

- Backend tests pass.
- Frontend production build passes.
- GitHub Actions API and Web jobs pass.
- No unsupported third voice provider is introduced.
- Live provider E2E passes for every provider intended for deployment.
- Stable production HTTPS/WSS and infrastructure are verified before Phase 12 production deployment.

CI green is necessary but does not replace live provider acceptance.
