<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI Project Context

Conceptual and scholarly context for anyone (human or agent) reasoning about DerridAI. Rules that apply to every change are in [AGENTS.md](../AGENTS.md); this document explains the reasons behind them.

Each capability carries a status. This table is maintained against current `master`; implementation details should still be verified in code before making a change:

- **Implemented** — present in the code.
- **Partial** — present in part; the gap is stated.
- **Intended** — a design goal not yet in the code. Do not describe it as existing.

## Mission

DerridAI is a local-first, evidence-grounded scholarly research environment, corpus manager, RAG system, and RAG/LLM evaluation framework, initially built around the works of Jacques Derrida. It is not a "chat with PDFs" tool. Its goal is AI-assisted philosophical research that is auditable from a generated claim back to exact source evidence.

Success is scholarly reliability, auditability, provenance, reproducibility, and local control. A fluent answer with a wrong attribution or a fabricated citation is a failed answer.

## The provenance chain

```text
SOURCE → PASSAGE → SPEAKER → POSITION HOLDER → STANCE → PROPOSITION → EXACT EVIDENCE → CITATION → CLAIM
```

Ordinary RAG keeps `chunk → similarity → answer`. DerridAI keeps the bibliographic and intellectual structure in between.

Derrida is a demanding test case because a passage he wrote often states someone else's position: he quotes, describes, reconstructs, questions, or criticizes other philosophers, and editors' and translators' text sits beside his own. These are different facts and must not be flattened:

```text
document_author = Derrida, speaker = Derrida, position_holder = Kant
speaker = Derrida, quoted_speaker = Heidegger, stance = critical
```

Neither of those means "Derrida believes X."

## Principles

1. **Evidence before eloquence.** A plainer answer with correct evidence beats a polished one that cannot be substantiated.
2. **Source identity is structured data.** Author, work, edition, translator, pages, and record identity come from the database, not from an LLM's recollection.
3. **LLM output is untrusted until validated.** Parsing as JSON does not make it correct.
4. **Deterministic code owns deterministic facts:** IDs, lookups, citations, page resolution, schema checks, exact quote existence, dedup, embedding dimensionality, job and cache state. LLMs handle semantic interpretation.
5. **Send only what is needed** in API requests, prompts, and updates. Use operation-specific schemas rather than one giant record payload.
6. **Failure stays visible.** Unresolved segmentation, failed extraction, thin evidence, and uncertain attribution are surfaced, not hidden behind manufactured certainty.
7. **Human control is first-class.** Researchers can inspect, edit, annotate, select, reject, rerun, and override.

## Corpus model

Conceptual hierarchy: `AUTHOR → WORK → EDITION/TRANSLATION → SOURCE DOCUMENT → DOCUMENT REGION → RECORD`. A work is not a source file: one work can have many editions/translations with different pagination, and one source container can hold several texts plus editorial/translational material.

| Capability                                                                                                                      | Status      | Notes                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Bibliographic fields (`translator`, `edition`, `original_title`, `isbn`, `canonical_work_id`)                                   | Implemented | Carried in corpus records and work metadata; `canonical_work_id` is derived from the title                                                                                                                                     |
| Document regions (`front_matter`, `main_text`, `notes`, `bibliography`, `index`, `back_matter`, `paratext`)                     | Implemented | Non-primary regions are excluded from primary-text status; reviewer-confirmed layout is authoritative                                                                                                                          |
| Attribution fields (`speaker`, `quoted_speaker`, `position_holder`, `target`, `stance`, `discourse_role`, `proposition_status`) | Implemented | Closed-vocabulary/schema validation; schema-valid non-empty model values remain visible for review, while calibrated autofill requires 90% blended confidence by default plus cited evidence and reviewer-precision safeguards |
| Explicit edition/translation relationships between works                                                                        | Partial     | Metadata fields exist; there is no cross-edition entity model or aligned passages                                                                                                                                              |
| Cross-language passage alignment and translation comparison                                                                     | Intended    | English/French collections are mirrored, but passages are not aligned                                                                                                                                                          |

## Corpus building

Supervised pipeline, not a text splitter: source validation, media-specific extraction/transcription, source-span normalization, structure/region detection, semantic segmentation, boundary validation, record assembly, metadata/attribution enrichment, validation, review, publication, indexing. PDF, text/RTF/DOCX, image, audio, URL, and Gutenberg sources use media-appropriate controls and evidence coordinates.

| Capability                                                             | Status      | Notes                                                                                                                                 |
| ---------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Semantic (not fixed-size) records with boundary validation             | Implemented |                                                                                                                                       |
| Unresolved segmentation regions preserved and retryable                | Implemented | Text is kept and marked; not collapsed into a confident result                                                                        |
| Source coverage and text-fidelity gate before publication              | Implemented | Publication is blocked until it passes                                                                                                |
| Bounded retry and review-provider escalation for structured LLM output | Implemented | Escalation is for malformed or failed output                                                                                          |
| Escalation triggered by validator-detected semantic ambiguity          | Partial     | Triggers are retry/failure driven, not general ambiguity signals                                                                      |
| Conservative text cleanup that preserves source truth                  | Implemented | Immutable extracted source is retained alongside cleaned/reviewed text                                                                |
| Multi-format source ingestion with bounded safety checks               | Implemented | Format-specific limits/provenance; active embedded content is not executed; audio uses timed evidence rather than fake page semantics |

Invariant: normalized input text should equal the concatenation of the resulting record texts, up to explicitly defined normalization. Segmentation must not lose, invent, duplicate, or reorder text.

Preprocessing must be conservative. Do not strip stopwords or normalize aggressively; words such as _not, without, if, perhaps, only, as if_ can determine the proposition. Take particular care with punctuation, quotation marks, emphasis, capitalization, proper names, French/Greek/German terms, and Derridean coinages.

## Retrieval and research

| Capability                                                                      | Status      | Notes                                                                                               |
| ------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------- |
| Dense, lexical, and MMR retrieval with RRF merge and dedup                      | Implemented | Search types are selectable per run                                                                 |
| Cross-encoder reranking with lexical fallback                                   | Implemented | Fallback is reported in run diagnostics                                                             |
| Language routing across `en`/`fr` derived collections                           | Implemented |                                                                                                     |
| Researcher-selected evidence (skip retrieval, synthesize from chosen passages)  | Implemented | `selected_evidence` on the run request                                                              |
| Canonical-work inference (question → likely central works → targeted retrieval) | Intended    | No question-to-work routing exists in `rag.py`; `canonical_work_id` is used for dedup and citation  |
| Evidence sufficiency validation before synthesis                                | Partial     | The prompt tells the model to say when evidence is insufficient; no deterministic sufficiency check |

The retrieval unit should be a scholar-useful discourse unit. Canonical-work routing, if added, is a prior, not an absolute filter unless the user restricts the scope.

## Citation, validation, and provenance

| Capability                                                                          | Status      | Notes                                                                                                                                                                 |
| ----------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Deterministic inline/full citations from record fields                              | Implemented | `rag.py` builds them from record metadata; the LLM cites evidence IDs (`E1`…) that are replaced by code                                                               |
| Answer binding to evidence IDs                                                      | Implemented | Prompt requires an evidence ID on every substantive claim                                                                                                             |
| Exact-quote existence check against source text                                     | Intended    | No post-generation quote or span validator                                                                                                                            |
| Claim/support persistence and source-revision binding                               | Partial     | Generated claims and support bindings can be persisted/resolved with stale-source detection; deterministic semantic entailment/attribution validation is not complete |
| Structural validation of LLM JSON (schema, enums, truncation)                       | Implemented |                                                                                                                                                                       |
| Relational validation (does the passage really attribute X to Y?)                   | Intended    |                                                                                                                                                                       |
| Claim graph (`claim → position holder → stance → evidence → source span → edition`) | Partial     | Claim/support objects and provenance memory exist; the full normalized scholarly relation graph and validators remain a longer-term direction                         |

Severe errors are not averaged into a quality score: assigning another philosopher's view to Derrida, fabricating a quotation, binding a claim to the wrong source or page, claiming support where the passage says the opposite, dropping negation, or treating editors' text as Derrida's.

## Evaluation and reproducibility

| Capability                                                                           | Status      | Notes                                                                             |
| ------------------------------------------------------------------------------------ | ----------- | --------------------------------------------------------------------------------- |
| LLM grading on multiple dimensions, stored on the response-cache entry               | Implemented | Grader provider/model/time kept as history                                        |
| Self-grading warning (same model generated and graded)                               | Implemented |                                                                                   |
| Saved run parameters, evidence, retrieval diagnostics, answer                        | Implemented | Response Library plus durable Research response/claim memory and support bindings |
| Full experiment record (prompt/template version, candidate list, validation results) | Partial     | Some, not all, of these are retained                                              |
| Severe-provenance-failure rate as a tracked metric                                   | Intended    |                                                                                   |

## Data and architecture notes

- **Vector stores are derived data.** The corpus/review/provenance stores are authoritative; ChromaDB collections and semantic projections can be deleted and rebuilt. Embedding model and dimension must match a collection.
- **Metadata exemplars are derived reviewed precedents.** Canonical reviewer decisions and evidence live outside the vector projection. Corrections carry rejected values as negative evidence, and confirmed absence is reusable only when explicitly evidence-bound.
- **Research memory is distinct from metadata memory.** Prior responses/generated claims/support bindings and metadata-enrichment precedents have different scopes and must not be merged simply because both use retrieval.
- **The response cache is a system/operational store, not a corpus store.** It is exposed as `_response_cache` and stored physically as `derridai_response_cache`.
- **Provider profiles are centralized** and reused by segmentation, metadata, audits, RAG, grading, and configured embedding work. Do not build per-feature model selectors.
- **Long operations are visible** as cancellable jobs. In-flight execution is process-local, while job snapshots/history are durably mirrored; interrupted work is marked failed on restart rather than silently replayed.
- Subsets (`source_kind: subset`) and annotations are stored and usable as RAG and search inputs.

## Failure modes to watch for

Records that are far too small or large; every region becoming unresolved; truncated LLM JSON; page-offset errors between PDF and printed pages; applying page/PDF semantics to non-paged media; unsafe or unbounded source parsing; editorial material attributed to Derrida; neighboring-record context contaminating speaker attribution; quoted philosophers treated as Derrida; lost negation; over-aggressive cleaning; stale evidence/support bindings silently rebound to newer text; unreviewed model output promoted as memory; wrong work inference; hallucinated bibliographies; embedding dimension mismatch; provider settings not reaching the model; hidden background resource use; oversized payloads; duplicated frontend state; grades not saved; self-grading without a warning; a vector projection treated as canonical data.

## Checklists

**Proposing a feature.** What scholarly problem does it solve? What is the source of truth? What can be deterministic, and what genuinely needs an LLM? How is the result validated, inspected, and reproduced? What happens when the model fails? How much data moves? Does it add attribution risk or lose edition/page provenance? Could a smaller model do it safely, with a validator deciding when to escalate?

**Evaluating an answer.** Is the question answered? Is every important claim supported, from the right work and page? Are the right speaker and position holder represented, with stance and negation preserved? Does the passage actually support the claim? Are countervailing passages omitted, or certainty overstated? Could a researcher audit it?
