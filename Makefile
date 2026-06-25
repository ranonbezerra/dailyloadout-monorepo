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
APP_API_URL := $(shell sed -n 's/^API_URL=//p' $(APP_DIR)/.env 2>/dev/null)
APP_DART_DEFINES := $(if $(APP_API_URL),--dart-define=API_URL=$(APP_API_URL),)

# Load root .env for infrastructure vars (ports, PG credentials)
ifneq (,$(wildcard .env))
  include .env
  export
endif

.DEFAULT_GOAL := help

# ── Helpers ─────────────────────────────────────────────────────────
define check
	@printf "\033[34m▶ %-40s\033[0m" "$(1)" && $(2) && printf "\033[32m ✓\033[0m\n" || (printf "\033[31m ✗\033[0m\n" && exit 1)
endef

define warn
	@printf "\033[34m▶ %-40s\033[0m" "$(1)" && $(2) && printf "\033[32m ✓\033[0m\n" || printf "\033[33m ⚠ (warning)\033[0m\n"
endef

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

.PHONY: api-test-cov
api-test-cov: ## Run API tests with coverage (fail under 80%)
	cd $(API_DIR) && poetry run pytest --cov=src/dailyloadout --cov-report=term-missing --cov-fail-under=90

.PHONY: igdb-check
igdb-check: ## Smoke-test the live IGDB client (make igdb-check q="Hollow Knight")
	cd $(API_DIR) && poetry run python scripts/check_igdb.py "$(or $(q),Hollow Knight)"

.PHONY: api-lint
api-lint: ## Lint API (ruff check)
	cd $(API_DIR) && poetry run ruff check .

.PHONY: api-format-check
api-format-check: ## Check API formatting (ruff format --check)
	cd $(API_DIR) && poetry run ruff format --check .

.PHONY: api-typecheck
api-typecheck: ## Type-check API (mypy strict)
	cd $(API_DIR) && poetry run mypy src/

.PHONY: api-security
api-security: ## Security scan API (bandit)
	cd $(API_DIR) && poetry run bandit -r src/ -ll -ii -c pyproject.toml

.PHONY: api-typos
api-typos: ## Spell-check API (typos)
	cd $(API_DIR) && poetry run typos src/ tests/

.PHONY: api-file-sizes
api-file-sizes: ## Check API file sizes (max 300 lines)
	@echo "Checking Python files > 300 lines..."
	@OVERSIZED=$$(find $(API_DIR)/src -name '*.py' -exec awk 'END{if(NR>300) print FILENAME": "NR" lines"}' {} \;); \
	if [ -n "$$OVERSIZED" ]; then \
		echo "$$OVERSIZED"; \
		echo "\033[31m✗ Files exceed 300-line limit\033[0m"; \
		exit 1; \
	else \
		echo "\033[32m✓ All files within limit\033[0m"; \
	fi

.PHONY: api-fmt
api-fmt: ## Format API code
	cd $(API_DIR) && poetry run ruff format .

.PHONY: worker
worker: ## Run Taskiq worker (async debrief extraction)
	cd $(API_DIR) && poetry run taskiq worker dailyloadout.infrastructure.tasks.debrief_extraction:broker

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
	cd $(WEB_DIR) && bun run test

.PHONY: web-lint
web-lint: ## Lint web (biome check)
	cd $(WEB_DIR) && bun run lint

.PHONY: web-typecheck
web-typecheck: ## Type-check web (tsc)
	cd $(WEB_DIR) && bun run tsc -b --noEmit

.PHONY: web-build
web-build: ## Build web for production
	cd $(WEB_DIR) && bun run build

.PHONY: web-fmt
web-fmt: ## Format web code
	cd $(WEB_DIR) && bun run format

.PHONY: web-install
web-install: ## Install web dependencies
	cd $(WEB_DIR) && bun install

# ─────────────────────────────────────────────
# App (packages/app) — Flutter
# ─────────────────────────────────────────────

.PHONY: app
app: ## Run Flutter app (uses preferred device, or: make app d=chrome)
	cd $(APP_DIR) && $(FLUTTER) run $(if $(d),-d $(d)) $(APP_DART_DEFINES)

.PHONY: app-devices
app-devices: ## List available Flutter devices
	cd $(APP_DIR) && $(FLUTTER) devices

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
# Quality gates (per-package)
# ─────────────────────────────────────────────

.PHONY: quality-api
quality-api: ## Full API quality gate
	@echo "\n\033[1;36m══════ API Quality Gate ══════\033[0m"
	$(call check,Ruff lint,                  cd $(API_DIR) && poetry run ruff check . --fix)
	$(call check,Ruff format,                cd $(API_DIR) && poetry run ruff format --check .)
	$(call check,Mypy strict,                cd $(API_DIR) && poetry run mypy src/)
	$(call check,Bandit security,            cd $(API_DIR) && poetry run bandit -r src/ -ll -ii -c pyproject.toml -q)
	$(call check,Typos spell-check,          cd $(API_DIR) && poetry run typos src/ tests/)
	$(call check,File sizes (≤300 lines),    $(MAKE) api-file-sizes > /dev/null 2>&1)
	$(call check,Pytest + coverage ≥90%,     cd $(API_DIR) && poetry run pytest -q --tb=short --cov=src/dailyloadout --cov-report=term-missing --cov-fail-under=90)
	@echo "\033[1;32m══════ API: All checks passed ══════\033[0m\n"

.PHONY: quality-web
quality-web: ## Full Web quality gate
	@echo "\n\033[1;36m══════ Web Quality Gate ══════\033[0m"
	$(call check,Biome lint + format,    cd $(WEB_DIR) && bun run lint)
	$(call check,TypeScript check,       cd $(WEB_DIR) && bun run tsc -b --noEmit)
	$(call check,Vitest + coverage ≥90%, cd $(WEB_DIR) && bun run test --coverage)
	$(call check,Vite build,             cd $(WEB_DIR) && bun run build > /dev/null 2>&1)
	@echo "\033[1;32m══════ Web: All checks passed ══════\033[0m\n"

.PHONY: quality-app
quality-app: ## Full App quality gate
	@echo "\n\033[1;36m══════ App Quality Gate ══════\033[0m"
	$(call check,Dart format,             cd $(APP_DIR) && $(DART) format --set-exit-if-changed .)
	$(call check,Flutter analyze,         cd $(APP_DIR) && $(FLUTTER) analyze)
	$(call check,Flutter test + cov ≥90%, cd $(APP_DIR) && $(FLUTTER) test --coverage && ./tool/check_coverage.sh 90)
	@echo "\033[1;32m══════ App: All checks passed ══════\033[0m\n"

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# ─────────────────────────────────────────────
# Quality gate (full monorepo)
# ─────────────────────────────────────────────

.PHONY: quality
quality: ## Run ALL quality gates (pre-commit + api + web + app)
	@echo "\n\033[1;35m╔══════════════════════════════════════╗\033[0m"
	@echo "\033[1;35m║     DailyLoadout — Quality Gate      ║\033[0m"
	@echo "\033[1;35m╚══════════════════════════════════════╝\033[0m"
	$(call check,Pre-commit hooks,  pre-commit run --all-files)
	@$(MAKE) quality-api
	@$(MAKE) quality-web
	@$(MAKE) quality-app
	$(call warn,Code duplication (jscpd ≤5%),  npx jscpd --silent)
	@echo "\033[1;32m╔══════════════════════════════════════╗\033[0m"
	@echo "\033[1;32m║     All quality gates passed ✓       ║\033[0m"
	@echo "\033[1;32m╚══════════════════════════════════════╝\033[0m"

# ─────────────────────────────────────────────
# Convenience aggregates
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
check: lint test ## Quick check (lint + test, no security/coverage)

# ─────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'
