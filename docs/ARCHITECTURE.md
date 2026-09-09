# Architecture

PSTN → Twilio → secure WebSocket → FastAPI → OpenAI Realtime → Twilio.

The application is multi-tenant. Authenticated requests derive tenant identity from signed claims; tenant IDs supplied by clients are never trusted as authorization. Calls pin an agent version so production conversations are reproducible.

Core services:
- Next.js/TypeScript dashboard
- FastAPI/Python API
- PostgreSQL/SQLAlchemy/Alembic
- Redis/Celery workers
- Twilio Voice Media Streams
- OpenAI Realtime
- Stripe webhook foundation
- AWS/Terraform deployment foundation
