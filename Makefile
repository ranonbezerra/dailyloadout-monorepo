# ─────────────────────────────────────────────
# DailyLoadout — Root Makefile
# All commands run from the monorepo root.
# ─────────────────────────────────────────────

COMPOSE := docker compose -f docker-compose.yml -f docker-compose.dev.yml
API_DIR := packages/api
APP_DIR := packages/app
WEB_DIR := packages/web
FLUTTER := fvm flutter
DART    := fvm dart

# Load root .env for infrastructure vars (ports, PG credentials)
ifneq (,$(wildcard .env))
  include .env
  export
endif

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────
# Infrastructure
# ─────────────────────────────────────────────

.PHONY: up
up: ## Start infrastructure (postgres, redis, ollama)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop infrastructure
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart infrastructure
	$(COMPOSE) restart

.PHONY: logs
logs: ## Tail infrastructure logs
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show infrastructure status
	$(COMPOSE) ps

.PHONY: clean
clean: ## Stop infrastructure and remove volumes
	$(COMPOSE) down -v

.PHONY: ollama-pull
ollama-pull: ## Pull Ollama models (gemma3:4b + gemma3:12b)
	ollama pull gemma3:4b
	ollama pull gemma3:12b

# ─────────────────────────────────────────────
# API (packages/api)
# ─────────────────────────────────────────────

.PHONY: api
api: ## Run API dev server (uvicorn with reload)
	cd $(API_DIR) && HF_HOME=$(HOME)/.cache/huggingface poetry run uvicorn src.dailyloadout.main:app --reload --host 0.0.0.0 --port $${API_PORT:-8100}

.PHONY: api-test
api-test: ## Run API tests
	cd $(API_DIR) && poetry run pytest

.PHONY: api-lint
api-lint: ## Lint API (ruff + ruff format + mypy)
	cd $(API_DIR) && poetry run ruff check . && poetry run ruff format --check . && poetry run mypy src/

.PHONY: api-fmt
api-fmt: ## Format API code
	cd $(API_DIR) && poetry run ruff format .

.PHONY: api-migrate
api-migrate: ## Run Alembic migrations
	cd $(API_DIR) && poetry run alembic upgrade head

.PHONY: api-migration
api-migration: ## Create new Alembic migration (usage: make api-migration msg="add users table")
	cd $(API_DIR) && poetry run alembic revision --autogenerate -m "$(msg)"

.PHONY: api-install
api-install: ## Install API dependencies
	cd $(API_DIR) && poetry install

# ─────────────────────────────────────────────
# Web (packages/web)
# ─────────────────────────────────────────────

.PHONY: web
web: ## Run web dev server (vite)
	cd $(WEB_DIR) && bun run dev --port $${WEB_PORT:-3200}

.PHONY: web-test
web-test: ## Run web tests
	cd $(WEB_DIR) && bun test

.PHONY: web-lint
web-lint: ## Lint web (biome)
	cd $(WEB_DIR) && bun run lint

.PHONY: web-fmt
web-fmt: ## Format web code
	cd $(WEB_DIR) && bun run format

.PHONY: web-build
web-build: ## Build web for production
	cd $(WEB_DIR) && bun run build

.PHONY: web-install
web-install: ## Install web dependencies
	cd $(WEB_DIR) && bun install

# ─────────────────────────────────────────────
# App (packages/app) — Flutter
# ─────────────────────────────────────────────

.PHONY: app
app: ## Run Flutter app on iOS simulator
	cd $(APP_DIR) && $(FLUTTER) run -d ios

.PHONY: app-android
app-android: ## Run Flutter app on Android emulator
	cd $(APP_DIR) && $(FLUTTER) run -d android

.PHONY: app-test
app-test: ## Run Flutter tests
	cd $(APP_DIR) && $(FLUTTER) test

.PHONY: app-lint
app-lint: ## Analyze Flutter code
	cd $(APP_DIR) && $(FLUTTER) analyze

.PHONY: app-install
app-install: ## Get Flutter dependencies
	cd $(APP_DIR) && $(FLUTTER) pub get

# ─────────────────────────────────────────────
# Quality gate (all packages)
# ─────────────────────────────────────────────

.PHONY: install
install: api-install web-install app-install ## Install all dependencies

.PHONY: lint
lint: api-lint web-lint app-lint ## Lint all packages

.PHONY: test
test: api-test web-test app-test ## Test all packages

.PHONY: fmt
fmt: api-fmt web-fmt ## Format all packages

.PHONY: check
check: lint test ## Full quality gate (lint + test)

# ─────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'
