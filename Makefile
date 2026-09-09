install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r apps/api/requirements.txt

dev:
	docker compose up --build

test:
	. .venv/bin/activate && cd apps/api && PYTHONPATH=. pytest tests -q

compile:
	python3 -m compileall -q apps/api/app

migrate:
	cd apps/api && alembic upgrade head

seed:
	python3 scripts/seed.py

clean:
	docker compose down -v
