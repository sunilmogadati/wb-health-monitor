# wb-health-monitor — the one documented entry point for the dev loop.
#
# `make up` takes a clean checkout to a running stack. The check targets (lint, typecheck,
# format-check, test) run the SAME tools CI runs, against the same configuration, so a local run and
# a CI run agree. `make ci` chains them in the order CI does.
#
# Requires GNU make, Docker and Docker Compose for the stack targets. The check targets additionally
# expect the dev dependencies installed (`pip install -e "backend/.[dev]"`) or are run inside the
# stack.

# Compose reads `.env` from the directory holding the first `-f` file, so the flag is passed
# explicitly to pick up the repository-root `.env`. The wildcard makes it conditional: `--env-file`
# on a missing file is a hard error, and a clean checkout has no `.env` until `.env.example` is copied.
ENV_FILE := $(wildcard .env)
COMPOSE := docker compose -f compose.yaml $(if $(ENV_FILE),--env-file .env,)
EXEC_API := $(COMPOSE) exec -T api

.DEFAULT_GOAL := help
.PHONY: help up down logs ps shell migrate migrate-down test lint typecheck format-check format ci clean

help: ## Show every target with its purpose
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- The stack -------------------------------------------------------------

up: ## Bring the whole stack up from empty state and wait for health
	$(COMPOSE) up --build --wait

down: ## Stop the stack and delete its volumes, returning to empty state
	$(COMPOSE) down -v --remove-orphans

logs: ## Follow logs for every service
	$(COMPOSE) logs -f

ps: ## Show each service and its health state
	$(COMPOSE) ps

shell: ## Open a shell in the API container
	$(COMPOSE) exec api bash

clean: down ## Alias for down

# --- Migrations ------------------------------------------------------------

migrate: ## Apply every migration to head
	$(EXEC_API) alembic upgrade head

migrate-down: ## Reverse the most recent migration
	$(EXEC_API) alembic downgrade -1

# --- Checks ----------------------------------------------------------------
# Run the same tools CI runs, against the same config. Point RUN at a container wrapper (e.g.
# `$(COMPOSE) run --rm --no-deps api`) to run these inside the stack instead of on the host.
RUN ?=

lint: ## Lint backend/ and tests/
	$(RUN) ruff check .

typecheck: ## Static type check
	$(RUN) mypy backend/app

format-check: ## Formatter check with no auto-fix, matching CI
	$(RUN) ruff format --check .

format: ## Auto-format the tree
	$(RUN) ruff format .

test: ## Run the test suite
	$(RUN) pytest -c backend/pyproject.toml

ci: lint typecheck format-check test ## Run every check the pipeline runs
	@echo "All local checks passed."
