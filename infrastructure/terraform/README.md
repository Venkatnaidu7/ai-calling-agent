# DigitalOcean deployment foundation

This Terraform configuration provisions the base compute host for the AI Calling Agent on DigitalOcean. Application deployment remains Docker Compose based.

## Provision

```bash
terraform init
cp terraform.tfvars.example terraform.tfvars
terraform plan
terraform apply
```

Never commit the real `terraform.tfvars` file.

## Application

Install Docker Engine and Docker Compose on Ubuntu, then clone the repository and run:

```bash
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose ps
```

Set production values in `.env`, including `SECRET_KEY`, `PUBLIC_BASE_URL`, OpenAI, Twilio and Stripe credentials.

## Cloudflare

Create a proxied DNS record for the application hostname pointing to the Droplet IP. Terminate HTTPS with Caddy or another production reverse proxy on the Droplet and use the same hostname for `PUBLIC_BASE_URL`.

Twilio inbound webhook:

```text
https://voice.example.com/api/v1/voice/twilio/inbound
```

The Twilio media stream must be reachable over WSS. Do not expose PostgreSQL or Redis publicly in production.

## Hardening

- Restrict SSH to trusted administrator IPs.
- Enable Droplet backups and monitoring.
- Keep secrets out of Git.
- Configure database backups and recovery tests.
- Add monitoring and alerting.
- Keep outbound calling disabled until consent and end-to-end testing are complete.
