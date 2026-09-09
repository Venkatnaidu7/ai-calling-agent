# AI Voice Employee Platform

Production-oriented multi-tenant AI voice SaaS foundation.

## Stack

Next.js/TypeScript, FastAPI/Python, PostgreSQL/SQLAlchemy/Alembic, Redis/Celery, Twilio Voice Media Streams, OpenAI Realtime, Stripe, Docker and AWS/Terraform.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Then run migrations and seed local demo data:

```bash
make migrate
make seed
```

Web: http://localhost:3000  
API: http://localhost:8000  
Docs: http://localhost:8000/docs

## Live voice setup

1. Deploy the API behind HTTPS with WSS support.
2. Set `PUBLIC_BASE_URL` to the public API origin.
3. Configure `OPENAI_API_KEY`.
4. Configure `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`.
5. Point the Twilio number Voice webhook to `/api/v1/voice/twilio/inbound`.
6. Assign the number to a published agent.

## Architecture

- Multi-tenant API with tenant-scoped data access and RBAC.
- Versioned voice agents with published configuration.
- Twilio bidirectional Media Streams using μ-law/8 kHz audio.
- OpenAI Realtime bridge with server-side VAD and interruption handling.
- Authorized backend tools for appointments, knowledge and business actions.
- Contacts, consent, campaigns, call lifecycle, transcripts, summaries and analytics.
- Redis/Celery worker foundation for asynchronous jobs.
- Stripe billing webhook foundation and usage accounting.
- Docker, CI, health/readiness endpoints and AWS/Terraform deployment foundation.

## Security

Never commit provider keys, JWT secrets, database passwords or production credentials. Use environment variables or a production secret manager. Keep outbound calling disabled until consent/compliance and provider verification are complete.

## Release status

This repository is a production-oriented foundation, not a claim that every external production dependency has been live-verified. Twilio/OpenAI credentials, public WSS, AWS infrastructure, billing configuration and end-to-end provider testing are required before production launch. See `docs/IMPLEMENTATION_STATUS.md` for the detailed status and remaining hardening work.
