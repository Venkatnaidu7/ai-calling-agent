# AI Calling Agent

> Production-oriented, multi-tenant AI phone calling platform for inbound and outbound voice conversations.

[![CI](https://github.com/Venkatnaidu7/ai-calling-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Venkatnaidu7/ai-calling-agent/actions/workflows/ci.yml)

Built with **FastAPI, Next.js, PostgreSQL, Redis/Celery, Twilio Voice Media Streams, OpenAI Realtime, Stripe, Docker/Podman, and AWS/Terraform foundations**.

---

# ⚡ Fastest Installation — Windows, Linux & macOS

The recommended local installation uses containers. You do **not** need to install PostgreSQL, Redis, Node.js, or npm separately.

## Prerequisites

| Platform | Required |
|---|---|
| Windows 10/11 | Git + Docker Desktop |
| macOS | Git + Docker Desktop |
| Linux + Docker | Git + Docker Engine + Docker Compose plugin |
| Linux + Podman | Git + Podman + Podman Compose |

Verify Docker when using Docker:

```bash
git --version
docker --version
docker compose version
```

Verify Podman when using Podman:

```bash
git --version
podman --version
podman compose version
```

> On Windows, run the commands below in PowerShell. On Linux/macOS, run them in Terminal.

---

# 🪟 Windows Setup

### 1. Clone

```powershell
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
```

### 2. Create `.env`

```powershell
Copy-Item .env.example .env
```

Generate a secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value in `.env`:

```env
SECRET_KEY=your-generated-secret
```

If Python is not installed on Windows, generate the secret with any trusted password/secret generator and place it in `.env`.

### 3. Start the platform

```powershell
docker compose up --build -d
```

### 4. Run migrations

```powershell
docker compose exec api alembic upgrade head
```

### 5. Verify

```powershell
docker compose ps
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/ready
```

Open:

- http://localhost:3000 — dashboard
- http://localhost:8000/docs — API documentation
- http://localhost:8000/health — health

---

# 🐧 Linux Setup — Docker

### 1. Install Docker

Install Git, Docker Engine, and the Docker Compose plugin using your Linux distribution's official package instructions.

Verify:

```bash
git --version
docker --version
docker compose version
```

If your user needs permission to run Docker without `sudo`, configure the Docker group according to your distribution's Docker documentation and start a new login session.

### 2. Clone

```bash
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
```

### 3. Create `.env`

```bash
cp .env.example .env
```

Generate a secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set it in `.env`:

```env
SECRET_KEY=your-generated-secret
```

### 4. Start

```bash
docker compose up --build -d
```

### 5. Migrate

```bash
docker compose exec api alembic upgrade head
```

### 6. Verify

```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Open http://localhost:3000.

---

# 🦭 Linux Setup — Podman

Podman is a supported container runtime for Linux. This is useful if you prefer **rootless containers** or want to run the project without Docker Engine.

The repository's `docker-compose.yml` is Compose-compatible. With Podman, use the Podman Compose provider:

```bash
podman compose version
```

If `podman compose` is not available on your distribution, install the `podman-compose` package using your distribution's package manager or Python package tooling. Then verify:

```bash
podman-compose --version
```

> **Recommendation:** Prefer your Linux distribution's packaged Podman Compose provider when available. Podman Compose implementations can differ slightly by version, so use the command supported by your installed provider consistently.

### 1. Install Podman

For Ubuntu/Debian-based systems, install the packages provided by your distribution, for example:

```bash
sudo apt update
sudo apt install -y podman
```

Then verify:

```bash
podman --version
```

Install Podman Compose if your distribution does not provide `podman compose`:

```bash
python3 -m pip install --user podman-compose
```

Then:

```bash
podman-compose --version
```

> Package names and recommended installation methods vary between Linux distributions. For Fedora, RHEL-compatible distributions, Arch, and other systems, use the official packages for that distribution.

### 2. Clone the repository

```bash
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
```

### 3. Create `.env`

```bash
cp .env.example .env
```

Generate a secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set it in `.env`:

```env
SECRET_KEY=your-generated-secret
```

### 4. Start with Podman

Preferred command when the Podman Compose plugin is installed:

```bash
podman compose up --build -d
```

If your system provides the standalone `podman-compose` command instead:

```bash
podman-compose up --build -d
```

### 5. Check containers

```bash
podman ps
```

For Compose-managed services:

```bash
podman compose ps
```

or:

```bash
podman-compose ps
```

### 6. Run database migrations

With the Podman Compose plugin:

```bash
podman compose exec api alembic upgrade head
```

With standalone Podman Compose:

```bash
podman-compose exec api alembic upgrade head
```

### 7. Verify the application

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Open:

- http://localhost:3000 — dashboard
- http://localhost:8000/docs — API documentation
- http://localhost:8000/health — health

### Podman common commands

Start:

```bash
podman compose up -d
```

Rebuild:

```bash
podman compose up --build -d
```

View services:

```bash
podman compose ps
```

API logs:

```bash
podman compose logs -f api
```

All logs:

```bash
podman compose logs -f
```

Run tests:

```bash
podman compose exec api pytest -q
```

Run migrations:

```bash
podman compose exec api alembic upgrade head
```

Stop:

```bash
podman compose down
```

Complete local reset:

```bash
podman compose down -v
podman compose up --build -d
podman compose exec api alembic upgrade head
```

> ⚠️ `down -v` removes local PostgreSQL/Redis volumes and therefore deletes local database data. Review your Podman Compose provider's behavior before using it on any environment containing data you need.

### Podman rootless notes

Podman is designed to support rootless containers. For this project:

- Prefer running Podman as your normal Linux user rather than using `sudo` unless your environment specifically requires rootful containers.
- Make sure your user session has the required user namespaces and networking support enabled by your Linux distribution.
- If published ports fail, first try ports above 1024 or check your distribution's rootless networking configuration.
- If containers cannot access the network, inspect the Podman networking configuration with `podman network ls` and `podman network inspect <network>`.
- If volume permissions cause startup failures, inspect the mounted volume and container logs before changing ownership or switching to rootful mode.

### Podman troubleshooting

Check all containers:

```bash
podman ps -a
```

Check images:

```bash
podman images
```

Check networks:

```bash
podman network ls
```

Inspect API logs:

```bash
podman logs --tail=200 <api-container>
```

If Compose itself fails:

```bash
podman compose version
podman compose config
```

If using standalone Podman Compose:

```bash
podman-compose --version
podman-compose config
```

> If a Compose feature is not supported by the installed Podman Compose implementation, do not modify the application blindly. Check the provider version and logs first; the same `docker-compose.yml` may require a small runtime-specific adjustment.

---

# 🍎 macOS Setup

### 1. Install prerequisites

Install **Git** and **Docker Desktop for Mac**.

Verify:

```bash
git --version
docker --version
docker compose version
```

### 2. Clone

```bash
git clone https://github.com/Venkatnaidu7/ai-calling-agent.git
cd ai-calling-agent
```

### 3. Create `.env`

```bash
cp .env.example .env
```

Generate a secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set it in `.env`:

```env
SECRET_KEY=your-generated-secret
```

### 4. Start

```bash
docker compose up --build -d
```

### 5. Migrate

```bash
docker compose exec api alembic upgrade head
```

### 6. Verify

```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Open http://localhost:3000.

---

# 🔄 Common Commands — Docker Platforms

### Start

```bash
docker compose up -d
```

### Rebuild

```bash
docker compose up --build -d
```

### Status

```bash
docker compose ps
```

### API logs

```bash
docker compose logs -f api
```

### All logs

```bash
docker compose logs -f
```

### Migrations

```bash
docker compose exec api alembic upgrade head
```

### Tests

```bash
docker compose exec api pytest -q
```

### Stop

```bash
docker compose down
```

### Complete local reset

```bash
docker compose down -v
docker compose up --build -d
docker compose exec api alembic upgrade head
```

> ⚠️ `docker compose down -v` removes local PostgreSQL/Redis volumes and therefore deletes local database data.

---

# 🔐 Environment Configuration

The complete template is `.env.example`.

Important variables:

| Variable | Purpose | First local boot |
|---|---|---|
| `SECRET_KEY` | Application/JWT signing | **Required** |
| `DATABASE_URL` | PostgreSQL | Docker/Podman default |
| `REDIS_URL` | Redis | Docker/Podman default |
| `FRONTEND_URL` | Dashboard origin | `http://localhost:3000` |
| `CORS_ORIGINS` | Browser origins | `http://localhost:3000` |
| `PUBLIC_BASE_URL` | Public API URL | Required for live calls |
| `OPENAI_API_KEY` | OpenAI Realtime | Optional initially |
| `OPENAI_REALTIME_MODEL` | Realtime model | `gpt-realtime` |
| `TWILIO_ACCOUNT_SID` | Twilio account | Optional initially |
| `TWILIO_AUTH_TOKEN` | Twilio authentication | Optional initially |
| `STRIPE_SECRET_KEY` | Stripe billing | Optional initially |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook | Optional initially |
| `OUTBOUND_ENABLED` | Outbound calling safety gate | `false` |
| `RECORDING_MODE` | Recording policy | `DISABLED` |

**Never commit `.env` or production credentials to GitHub.**

---

# ☎️ Enable Real AI Phone Calls

Local boot does not require OpenAI/Twilio credentials. Real phone calls require:

1. OpenAI Realtime credentials
2. Twilio account and phone number
3. Public HTTPS endpoint
4. Public WSS support for the media stream
5. Configured and published AI agent

Add to `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_REALTIME_MODEL=gpt-realtime
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
PUBLIC_BASE_URL=https://your-public-host
OUTBOUND_ENABLED=false
RECORDING_MODE=DISABLED
```

Configure the Twilio incoming Voice webhook:

```text
https://your-public-host/api/v1/voice/twilio/inbound
```

Then rebuild:

```bash
docker compose up -d --build api celery
```

For Podman:

```bash
podman compose up -d --build api celery
```

Keep outbound calling disabled until consent, compliance, provider configuration, and end-to-end testing are complete.

---

# 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │  Next.js Dashboard   │
                         └──────────┬───────────┘
                                    │ HTTPS
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │ Auth / API / Voice   │
                         └──────┬───────┬───────┘
                                │       │
                     ┌──────────┘       └──────────┐
                     ▼                             ▼
              ┌──────────────┐              ┌──────────────┐
              │ PostgreSQL   │              │ Redis/Celery │
              └──────────────┘              └──────────────┘

Phone → Twilio → FastAPI Voice Gateway → OpenAI Realtime
```

---

# 🧩 Technology Stack

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + Python
- **Database:** PostgreSQL + SQLAlchemy
- **Migrations:** Alembic
- **Queue/cache:** Redis + Celery
- **Telephony:** Twilio Voice Media Streams
- **Realtime AI:** OpenAI Realtime
- **Billing:** Stripe
- **Containers:** Docker + Docker Compose or Podman + Podman Compose
- **Cloud foundation:** AWS + Terraform
- **CI:** GitHub Actions

---

# 📁 Project Structure

```text
ai-calling-agent/
├── apps/
│   ├── api/                  # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/          # REST + voice routes
│   │   │   ├── core/         # Config + security
│   │   │   ├── db/           # Database
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   ├── providers/    # Twilio/OpenAI
│   │   │   ├── services/     # Business logic
│   │   │   └── workers/      # Celery
│   │   ├── alembic/          # Migrations
│   │   └── tests/            # Tests
│   └── web/                  # Next.js dashboard
├── docs/                     # Architecture/security/deployment
├── infrastructure/terraform/ # AWS foundation
├── scripts/
├── .github/workflows/        # CI
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# 🧪 Testing

Inside Docker:

```bash
docker compose exec api pytest -q
docker compose exec api alembic current
```

Inside Podman:

```bash
podman compose exec api pytest -q
podman compose exec api alembic current
```

Health checks:

```bash
# Linux/macOS
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Windows PowerShell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/ready
```

---

# 🛠️ Troubleshooting

### Docker/Podman command is not recognized

Install/start the selected container runtime, then reopen your terminal.

Docker:

```bash
docker --version
docker compose version
```

Podman:

```bash
podman --version
podman compose version
```

### API is restarting

Docker:

```bash
docker compose logs --tail=200 api
```

Podman:

```bash
podman compose logs --tail=200 api
```

### PostgreSQL problem

Docker:

```bash
docker compose ps postgres
docker compose logs --tail=100 postgres
docker compose restart postgres api
```

Podman:

```bash
podman compose ps postgres
podman compose logs --tail=100 postgres
```

### Redis problem

Docker:

```bash
docker compose ps redis
docker compose logs --tail=100 redis
docker compose restart redis celery api
```

Podman:

```bash
podman compose ps redis
podman compose logs --tail=100 redis
```

### Port 3000 or 8000 is busy

Change the published port in `docker-compose.yml` or stop the process using the port.

Windows:

```powershell
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

Linux/macOS:

```bash
lsof -i :3000
lsof -i :8000
```

---

# 🔒 Security & Production

The project contains a production-oriented foundation including tenant isolation, RBAC, authentication, agent/version management, API keys, audit logs, Twilio signature validation, consent/compliance records, outbound safety controls, usage accounting, billing foundation, request IDs, health/readiness endpoints, and AWS/Terraform foundations.

Before production launch, configure and validate:

- HTTPS/WSS
- Production secret management
- PostgreSQL backups/recovery
- Monitoring and alerting
- Rate limiting
- Provider webhooks
- Calling consent and applicable laws
- Recording/retention policy
- Production AWS infrastructure
- End-to-end voice testing
- Container runtime hardening
- Rootless/container permissions where appropriate

This repository is a **production-oriented foundation**, not a claim that every production requirement is complete. See `docs/IMPLEMENTATION_STATUS.md` for the current status.

---

# 📚 Documentation

- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/TELEPHONY.md`
- `docs/AI_RUNTIME.md`
- `docs/DEPLOYMENT.md`
- `docs/COMPLIANCE.md`
- `docs/TESTING.md`
- `docs/IMPLEMENTATION_STATUS.md`

---

# 🤝 Development Workflow

Docker:

```bash
git pull origin main
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api pytest -q
docker compose ps
```

Podman:

```bash
git pull origin main
podman compose up --build -d
podman compose exec api alembic upgrade head
podman compose exec api pytest -q
podman compose ps
```

Before pushing:

1. Run tests.
2. Verify migrations.
3. Verify health/readiness.
4. Test affected endpoints.
5. Never commit secrets.
6. Check the GitHub Actions result.

---
