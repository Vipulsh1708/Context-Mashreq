# Local Test Environment — Bug 7705 Reproduction

**Goal:** Reproduce Bug 7705 (workflow shows "Completed" while component nodes remain stuck in "Queued") locally, using the real WF-Email-Triage workflow shared in the ticket comments.

**Status as of 2026-09-11:** Local environment fully working end-to-end. Bug NOT yet reproduced — all test runs complete cleanly with no stuck/queued nodes. Currently deciding between further scale-up vs. code-level investigation.

---

## Repo Location

```
C:\Users\Dell\Desktop\Mashreq\Tadastudio\New-Tada
```

Cloned separately from the original `Tadabuilderapp` folder — this is the updated repo to work from.

---

## PHASE 1: Getting Tada Studio Running Locally

### 1. Environment setup
- Installed Python, Node.js, Docker Desktop
- Cloned repo into `Tadastudio\New-Tada`

### 2. Manual (non-Docker) setup — abandoned
- Tried `uv sync` + `python -m backend.app` directly
- Hit PyTorch DLL load failures on Windows (`OSError: [WinError 1114]`)
- Switched to Docker instead

### 3. Docker build — slow build issue
- First `docker-compose build` took **15+ hours** — caused by LLM Guard security/content scanning running on every file during the image build
- **Fix:** added `LLM_GUARD_MODE=disabled` to `.env` → rebuild dropped to ~30 minutes

### 4. Missing database
- `docker-compose.yml` (as provided) has no `postgres` service — only `backend`, `frontend`, `llm-guard`, `phoenix`
- **Fix:** added a `postgres` service (pgvector/pgvector:pg16 image) to `docker-compose.yml`, wired `KEY_POSTGRES_*` env vars on the backend, added `depends_on: postgres` and a named volume
- ⚠️ This is a change to a **git-tracked file** — must be reverted before any commit (see "Changes to Revert" below)

### 5. SSO login blocked
- Can't log in with Mashreq SSO/ID from current location (India) — VPN/network restriction
- Found a built-in dev bypass in `backend/api/auth/dependencies.py`:
  ```
  SKIP_AUTH = os.getenv("SKIP_AUTH", "false")
  DEV_USER_EMAIL = os.getenv("DEV_USER_EMAIL", "dev@localhost")
  ```
- **Fix:** added `SKIP_AUTH=true`, `DEV_USER_EMAIL=dev@localhost`, `DEV_USER_NAME=Dev User` to `.env`

### 6. No Settings/Admin access
- Dev user wasn't an admin, so Settings UI (LLM providers, etc.) never appeared
- **Fix:** added `ADMIN_USERS=dev@localhost` to `.env`

### 7. Credential encryption missing
- Model deployment creation failed silently: `CREDENTIAL_ENCRYPTION_KEY environment variable is required but not set`
- **Fix:** generated a Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`), added as `CREDENTIAL_ENCRYPTION_KEY` in `.env`

### 8. VDI Docker (separate machine) — unresolved, deprioritized
- Docker installed in VDI but `docker ps` fails with "failed to connect to docker api"
- No Docker service registered (`sc query docker` → service does not exist)
- Reported to IT (Abid) with diagnostic info; not blocking since main machine works

---

## PHASE 2: Importing the Real Workflow

### 9. Got the real workflow JSON
- Someone shared a link in the Azure DevOps ticket comments to the actual 700+-node `WF-Email-Triage-v7.9.1` workflow (the one reproducing the bug in UAT)
- Downloaded as JSON, saved locally at `C:\Users\Dell\Desktop\Mashreq\WF-Email-Triage-v7.9.1.json`
- **Redacted real secrets** before saving: OAuth `client_secret` and a Bearer token were replaced with `"REDACTED"`
- **Trimmed massive prompt texts** (multi-thousand-word agent system prompts) to keep the file manageable — this caused follow-on issues (see #12, #13)
- Imported via Tada Studio's "Import Workflow" feature (backed by `POST /api/graph/import-raw`)

### 10. LLM provider missing (no Azure OpenAI creds available)
- Every AGENT node showed "Unconfigured Nodes — missing LLM configuration"
- No Azure OpenAI / OpenAI / Anthropic key available; user has a **Groq** key
- Discovered Groq is not a registered provider in `backend/services/llm_models/factory.py` (`_providers` dict only has `azure_openai`, `azure_openai_ptu`, `gpu_con`, `openai`, `anthropic`)
- **Workaround:** Groq exposes an OpenAI-compatible endpoint. Configured a model deployment with:
  - `provider: "openai"`
  - `settings.base_url: "https://api.groq.com/openai/v1"`
  - `credentials.api_key: <groq key>`
  - Created via direct API call (`POST /api/model-deployments`) since Settings UI page itself never surfaced despite admin access — used `curl -d @file.json` to avoid CMD quoting issues
  - Deployment ID: `3ed28c0a-e4b3-4481-b504-e8f32dce8d53`

### 11. Applying the LLM config to all 27 agent nodes — hit a real Tada Studio bug
- Tried `PUT /api/graph/node/llm/configure` per node (scripted via `configure_agents_groq.py`) — API returned `success: true`
- But `GET /api/graph/node/{...}/llm` showed `llm_config: null` again afterward
- **Root cause found in code:** `handle_configure_node_llm` only updates the **in-memory** graph object (`get_graph_manager().get_graph()`), never persists. The `/save/{graph_name}` endpoint (`handle_save_graph`) calls `get_graph_or_404(..., reload=True)` **before** saving — this reloads from DB first, silently discarding the in-memory edit, then saves that stale (unmodified) copy back on top of itself.
- This is a genuine bug in Tada Studio itself (save-after-reload race), separate from Bug 7705, but it blocked our setup.
- **Workaround:** bypassed the API entirely — connected directly to Postgres (`psycopg2`) and patched the `definition_json` JSON column in the `graph_definitions` table, writing the LLM config straight into each AGENT node's `agent_config.llm_config`. Script: `fix_llm_config_db.py`. Followed by `POST /api/graph/reload/{graph_name}` to force the GraphManager to pick up the DB change.

### 12. Wrong/deprecated Groq model names
- First tried `llama-3.3-70b-versatile` → `404 model_not_found`
- Then `llama-3.1-8b-instant` → same error
- Queried Groq's live model list directly: `GET https://api.groq.com/openai/v1/models` (had to spoof a `User-Agent` header — default `urllib` UA got blocked by Cloudflare bot protection, error code 1010)
- Real current models included: `groq/compound`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.6-27b`, etc. (old Llama names gone entirely)
- **Settled on `openai/gpt-oss-20b`** — updated both the model_deployment record (via `PUT /api/model-deployments/{id}`) and the embedded `model_name` in every node's `llm_config` (via `fix_llm_config_db.py`)

### 13. "System prompt is required for agents" validation error
- Caused by trimming system_prompt too aggressively when saving the workflow JSON (see #9)
- **Fix:** `fix_llm_config_db.py` also back-fills a placeholder `system_prompt` (and `prompt_template`) for every AGENT node that's missing one

### 14. FOR_EACH loop had nothing to iterate over
- "Unprocessed Case ID Fetcher" queries a `crm_ingested_cases` table that doesn't exist anywhere in Tada Studio's own schema — it's Mashreq/Altair-specific business data that only exists on their real UAT database
- Reverse-engineered the schema from SQL statements embedded in the various agents' prompts (Customer Upsert Agent, Case Insert Agent, Triage Insert Agent, Classification Insert Agent, Taxonomy Validation Sub-Agent)
- **Built 12 tables from scratch** via `seed_altair_schema.py`:
  `crm_ingested_cases`, `customers`, `cases`, `case_types`, `service_type`, `case_sub_type`, `ai_sentiment`, `ai_tone`, `priorities`, `triage_statuses`, `triages`, `ai_classifications`
- Seeded minimal taxonomy reference rows (case types, one service/sub-type combo, sentiment labels, tone, priorities, triage status) + **5 dummy test cases**

### 15. "For each 1" also missing structured output schema
- "Unprocessed Case ID Fetcher" returned a generic `response` instead of `{"results": [...]}`, which "For each 1" needs (`field_path: fields.results`)
- Caused by the same over-trimming when saving the workflow JSON
- **Fix:** `fix_structured_output.py` added back the `structured_outputs` schema (`results: List[str]`) to that specific node via direct DB patch

---

## PHASE 3: Trying to Trigger the Bug

### 16. First full run — only 4 nodes executed
- With only 5 seeded cases, ran clean: `Start → Fetcher → For Each → End`, all "Completed"
- FOR_EACH's 35-node body never ran because the fetcher initially returned 0 items on the very first attempt (before seeding), then completed too quickly/cleanly with only 5 items

### 17. Scaled up — 40 more dummy cases seeded (45 total)
- Script: `seed_more_cases.py` — generates cases from 10 rotating templates (complaints, inquiries, service requests, feedback)
- Re-ran the workflow — **still no reproduction.** Everything completed cleanly, no nodes stuck in "Queued"

### Current hypothesis
- Our test runs are all-success at scale (1,500+ node executions with zero failures)
- The real UAT case had 714 total nodes **with 12 failures mixed in**
- The race condition may specifically depend on **failure and success paths competing** to update the same execution/workflow completion record — not just raw concurrent volume of successful nodes
- Pure scale-up of clean successes may not be sufficient to reproduce it

### Decision point (as of last session)
Two paths forward:
- **A) Keep scaling** — even more concurrent cases, possibly need to engineer actual node failures happening concurrently with successes
- **B) Pivot to code investigation** — read `backend/services/execution/workflow_executor.py` (6-phase execution lifecycle, esp. "Finalize Execution") and node-status-write logic directly, to find the race condition logically instead of by luck

---

## Key Files Created (all in `C:\Users\Dell\Desktop\Mashreq\`, NOT part of the git repo)

| File | Purpose |
|---|---|
| `BUG_7705_CONTEXT.md` | Original ticket context, Issue 1 vs Issue 2 breakdown |
| `WF-Email-Triage-v7.9.1.json` | The real workflow JSON (trimmed, secrets redacted) |
| `groq_deployment.json` | ⚠️ Contains your real Groq API key — payload used to create the model deployment |
| `configure_agents_groq.py` | (Superseded — API-based approach that didn't persist) Configures LLM via PUT API per node |
| `fix_llm_config_db.py` | Direct DB patch: LLM config + system_prompt for all AGENT nodes |
| `fix_structured_output.py` | Direct DB patch: structured_outputs schema for the fetcher node |
| `seed_altair_schema.py` | Creates the 12-table Altair business schema + seeds 5 test cases + taxonomy |
| `seed_more_cases.py` | Seeds 40 additional dummy test cases |
| `localtest.md` | This file |

---

## Changes to Revert Before Any Git Commit

**🔴 Only ONE file is git-tracked and modified — must revert:**

```
Tadastudio\New-Tada\docker-compose.yml
  → Added `postgres` service (marked "LOCAL DEV ONLY" comment)
  → Added `depends_on: postgres` to backend
  → Added KEY_POSTGRES_* env vars to backend
  → Added `postgres_data_local_dev` volume

Revert with: git checkout -- Tadastudio/New-Tada/docker-compose.yml
```

**🟡 Not git-tracked (`.env` is gitignored) — no action needed, but for reference:**

```
Tadastudio\New-Tada\.env  (entire file is new/local-only)
  LLM_GUARD_MODE=disabled
  SKIP_AUTH=true
  DEV_USER_EMAIL=dev@localhost
  DEV_USER_NAME=Dev User
  ADMIN_USERS=dev@localhost
  HTTP_REQUEST_ALLOWED_IPS=jsonplaceholder.typicode.com
  CREDENTIAL_ENCRYPTION_KEY=Kowir40RI5cTSVogmvSYtmgnwMSMt82jNQDS5R0lB-s=
```

**🔵 Local database state (your own Docker Postgres container, isolated, not committed anywhere):**

1. Imported workflow "WF-Email-Triage-v7.9.1 (Copy)TadaTeam"
2. Created model_deployment "groq-llama" (Groq key stored encrypted)
3. Patched `graph_definitions.definition_json` directly (LLM config + system prompts on 27 agent nodes)
4. Added `structured_outputs` to the fetcher node
5. Created 12 new Altair business tables
6. Seeded taxonomy reference data + 45 dummy test cases
7. Multiple workflow executions logged in execution history tables

To fully wipe: `docker-compose down -v` (removes the Postgres volume entirely)

**🟢 Scratch files outside the repo** — not part of git at all, safe to leave or delete anytime.

---

## How to Resume Next Session

```cmd
cd C:\Users\Dell\Desktop\Mashreq\Tadastudio\New-Tada
docker-compose up postgres backend frontend
```

Wait for "Application startup complete", then open http://localhost:3000

If the graph's in-memory state seems stale after a restart, force a reload:
```cmd
curl -s -X POST "http://localhost:8000/api/graph/reload/WF-Email-Triage-v7.9.1%20(Copy)TadaTeam"
```
