# Vardhan Service Copilot

An end-to-end "AI Forward Deployed Engineer" project. A fictional client, **Vardhan Pumps & Services** (Pune), gets about 300 customer emails a day. A person reads each one, searches 3 systems and replies, and replies take 1 to 2 days. The client's brief was vague on purpose: *"We want AI to handle our customer emails."*

This repo is what we build for them:

1. **Migrate** a messy legacy SQLite file and CSV exports into Postgres, with a read-only role for the agent.
2. **Fine-tune** a DistilBERT email-intent classifier with 6 intents.
3. **RAG** over the pump manuals and warranty policy, using Chroma, local `bge-small` embeddings and citations.
4. **Three MCP servers** built on the official `mcp` Python SDK: `company-db`, `gmail` and `calendar`. Gmail and Calendar each have a mock mode and a real Google mode.
5. **A LangGraph agent** that runs classify → route → tools/RAG → draft → **human approval** → act → audit log.
6. **A Streamlit UI** with Approve / Edit / Reject, plus an audit log page.
7. **Evals** on 50 held-out, hand-written emails.
8. **Deploy** with Docker Compose (Postgres + app) and GitHub Actions CI with an eval gate.

Everything runs on a laptop with **no Google account and no paid LLM key**. Only the reply-drafting step needs an LLM. Without a key it stops with a clear message and never fakes output.

---

## Architecture

```
                         ┌─────────────────────── Streamlit UI (07_app) ───────────────────────┐
                         │ inbox · intent + confidence · sources · draft · Approve/Edit/Reject  │
                         └───────────────▲───────────────────────────────┬─────────────────────┘
                                         │ state                         │ human decision
                                         │                               ▼
 ┌──────────────────────────────── LangGraph agent (06_agent) ─────────────────────────────────────┐
 │                                                                                                 │
 │ load_email ─► classify ─► route ─┬─► lookup_order ───────┐                                      │
 │      │        (DistilBERT +      ├─► search_knowledge ───┤                                      │
 │      │        escalation rule)   ├─► find_slots ─────────┼─► draft_reply ─► human_approval ─► act│
 │      │                           ├─► holding_reply ──────┘     (LLM)       (interrupt,       │   │
 │      │                           └─► escalate_complaint ─────────────────► checkpointed)    │   │
 │      │                               (ticket, HIGH, no AI reply)                            │   │
 └──────┼──────────────────────┬────────────────────┬──────────────────────────────────────────┼───┘
        │ MCP (stdio)          │ MCP                │ in-process                                │ MCP
        ▼                      ▼                    ▼                                           ▼
 ┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐                        send_draft (approved_by)
 │ gmail       │   │ company-db       │   │ RAG (04_rag)     │                        create_event
 │ mock JSON / │   │ read-only views  │   │ Chroma +         │                        create_service_ticket
 │ Gmail API   │   │ + 2 writable     │   │ bge-small        │                        write audit log
 ├─────────────┤   │ tables           │   │ manuals/warranty │
 │ calendar    │   └────────┬─────────┘   └──────────────────┘
 │ mock JSON / │            │ role copilot_agent (Postgres) / SQLite authorizer (fallback)
 │ Google Cal  │            ▼
 └─────────────┘   ┌──────────────────┐        ┌──────────────────────────┐
                   │ Postgres         │ ◄───── │ 02_migration             │ ◄── legacy.db (1 wide table)
                   │ customers pumps  │        │ dedupe · clean dates ·   │ ◄── orders_*.csv
                   │ orders tickets   │        │ statuses · amounts       │ ◄── technicians.csv
                   │ technicians      │        └──────────────────────────┘
                   │ agent_audit_log  │
                   └──────────────────┘
```

Routing is plain Python, not an LLM:

| Intent | What the agent does | Human approval |
|---|---|---|
| `order_status` | `company-db.get_order_status` (order number from the email, or the sender's recent orders) | to send |
| `technical_question` | `company-db.get_pump_history` + RAG over the customer's pump manual | to send |
| `warranty_claim` | `get_pump_history` (install date, warranty end) + RAG over the manual and warranty policy | to send |
| `service_booking` | `get_customer` → skill needed → `calendar.find_free_slots` → proposes 2 slots | to send **and** to book |
| `complaint` | `create_service_ticket(priority=high)` and escalate. **The AI never writes a reply.** | a human writes it |
| `other` | polite holding reply | to send |

There is a safety net on top of the classifier. Words like "refund", "consumer court" or "very poor" always route to `complaint`. Below 80% confidence, the UI tells the reviewer to double-check the intent.

---

## Quickstart

You need Python 3.11+. [`uv`](https://docs.astral.sh/uv/) is optional but faster.

```bash
cd project
make setup          # creates .venv, installs requirements, copies .env.example -> .env
make all            # builds everything and runs tests + evals (~2 min after the first model downloads)
make app            # opens the UI at http://localhost:8501
```

Without `make`:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python 01_legacy_data/generate_legacy.py
python 02_migration/migrate.py
python 03_classifier/generate_emails.py
python 03_classifier/train.py --epochs 1
python 04_rag/build_index.py
python 05_mcp_servers/seed_mock_data.py
streamlit run 07_app/app.py
```

To get drafts, add an LLM key to `.env`:

```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-5-5
ANTHROPIC_API_KEY=sk-ant-...
```

The model is chosen with LangChain's `init_chat_model`, so you can switch providers in `.env` without changing code:

| Provider | `.env` | Extra install |
|---|---|---|
| Anthropic (default) | `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-opus-5-5` | none |
| OpenAI | `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini`, `OPENAI_API_KEY=...` | `pip install langchain-openai` |
| Ollama (local, free) | `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.1` | `pip install langchain-ollama`, `ollama pull llama3.1` |

All downloads and generated files (models, Chroma index, databases, mock inbox) go into `artifacts/`, which is git-ignored. Hugging Face downloads also stay there (`HF_HOME=artifacts/hf_cache`).

---

## Chapter by chapter (matches the video)

| # | Folder | Run | What you see |
|---|---|---|---|
| 1 | `01_legacy_data/` | `make data` | `legacy.db` with one wide `jobs` table (5 date formats, free-text status like `DELIVERD`, the same customer typed 5 ways, amounts like `Rs. 12,500`), plus CSV exports with different column names. The manuals and warranty policy are in `client_docs/`. |
| 2 | `02_migration/` | `make migrate` | A data-quality report. Clean tables, `v_*` views, and the `copilot_agent` role. |
| 3 | `03_classifier/` | `make classifier-data train eval-classifier` | 2,040 synthetic labelled emails (no API), a plain PyTorch fine-tuning loop, and fine-tuned vs zero-shot LLM on 50 hand-written emails. |
| 4 | `04_rag/` | `make rag ask` | One chunk per `##` heading, local embeddings, and retrieval with `[Doc § Section]` citations. |
| 5 | `05_mcp_servers/` | `make mock mcp-tools` | Starts each MCP server over stdio and lists its tools. |
| 6 | `06_agent/` | `make agent` or `python 06_agent/run_agent.py m021` | The graph runs on the mock inbox and pauses at human approval. |
| 7 | `07_app/` | `make app` | The support team's screen. |
| 8 | `08_evals/` | `make evals` | Intent and routing accuracy, context recall, and groundedness + cost (with a key). Add `--gate` for CI. |
| 9 | `09_deploy/` | `make docker` | Postgres and the app in Docker. CI is in `.github/workflows/ci.yml`. |

Useful agent commands:

```bash
python 06_agent/run_agent.py m021                  # one email (a complaint: no LLM needed at all)
python 06_agent/run_agent.py --all                 # the whole inbox
python 06_agent/run_agent.py m021 --approve Asha   # resume a paused email: approve
python 06_agent/run_agent.py m021 --reject         # or reject
make reset                                         # fresh inbox + calendar, forget agent runs
```

---

## Mock mode vs real Google mode

`GOOGLE_MODE` in `.env` switches both the `gmail` and `calendar` MCP servers. The tool names and arguments are identical in both modes, so the agent can't tell the difference.

**Mock mode** (`GOOGLE_MODE=mock`, the default):
- The inbox is `artifacts/mock_gmail.json`: 30 realistic unread emails covering all 6 intents, about the same customers, orders and serial numbers that are in the database.
- The calendar is `artifacts/mock_calendar.json`: 5 technicians with skills (centrifugal / submersible / booster) and about 60% of their 2-hour slots already booked over the next 14 days.
- "Sending" moves a draft to `sent` and marks the email read. `make reset` restores everything.

**Real mode** (`GOOGLE_MODE=real`) uses your own Gmail and Google Calendar:
1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project.
2. Under **APIs & Services → Library**, enable **Gmail API** and **Google Calendar API**.
3. Under **OAuth consent screen**, choose External and add your Gmail address as a **test user**.
4. Under **Credentials → Create credentials → OAuth client ID**, choose **Desktop app**, then download the JSON.
5. Save it as `project/credentials.json` (git-ignored).
6. Run `python 05_mcp_servers/google_login.py`. A browser opens, you approve, and the token is saved to `artifacts/google_token.json`.
7. Set `GOOGLE_MODE=real`. Map technicians to calendar ids in `05_mcp_servers/technician_calendars.json`. The default is `primary`, which means your own calendar.

Scopes: `gmail.modify` (read, mark as read, drafts, send) and `calendar`. Use a test Gmail account: in real mode, "Approve & send" really sends.

---

## Database: Postgres, or the SQLite fallback

- With `DATABASE_URL` set to Postgres, the migration creates the tables, the `v_*` views, and a **`copilot_agent` login role**. That role can only `SELECT` the views, `SELECT/INSERT/UPDATE` `service_tickets`, and `INSERT` into `agent_audit_log`. Point `AGENT_DATABASE_URL` at that role.
- With **no `DATABASE_URL`**, everything uses SQLite at `artifacts/vardhan.db`, so the demo runs anywhere without Docker. SQLite has no roles, so `common/db.py` installs a **SQLite authorizer**: a function SQLite calls before every read and write. It enforces the same rules. The agent can't read raw tables (for example, technicians' phone numbers), can't update or delete, and can't change the schema.
- The UI's audit-log page and the migration use the admin connection. The agent and its MCP servers only ever use the restricted one.

Postgres via Docker:

```bash
docker compose -f 09_deploy/docker-compose.yml up --build    # postgres:16 + the app on :8501
```

Postgres without Docker (local install):

```bash
DATABASE_URL=postgresql+psycopg://vardhan:vardhan@localhost:5432/vardhan \
AGENT_DATABASE_URL=postgresql+psycopg://copilot_agent:change-me@localhost:5432/vardhan \
python 02_migration/migrate.py
```

---

## Results (measured on 20 Oct 2026, MacBook, Apple Silicon)

All numbers come from actual runs of the scripts in this repo. Nothing is estimated.

**Migration** (`make migrate`)

| | |
|---|---|
| legacy `jobs` rows + shop CSV rows | 561 + 65 |
| customer rows before → after dedupe (key: phone number) | 626 → **162** |
| orders (2 found in both legacy.db and CSV, merged) | 232 |
| pumps / historical service tickets | 162 / 392 |
| unreadable dates | 0 |

**Intent classifier**: DistilBERT, 1 epoch, 1,632 synthetic training emails, trained in under 20 seconds on Apple MPS.

| Test set | Fine-tuned DistilBERT | Zero-shot LLM (`claude-opus-5-5`) |
|---|---|---|
| Synthetic test split (204, same templates as training) | 100% | not run |
| **50 hand-written held-out emails** | **92.0% (46/50)** | **not measured: no API key in this environment** |
| Latency per email | **10 ms** (CPU) | not measured |
| Cost per 1,000 emails | $0 (runs locally) | not measured |

The 100% on the synthetic split only shows the model learned the templates. The 92% on hand-written emails is the honest number. The 4 mistakes were 2 order-status emails read as technical/booking, 1 complaint read as other, and 1 thank-you read as technical. To fill in the LLM column, add a key and run `make eval-classifier`. It prints accuracy, latency and cost per 1K emails for both models side by side.

**Agent evals** (`make evals`, 50 held-out emails, offline part)

| Metric | Result | CI gate |
|---|---|---|
| Intent accuracy (classifier + escalation rule) | **92.0%** | ≥ 85% |
| Tool-routing accuracy (called the expected tool) | **92.0%** | ≥ 85% |
| Context recall (must-include facts found in tool/RAG results) | **86.5%** | ≥ 80% |
| Offline latency per email (classify + route + tools + RAG) | **~120–160 ms** | – |
| Groundedness (facts present in the LLM draft) | not measured (needs a key) | ≥ 80% when measured |
| Citation validity (cited `[Doc § Section]` actually retrieved) | not measured (needs a key) | – |
| LLM latency and cost per email | not measured (needs a key) | – |

Every remaining context-recall miss comes from the 2 misclassified order-status emails, which went down the wrong branch. The evals found 3 real bugs, all now fixed:
- the migration threw away the reason behind "on hold - payment"
- warranty end dates for the 29th/30th/31st were off by days
- RAG only searched the customer's own pump manual even when the email asked about a different pump

**Tests**: `pytest`: **24 passed**. They cover cleaning functions, least-privilege rules, the mock Gmail/Calendar, chunking, routing, the missing-key error, and end-to-end graph runs: a complaint is escalated and never auto-replied; a booking waits for approval and then books; a rejected draft sends nothing.

**Full pipeline** (`make all`, models already downloaded): 1 min 53 s.

---

## Ship it to AWS EC2

The `deploy` job in `.github/workflows/ci.yml` runs only on `main`, and only after the tests and the eval gate pass. It connects to your server over SSH, pulls the new code and restarts the app with Docker Compose, then checks the app answers on the server itself.

### One-time setup

1. **Launch the server.** In the EC2 console, launch an Ubuntu 24.04 instance. A `t3.large` (8 GB RAM) is comfortable, because the app loads the classifier and the embedding model. Give it a 30 GB disk and create a key pair (you'll download a `.pem` file).
2. **Security group (the server's firewall).** Add two inbound rules and nothing else:
   - SSH, port 22, source: your own IP (`My IP` in the console).
   - Custom TCP, port 8501, source: the client office's IP range. The app has no login of its own and it shows customer emails, so never open 8501 to `0.0.0.0/0`.

   The compose file also maps Postgres to port 5432. Leave it closed in the security group, so only the app container can reach the database.
3. **Install Docker and clone the project on the server:**
   ```bash
   ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker ubuntu && exit        # log out and back in so the group applies
   ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
   git clone https://github.com/<you>/<repo>.git ~/vardhan-copilot
   ```
   For a private repo, add a read-only deploy key to the repo and use the SSH clone URL.
4. **Put the server's settings in `~/vardhan-copilot/.env`** (never commit it). Copy `.env.example` and set at least `ANTHROPIC_API_KEY` and a real `AGENT_DB_PASSWORD`.
5. **Add three secrets in GitHub** (Settings → Secrets and variables → Actions):

   | Secret | Value |
   |---|---|
   | `EC2_HOST` | the server's public IP or DNS name |
   | `EC2_USER` | `ubuntu` |
   | `EC2_SSH_KEY` | the full contents of your `.pem` file |

6. **First start:** run `docker compose -f 09_deploy/docker-compose.yml up -d --build` on the server once (it builds the data, trains the classifier and indexes the manuals on first boot), or push to `main` and let the `deploy` job do it.

After that, every push to `main` that passes the eval gate is live a few minutes later. A push that drops below the gate never reaches the server.

### What this doesn't cover
HTTPS and a real login. For a client pilot, put the app behind a load balancer with a TLS certificate, or keep it reachable only over the company VPN.

## Using the MCP servers from Claude Desktop (bonus)

The servers are ordinary stdio MCP servers, so any MCP host can use them. In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vardhan-company-db": {
      "command": "/ABSOLUTE/PATH/project/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/project/05_mcp_servers/company_db_server.py"]
    }
  }
}
```

---

## Notes

- **FastMCP is now `MCPServer`.** In `mcp` 2.x (installed here: 2.3.0), `FastMCP` was renamed to `mcp.server.MCPServer`. The decorator API (`@mcp.tool()`, `mcp.run()`) is the same. If you pin `mcp<2`, write `from mcp.server.fastmcp import FastMCP` instead.
- **Opus 5.5 always thinks before it answers.** There's no temperature setting (it rejects sampling parameters), and `max_tokens` covers thinking plus the reply, which is why `get_llm()` defaults to 16,000.
- **Least privilege covers sending too.** `send_draft` refuses to run without `approved_by`, and the graph only reaches the `act` step after a human resumes it from the UI.
- **Evals never touch real data.** They run on a copy of the database, talk to the MCP servers in-process, and don't write to the audit log.
