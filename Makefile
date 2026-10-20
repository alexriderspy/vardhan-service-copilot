# Each target = one chapter of the video. Run `make all` for everything.
PY := .venv/bin/python

.PHONY: setup data migrate classifier-data train eval-classifier rag ask mock mcp-tools agent app evals test lint all docker reset

setup:            ## create .venv and install everything (uses uv if you have it, else pip)
	@if command -v uv >/dev/null; then uv venv --python 3.12 .venv && uv pip install --python $(PY) -r requirements.txt; \
	else python3 -m venv .venv && $(PY) -m pip install -r requirements.txt; fi
	@[ -f .env ] || cp .env.example .env

data:             ## 01: messy legacy.db + CSV exports
	$(PY) 01_legacy_data/generate_legacy.py

migrate:          ## 02: clean -> Postgres (or SQLite fallback), views, agent role
	$(PY) 02_migration/migrate.py

classifier-data:  ## 03a: 2,040 synthetic labelled emails (no API)
	$(PY) 03_classifier/generate_emails.py

train:            ## 03b: fine-tune DistilBERT (1 epoch, ~1 min on a laptop)
	$(PY) 03_classifier/train.py --epochs 1

eval-classifier:  ## 03c: fine-tuned vs zero-shot LLM on 50 hand-written emails
	$(PY) 03_classifier/eval_vs_llm.py

rag:              ## 04a: chunk manuals + warranty, embed locally, store in Chroma
	$(PY) 04_rag/build_index.py

ask:              ## 04b: retrieval (offline) + cited answer (LLM)
	$(PY) 04_rag/ask.py "My booster pump keeps switching on and off with a click"

mock:             ## 05: mock Gmail inbox (30 emails) + technician calendar
	$(PY) 05_mcp_servers/seed_mock_data.py

mcp-tools:        ## 05: start each MCP server over stdio and list its tools
	$(PY) 05_mcp_servers/list_tools.py

agent:            ## 06: run the LangGraph agent over the whole mock inbox
	$(PY) 06_agent/run_agent.py --all

app:              ## 07: the Streamlit UI
	.venv/bin/streamlit run 07_app/app.py

evals:            ## 08: full eval on 50 held-out emails, with CI gate
	$(PY) 08_evals/run_evals.py --gate

test:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check .

all: data migrate classifier-data train rag mock eval-classifier mcp-tools test evals

docker:           ## 09: Postgres + app in Docker
	docker compose -f 09_deploy/docker-compose.yml up --build

reset:            ## fresh demo: new inbox/calendar, forget agent runs
	rm -f artifacts/agent_checkpoints.db
	$(PY) 05_mcp_servers/seed_mock_data.py
