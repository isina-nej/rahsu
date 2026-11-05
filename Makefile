.PHONY: test lint check migrate seed up down
check:
	cd backend && uv run --project .. python manage.py check
migrate:
	cd backend && uv run --project .. python manage.py migrate
seed:
	cd backend && uv run --project .. python manage.py seed_pride
test:
	uv run --extra dev pytest -q
lint:
	uv run --extra dev ruff check backend tests
up:
	docker compose up -d --build
down:
	docker compose down
