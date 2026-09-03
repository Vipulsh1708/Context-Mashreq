# Embedding Strategy — Decision and Reasoning

**Context:** Part of the Tada Studio data/context layer architecture assignment (see `context.md` Part 12/14, `project_vipul_data_layer_assignment` memory). This covers the embeddings sub-decision — which model turns finished chunks (from `chunking-strategy.md`) into searchable vectors — following the same pattern as `parsingstrategy.md` and `chunking-strategy.md`: list real options, evaluate against our banking/compliance context, decide, and document what's still open.

---

## 1) The Decision

**Final decision: Azure OpenAI `text-embedding-3-large`, accessed in-tenant.**

Confirmed 2026-09-03: Arabic/multilingual support is **not** a requirement for this platform's document mix, which closes the one open item that could have flipped this toward Cohere. The remaining items in section 7 (in-tenant approval, cost-at-scale modeling, data-residency stress-test) are still open, but none of them changes *which model* — only how it gets deployed/sized.

---

## 2) The Options Considered

**Category A — Proprietary/API-based:**
1. OpenAI's `text-embedding-3` (small/large), via Azure OpenAI in-tenant
2. Cohere Embed (multilingual-v3)
3. Voyage AI embeddings

**Category B — Open-source/self-hostable:**
4. BGE (`bge-large-en`, `bge-m3`)
5. E5 / multilingual-E5
6. Nomic Embed
7. Jina Embeddings (v2/v3) — notably, the model family that supports **late chunking**
8. GTE (General Text Embeddings)

**Category C — Domain-tuned:** no mainstream ready-made banking-specific embedding model exists; would require fine-tuning a Category A/B base model ourselves — a build, not a pick.

---

## 3) Why API (Category A), Not Self-Hosted (Category B)

**The trade-off, as evaluated:** Category A trades data control for convenience and zero infrastructure maintenance — text is sent to the vendor's service (even if "in-tenant," it's still their infrastructure processing it). Category B keeps everything on Mashreq's own infrastructure, but means owning the compute (GPU/CPU) and ongoing maintenance of running the model ourselves.

**Why Category A was chosen, being honest about the reasoning:** this was a practical, pragmatic call rather than an exhaustively justified one. The core reasoning: self-hosted parsing (Docling, Tier 1 in `parsingstrategy.md`) already covers the primary on-prem/data-residency need at the *parsing* stage — the raw document content is already kept in-network there. Standing up and maintaining a *second* piece of self-hosted infrastructure (GPU capacity for an open-source embedding model) on top of that, when an in-tenant Azure OpenAI relationship is already being pursued anyway for the Vision-LLM tier (Tier 3), adds infrastructure ownership without a clearly demonstrated need. Going with Category A reuses that same tenancy conversation instead of opening a new one.

**What this means honestly:** this decision has not been rigorously stress-tested against a specific, confirmed data-residency requirement that would rule out an in-tenant API call — it assumes that "in-tenant Azure" is an acceptable boundary for embeddings the same way it's being treated as acceptable for Vision-LLM. If that assumption turns out to be wrong (e.g. compliance requires embeddings specifically to never leave fully-owned infrastructure, even in-tenant), this decision would need revisiting in favor of a self-hosted Category B option — most likely Jina (since it also unlocks late chunking) or BGE-m3 (since it also handles multilingual + hybrid dense/sparse in one model).

---

## 4) Why Azure OpenAI, Not Cohere or Voyage, Within Category A

- **Voyage AI — ruled out.** High benchmark quality, but not available via in-tenant Azure. Choosing it would mean a brand-new vendor relationship and a brand-new governance/data-residency review, for a provider with no existing foothold in Mashreq's infrastructure conversations, for no clearly demonstrated quality gain over OpenAI's models that would justify that cost.
- **Cohere — ruled out for now, conditionally, not permanently.** Cohere's multilingual embeddings are a genuinely strong option specifically for Arabic-language content. This wasn't dismissed on merit — it's parked pending confirmation of whether Arabic support is actually a real requirement (see section 5). If confirmed yes, this decision should flip to Cohere.
- **Azure OpenAI (OpenAI's models via Azure) — chosen.** Reuses the exact in-tenant tenancy/governance relationship already being pursued for the Vision-LLM tier (Tier 3 of the parsing cascade) — meaning one approval conversation covers both, instead of separate ones per vendor.

---

## 5) Why `text-embedding-3-large`, Not `text-embedding-3-small`

**The hard constraint that shaped this decision:** embedding vectors from different models (or the same model at different output dimensions) cannot be meaningfully compared to each other. A vector from `small` and a vector from `large` don't live in the same mathematical space — comparing them for similarity produces meaningless results. This rules out any cascade-style approach here (unlike parsing, where cheap tools escalate to expensive ones per-document) — **whichever model is chosen must be used consistently across every chunk that needs to be searched together**, platform-wide, not decided per document or per content type.

**Given that constraint, the choice came down to where the accuracy stakes actually are:**
- This is a bank; a wrong retrieval match has real consequences, not just a UX inconvenience.
- Significant care already went into getting chunk *boundaries* precisely right (row-based chunking with the backfill rule, hierarchical parent-child linking, metadata tagging — see `chunking-strategy.md`). Using a weaker embedding model on top of that careful chunking work would undercut the accuracy those decisions were meant to protect.
- `large` has meaningfully better retrieval accuracy on standard benchmarks than `small`.

**The cost lever preserved instead of downgrading models:** both `small` and `large` support a `dimensions` API parameter that lets you request a smaller output vector than the model's default (large defaults to 3072 dimensions). If storage/embedding cost at full platform scale becomes a real problem later, **reducing `large`'s output dimensions is the lever to pull** — not downgrading to `small` outright, which would mean a genuine accuracy drop rather than a storage optimization.

---

## 6) What This Decision Resolves in `chunking-strategy.md`

Section 3 of `chunking-strategy.md` ("Conditional / Infra-Dependent") left **late chunking** open, pending whether the platform's embedding model supports it. Late chunking requires a model that exposes token-level embeddings before pooling — standard embedding APIs, including Azure OpenAI's `text-embedding-3` family, return a single pooled vector per input, not token-level embeddings.

**This decision resolves that: late chunking is off the table.** The fallback described in `chunking-strategy.md` section 1.8 — **contextual prefixing + reranker** — is now the actual plan for that gap, not a hedge held in reserve. (If the self-hosted fallback in section 3 above is ever triggered — e.g. Jina — that would reopen late chunking as a real option, since Jina's embedding family is specifically what supports it.)

---

## 7) What's Still Open

1. **Arabic/multilingual requirement — RESOLVED 2026-09-03: not a requirement.** No longer a risk to this decision.
2. **In-tenant Azure OpenAI approval/setup** — same open item already flagged in `parsingstrategy.md` for the Vision-LLM tier. This decision assumes that gets confirmed; if in-tenant Azure OpenAI turns out not to be viable at all, both this decision and the Vision-LLM tier need revisiting together.
3. **Real cost at platform scale** — `large`'s per-token cost, multiplied by the chunk volume our row-based chunking approach produces (many small chunks per document), hasn't been modeled against actual expected document volume. Worth a rough cost estimate once volume assumptions are available, using the `dimensions` parameter as the adjustment lever if needed (see section 5).
4. **Data-residency stress-test** — as noted in section 3, the choice of Category A over Category B assumes in-tenant Azure is an acceptable boundary; this hasn't been explicitly confirmed against Mashreq's actual compliance requirements for embeddings specifically (as distinct from the same question already open for Vision-LLM).
