.DEFAULT_GOAL := help
PY := uv run python
# Milvus Lite (local file) by default; use http://localhost:19530 with `make up`
MILVUS_URI ?= ./.milvus/bible_rag.db

.PHONY: help install up down logs ps schema ingest reingest fe-install fe-dev fe-build fe-mock api eval test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

## --- Python ---
install: ## Install Python deps with uv
	uv sync

## --- Milvus ---
up: ## Start Milvus standalone in docker (optional; Lite is default)
	docker compose up -d

down: ## Stop Milvus
	docker compose down

logs: ## Tail Milvus logs
	docker compose logs -f milvus

ps: ## Show container status
	docker compose ps

## --- Data ---
schema: ## Create Milvus collections (no-op if they exist)
	mkdir -p .milvus && $(PY) -c "from bible_rag.store.schema import init; init('$(MILVUS_URI)')"

ingest: ## Load EN + ZH verses into `passages`
	mkdir -p .milvus && $(PY) -m bible_rag.ingest.passages --uri $(MILVUS_URI)

reingest: ## Drop collections and load again
	mkdir -p .milvus && $(PY) -m bible_rag.ingest.passages --uri $(MILVUS_URI) --drop

## --- Backend ---
api: ## Run FastAPI dev server on :8000
	uv run uvicorn bible_rag.api.main:app --reload --port 8000

## --- Frontend ---
fe-install: ## npm install in frontend/
	cd frontend && npm install

fe-dev: ## Vite dev server (real API via /api proxy)
	cd frontend && VITE_USE_MOCK=false npm run dev

fe-mock: ## Vite dev server with mock data
	cd frontend && npm run dev

fe-build: ## Production build of the frontend
	cd frontend && npm run build

## --- Quality ---
eval: ## Run DeepEval on the golden datasets
	uv run deepeval test run evals/

test: ## Run pytest
	uv run pytest -q

lint: ## Ruff lint + format check
	uv run ruff check src tests && uv run ruff format --check src tests

clean: ## Remove caches and build output
	rm -rf .pytest_cache .ruff_cache frontend/dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
