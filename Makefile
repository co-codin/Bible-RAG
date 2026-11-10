.DEFAULT_GOAL := help
PY := uv run python
# Milvus Lite (local file) by default; use http://localhost:19530 with `make up`
MILVUS_URI ?= ./.milvus/bible_rag.db

.PHONY: help install up down logs ps schema ingest reingest chunks chunks-smoke fetch-index index-check fe-install fe-dev fe-build fe-mock api eval eval-guards eval-deepeval test lint clean

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

chunks: ## Chunk + embed (bge-m3 dense+sparse) all EN/ZH texts into `chunks`
	mkdir -p .milvus && $(PY) -m bible_rag.ingest.chunks --uri $(MILVUS_URI)

chunks-smoke: ## Embed the first 500 chunks per translation (quick check)
	mkdir -p .milvus && $(PY) -m bible_rag.ingest.chunks --uri $(MILVUS_URI) --limit 500

HF_INDEX_REPO ?= etsin-ai/bible-rag-index
fetch-index: ## Download a pre-built Milvus Lite db + manifest.json from HF (HF_INDEX_REPO)
	@# Milvus Lite stores bible_rag.db as a directory, so fetch the whole folder, not one file.
	mkdir -p .milvus && $(PY) -c "from huggingface_hub import snapshot_download as d; \
	print(d('$(HF_INDEX_REPO)', repo_type='dataset', local_dir='.milvus', \
	allow_patterns=['manifest.json', 'bible_rag.db/**']))"
	$(PY) -m bible_rag.index_manifest check --uri $(MILVUS_URI)

index-check: ## Verify the local index matches the current model / chunking / data
	$(PY) -m bible_rag.index_manifest check --uri $(MILVUS_URI)

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
eval-guards: ## Input-guard block / false-refusal rates (no LLM)
	$(PY) -m evals.eval_guards

eval-deepeval: ## Run DeepEval (needs OPENAI_API_KEY and ANTHROPIC_API_KEY)
	$(PY) -m evals.run_deepeval

eval: eval-deepeval ## Run DeepEval on the golden datasets (needs keys; not for CI)


test: ## Run pytest
	uv run pytest -q

lint: ## Ruff lint + format check
	uv run ruff check src tests && uv run ruff format --check src tests

clean: ## Remove caches and build output
	rm -rf .pytest_cache .ruff_cache frontend/dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
