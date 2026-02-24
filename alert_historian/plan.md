# Narrative Engine — Phase 1: Blueprint

**Vision:** Move from *Passive Alerts* to *Active Intelligence* — not just "what happened today" but *how today's news changes the story that began months ago.*

**Scope:** Ingest Google Alert email histories (IMAP or exported JSON), then produce:
1. **Daily summary** of events  
2. **Persistent, evolving narrative timeline** (Long-term Chronicle)

---

## 1. Sub-Agent Module Decomposition

### 1.1 Ingestion Agent (Data Layer)

**Responsibilities**
- Connect to Gmail via IMAP (or accept exported JSON for batch/backfill).
- Filter messages by Google Alerts: target `List-ID: <alerts.google.com>` (and/or `X-Google-Alert-*` / `From: googlealerts-noreply@google.com` as fallbacks).
- Parse each alert: subject (query/topic), date, snippet list, optional link list.
- Clean and normalize text (strip HTML, truncate, normalize whitespace).
- Deduplicate snippets (e.g., content hash or fuzzy match) and optional per-alert dedup by URL.
- Output a **canonical alert payload** (e.g., JSON) for downstream agents: `{ alert_id, topic, date, snippets[], urls[], source }`.

**Difficulty:** [MEDIUM]  
- IMAP + OAuth2 (or app password) and folder selection is standard but has edge cases (rate limits, pagination).  
- List-ID parsing is [EASY]; robust dedup and snippet extraction across varied alert HTML layouts is [MEDIUM].

**Deliverables**
- `ingestion/` module: IMAP client, alert filter, parser, dedup, schema.
- Optional: JSON export adapter for Takeout or manual export.
- Config: `IMAP_HOST`, `IMAP_USER`, credentials path or env, `ALERT_LIST_ID` / sender allowlist.

---

### 1.2 Narrative Memory Agent (Intelligence Layer)

**Responsibilities**
- **RAG strategy:** Store alert snippets (and/or summarized “events”) in a **vector DB** for semantic retrieval.  
  - **Recommendation:** Start with **ChromaDB** (local, zero config, good for dev and single-user). Option to add **Pinecone** (or similar) later for scale/compliance.
- **Embedding:** Use a single embedding model for all content (e.g., OpenAI `text-embedding-3-small`, or local `sentence-transformers`) so that “today’s alert” can be retrieved by similarity to “past narrative.”
- **Recursive summarization:**  
  - Maintain a **Long-term Chronicle** (e.g., one or more markdown files or structured docs by theme/time).  
  - After each run (e.g., daily): (1) retrieve relevant past context from the vector store for “today’s” alerts; (2) run a summarization step that *updates* the Chronicle (append/revise sections) so the narrative evolves.
- **System 2–style reasoning:** A dedicated prompt (or small chain) that analyzes the *delta* between recent alerts and the Chronicle to detect:  
  - **Shifts in industry velocity** (e.g., “coverage of X has doubled in the last 2 weeks”),  
  - **Sentiment or framing changes** (e.g., “tone moved from skeptical to adoption-focused”).  
  Output: structured notes (e.g., JSON or markdown) that the Orchestrator can fold into the digest.

**Difficulty:** [HARD]  
- RAG + ChromaDB is [MEDIUM].  
- Recursive summarization that keeps the Chronicle coherent and non-redundant is [HARD].  
- Reliable “velocity/sentiment” detection is [MEDIUM] (prompt design + few-shot or light eval).

**Deliverables**
- `narrative_memory/` module: vector store client, embedding pipeline, Chronicle read/write, “System 2” analysis prompt/chain.
- Config: vector DB path (Chroma) or Pinecone env vars, embedding model name, Chronicle file path(s).

---

### 1.3 Orchestrator & Digest Agent (Delivery Layer)

**Responsibilities**
- **Orchestration:** In order: run Ingestion → pass canonical alerts to Narrative Memory → run Memory’s summarization and System 2 step → then format output.
- **Daily report:** Produce a **high-signal Markdown report** (e.g., `reports/daily/YYYY-MM-DD.md`):  
  - Brief “What happened today” (from daily summary),  
  - **Narrative Delta** section: e.g., “This alert confirms a trend we first saw in Oct 2025” (from Memory’s RAG + Chronicle).  
- **Narrative Delta:** Use Memory’s retrieval to link today’s items to past Chronicle entries and emit 1–2 sentence “story links” per major topic.

**Difficulty:** [MEDIUM]  
- Wiring the pipeline and file output is [EASY].  
- Designing the Markdown template and stable “Narrative Delta” phrasing from RAG results is [MEDIUM].

**Deliverables**
- `orchestrator/` or `digest/` module: pipeline runner, report template, Narrative Delta formatter.
- Output: daily Markdown report plus optional JSON manifest (e.g., list of report paths and timestamps).

---

### 1.4 Forecasting Module (Analytic Layer)

**Responsibilities**
- A **prompt chain** that uses:  
  - Historical context from the Chronicle and/or vector DB,  
  - Recent velocity/sentiment from the Narrative Memory agent,  
  to project **6‑month trajectories** (e.g., “Where is topic X heading?”).  
- Output: short narrative or bullet summary (e.g., Markdown or JSON) that can be included in the weekly digest or on-demand.

**Difficulty:** [HARD]  
- Consuming Chronicle + RAG context is [MEDIUM].  
- Designing a prompt chain that yields stable, useful (and optionally calibrated) forecasts is [HARD].

**Deliverables**
- `forecasting/` module: prompt chain, optional few-shot examples, output schema.
- Trigger: on-demand or on a schedule (e.g., weekly); output path configurable.

---

## 2. Tech Stack Proposal

| Layer           | Recommendation        | Rationale |
|----------------|------------------------|-----------|
| **Runtime**    | **Python 3.11+**      | Best fit for IMAP libs, ML/embedding libs, and async pipelines; aligns with your existing FastAPI/Python use (e.g. careful-clinical-core). |
| **API / Jobs** | **FastAPI** + CLI      | FastAPI for optional REST endpoints (e.g. trigger run, health); primary execution via **CLI** or **scheduled job** (cron / launchd) for daily ingest + digest. |
| **Vector DB**  | **ChromaDB** (default) | Local, no API keys for the DB itself; easy to swap to Pinecone later via a thin abstraction. |
| **Embeddings** | **OpenAI** or **sentence-transformers** | OpenAI for best quality and simplicity; sentence-transformers for local/offline and cost control. |
| **LLM**        | **OpenAI API** or **Anthropic** | For summarization, System 2 reasoning, and forecasting; keep provider behind an interface for swap. |
| **Config**     | **pydantic-settings** + `.env` | Centralized config and secrets (IMAP, API keys, paths). |
| **Project layout** | `src/<package>/` + `pyproject.toml` | Single package (e.g. `narrative_engine`) with submodules: `ingestion`, `narrative_memory`, `orchestrator`, `forecasting`. |

**Non-goals for Phase 1**
- No Next.js/frontend required for the blueprint; optional later.
- No real-time streaming; batch daily (or configurable interval) is sufficient.

---

## 3. Tooling & MCP Suggestions

- **Web search (for future enrichment):** Use an **MCP server that exposes web search** (e.g. Cursor’s built-in web tools, or a dedicated “search” MCP). Useful for: validating or enriching alert snippets and for “today’s context” in the Forecasting module.  
  - *Suggestion:* Configure once in Cursor/IDE for ad-hoc research; the Narrative Engine itself can remain batch-only in Phase 1.

- **Long-term memory / context:** For *agent–agent* or *run-to-run* context (e.g. “what the system already said about topic X”), the **Narrative Engine’s own Chronicle + vector DB** is the source of truth. For *IDE/LLM* long-term memory (e.g. user preferences or project context), consider the **Memory MCP Server** (knowledge graph: entities, relations, observations) so that Cursor/agents can recall prior decisions.  
  - *Suggestion:* Use Memory MCP for project-level “how we decided X” and the app’s ChromaDB + Chronicle for narrative content.

---

## 4. Difficulty Summary

| Step | Module                  | Rating   |
|------|-------------------------|----------|
| 1    | Ingestion Agent         | [MEDIUM] |
| 2    | Narrative Memory Agent  | [HARD]   |
| 3    | Orchestrator & Digest    | [MEDIUM] |
| 4    | Forecasting Module      | [HARD]   |

---

## 5. Suggested Implementation Order

1. **Ingestion** — So we have canonical alert data for all other modules.  
2. **Narrative Memory (RAG + Chronicle)** — Core intelligence; Digest depends on it.  
3. **Orchestrator & Digest** — Wire pipeline and daily report.  
4. **System 2 / velocity–sentiment** — Enhance Memory output.  
5. **Forecasting** — Add once Chronicle and Memory are stable.

---

## 6. Approval Gate

**Phase 1 ends here.** No implementation or sub-tasks will be started until you review this plan and approve (or request changes). Once approved, the next step is to scaffold the repo (e.g. under `alert_historian/` or a new `narrative-engine/` directory) and then implement modules in the order above.

---

*Document version: 1.0 — Phase 1 Blueprint*
