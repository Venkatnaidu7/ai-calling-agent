# Deployment

## Local

1. Copy `.env.example` to `.env`.
2. Set a strong `SECRET_KEY`.
3. Run `docker compose up --build`.
4. Run migrations.
5. Open the web dashboard.

## Production

Run API/worker/web containers behind HTTPS, use managed PostgreSQL and Redis, private subnets, encrypted object storage, centralized secrets, backups, WAF/rate limits, structured logs and metrics. Configure a public WSS endpoint for Twilio and perform dedicated staging call tests before enabling outbound campaigns.
