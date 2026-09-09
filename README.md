# AI Calling Agent

> **Production-oriented AI voice calling platform for inbound and outbound phone conversations.**
>
> Built with FastAPI, Next.js, PostgreSQL, Redis/Celery, Twilio Voice Media Streams, OpenAI Realtime, Stripe, Docker, and AWS/Terraform foundations.

[![CI](https://github.com/Venkatnaidu7/ai-calling-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Venkatnaidu7/ai-calling-agent/actions/workflows/ci.yml)

## ⚡ Fastest Windows Setup

This is the recommended path for getting the platform running locally on **Windows 10/11**.

### What you need

Install:

- **Git**
- **Docker Desktop** with Docker Compose

You do **not** need to install PostgreSQL, Redis, Python, Node.js, or npm separately for the Docker-based setup.

Verify from PowerShell:

```powershell
git --version
docker --version
docker compose version
```

If those commands work, continue.

### 1. Clone the repository

```powershell
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
```

### 2. Create the environment file

```powershell
Copy-Item .env.example .env
```

Generate a secure application secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `.env` and replace:

```env
SECRET_KEY=replace-with-a-long-random-secret
```

with the generated value.

For the **first local boot**, OpenAI, Twilio, and Stripe credentials can remain empty.

### 3. Start the complete local stack

```powershell
docker compose up --build -d
```

This starts:

- Next.js web dashboard
- FastAPI API
- PostgreSQL
- Redis
- Celery worker

Check the containers:

```powershell
docker compose ps
```

### 4. Run database migrations

```powershell
docker compose exec api alembic upgrade head
```

### 5. Verify the installation

Open these in your browser:

| Component | Address |
|---|---|
| **Web dashboard** | http://localhost:3000 |
| **API** | http://localhost:8000 |
| **API docs** | http://localhost:8000/docs |
| **Health** | http://localhost:8000/health |
| **Readiness** | http://localhost:8000/ready |

Or verify from PowerShell:

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/ready
```

### ✅ Installation complete

If the dashboard opens and `/health` returns successfully, the platform is running locally.

---

# 🚀 Daily Windows Commands

After the initial installation, you normally only need:

### Start

```powershell
docker compose up -d
```

### Start and rebuild after code changes

```powershell
docker compose up --build -d
```

### View running services

```powershell
docker compose ps
```

### View API logs

```powershell
docker compose logs -f api
```

### View all logs

```powershell
docker compose logs -f
```

### Run migrations

```powershell
docker compose exec api alembic upgrade head
```

### Run backend tests

```powershell
docker compose exec api pytest -q
```

### Stop services

```powershell
docker compose down
```

### Completely reset local data

```powershell
docker compose down -v
docker compose up --build -d
docker compose exec api alembic upgrade head
```

> ⚠️ `docker compose down -v` deletes the local PostgreSQL and Redis volumes. Use it only when you intentionally want a clean local environment.

---

# 📞 Enable Real AI Phone Calls

The local application can boot without provider credentials. Real phone conversations require **OpenAI Realtime + Twilio + a public HTTPS/WSS endpoint**.

## 1. Configure OpenAI

Edit `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_REALTIME_MODEL=gpt-realtime
```

## 2. Configure Twilio

```env
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

## 3. Configure the public API URL

For local phone testing, your API must be reachable from the internet and support HTTPS/WSS.

```env
PUBLIC_BASE_URL=https://your-public-host
```

Do not use `http://localhost:8000` for the Twilio webhook.

## 4. Configure the Twilio Voice webhook

Set the Twilio phone number's incoming Voice webhook to:

```text
https://your-public-host/api/v1/voice/twilio/inbound
```

The application validates the Twilio request, resolves the phone number to the configured tenant/agent, creates the call, and starts the realtime voice stream.

## 5. Publish an AI agent

Before a phone number can route to an agent, configure the agent, create its version, and publish the version.

## 6. Restart the voice services

```powershell
docker compose up -d --build api celery
```

### Outbound calling safety

Keep this disabled while configuring and testing the platform:

```env
OUTBOUND_ENABLED=false
```

Only enable outbound calling after consent, compliance, phone-number configuration, provider configuration, and end-to-end testing have been verified.

---

# 🔐 Environment Configuration

The full template is available in `.env.example`.

| Variable | Purpose | Local setup |
|---|---|---|
| `APP_ENV` | Application environment | `development` |
| `SECRET_KEY` | JWT/application signing secret | **Required** |
| `DATABASE_URL` | PostgreSQL connection | Docker default |
| `REDIS_URL` | Redis connection | Docker default |
| `PUBLIC_BASE_URL` | Public API origin | Required for live calls |
| `FRONTEND_URL` | Web application origin | `http://localhost:3000` |
| `CORS_ORIGINS` | Allowed browser origins | `http://localhost:3000` |
| `OPENAI_API_KEY` | OpenAI Realtime authentication | Required for AI calls |
| `OPENAI_REALTIME_MODEL` | Realtime voice model | `gpt-realtime` |
| `TWILIO_ACCOUNT_SID` | Twilio account | Required for phone calls |
| `TWILIO_AUTH_TOKEN` | Twilio authentication | Required for phone calls |
| `STRIPE_SECRET_KEY` | Stripe API | Required for billing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | Required for billing webhooks |
| `AWS_REGION` | AWS region | Example: `ap-south-1` |
| `S3_BUCKET` | Object storage bucket | Production configuration |
| `OUTBOUND_ENABLED` | Outbound calling gate | `false` |
| `RECORDING_MODE` | Recording policy | `DISABLED` |

### Security rules

**Never commit `.env`, API keys, access tokens, private keys, or production secrets to GitHub.**

Use a managed secret store for production deployments.

---

# 🏗️ Architecture

```text
                         ┌───────────────────────┐
                         │    Next.js Dashboard  │
                         │       TypeScript      │
                         └───────────┬───────────┘
                                     │ HTTPS
                                     ▼
                         ┌───────────────────────┐
                         │        FastAPI        │
                         │ Auth / API / Voice    │
                         └───────┬───────┬───────┘
                                 │       │
                  ┌──────────────┘       └──────────────┐
                  ▼                                     ▼
        ┌──────────────────┐                 ┌──────────────────┐
        │   PostgreSQL     │                 │ Redis + Celery   │
        │ Tenant data      │                 │ Async workloads  │
        └──────────────────┘                 └──────────────────┘

                           PHONE CALL
                               │
                               ▼
                         ┌────────────┐
                         │   Twilio   │
                         │ Voice/Media│
                         └─────┬──────┘
                               │ WebSocket
                               ▼
                       ┌─────────────────┐
                       │ FastAPI Voice   │
                       │ Gateway         │
                       └────────┬────────┘
                                │ Realtime WS
                                ▼
                       ┌─────────────────┐
                       │ OpenAI Realtime │
                       │ Voice Runtime   │
                       └─────────────────┘
```

---

# 🧩 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js + TypeScript |
| API | FastAPI + Python |
| Database | PostgreSQL + SQLAlchemy |
| Migrations | Alembic |
| Cache / Queue | Redis + Celery |
| Telephony | Twilio Voice Media Streams |
| Realtime AI | OpenAI Realtime |
| Billing | Stripe |
| Containers | Docker + Docker Compose |
| Cloud foundation | AWS + Terraform |
| CI | GitHub Actions |

---

# 📁 Project Structure

```text
ai-calling-agent/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/             # REST and voice routes
│   │   │   ├── core/            # Configuration and security
│   │   │   ├── db/              # Database setup
│   │   │   ├── models/          # SQLAlchemy models
│   │   │   ├── providers/       # Twilio/OpenAI providers
│   │   │   ├── services/        # Business logic
│   │   │   └── workers/         # Celery workloads
│   │   ├── alembic/             # Database migrations
│   │   ├── tests/               # Backend tests
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── web/                     # Next.js dashboard
├── docs/                        # Architecture/security/deployment docs
├── infrastructure/terraform/   # AWS/Terraform foundation
├── scripts/                     # Utility scripts
├── .github/workflows/           # CI workflows
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# 🧪 Testing

Run the backend test suite inside Docker:

```powershell
docker compose exec api pytest -q
```

Check migration state:

```powershell
docker compose exec api alembic current
```

Apply all migrations:

```powershell
docker compose exec api alembic upgrade head
```

Check the API:

```powershell
curl.exe http://localhost:8000/health
```

---

# 🛠️ Windows Troubleshooting

## Docker command not found

Install and start Docker Desktop, then reopen PowerShell.

```powershell
docker --version
docker compose version
```

## Port 3000 is already in use

```powershell
netstat -ano | findstr :3000
```

## Port 8000 is already in use

```powershell
netstat -ano | findstr :8000
```

Stop the conflicting process or change the published port in `docker-compose.yml`.

## API container is restarting

```powershell
docker compose logs --tail=200 api
```

## PostgreSQL is unavailable

```powershell
docker compose ps postgres
docker compose logs --tail=100 postgres
```

Then restart:

```powershell
docker compose restart postgres api
```

## Redis is unavailable

```powershell
docker compose ps redis
docker compose logs --tail=100 redis
```

Then:

```powershell
docker compose restart redis celery api
```

## Need a completely clean installation

```powershell
docker compose down -v
docker compose up --build -d
docker compose exec api alembic upgrade head
```

---

# 🔒 Security & Compliance

The platform includes a production-oriented foundation for:

- Multi-tenant data isolation
- Authentication and RBAC
- Agent/version management
- API key authentication
- Audit logging
- Twilio signature validation
- Consent and compliance records
- Outbound calling safety controls
- Usage accounting
- Billing webhook foundation
- Request IDs and health/readiness endpoints

Before production launch, additionally configure and validate:

- HTTPS/WSS
- Production secret management
- Database backups and recovery
- Data retention policies
- Monitoring and alerting
- Rate limiting at the distributed edge
- Provider credentials and webhooks
- Calling consent and applicable telecommunications laws
- Recording/retention policies
- Production AWS infrastructure
- End-to-end voice testing

---

# ☁️ Production Deployment

The repository contains an AWS/Terraform foundation and deployment documentation.

Production deployment should **not** be treated as `docker compose up` on a public server. A proper deployment should include secure networking, secret management, TLS, persistent PostgreSQL, Redis strategy, scalable workers, observability, backups, deployment automation, and provider webhook configuration.

See:

- `docs/DEPLOYMENT.md`
- `docs/SECURITY.md`
- `docs/ARCHITECTURE.md`
- `docs/TELEPHONY.md`
- `docs/AI_RUNTIME.md`
- `docs/COMPLIANCE.md`
- `docs/TESTING.md`
- `docs/IMPLEMENTATION_STATUS.md`

---

# 📌 Current Release Status

This repository is a **production-oriented platform foundation**, not a declaration that every production requirement has been completed.

Core areas include the API, multi-tenancy, RBAC, versioned agents, calls, contacts, knowledge, appointments, campaigns, human-agent records, Twilio voice integration, OpenAI Realtime integration, PostgreSQL/Alembic, Redis/Celery, dashboard, billing foundation, CI, and AWS/Terraform foundation.

Remaining production work includes provider credential validation, public WSS infrastructure, full end-to-end testing, production AWS configuration, complete outbound orchestration, remaining integrations, operational hardening, monitoring, retention, and compliance verification.

The authoritative implementation checklist is:

```text
docs/IMPLEMENTATION_STATUS.md
```

---

# 🤝 Development Workflow

Recommended workflow:

```powershell
# Get the latest code
git pull origin main

# Rebuild local services
docker compose up --build -d

# Apply migrations
docker compose exec api alembic upgrade head

# Run tests
docker compose exec api pytest -q

# Inspect status
docker compose ps
```

Before pushing changes:

1. Run the backend tests.
2. Verify migrations.
3. Check API health/readiness.
4. Test affected endpoints.
5. Never commit secrets.
6. Review the GitHub Actions result.

---

# 📄 License

A project license should be added before public distribution.

---

## 🚀 Quick Reference

For a fresh Windows machine:

```powershell
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Put the generated value into .env as SECRET_KEY

docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose ps
```

Then open:

```text
http://localhost:3000
http://localhost:8000/docs
http://localhost:8000/health
```

**Local platform setup is complete when the services are healthy and the API health endpoint responds successfully.**
