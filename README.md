# AI Calling Agent

Production-oriented, multi-tenant AI phone calling platform for inbound and outbound voice conversations.

> **Goal:** get the platform running locally as fast as possible, then connect Twilio + OpenAI for real phone calls.

## ⚡ Fastest Windows Setup

### 1. Install the prerequisites

You only need these for the local Docker setup:

- **Git**
- **Docker Desktop** with Docker Compose

Verify in PowerShell:

```powershell
git --version
docker --version
docker compose version
```

If all three commands work, continue.

### 2. Clone the repository

```powershell
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
```

### 3. Create your environment file

```powershell
Copy-Item .env.example .env
```

For the **first local boot**, you can leave the provider API keys empty. The local API, PostgreSQL, Redis and web dashboard can be started before connecting live voice providers.

### 4. Start everything

```powershell
docker compose up --build
```

Keep this terminal running.

### 5. Run database migrations

Open a **second PowerShell** in the project directory:

```powershell
docker compose exec api alembic upgrade head
```

### 6. Open the application

| Service | URL |
|---|---|
| Web dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API documentation | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

If `/health` returns successfully, the backend is running.

---

## 🚀 One-Command Windows Start

After cloning and creating `.env`, you can use:

```powershell
docker compose up --build -d
```

Then:

```powershell
docker compose exec api alembic upgrade head
```

Check the containers:

```powershell
docker compose ps
```

View logs:

```powershell
docker compose logs -f api
```

Stop the platform:

```powershell
docker compose down
```

Stop and remove local database/Redis volumes too:

```powershell
docker compose down -v
```

> `docker compose down -v` deletes local PostgreSQL data. Do not use it if you need to preserve your local data.

---

## 🧩 Technology Stack

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + Python
- **Database:** PostgreSQL + SQLAlchemy + Alembic
- **Queue/cache:** Redis + Celery
- **Telephony:** Twilio Voice Media Streams
- **Realtime AI:** OpenAI Realtime
- **Billing:** Stripe
- **Containers:** Docker + Docker Compose
- **Cloud foundation:** AWS + Terraform
- **CI:** GitHub Actions

---

## 🏗️ Architecture

```text
                    ┌──────────────────────┐
                    │   Web Dashboard      │
                    │   Next.js / TS       │
                    └──────────┬───────────┘
                               │ HTTPS
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │ Auth / Tenants / API │
                    └──────┬───────┬───────┘
                           │       │
                ┌──────────┘       └──────────┐
                ▼                             ▼
        ┌───────────────┐              ┌──────────────┐
        │ PostgreSQL    │              │ Redis/Celery │
        │ Application DB│              │ Async Jobs   │
        └───────────────┘              └──────────────┘

Twilio Phone
     │
     │ Voice + Media Stream
     ▼
┌───────────────┐       WebSocket       ┌─────────────────┐
│ Twilio        │ ◄───────────────────► │ FastAPI Voice   │
└───────────────┘                       │ Gateway         │
                                        └────────┬────────┘
                                                 │ Realtime WS
                                                 ▼
                                        ┌─────────────────┐
                                        │ OpenAI Realtime │
                                        │ Voice Model     │
                                        └─────────────────┘
```

---

## ☎️ Enable Real AI Phone Calls

The local application does **not** need Twilio/OpenAI credentials to boot. Add them only when you are ready to test real calls.

### 1. Configure `.env`

Set:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_REALTIME_MODEL=gpt-realtime

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token

PUBLIC_BASE_URL=https://your-public-api-domain

OUTBOUND_ENABLED=false
RECORDING_MODE=DISABLED
```

Keep `OUTBOUND_ENABLED=false` until consent, compliance and provider configuration are verified.

### 2. Restart the API

```powershell
docker compose up -d --build api celery
```

### 3. Expose the local API publicly

Twilio needs a public **HTTPS** endpoint and the voice stream needs **WSS** support. For local development, use a secure tunneling solution that provides HTTPS/WSS and set `PUBLIC_BASE_URL` to that public origin.

Example target:

```text
https://your-public-host
```

### 4. Configure Twilio

Set the phone number's incoming Voice webhook to:

```text
https://your-public-host/api/v1/voice/twilio/inbound
```

The application then resolves the phone number to the configured tenant/agent and starts the realtime voice flow.

### 5. Publish an agent

Create/configure an agent, create its version, and publish the version before expecting a phone number to route to it.

---

## 🔐 Environment Variables

The complete environment template is in `.env.example`.

Important values:

| Variable | Purpose | Local first boot |
|---|---|---|
| `SECRET_KEY` | JWT/application signing secret | **Set a strong random value** |
| `DATABASE_URL` | PostgreSQL connection | Already configured for Docker |
| `REDIS_URL` | Redis connection | Already configured for Docker |
| `OPENAI_API_KEY` | Realtime AI | Optional until voice testing |
| `OPENAI_REALTIME_MODEL` | Realtime model | `gpt-realtime` |
| `TWILIO_ACCOUNT_SID` | Twilio account | Optional until voice testing |
| `TWILIO_AUTH_TOKEN` | Twilio authentication | Optional until voice testing |
| `PUBLIC_BASE_URL` | Public API origin | Required for live Twilio calls |
| `STRIPE_SECRET_KEY` | Stripe billing | Optional until billing testing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | Optional until billing testing |
| `OUTBOUND_ENABLED` | Outbound calling safety gate | `false` |
| `RECORDING_MODE` | Call recording mode | `DISABLED` |

Generate a strong secret on Windows with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the result into `.env` as `SECRET_KEY`.

**Never commit `.env` or production credentials to GitHub.**

---

## 🧪 Development & Testing

Run Python tests inside the API container:

```powershell
docker compose exec api pytest -q
```

Check the API health endpoint:

```powershell
curl.exe http://localhost:8000/health
```

Check readiness:

```powershell
curl.exe http://localhost:8000/ready
```

Run migrations:

```powershell
docker compose exec api alembic upgrade head
```

Check migration status:

```powershell
docker compose exec api alembic current
```

---

## 📁 Project Structure

```text
ai-calling-agent/
├── apps/
│   ├── api/                  # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/          # REST + voice routes
│   │   │   ├── core/         # Config + security
│   │   │   ├── db/           # Database session/base
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   ├── providers/    # Twilio/OpenAI integrations
│   │   │   ├── services/     # Business logic
│   │   │   └── workers/      # Celery jobs
│   │   ├── alembic/          # Database migrations
│   │   └── tests/            # Backend tests
│   └── web/                  # Next.js dashboard
├── docs/                     # Architecture, security, deployment, testing
├── infrastructure/terraform/ # AWS/Terraform foundation
├── scripts/                  # Utility scripts
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🛠️ Common Windows Fixes

### Docker is not recognized

Install and start Docker Desktop, then reopen PowerShell:

```powershell
docker --version
docker compose version
```

### Port 3000 or 8000 is already in use

Find the process using the port:

```powershell
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

Stop the conflicting process or change the exposed port in `docker-compose.yml`.

### API container keeps restarting

View the error:

```powershell
docker compose logs --tail=200 api
```

### Database connection error

Make sure PostgreSQL is running:

```powershell
docker compose ps postgres
```

Then restart:

```powershell
docker compose restart postgres api
```

### Fresh local reset

```powershell
docker compose down -v
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Again, `-v` removes local database data.

---

## 🔒 Security

This platform is designed as a production-oriented foundation with tenant isolation, RBAC, authentication, audit logging, provider signature validation, compliance controls and usage accounting.

Before production:

- Use a strong production `SECRET_KEY`.
- Store secrets in a proper secret manager.
- Enable HTTPS/WSS everywhere.
- Validate Twilio signatures.
- Keep tenant data isolated.
- Verify call consent and applicable calling laws.
- Keep outbound calling disabled until compliance is configured.
- Configure production database backups and retention.
- Configure monitoring, alerting and log retention.
- Perform end-to-end Twilio/OpenAI testing with production-like credentials.

---

## 📊 Current Release Status

The repository contains the core production-oriented platform foundation, including the API, tenant/RBAC model, versioned agents, voice gateway, Twilio/OpenAI realtime integration, database migrations, Redis/Celery foundation, dashboard, billing foundation, CI and AWS/Terraform foundation.

**It is not yet a claim of full production readiness.** Live provider credentials, public WSS infrastructure, production AWS configuration, billing setup, compliance verification, end-to-end testing and remaining hardening work are required before a production launch.

See:

- `docs/IMPLEMENTATION_STATUS.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/TELEPHONY.md`
- `docs/AI_RUNTIME.md`
- `docs/DEPLOYMENT.md`
- `docs/COMPLIANCE.md`
- `docs/TESTING.md`

---

## 🆘 Recommended First Run

If you are setting this up on a Windows PC for the first time, follow exactly these commands:

```powershell
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value into `.env` as `SECRET_KEY`, then run:

```powershell
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose ps
```

Finally open:

```text
http://localhost:3000
http://localhost:8000/docs
http://localhost:8000/health
```

**Once these three endpoints work, the platform is successfully running locally.**

---

## License

Add the project's license before public distribution.
