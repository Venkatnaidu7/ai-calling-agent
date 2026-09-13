# Production deployment

This directory contains the production deployment baseline for the AI calling platform.

## Runtime

- API: FastAPI/Uvicorn on port 8000 inside the service network.
- Worker: Celery worker on the `voice` queue.
- PostgreSQL and Redis are private services; do not expose them publicly.
- Frontend is served separately over HTTPS.
- Public voice callbacks and WebSocket endpoints require stable HTTPS/WSS.
- Telephony providers supported by this application are Twilio and Plivo only.

## Required production configuration

Set these through the deployment secret manager, never in git:

- `APP_ENV=production`
- `SECRET_KEY` (random, unique, >=32 characters)
- `DATABASE_URL`
- `REDIS_URL`
- `REDIS_PASSWORD`
- `PUBLIC_BASE_URL` (stable HTTPS URL)
- `FRONTEND_URL` (stable HTTPS URL)
- `CORS_ORIGINS` and `TRUSTED_HOSTS` restricted to production domains
- Twilio credentials and/or Plivo credentials as required
- `OPENAI_API_KEY`
- `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` when billing is enabled
- AWS/S3 settings when object storage is enabled

## Release order

1. Build immutable API and web images.
2. Provision private PostgreSQL/Redis and networking.
3. Inject secrets.
4. Run `alembic upgrade head` as a release migration job.
5. Deploy API and worker replicas.
6. Verify `/health`, `/liveness`, and `/ready`.
7. Deploy frontend over HTTPS.
8. Configure Twilio/Plivo callbacks to stable HTTPS/WSS endpoints.
9. Configure Stripe webhook delivery to `/api/v1/billing/stripe/webhook`.
10. Run authenticated API, billing, inbound voice and handoff smoke tests.
11. Enable outbound calling only after consent, DNC and billing controls are verified.

## Security

Never commit `.env.production` or real provider credentials. Keep PostgreSQL and Redis private, terminate TLS at the public edge, rotate secrets, and keep recording disabled unless the tenant's lawful policy permits it.

Never use the Cloudflare Quick Tunnel for production traffic; it is suitable only for temporary development testing.
