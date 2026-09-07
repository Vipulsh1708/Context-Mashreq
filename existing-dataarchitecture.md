# Data Lifecycle & Context Layer — Existing (As-Is) Architecture

**Source:** Screenshots of an architecture-analysis document (Step 15 of 16) generated from the actual current Tada Studio codebase — transcribed here verbatim/faithfully from the images, not from theory or assumption.

**What this page covers:** the data and knowledge hub lifecycle — insertion, storage, retrieval, runtime usage — and governance gaps, as a basis for the context-layer redesign work.

---

## 1) End-to-End Lifecycle (Current State in Code)

**Lifecycle diagram: Ingestion to Runtime Context**

```
Upload file → Create document row → Parse + chunk → Generate embeddings → Store chunks + vectors →
Search (vector / text / hybrid) → Inject into agent context
```

1. **Insertion: upload API receives files**
   Route `backend/api/documents/router.py` (`/api/documents/upload`) validates ownership, file type, and collection constraints.

2. **Raw asset persistence**
   `backend/services/document_storage/service.py` persists originals either to local storage (`workspace/documents`) or Azure Blob (`azureblob://...` references).

3. **Processing and chunk creation**
   The same service loads content through loader factories, chunks via chunking strategies, and annotates chunk metadata (page/source/chunk index).

4. **Embedding generation**
   `backend/services/document_storage/embeddings/manager.py` resolves the embedding model; `backend/services/document_storage/embeddings/batch_processor.py` batches embedding calls with retry and token/cost accounting.

5. **Structured storage**
   `backend/services/document_storage/storage/repository.py` writes into `documents` and `document_chunks` (with vector field), then marks status processed/failed.

6. **Retrieval API and search modes**
   `backend/api/documents/router.py` `/search` calls `backend/services/document_storage/search_service.py` for similarity, text, or hybrid retrieval across selected collections.

7. **Workflow runtime context consumption**
   `DOCUMENT_SEARCH` tool nodes and `DOCUMENT_LOAD` executor consume retrieved chunks/full content and inject outputs into workflow state for downstream `AGENT` prompts.

---

## 1a) Granular Flow Diagram (added 2026-09-02)

A more detailed view of the same seven-stage lifecycle above, showing the actual data domains it touches and exactly where the three gaps below bite in the live flow (not just as an abstract list).

```mermaid
flowchart TD
    subgraph UPLOAD["1. Insertion"]
        U1["User uploads file"] --> U2["backend/api/documents/router.py<br/>/api/documents/upload"]
        U2 --> U3{"Validate:<br/>ownership / file type /<br/>collection constraints"}
    end

    subgraph PERSIST["2. Raw Asset Persistence"]
        U3 -->|pass| P1["backend/services/document_storage/service.py"]
        P1 --> P2{"Storage target?"}
        P2 -->|local| P3["workspace/documents<br/>(local filesystem)"]
        P2 -->|cloud| P4["Azure Blob<br/>(azureblob://... reference)"]
        P3 --> P5["documents.storage_path<br/>(pointer saved)"]
        P4 --> P5
    end

    subgraph PROCESS["3. Processing & Chunk Creation"]
        P5 --> C1["Loader factories<br/>load content by file type"]
        C1 --> C2["Chunking strategies<br/>(GAP: mostly parameter-driven,<br/>no adaptive policy per content type)"]
        C2 --> C3["Annotate chunk metadata<br/>page / source / chunk index<br/>(lightweight only)"]
    end

    subgraph EMBED["4. Embedding Generation"]
        C3 --> E1["embeddings/manager.py<br/>resolves embedding model"]
        E1 --> E2["embeddings/batch_processor.py<br/>batches calls + retry +<br/>token/cost accounting"]
    end

    subgraph STORE["5. Structured Storage"]
        E2 --> S1["storage/repository.py"]
        S1 --> S2[("documents table<br/>status, ownership,<br/>embedding cost/tokens")]
        S1 --> S3[("document_chunks table<br/>(pgvector)<br/>chunk text + vector field")]
        S1 --> S4{"Mark status"}
        S4 -->|success| S5["processed"]
        S4 -->|failure| S6["failed"]
    end

    subgraph ACCESS["Collection Access Model (cross-cutting)"]
        A1[("document_collections<br/>.visible_to_groups (JSONB)")]
        A2["Owned / shared / all<br/>filtering + read-only views"]
        A1 --> A2
        A3["GAP: orphan-blob fallback<br/>bypasses collection auth<br/>when DB row missing"]
    end

    subgraph RETRIEVE["6. Retrieval"]
        S3 -.available to search.-> R1["backend/api/documents/router.py<br/>/search"]
        A2 -.access filter.-> R1
        R1 --> R2["search_service.py"]
        R2 --> R3{"Search mode"}
        R3 -->|vector| R4["Embed query, vector distance<br/>in document_chunks,<br/>top-k + metadata + source links"]
        R3 -->|text| R5["PostgreSQL full-text ranking<br/>tsvector / tsquery,<br/>lexical matches + snippets"]
        R3 -->|hybrid| R6["Combine vector + text ranks,<br/>reciprocal-rank-fusion scoring"]
        R4 --> R7["Results + metadata<br/>(chunk/doc IDs, file URL,<br/>query embedding cost)"]
        R5 --> R7
        R6 --> R7
        R7 -.GAP: no reranker /<br/>citation confidence layer.-> R7
    end

    subgraph RUNTIME["7. Workflow Runtime Consumption"]
        R7 --> W1["DOCUMENT_SEARCH tool node"]
        R7 --> W2["DOCUMENT_LOAD executor"]
        W1 --> W3["WorkflowState.node_outputs<br/>+ execution history tables"]
        W2 --> W3
        W3 --> W4["Injected into<br/>downstream AGENT prompt"]
    end

    style C2 fill:#ffe0e0
    style A3 fill:#ffe0e0
    style R7 fill:#ffe0e0
```

**The three red points are where the Section 4 gaps live in the actual flow, not just as an abstract list:**
- **Chunking step (Stage 3):** parameter-driven, no content-type awareness — this is precisely what `chunking-strategy.md` is designed to replace.
- **Access model:** the orphan-blob fallback that skips authorization entirely when a document's DB row is missing — a live governance risk, not a future one.
- **Retrieval output:** no reranker/citation-confidence layer sits between search results and what gets used downstream.

Everything else in this diagram — upload validation, blob/local persistence, embedding batching with retry/cost tracking, the three search modes, workflow injection — is working infrastructure the redesign builds on top of, not replaces.

---

## 2) Data Domains in the Knowledge Hub

| Domain | Current Storage | Usage | Main Files |
|---|---|---|---|
| Raw document files | Azure Blob or local filesystem path in `documents.storage_path` | Download/view, reprocessing source | `backend/services/document_storage/service.py` |
| Document metadata | `documents` table | Status, ownership, embedding cost/tokens, listing/filtering | `backend/services/document_storage/storage/repository.py` |
| Knowledge chunks + vectors | `document_chunks` table (pgvector) | Semantic and hybrid retrieval | `backend/services/document_storage/search_service.py` |
| Collection-level access model | `document_collections.visible_to_groups` (JSONB) | Owned/shared/all filtering and read-only views | `backend/services/document_storage/collections/repository.py` |
| Execution context output | `WorkflowState.node_outputs` + execution history tables | Prompt context chaining, run replay, observability | `backend/services/nodes/executors/document_load.py` |

---

## 3) Retrieval Behavior in Practice

**Vector search:** Embeds user query, computes vector distance in `document_chunks`, returns top-k chunks with metadata and source links.

**Text search:** Uses PostgreSQL full-text ranking (`tsvector`/`tsquery`) over chunk content for lexical matches and snippets.

**Hybrid search:** Combines vector and text result ranks with reciprocal-rank-fusion style scoring for better recall/precision balance.

**Metadata capture:** Search metadata includes chunk/document identifiers, file URL/source location, and query embedding cost metrics.

---

## 4) Current Gaps in the Context Layer

| Gap Area | Observed Gap | Impact |
|---|---|---|
| Knowledge modeling | Chunks are mostly text slices with lightweight metadata, no ontology graph or canonical entity/relation layer. | Weak reasoning over relationships, limited explainability and lineage. |
| Cross-collection intelligence | Search is collection-scoped and query-time fused, without a global knowledge index strategy. | Lower recall for enterprise knowledge spread across domains. |
| Authorization consistency | Collection access checks exist, but orphan-blob fallback paths explicitly bypass collection authorization when the DB row is missing. | Potential governance risk and audit complexity for detached artifacts. |
| Chunk quality controls | No adaptive chunking policy per content type/domain confidence; mostly parameter-driven chunking. | Context fragmentation and variable retrieval quality. |
| Grounding and reranking | No dedicated reranker/citation confidence layer beyond base vector/text/hybrid ordering. | Higher hallucination risk under ambiguous queries. |
| Lifecycle versioning | Document reprocessing exists, but no first-class semantic versioning for chunks and ontology evolutions. | Difficult comparison, rollback, and impact analysis after re-indexing. |

**Note — direct link to the ongoing chunking-strategy work:** the "Chunk quality controls" gap ("no adaptive chunking policy per content type/domain confidence; mostly parameter-driven chunking") is exactly the problem the current chunking-strategy evaluation (see this session's Strategy 1-16 walkthrough on bank statement samples) is meant to address — the existing system doesn't pick a chunking approach based on what kind of document/content it's looking at, it just applies fixed parameters regardless of content type.

---

## 5) Redesign Direction for Knowledge Hub 2.0

**Redesign flow diagram:**

```
Raw assets → Normalization + enrichment → Ontology mapping → Hybrid indexes (vector + lexical + graph) →
Policy-aware retrieval → Grounded answer package
```

**Ontology layer:** Introduce entity, relation, and concept taxonomies so retrieval can answer not only "what text matches" but also "what relationships are relevant." *(Direct match to Vishal's ontology/knowledge-graph expansion of the assignment — see context.md Part 14.)*

**Knowledge RAG:** Add a multi-stage retriever: candidate generation, reranking, evidence packing, and citation confidence scoring before LLM generation.

**Governance-by-design:** Unify data access checks across document, chunk, and blob paths. Enforce deny-by-default with complete access audit events.

**Re-index lifecycle:** Version embeddings/chunks per strategy and model, track drift metrics, and enable rollback to known-good retrieval snapshots.

---

## 6) Practical Roadmap Starter

1. Stabilize current ingestion and authorization boundaries; remove unmanaged orphan access paths.
2. Add retrieval evaluation harness: precision@k, recall@k, groundedness, citation quality, latency and cost.
3. Introduce ontology extraction pipeline and persist entity-relation graph alongside chunk vectors.
4. Add reranker and evidence-pack builder between retrieval and AGENT prompt assembly.
5. Roll out collection-to-workspace governance model and policy-aware query planner for enterprise scale.

**What this unlocks:** A stronger context layer turns Tada from "workflow automation with document lookup" into a governed enterprise knowledge system where answers are grounded, explainable, and policy-compliant by default.

---

## 7) Vishal's Own Review Slides (2026-09-03) — Confirmed vs. NOT VERIFIED

**Source:** Screenshots of Vishal's "Data Handling Strategy" deck, slides titled "Review One-Pager — Confirmed, Unverified, Operational" and "End-to-End Flow — Upload to Agent Context." This is a **different, more authoritative source** than Sections 1-6 above (which came from an AI-generated code review) — this is Vishal's own team explicitly stating what is confirmed vs. unverified in the current system.

### 7a) Confirmed by Approved Facts

- Raw bytes: Azure Blob when enabled; local filesystem fallback only; `storage_path` ref held in `documents`.
- PostgreSQL schema: `documents` (metadata, status, storage_path); `document_chunks` (chunk_text, chunk_metadata, embedding via pgvector).
- Retrieval composition: similarity = vector distance; text = full-text; hybrid = candidates → fusion/rerank → cross-collection merge → top-k. Collection-level authorization runs before retrieval.
- Verified technical parameters: `chunk_size` = 1000 chars, `chunk_overlap` = 200 chars (character-based, not token-based), `strategy` = recursive, `embedding_batch_size` = 64, `embedding_retries` = 3, `retry_delay` = 1.0s **(note: an earlier slide from the same deck stated 1.5s — unresolved discrepancy between two of Vishal's own slides, needs confirming)**. Token and cost accounting is tracked in the embedding and search flow.

### 7b) NOT VERIFIED (Vishal's own list, not our assumption)

- Unknown thresholds: default `k`, similarity score cut-offs, context size limits.
- Unknown formulas: distance metric, hybrid fusion algorithm, rerank algorithm.
- Unknown runtime tuning: embedding model identity (!), vector dimensionality, queueing behavior, dead-letter behavior, intermediate status values.
- Sub-collection permission enforcement, audit logging, policy lineage.
- Evidence durability, reproducibility, all KPI baselines.

**No baseline exists for any of these metrics:** retrieval latency, precision@k, groundedness, policy deny/allow accuracy, processing cost per document. All five explicitly marked NOT VERIFIED — meaning current retrieval quality has never actually been measured.

**Readiness stated on the slide:** "Current-state architecture is review-ready with the listed NOT VERIFIED items" — i.e. Vishal's team considers this an honest, acceptable snapshot, not a finished verification.

### 7c) End-to-End Flow — 10 Numbered Steps

**Upload & Persist:** (1) Upload accepted — backend API. (2) File persisted — raw bytes in blob/local. (3) Document record created — `documents` row.

**Transform & Index:** (4) Content parsed/extracted — output: parsed text; failure → `failed`. (5) Text chunked — output: chunks, 1000/200 chars, recursive. (6) Embeddings generated — output: vectors, batch 64, 3 retries @ 1.0s. (7) Chunk rows persisted — output: `document_chunks` + embedding.

**Retrieve & Inject:** (8) Status updated — outcome: processed or failed. (9) Authorized search executed — artifact: ranked evidence set. (10) Context injected — chunk text + chunk_id + doc_id + source ref.

**Retrieval decision sub-flow (detail on step 9):**
`Mode select (similarity/text/hybrid) → Candidate generation (vector distance / full text) → Fusion/rerank (hybrid mode only) → Cross-collection merge (results across collections) → Top-k context shaping (chunk + ids + source ref)`

**Assumptions explicitly marked NOT VERIFIED on this slide:** embedding model, vector dimensionality, distance metric, fusion/rerank formula, default k, queueing and dead-letter behaviour, status values.

### 7d) Where This Contradicts Sections 1-6 Above

The AI-generated review (Sections 1-6) stated some things as confirmed facts that Vishal's own team explicitly marks as unverified:

| Claim | Sections 1-6 (AI review) says | Section 7 (Vishal's slides) says |
|---|---|---|
| Hybrid fusion algorithm | States as fact: "reciprocal-rank-fusion style scoring" | NOT VERIFIED — fusion/rerank formula unknown |
| Reranker | States as confirmed gap: "No dedicated reranker... layer" | A "Fusion/rerank" step already exists in the flow (hybrid mode only) — unverified whether it's functional, not confirmed absent |
| Cross-collection search | States as confirmed gap: "without a global knowledge index strategy" | A "Cross-collection merge" step already exists in the flow — unverified whether functional |

**Practical implication:** treat "reranker" and "cross-collection search" as **verify-and-fix** items, not necessarily **build-from-scratch** items, until Dipankar confirms whether these named steps actually execute working code or are stubs/placeholders. The orphan-blob authorization bypass (Section 4) is not addressed either way by Vishal's slides — it remains sourced only from the AI review and still needs independent verification.

### 7e) Update (2026-09-03) — Dipankar confirms cross-collection search works

Dipankar confirmed: **the Document Search UI already supports selecting multiple collections and searching across them to answer one query.** This resolves the "cross-collection merge" item from the unverified list above — it is not a stub, it is real, working functionality today.

**What this changes:**
- "Cross-collection search" moves from "VERIFY FIRST" to **CONFIRMED WORKING**. It is no longer a build-from-scratch item.
- **Still open:** the *quality* of how results from multiple collections get merged/ranked together is not yet confirmed — i.e. does it properly re-rank combined results, or does it just concatenate separate per-collection result lists? This is a narrower, quality-focused question rather than an existence question.
- The "Fusion/rerank" step's status is **still unresolved** — Dipankar's confirmation covered cross-collection merge specifically, not the fusion/rerank algorithm. That item remains VERIFY FIRST.
- The orphan-blob authorization bypass also remains unverified — not addressed by this update.
