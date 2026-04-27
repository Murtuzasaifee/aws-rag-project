.PHONY: dev test lint format type-check docker-up docker-down clean install

# ── Development ───────────────────────────────────────────────────────────────

install:
	pip install -e ".[dev,test]"

dev:
	uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# ── Quality ───────────────────────────────────────────────────────────────────

lint:
	flake8 src/ tests/

format:
	black src/ tests/

type-check:
	mypy src/

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=ragapp --cov-report=term-missing --cov-report=html

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f app

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache .coverage
