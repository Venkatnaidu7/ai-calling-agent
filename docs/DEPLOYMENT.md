# Deployment

## Local

1. Copy `.env.example` to `.env`.
2. Set a strong `SECRET_KEY`.
3. Run `docker compose up --build`.
4. Run migrations.
5. Open the web dashboard.

## Production — DigitalOcean + Cloudflare

The production target for this repository is DigitalOcean rather than AWS.

### Infrastructure

1. Provision an Ubuntu 24.04 Droplet with `infrastructure/terraform`.
2. Restrict SSH to trusted administrator IPs.
3. Keep PostgreSQL and Redis private.
4. Put Cloudflare DNS in front of the public application hostname.
5. Terminate HTTPS with Caddy or another production reverse proxy.
6. Run the existing Docker Compose services on the Droplet.
7. Configure managed/off-host database backups and test recovery.
8. Enable monitoring and alerting.

### Application

Run:

```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose ps
```

Set `PUBLIC_BASE_URL` to the Cloudflare hostname.

The Twilio inbound webhook is:

```
https://your-domain.example/api/v1/voice/twilio/inbound
```

The Twilio media stream must be publicly reachable over WSS.

Do not expose PostgreSQL or Redis to the public internet.

### Production controls

Use strong secrets, least-privilege database access, rate limiting/WAF, backups, structured logs, metrics, alerting, staging call tests, and a documented recording/retention policy. Keep outbound calling disabled until consent, provider configuration, compliance review, and end-to-end testing are complete.
