# DERRIDAI Core Specification 1.0

**Document-Extracted Record Retrieval Information Design for Artificial Intelligence**

**Author:** Dr. Aaron John Schlosser  
**Affiliation:** The New England Transcendental Club of California  
**Specification Version:** 1.0  
**Date:** September 2026  
**Status:** Normative specification

DERRIDAI defines a normalized, traceable, and reproducible information architecture for AI-assisted documentary research. In the name DERRIDAI, **Retrieval** is used in both a broad research sense - the recovery of relevant documentary information for active use - and a narrower technical sense that includes vector, lexical, hybrid, filtered, and other computational search methods. Vector search is one retrieval mechanism, not the meaning of the specification as a whole.

## Contents

- [How to Read This Specification](#how-to-read-this-specification)
- [Foundations](#foundations)
- [Documentary and Record Layer](#documentary-and-record-layer)
- [Publication, Storage, and Retrieval](#publication-storage-and-retrieval)
- [Evidence, Claims, Traceability, and Reproducibility](#evidence-claims-traceability-and-reproducibility)
- [Interfaces, Validation, and Governance](#interfaces-validation-and-governance)
- [Interoperability, Portability, and External Standards](#interoperability-portability-and-external-standards)
- [Extensibility, Conformance, and Reference Schemas](#extensibility-conformance-and-reference-schemas)

---

## How to Read This Specification

The specification is organized from the most durable information outward. It begins with sources and Records, then defines metadata assertions and semantic relations, then describes evidence acquisition and AI use, and finally addresses APIs, deployment, versioning, and conformance.

The specification deliberately uses technical object names such as **SourceSpan**, **FieldAssertion**, and **EvidenceRef**. These names refer to conceptual roles; an implementation does not have to use the same class names, database tables, or programming language. What matters is that it preserves the required distinctions and relationships.

> **Normative versus explanatory text.** Requirements containing MUST, MUST NOT, SHOULD, SHOULD NOT, or MAY define conformance. Plain-language notes and examples explain the intent of those requirements but do not add new requirements.

## Foundations

### Status, Purpose, and Normative Language

#### Status and purpose

Document-Extracted Record Retrieval Information Design for Artificial Intelligence (DERRIDAI) defines an information model and interoperability requirements for transforming documents into records that can be extracted, enriched, reviewed, stored, located, selected as evidence, supplied to artificial-intelligence systems, and traced back to authoritative sources.

The specification is intended for systems in which document provenance, attribution, evidentiary support, source identity, record identity, normalization, traceability, information quality, and reproducibility materially affect the credibility of AI-assisted research.

DERRIDAI is not a retrieval algorithm, model protocol, vector-database format, user-interface specification, or single application architecture. It defines the information that must remain stable across such systems and the relationships that must be preserved when information moves between them.

A conforming implementation MAY use local or remote databases, files, object stores, APIs, vector indexes, local models, hosted models, browser clients, desktop applications, command-line tools, or other technical means. Conformance depends on preservation of the DERRIDAI information model and invariants, not on implementation technology.

The DerridAI application is the originating reference implementation.

#### Normative terms

The terms **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are normative. MUST and MUST NOT are necessary for conformance to the applicable profile. SHOULD and SHOULD NOT may be departed from only for a documented reason that does not violate a MUST-level invariant. MAY describes permitted behavior.

Sections explicitly marked _Non-normative_ are explanatory.

#### Design goals

A DERRIDAI system is designed so that: heterogeneous documentary inputs are normalized into stable research objects with declared semantics; documentary data remains traceable to source; logical record identity remains distinct from storage identity; source facts remain distinguishable from deterministic derivations, model inferences, human judgments, unresolved states, and explicit absence; retrieval diagnostics remain properties of retrieval events rather than of the source record; evidence can be bound explicitly to generated claims; research runs retain enough versioned state for substantial reproducibility; source-derived facts such as identifiers, page maps, schema validity, and citation structure are handled deterministically when possible - that is, by fixed procedures whose results do not depend on model interpretation; uncertainty remains representable; and derived indexes do not silently replace authoritative corpus state.

> **Core rule.** The identity, provenance, and evidentiary integrity of documentary information MUST survive the transformations between source extraction and AI-assisted research, while computational mechanisms operating over that information remain replaceable.

### Architectural Model

#### Durable Research Layer

A DERRIDAI implementation SHOULD distinguish a **Durable Research Layer** from derived computational state. The Durable Research Layer comprises research information whose identity or scholarly meaning is intended to persist across model substitutions, index rebuilds, prompt changes, and research runs.

It MAY include SourceDocuments, SourceUnits, SourceSpans, Records, RecordRevisions, bibliographic metadata, MetadataSchemas, FieldAssertions, Relations, human review decisions, annotations, CorpusPublications, and other domain-specific durable objects.

#### Derived Computational Layer

Embeddings, vector indexes, lexical indexes, query decompositions, retrieval rankings, reranker scores, model contexts, caches, temporary evidence ordering, and generation state SHOULD be treated as derived or run-specific unless an implementation explicitly declares otherwise.

A rebuildable derived representation MUST NOT silently become more authoritative than the corpus or source data from which it was created.

#### Conceptual flow

The normative conceptual flow is:

`SourceDocument -> SourceSpan -> Record -> EvidenceAcquisition -> Evidence -> GenerationRun -> GeneratedClaim`

with the auditable reverse path:

`GeneratedClaim -> SupportBinding -> EvidenceRef -> RecordRevision -> SourceSpan -> SourceDocument`.

A system MAY omit stages that are not applicable. For example, a search-only implementation need not perform generation, and a long-context system may acquire evidence without a vector retrieval stage.

> **Plain-language summary.** The core obligation is traceability. A system may use very different software internally, but it should still be able to answer: Which source did this Record come from? Which version of the Record was used? Which evidence supported this claim?

#### Research normalization

DERRIDAI normalization concerns the information model rather than stylistic normalization of source text. A conforming implementation MUST give durable research objects stable identifiers and declared semantics sufficient to distinguish source identity, Record identity, revisions, source locations, metadata assertions, evidence references, and run-specific computational state.

A domain profile MAY add specialized metadata fields. Such specialization MUST NOT silently redefine the semantics of Core identifiers or provenance relations. Normalization therefore establishes a common structural contract while preserving domain-specific interpretation.

> **Plain-language interpretation.** Two corpora do not need the same scholarly vocabulary to conform to DERRIDAI. They do need to agree on what a Record is, how it points back to a source, how revisions are identified, and how later evidence and claims refer to it.

## Documentary and Record Layer

### Source Documents and Source Location

#### SourceDocument

A **SourceDocument** represents a documentary source from which records derive. It MUST have a stable `source_document_id`. The identifier MUST NOT depend solely on a temporary path, vector-store identifier, browser identifier, or database row number.

When the original source bytes are available, an implementation SHOULD record a cryptographic content digest - a compact digital fingerprint computed from the file contents. The digest identifies a digital representation; it MUST NOT automatically be treated as the identity of the abstract intellectual work.

A SourceDocument SHOULD support, where applicable: `source_document_id`, `source_hash`, `media_type`, `source_filename`, `source_uri`, `title`, `document_author`, `edition`, `translator`, `publisher`, `publication_place`, `publication_year`, `original_language`, `document_language`, `page_count`, and domain metadata.

#### Physical and scholarly location

DERRIDAI distinguishes physical navigation from scholarly citation. An implementation MUST NOT silently assume that physical PDF page number and printed page number are equivalent.

A location MAY include `physical_page`, `printed_page`, `printed_page_label`, `volume`, `section`, `chapter`, `paragraph`, `column`, bounding boxes, and character offsets. When multiple page systems exist, the representation MUST identify which system a value belongs to.

#### SourceUnit

A **SourceUnit** is an addressable unit produced directly or near-directly from document extraction, such as a PDF block, OCR region, paragraph candidate, XML node, line group, or page region. A SourceUnit SHOULD include a stable ID, source-document ID, extracted text, location, unit type, extraction method, and extraction confidence where available.

SourceUnits MUST NOT acquire semantic significance merely because they are physical extraction units.

#### SourceSpan

A **SourceSpan** identifies the documentary region from which a Record or EvidenceRef derives. It MUST refer to one SourceDocument and MAY be represented using SourceUnit IDs, page ranges, offsets, bounding boxes, or another reproducible locator.

A SourceSpan MUST NOT imply greater precision than the implementation actually possesses. The implementation SHOULD declare locator precision when exact offsets are unavailable.

### Records, Identity, Revisions, and Text Fidelity

#### Record

A **Record** is the central DERRIDAI information object. It represents a persistent research unit derived from one or more contiguous or explicitly related SourceSpans.

A conforming Record MUST contain `record_id`, `source_document_id`, `text`, and `source_spans`. It MAY also contain bibliographic, linguistic, semantic, discourse, attribution, indexing, and domain-specific metadata.

A Record MUST NOT contain retrieval rank, vector distance, reranker score, UI selection state, or other operation-specific values as though those were intrinsic source properties.

#### Record identity

`record_id` MUST identify the logical Record. Storage-system identifiers MUST NOT silently replace it.

A metadata edit that does not change the identity of the represented source unit SHOULD preserve `record_id` and create a new revision when publication-relevant state changes. An edit to authoritative text MAY preserve `record_id` when the same conceptual research object remains represented, but MUST create a new RecordRevision.

Splitting one Record into two or more independently retrievable Records MUST create new record IDs. Merging two or more Records into a new independently retrievable Record SHOULD create a new record ID. Lineage SHOULD be retained. Retired IDs MUST NOT be reused for unrelated material.

#### RecordRevision

A **RecordRevision** identifies a specific state of a Record. It SHOULD record `record_id`, revision identifier, creation time, actor, change reason, and parent revision where applicable.

A revision identifier MUST change when authoritative record text changes and SHOULD change when publication-relevant metadata changes. Evidence that depends on offsets or hashes SHOULD identify the applicable RecordRevision.

An implementation MUST NOT silently resolve an EvidenceRef against a different revision when doing so changes the evidence referenced.

#### Record text and source text

DERRIDAI distinguishes source-extracted text from reviewed or normalized record text. When extracted text is modified, the implementation MUST preserve sufficient information to determine what changed, by retaining the original extraction, an immutable source representation from which it can be reconstructed, or an auditable transformation trail.

Cleaning MAY correct extraction artifacts, formatting noise, or layout reconstruction. Cleaning MUST NOT silently paraphrase, summarize, translate, alter proposition-bearing negation, remove meaningful qualification, or normalize away semantically material distinctions.

Model-based correction MUST be treated as an inference or proposal unless explicitly accepted under the implementation’s authority policy.

#### Text-conservation invariant

When a source scope is segmented into Records, source text MUST NOT be silently lost, invented, duplicated, or reordered. The normalized concatenation of resulting coverage SHOULD equal the normalized source content of the declared scope except for explicitly declared exclusions or overlaps.

Provider failure, malformed model output, or model uncertainty MUST NOT by itself justify discarding source material.

### Record Field Classes and Assertions

#### Field classes

Implementations SHOULD distinguish at least: identity fields; source-bound fields; document-inherited fields; semantic or interpretive fields; derived fields; and operational fields. Operational fields MUST NOT be silently published as scholarly record content.

#### FieldAssertion

A value stored on a Record and an assertion concerning that value are distinct concepts. A **FieldAssertion** SHOULD support `field`, `value`, `status`, `method`, `checked`, `confidence`, `reason`, `evidence_refs`, `actor`, `model`, and `created_at` where relevant.

An implementation MAY materialize the currently authoritative value directly on the Record for convenience. Provenance of interpretive or disputed values SHOULD remain available separately.

#### Assertion status

DERRIDAI defines the base statuses `deterministic`, `model_inferred`, `human_confirmed`, `human_override`, `unresolved`, `invalid`, and `confirmed_absent`. Profiles MAY add others.

`unresolved` and `confirmed_absent` MUST NOT be treated as equivalent.

#### Checked state and confidence

Systems MUST distinguish, when relevant, among not evaluated; evaluated with a result; evaluated with no supported value; evaluated but confidence unavailable; and evaluation failed.

A field MUST NOT be described as checked merely because a processing stage ran somewhere in the same record.

Confidence MUST be metadata about an assertion rather than an intrinsic property of the source fact. Numeric confidence SHOULD use a documented scale, normally 0 to 1. A system MUST NOT fabricate numeric zero because confidence was omitted. `confidence: null` MAY represent an explicitly unavailable confidence when the field was in fact evaluated.

Implementations MUST NOT present confidence as a calibrated probability unless calibration has actually been established.

#### Disagreement and authority

A system MAY retain multiple FieldAssertions for the same field. When deterministic, inherited, model-derived, and human-derived values disagree, the implementation SHOULD retain the disagreement rather than overwriting it without trace.

The implementation MUST have a declared authority or resolution policy for selecting a materialized current value. A human override MUST be explicit and auditable.

### Attribution and Semantic Relations

#### Scholarly attribution

The DERRIDAI Scholarly Attribution Profile RECOMMENDS support for the following fields when their distinctions are relevant:

- `speaker`, `quoted_speaker`, `quoted_author`, and `quoted_work`;

- `quoted_position_holder`, `quoted_addressee`, and `quoted_referent`;

- `quotation_chain`;

- `position_holder`, `target`, `stance`, `discourse_role`, and `proposition_status`.

A passage written by an author does not entail that every proposition within it is held by that author. A conforming Scholarly Attribution implementation MUST be able to represent a difference between document author or textual speaker and proposition holder.

#### Relation

Implementations requiring greater generality SHOULD represent semantic relationships as **Relation** objects with a relation ID, subject, predicate, object, epistemic status, evidence references, and assertion references where applicable.

Profiles MAY define controlled predicates. Relations MUST retain the epistemic status of the information from which they are derived.

### Metadata Schemas

#### MetadataSchema

A DERRIDAI implementation MAY support configurable MetadataSchemas. A schema defines what metadata fields exist, their types and allowed values, validation rules, and, when applicable, what an AI system is instructed to evaluate.

A schema SHOULD declare a schema ID, schema version, name, description, groups, fields, and content hash. Field definitions SHOULD declare name, type, group, allowed values, strictness, instruction, evidence requirement, assessment requirement, and review requirement where applicable.

Schema-defined fields MUST NOT silently collide with reserved identity, source, provenance, or operational names.

#### Locked core fields

A profile MAY identify locked core fields whose semantics cannot be removed or redefined by a user schema. An implementation MUST publish the names and semantics of its locked fields. A schema editor MUST NOT permit a custom field to shadow a locked field.

#### Schema snapshots

When a processing run depends on a configurable schema, the run MUST retain either the exact schema snapshot or an immutable reference to that exact version. Editing a saved schema after a run begins MUST NOT silently alter the semantics of the active or completed run. A schema content hash SHOULD be retained.

### Lifecycle, Transformation, Segmentation, and Review

#### Lifecycle

DERRIDAI does not mandate a UI workflow. Implementations SHOULD nevertheless be able to represent a lifecycle such as source, extracted, segmented, enriched, reviewed, published, indexed, acquired as evidence, and used in research.

A Record MAY be searchable before human review if the applicable profile permits it, but its review and epistemic states MUST remain inspectable.

#### Transformation

A meaningful change from source or prior record state SHOULD be representable as a **Transformation** identifying input, output, operation, method, actor, model where applicable, parameters, time, and reason. A transformation SHOULD state whether it was deterministic, human, model-assisted, or model-generated.

A transformation that changes source-derived text SHOULD be auditable.

#### Segmentation

Segmentation boundaries MAY be semantic, structural, editorial, retrieval-engineering, or human-defined. An implementation MUST NOT represent an engineering size split as semantic evidence merely because it created a Record boundary.

Protected attribution or syntax transitions SHOULD NOT be crossed merely to satisfy a preferred record size when a safer alternative exists.

#### Human review

Human review is an authority event. Review decisions SHOULD record actor, time, previous value, new value, reason, affected field, and RecordRevision.

A human-confirmed semantic value MUST NOT later be overwritten silently by a background model job. Contradictory later evidence SHOULD create a dispute, alternative assertion, or reopened review state rather than silently replacing the human decision.

## Publication, Storage, and Retrieval

### Publication and Corpus Interchange

#### CorpusPublication

A **CorpusPublication** is an immutable snapshot intended for interchange, indexing, citation, analysis, or later retrieval. It MUST identify `publication_id`, `corpus_id`, publication version, applicable specification or schema version, creation time, and records or immutable references to them.

Once declared final, a CorpusPublication MUST NOT be changed in place. Corrections MUST create a new publication or revision.

#### Publication validation

Before publication, every published Record MUST pass structural validation. At minimum, `record_id`, `source_document_id`, non-empty `text`, and `source_spans` MUST be present; typed values MUST match declared types; and controlled fields MUST satisfy applicable vocabularies.

Publication MUST fail rather than silently remove a required field whose absence would break provenance.

#### Operational-field exclusion

Queue state, temporary credentials, UI flags, worker checkpoints, cache keys, and similar implementation details MUST NOT be included in a public Record unless a publication profile explicitly defines them as provenance. A publication MAY include a separate build-provenance object.

#### JSONL profile

The DERRIDAI JSONL Profile defines one complete published Record per UTF-8 line. Line order MUST NOT be the only means of identifying records. Each Record MUST contain its own `record_id`.

Implementation-specific public formats, including `derridai-corpus-jsonl-v1`, MAY define additional requirements while remaining mappings of the DERRIDAI Core model.

### Storage and Derived Representations

#### Authoritative corpus

A DERRIDAI implementation MUST identify its authoritative corpus representation. A vector store MUST NOT be treated as the sole authoritative source of record content when the system claims the vector store is derived or rebuildable.

If a derived store differs from the authoritative corpus, the discrepancy MUST be detectable.

#### StorageProjection

A **StorageProjection** is a technology-specific representation of a Record. It MAY contain `storage_id`, a RecordRef, document text, metadata, and embedding. `storage_id` MAY differ from `record_id`, but the mapping MUST remain recoverable.

A StorageProjection MUST NOT silently alter semantic Record values. Storage-specific encoding is permitted when decoding is lossless for the declared contract.

#### Embedding contract

A vector collection SHOULD declare embedding provider, model, immutable revision or digest where available, dimension, distance metric, indexed text field, and retrieval mode. Once vectors exist, an incompatible embedding change MUST NOT occur in place without explicit migration or rebuild. Dimension mismatches MUST fail explicitly.

#### Collection manifest

A derived retrieval collection SHOULD expose a manifest containing a manifest version, collection ID, source publication or snapshot identity, source record count, source works where relevant, embedding contract, filter fields, language coverage, collection role, build ID, build history, and status.

### Evidence Acquisition

#### General model

**Evidence Acquisition** is the process by which Records or source spans become candidates for evidentiary use. It provides a mechanism-neutral term for bringing documentary information into an evidentiary role.

#### Meaning of retrieval in DERRIDAI

The term **Retrieval** has two related meanings in this specification family. In the broad sense, retrieval is the recovery of relevant documentary information from the Durable Research Layer for active research use. In the technical sense, retrieval is a computational search operation over an index, store, or corpus using a defined query and retrieval method.

Vector similarity search is one technical retrieval method. Lexical search, metadata filtering, hybrid retrieval, database queries, and other computational methods are also retrieval methods. Human selection and model-located source spans participate in the broader recovery of evidence even when they do not constitute a conventional search query. The specification uses **Evidence Acquisition** when it needs a mechanism-neutral name for all such paths into evidence.

An acquisition method MAY be semantic retrieval, lexical retrieval, hybrid retrieval, deterministic filtering, database query, human selection, direct reference, agentic search, model-located source spans in a long context, or another method.

Every acquired evidence object intended for downstream audit SHOULD resolve to a persistent Record or SourceSpan regardless of acquisition method.

#### Acquisition provenance

An acquisition event SHOULD record its method, query or selection condition where applicable, source corpus or collection, parameters, time, and actor or computational component. Acquisition diagnostics MUST NOT become intrinsic Record metadata.

### Retrieval Profile

The DERRIDAI Retrieval Profile specifies the technical sense of retrieval: explicit search and ranking operations such as vector similarity search, lexical search, filtering, hybrid search, fusion, and reranking. It does not restrict the broader DERRIDAI concept of retrieval to vector databases.

#### RetrievalRun

A **RetrievalRun** represents one retrieval operation. It SHOULD record a retrieval-run ID, original query, source collections or publications, retrieval methods, parameters, and timestamps. If query decomposition or translation is used, the original user query MUST remain preserved and derived queries MUST be identified as derived.

#### RetrievalHit

A **RetrievalHit** describes one Record’s appearance in one retrieval route. It SHOULD include collection, search type, rank, raw score, and score semantics. A distance or similarity value MUST NOT be described as confidence or probability unless the retrieval system actually defines it that way.

#### RetrievalCandidate

A **RetrievalCandidate** wraps or references a Record and adds retrieval-specific information such as candidate ID, RecordRef, collection, distance, RRF score, rerank score, MMR score, RetrievalHits, and selection state.

At least one of RecordRef or embedded Record MUST be present. A RetrievalCandidate MUST NOT mutate the authoritative Record merely to attach retrieval information.

The same logical Record found through multiple routes SHOULD be deduplicated by logical identity while retaining all contributing RetrievalHits.

#### Fusion and reranking

When multiple retrieval routes contribute to a candidate, the fusion method MUST be recorded and route-specific ranks SHOULD remain available. Reranking MUST be represented as an operation on RetrievalCandidates, not as a change to Record metadata.

If a preferred reranker fails and a fallback is used, the fallback MUST be reported.

#### User-selected evidence

A user MAY designate a Record or RecordSpan as evidence independently of retrieval rank. Selected evidence MUST retain authoritative Record identity. A client SHOULD transmit a RecordRef rather than a complete Record when the server can safely rehydrate the authoritative source.

Selected evidence MAY bypass retrieval entirely and SHOULD be normalized into the same evidence model used by retrieved evidence so downstream citation and validation do not depend on acquisition method.

## Evidence, Claims, Traceability, and Reproducibility

### Evidence Profile

#### EvidenceRef

An **EvidenceRef** identifies exact source material used to support, contextualize, contrast with, quote, or otherwise bear on a downstream claim. It SHOULD contain an evidence-reference ID, Record ID, RecordRevision, SourceDocument ID, source spans, and exact offsets or another locator when the evidence is a strict subset of the Record. A quote hash MAY be included.

The local evidence-reference ID MUST NOT replace persistent Record identity.

#### EvidenceItem

An **EvidenceItem** combines an EvidenceRef with information needed by a research process. It SHOULD contain a run-local evidence ID, EvidenceRef, RecordRef or Record, acquisition provenance, inline citation, full citation, truncation state, and selection reason.

#### Evidence text and truncation

Evidence supplied to a model MAY be truncated. If it is, the truncation MUST be declared; the authoritative EvidenceRef MUST remain unchanged; and the full source SHOULD remain recoverable to an authorized auditor. Truncated text MUST NOT be represented as the complete Record.

#### EvidencePacket

An **EvidencePacket** is an ordered set of EvidenceItems supplied to or selected for a research operation. It SHOULD record packet ID, creation time, source publication IDs, items, context limit, and truncation policy where applicable. Reordering MUST NOT change underlying evidence identity.

#### Evidence sufficiency

Implementations SHOULD perform deterministic evidence-sufficiency checks before generation where possible. Evidence intended to support a scholarly claim SHOULD have Record identity, SourceDocument identity, non-empty exact text, work or document identity, and citation-resolvable location. Missing provenance MUST NOT be manufactured merely to satisfy a check.

### Citation

Citations SHOULD be generated deterministically from authoritative bibliographic and location metadata when those facts are available. An LLM MUST NOT be treated as authoritative for a citation that can be generated from structured corpus data.

If required citation metadata is unavailable, the system SHOULD report incompleteness rather than invent missing bibliographic facts.

A citation in generated output SHOULD originate from an EvidenceRef or EvidenceItem. Citation formatting MAY vary by style guide, but underlying source identity MUST remain stable across styles.

### Generation, Claims, and Support Bindings

#### GenerationRun

A **GenerationRun** represents an AI generation operation using DERRIDAI evidence. It SHOULD identify run ID, prompt, instructions, provider, model, model revision where available, generation parameters, prompt-contract version, evidence packet, execution locality, timestamps, and answer.

Secrets such as API keys MUST NOT be stored in a public GenerationRun.

#### Evidence-bounded generation

A DERRIDAI Evidence-Grounded Generation implementation MUST instruct the generator that supplied evidence is the basis for substantive source claims. The generator MUST NOT be instructed to fabricate supporting citations. When evidence is insufficient, the system SHOULD permit or require an explicit statement of insufficiency.

#### GeneratedClaim

A **GeneratedClaim** is a proposition or substantive assertion in generated output. It SHOULD contain claim ID, generation-run ID, claim text, answer offsets where available, support bindings, and claim status.

A system MAY omit explicit GeneratedClaim objects if it does not claim proposition-level traceability. A system claiming DERRIDAI Claim-Binding conformance MUST materialize or reproducibly derive them.

#### SupportBinding

A **SupportBinding** associates a GeneratedClaim with one or more EvidenceRefs. It SHOULD identify the relation between claim and evidence - for example, support, contrast, contextualization, quotation, or attribution - together with validation status and results where available.

A GeneratedClaim MUST NOT be described as supported by an EvidenceRef merely because the evidence appeared in model context.

#### Evidence markers and exact quotation

Temporary evidence markers such as `[[E0]]` MAY be used during generation and SHOULD be resolved deterministically afterward. Unknown evidence markers MUST NOT silently resolve to unrelated sources.

When a GeneratedClaim contains a purported exact quotation, a Claim-Binding implementation SHOULD verify that the quoted text exists in the cited authoritative source or declared normalized equivalent. A failed exact-quote check MUST NOT be silently treated as successful support.

#### High-severity relational failures

Validation systems SHOULD treat wrong-person attribution, fabricated quotation, wrong source binding, wrong page or span binding, support where evidence states the opposite, dropped proposition-bearing negation, and confusion of editorial or translator text with primary-author position as high-severity failures.

### Traceability Matrix

A DERRIDAI **traceability matrix** is the logical set of relations that connects research output to the documentary and computational state on which it depends. The matrix MAY be implemented as relational tables, graph edges, structured JSON, event records, or another representation; a literal tabular matrix is not required.

For a GeneratedClaim represented as evidentially supported, a Claim-Binding conforming implementation MUST be able to identify the applicable SupportBinding and EvidenceRef. The EvidenceRef MUST resolve to a Record or RecordRevision, and the Record MUST remain traceable to its SourceDocument and SourceSpan at the precision claimed by the implementation.

Where a claim depends materially on interpretive metadata, the implementation SHOULD retain the FieldAssertion or equivalent provenance that established the relevant value. Where a claim depends on a particular research run, the implementation SHOULD retain or reference the ResearchRunManifest that identifies the corpus state, evidence-acquisition configuration, model, prompt contract, and validation state.

The traceability relation can therefore be summarized as:

`Claim -> SupportBinding -> EvidenceRef -> RecordRevision -> SourceSpan -> SourceDocument`

with optional branches to FieldAssertions, Relations, RetrievalRuns, GenerationRuns, validators, and graders.

A system MUST NOT describe a claim as fully traceable merely because it contains a human-readable citation if the internal evidence-to-record or record-to-source relationship cannot be resolved.

> **Why call this a matrix?** In systems engineering, a traceability matrix shows how requirements connect to tests, implementations, or evidence. Here the same idea is applied to scholarship: a claim can be followed backward through the evidence and processing relationships that justify its presence in the research output.

### Reproducibility and Evaluation

#### Reproducibility levels

DERRIDAI distinguishes three levels of reproducibility. **Corpus reproducibility** identifies the source documents, publication snapshot, Record revisions, schemas, and other durable research state. **Process reproducibility** identifies the query, evidence-acquisition or retrieval configuration, candidate and selected evidence where retained, model/provider, prompt contract, generation parameters, validators, and graders. **Output reproducibility** concerns whether the same execution produces identical generated wording.

Core and Reproducible Research conformance MUST NOT imply byte-identical output reproduction from a stochastic or externally mutable model. The required goal is preservation of the research state and process information needed to reconstruct and evaluate the operation, with the limitations of the original execution environment made explicit.

#### ResearchRunManifest

A research system SHOULD maintain a **ResearchRunManifest** sufficient to inspect and substantially reproduce a run. It SHOULD identify specification version, corpus publications, collection manifests, original and derived queries, acquisition and retrieval parameters, candidate identifiers where relevant, selected evidence, evidence packet, generation model and parameters, prompt contract, execution locality, validation results, output, grader information, and timestamps.

DERRIDAI does not require bit-identical regeneration from nondeterministic models. It requires a distinction between reproducibility of inputs and configuration and deterministic reproduction of output.

#### Candidate retention

Benchmark and audit workflows SHOULD retain the candidate set presented to reranking or evidence selection. If only final evidence is retained, the implementation SHOULD disclose that retrieval reconstruction may be incomplete.

#### Grading

If output is graded by an AI model, the grade SHOULD record grader provider, model, immutable revision where available, grading prompt or contract version, dimensions, and time. A system SHOULD warn when the same model configuration generates and grades the same answer. Grades MUST NOT replace underlying evidence or validation records.

## Interfaces, Validation, and Governance

### Transport and API Contracts

#### Minimum necessary transport

DERRIDAI interfaces SHOULD send only the information necessary for the requested operation. The existence of a complete Record schema MUST NOT be interpreted as a requirement that every request transmit the complete Record.

#### Operation-specific envelopes

Interfaces SHOULD define narrow payloads such as RecordRef, RecordPatch, RecordSelection, RecordUpsert, AcquisitionRequest, RetrievalRequest, EvidenceSelection, GenerationRequest, ValidationRequest, and PublicationRequest. A universal request containing every possible field is NOT RECOMMENDED.

#### RecordRef

A **RecordRef** SHOULD contain only the information necessary to identify a Record, such as corpus ID, publication ID, Record ID, and RecordRevision. Storage-specific addressing MAY additionally include collection and storage ID, but storage-specific values MUST remain distinguishable from logical identity.

#### Sparse mutation

A partial update MUST contain only fields intended to change unless the operation is explicitly defined as full replacement. Omitted fields MUST mean “leave unchanged” in a sparse patch. `null` MUST NOT mean “leave unchanged” unless the schema explicitly says so. Deliberate clear MUST remain distinguishable from omission.

#### Audit deltas and rehydration

When mutation history is retained, a client SHOULD be able to send only new audit entries rather than round-tripping full history. When a server can rehydrate an authoritative Record from a RecordRef, clients SHOULD send the reference rather than the full Record unless the use case requires a client-local record.

#### Boundary validation

Transport boundaries MUST validate incoming data against the operation schema. Model output entering the authoritative data model MUST be validated separately from HTTP or serialization validity. Syntactically valid JSON is not sufficient evidence of semantically valid metadata.

### Validation

#### Validation classes

A DERRIDAI implementation SHOULD distinguish structural, type, vocabulary, referential, source-fidelity, evidence, relational, publication, and retrieval-contract validation.

#### Structural and referential validation

Structural validation determines whether an object satisfies required shape and types. Referential validation determines whether referenced entities exist and are compatible, including whether a RecordRef resolves, an EvidenceRef resolves to the specified revision, a SourceSpan resolves to the declared SourceDocument, and a collection manifest refers to an existing source snapshot.

#### Source-fidelity validation

Source-fidelity validation SHOULD detect missing coverage, duplicated coverage, out-of-order material, unsupported text insertion, unexpected text loss, invalid page mapping, and invalid span references.

#### Relational validation

Relational validation concerns whether semantic relationships are actually supported by evidence, such as whether a proposition is attributed to the correct person, a stated stance matches the passage, a quotation is actually a quotation, or a target is actually targeted. Such validation MAY require semantic inference and MUST NOT be described as deterministic merely because it runs automatically.

#### ValidationResult

A **ValidationResult** SHOULD identify validator, validator version, severity, code, entity reference, field where applicable, message, evidence references, and status. Severity SHOULD distinguish at least info, warning, error, and critical. Publication profiles MUST define which severities block publication.

### Failure and Uncertainty

Failures that can affect provenance, attribution, evidence, publication, or corpus integrity MUST remain visible. A system MUST NOT silently convert a failed semantic operation into a confident result. Fallback behavior MUST remain distinguishable from preferred-path success.

Model timeout, malformed structured output, unavailable provider, truncated JSON, or failed schema validation MUST NOT by themselves establish a semantic conclusion. A conservative fallback MAY preserve source material or existing authoritative values.

An unresolved state is a valid DERRIDAI state. Systems MUST NOT manufacture values solely to eliminate unresolved fields.

### Security, Access, and Disclosure

Authorization MUST be enforced at the authoritative data boundary, not solely in the user interface. A disabled client control is not sufficient enforcement.

An implementation MAY redact or transform source text for unauthorized clients while retaining permitted RecordRefs, evidence identifiers, citations, or metadata. Such a projection MUST NOT create a false impression that the client received the full source. Provider credentials, API keys, session secrets, and similar authentication material MUST NOT be included in public corpus publications, evidence packets, or public run manifests.

DERRIDAI does not itself establish legal compliance with copyright, confidentiality, data-protection, professional-privilege, or contractual regimes. Those depend on deployment, policy, and applicable law.

### Language and Translation

A Record MAY have a language different from the application interface language. Documentary language metadata MUST NOT be silently translated merely to match UI locale. Source text, quotations, bibliographic titles, and evidence SHOULD retain authoritative source language unless an explicit translation transformation is represented.

A translation used as evidence MUST remain distinguishable from the source-language text from which it derives. A translated Record or EvidenceItem SHOULD reference the source Record or SourceSpan when available. Machine translation MUST be identified as such.

### Model Independence and Execution Locality

#### Model independence

A conforming DERRIDAI implementation MUST preserve authoritative Record identity and documentary provenance independently of the language model, embedding model, retrieval engine, or provider used to process or consume those Records.

Replacing a computational model MUST NOT, by itself, alter authoritative Record identity, source relationships, or human-confirmed assertions.

#### Execution locality

A DERRIDAI system MAY execute locally, remotely, or in hybrid form. ResearchRun provenance SHOULD identify external computational services that receive source, Record, Evidence, or prompt content when that information is relevant to audit or policy.

The information model MUST NOT require remote custody of the authoritative corpus.

#### Pipeline sovereignty

DERRIDAI uses **pipeline sovereignty** to describe the technical capacity of a researcher or research organization to determine where stages of the documentary and AI-processing pipeline execute, where data is stored, and which external systems may receive it.

Pipeline sovereignty is an architectural property, not a legal conclusion about ownership, confidentiality, or compliance.

### Local Sovereign Profile

An implementation claiming **DERRIDAI Local Sovereign 1.0 Conformance** MUST permit essential research operations without mandatory remote storage, remote embedding, remote model inference, remote authentication, or remote telemetry.

At minimum, the profile MUST permit within researcher-controlled infrastructure: document ingestion; source storage; Record construction; metadata and provenance storage; corpus publication; search or evidence acquisition; evidence selection; citation; AI inference; validation; and research-output storage.

An implementation MAY additionally support hosted services. Use of such services MUST be optional for Local Sovereign conformance and SHOULD be identifiable as an explicit execution choice.

## Interoperability, Portability, and External Standards

### Interoperability Architecture

#### Purpose

DERRIDAI defines a domain-specific information architecture for AI-assisted documentary research. It does not attempt to replace general-purpose standards for provenance, research-object packaging, linked-data publication, workflow description, archival preservation, persistent identification, or machine-readable scholarly assertions.

A conforming implementation MAY expose DERRIDAI data through external standards where doing so improves portability, archival preservation, interoperability, or integration with other research systems. External representations MUST preserve the semantics of the authoritative DERRIDAI objects from which they are derived.

An external mapping MUST NOT become the authoritative source of Record identity, documentary provenance, human-confirmed metadata, or ResearchRun state merely because an export has been generated. Unless an implementation explicitly adopts an external representation as its native storage model, the normal relationship is:

`DERRIDAI native model -> interoperability adapter -> external representation.`

> **Why this separation exists.** A provenance standard can represent that one entity was derived from another. It does not necessarily know that the first entity is a passage from a particular edition, that Derrida is speaking while representing Levinas’s position, that a model inferred the position holder, or that a researcher later confirmed the inference. External standards provide reusable infrastructure; DERRIDAI supplies the research-specific semantics.

#### Three interoperability layers

A conforming implementation SHOULD distinguish three layers.

1.  **Native semantic layer.** The DERRIDAI objects and relations defined by this specification, including SourceDocument, SourceSpan, Record, RecordRevision, FieldAssertion, EvidenceRef, ResearchRun, GeneratedClaim, SupportBinding, and ValidationResult. This layer defines what the information means.

2.  **Interoperability mapping layer.** A translation from DERRIDAI semantics to another conceptual model, such as RecordRevision to a PROV Entity or ResearchRun to an RO-Crate contextual entity. This layer defines correspondence between information models.

3.  **Serialization and packaging layer.** The physical encoding or package, such as JSON, JSON-LD, RDF/Turtle, PROV-N, JSONL, ZIP, or RO-Crate. This layer defines how information is transported.

Implementations SHOULD avoid conflating these layers. JSON-LD, for example, is a serialization technology; it is not itself a provenance model.

#### Interoperability must not weaken scholarly meaning

An interoperability representation MUST preserve every DERRIDAI distinction necessary to interpret the exported object correctly. Where the target standard cannot directly express a DERRIDAI concept, the exporter MUST preserve the concept through a DERRIDAI-specific extension term, an associated DERRIDAI artifact, a documented companion representation, or an explicit loss-of-information declaration.

The exporter MUST NOT silently collapse materially different scholarly states. In particular, values such as `model_inferred`, `human_confirmed`, `deterministically_established`, `unresolved`, `confirmed_absent`, and `invalid` MUST NOT become indistinguishable merely because a target standard has no direct equivalent. Likewise, `speaker`, `document_author`, `quoted_speaker`, `position_holder`, and `target` MUST NOT be collapsed into a generic creator or author relation when doing so would alter scholarly interpretation.

#### Interoperability fidelity

DERRIDAI defines three descriptive levels of mapping fidelity.

- A **lossless mapping** preserves all DERRIDAI information required to reconstruct the exported object’s relevant semantics. Lossless does not require byte-identical serialization; it requires preservation of material meaning.

- A **semantically compatible mapping** preserves major identity, provenance, and research relationships while omitting nonessential implementation detail. For example, it may preserve RecordRevision, EvidenceRef, ResearchRun, model identity, and human review while omitting transient UI state.

- A **lossy mapping** omits one or more material DERRIDAI distinctions. A lossy exporter MUST identify the omitted semantic classes or fields and MUST NOT describe the export as a complete DERRIDAI representation.

#### Stable identifiers

Exporters SHOULD preserve native DERRIDAI identifiers rather than mint unrelated identifiers for every export. Where the corresponding object exists, exported representations SHOULD preserve `source_document_id`, `record_id`, `record_revision`, `publication_id`, `evidence_id`, `run_id`, and `claim_id`.

External representations MAY encode these identifiers as URIs or IRIs. Global resolvability is OPTIONAL for Core conformance. A local DERRIDAI implementation MUST be able to maintain stable identifiers without depending on an external identifier service.

#### Version identity

An exported object SHOULD identify the applicable DERRIDAI Core version, DERRIDAI profile versions, serialization-profile version, and external-standard version where those values are known. A version declaration MUST describe the contract under which the artifact was produced, not merely the current application version.

#### Interoperability and reproducibility

Interoperability asks whether another system can understand or consume a research object. Reproducibility asks whether enough state has been preserved to reconstruct, repeat, inspect, or meaningfully compare the research process. The two properties are complementary.

A PROV graph may be interoperable but insufficient for reproducing a ResearchRun if the EvidencePacket or model configuration is missing. Conversely, a complete local ResearchRunManifest may support substantial reproducibility even if it has not been exported through any external standard.

### DERRIDAI PROV Mapping Profile

#### Scope and purpose

The DERRIDAI PROV Mapping Profile defines how DERRIDAI research lineage can be expressed using the W3C PROV family of standards. W3C PROV supplies a general-purpose model based on **Entity**, **Activity**, and **Agent**. DERRIDAI uses this framework to expose the history of scholarly and computational objects without replacing DERRIDAI’s domain semantics.

In simplified terms, PROV addresses questions such as: What depended on what? What process occurred? Which person, organization, or software agent participated? DERRIDAI adds questions such as: What scholarly object was involved? Who was speaking? Whose position was represented? What was the epistemic status of a metadata assertion? Which exact source span supported the claim?

A DERRIDAI implementation MAY support this profile without using RDF, PROV-O, or PROV internally.

#### Entity mapping

The following DERRIDAI objects SHOULD be exportable as PROV Entities when present: SourceDocument, SourceUnit, SourceSpan, Record, RecordRevision, MetadataSchema, FieldAssertion, CorpusPublication, EvidenceRef, EvidenceItem, EvidencePacket, ResearchRunManifest, GeneratedClaim, ValidationResult, and GradeResult.

Where both Record and RecordRevision are exported, the persistent logical Record MUST remain distinguishable from a particular revision of that Record. A consumer MUST be able to determine which exact RecordRevision was used as evidence when the native ResearchRun preserves that information.

| **DERRIDAI object**                        | PROV-oriented representation                                                                           |
| :----------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| **SourceDocument, SourceUnit, SourceSpan** | Entity representing documentary material or an identified portion of it.                               |
| **Record, RecordRevision**                 | Entity representing persistent scholarly identity and a particular state of that identity.             |
| **FieldAssertion**                         | Entity whose lineage records inference, validation, confirmation, or override.                         |
| **CorpusPublication**                      | Entity representing an immutable/versioned corpus release.                                             |
| **EvidenceRef, EvidencePacket**            | Entity representing research evidence or a set of evidence supplied to a run.                          |
| **ResearchRunManifest**                    | Entity describing a preserved run state; associated Activities represent the operations that occurred. |
| **GeneratedClaim**                         | Entity representing an identified proposition or claim produced by generation.                         |
| **ValidationResult, GradeResult**          | Entity representing a result of validation or evaluation.                                              |

#### Record and RecordRevision

DERRIDAI distinguishes a persistent logical Record from particular revisions. This distinction SHOULD survive PROV export. Successive RecordRevisions SHOULD preserve their relationship to the persistent Record and to prior revisions. An implementation MAY use PROV specialization, derivation, revision relations, or DERRIDAI extension properties as appropriate.

`Record R17 -> RecordRevision R17@1 -> R17@2 -> R17@3.`

The exported graph MUST NOT force a consumer to infer a particular revision from timestamps when the native system has an explicit revision identifier.

#### Source derivation

A RecordRevision SHOULD be traceable to its documentary origin. A typical lineage is:

`SourceDocument D4 -> SourceSpan S42 -> RecordRevision R17@3.`

If a Record derives from multiple discontinuous SourceSpans, each material span SHOULD be represented. An exporter MUST NOT reduce multiple-source provenance to a single source merely for convenience.

#### Activity mapping

Processing steps SHOULD be exportable as PROV Activities when their provenance is material to audit, reconstruction, or scholarly interpretation. Examples include source extraction, OCR, normalization, page-map construction, segmentation, metadata inference, metadata validation, human review, Record revision, corpus publication, embedding generation, lexical indexing, vector indexing, query decomposition, retrieval, reranking, evidence selection, evidence-packet construction, generation, citation resolution, claim extraction, claim/evidence validation, and grading.

Not every internal function call needs to become a PROV Activity. Implementations SHOULD choose a level of granularity useful to research audit rather than exposing incidental software implementation detail.

#### Agent mapping

Researchers, reviewers, organizations, deterministic validators, LLM providers, language models, embedding models, rerankers, and other software components MAY be represented as PROV Agents or appropriate specialized agents. Human and computational agents MUST remain distinguishable where known.

Where model identity is material, the export SHOULD preserve provider, model name, model revision or digest where available, quantization where material, and runtime information where material. When an immutable revision cannot be established, the representation SHOULD state the identifier actually known rather than implying stronger reproducibility.

#### Human and machine participation

A central DERRIDAI requirement is preservation of the difference between computational inference and human scholarly judgment. If Model M inferred `position_holder = Levinas` and Reviewer H later confirmed it, the exported provenance SHOULD preserve the inference and review as separate activities. It SHOULD NOT rewrite the history as though the human originally supplied the value.

Likewise, a human override SHOULD preserve the fact that an earlier computational assertion existed when that history is retained in the native system.

#### Field-level epistemic provenance

Generic provenance alone is insufficient for DERRIDAI metadata. A FieldAssertion MUST retain DERRIDAI-specific epistemic properties when exported. PROV MAY describe the activities that generated and reviewed the assertion, but it MUST NOT replace DERRIDAI assertion status with a generic derivation relation.

For example, a PROV “was derived from” relation does not by itself establish whether a DERRIDAI assertion is human-confirmed, model-inferred, deterministically established, or unresolved. Those remain DERRIDAI semantics.

#### Retrieval and evidence-acquisition provenance

The PROV mapping MUST preserve the two senses of retrieval used by DERRIDAI. In the narrow technical sense, retrieval may involve vector similarity, lexical search, hybrid search, metadata filtering, or reranking. In the broader sense, retrieval is the recovery of relevant documentary information for research use.

An EvidenceAcquisition activity MAY therefore represent vector retrieval, lexical retrieval, hybrid retrieval, manual researcher selection, deterministic query, database lookup, model-located evidence, imported evidence, or another declared acquisition method. An EvidenceRef SHOULD retain its acquisition method where known.

#### Retrieval candidates and authoritative Records

A RetrievalCandidate is a contextual computational object. It MUST NOT replace authoritative Record identity in a PROV export. Retrieval rank, distance, RRF score, reranker score, MMR score, and similar diagnostics describe a candidate within a retrieval event; they do not become intrinsic properties of the underlying RecordRevision.

#### Generation provenance

A GenerationRun SHOULD be exportable as an Activity. It SHOULD identify, where known, the EvidencePacket used, prompt contract, model, provider, generation parameters, ResearchRun, and generated output. A generated answer SHOULD be represented as an Entity. Where the answer is decomposed into GeneratedClaims, those claims SHOULD also be separately identifiable.

#### Claim-to-evidence provenance

Where Claim-Binding is implemented, the exported graph SHOULD preserve:

`GeneratedClaim -> SupportBinding -> EvidenceRef -> RecordRevision -> SourceSpan -> SourceDocument.`

A consumer SHOULD be able to begin with a generated claim and identify the documentary material represented as supporting it.

#### Citation provenance

Citation rendering and documentary provenance MUST remain conceptually distinct. The exported representation SHOULD preserve the structured bibliographic and source-location information from which a citation is rendered. Changing citation style SHOULD NOT alter the underlying provenance.

#### Validation and grading provenance

A ValidationResult SHOULD preserve the object or relation it evaluated. If an LLM performs grading or validation, the model SHOULD be represented as a computational agent and the grading activity SHOULD remain distinguishable from deterministic validation. A model-generated grade MUST NOT be represented as though it were a deterministic fact.

#### Minimum PROV export

A DERRIDAI PROV export claiming the minimum mapping profile MUST preserve, where applicable, SourceDocument identity, Record identity, Record revision, source derivation, EvidenceRef identity, ResearchRun identity, GenerationRun identity, generated output identity, participating human or computational agents, and claim/evidence relationships when available.

A PROV export MUST NOT claim complete DERRIDAI provenance conformance if it omits a material lineage relationship known to the native system, such as RecordRevision, SourceSpan, human/model distinction, claim/evidence binding, or metadata epistemic status.

### DERRIDAI RO-Crate Profile

#### Purpose and profile identity

The DERRIDAI RO-Crate Profile defines how DERRIDAI research artifacts may be packaged into a portable research object. RO-Crate addresses a different problem from PROV: PROV describes how things came to exist and relate through processes; RO-Crate describes which research objects belong together, what they are, and how they can be packaged with machine-readable contextual metadata.

The DERRIDAI RO-Crate Profile SHOULD be published as a versioned RO-Crate profile with a persistent profile identifier and SHOULD identify the applicable RO-Crate version. A crate claiming the DERRIDAI profile MUST also satisfy the requirements of the declared RO-Crate version.

#### Crate scopes

DERRIDAI defines three conceptual crate scopes.

- A **Corpus Crate** represents a portable CorpusPublication and SHOULD contain or reference the corpus manifest, MetadataSchema, public Records, source-document descriptors, bibliographic metadata, and publication/version information. It MAY contain source documents, annotations, validation reports, PROV representation, and derived index manifests.

- A **Research Run Crate** represents a particular AI-assisted research operation and SHOULD contain or reference the ResearchRunManifest, corpus/publication identity, query, evidence-acquisition configuration, EvidencePacket, model configuration, prompt-contract identity, generated output, citations, validation results, grades, and warnings.

- A **Project Snapshot Crate** represents a broader research state and MAY contain one or more CorpusPublications, multiple ResearchRuns, annotations, research notes, validation reports, comparison results, configuration snapshots, PROV graphs, derived outputs, and bibliographic resources.

A Project Snapshot Crate SHOULD identify which artifacts are authoritative and which are derived.

#### Illustrative package structure

An implementation MAY serialize a Research Run Crate conceptually as follows. File names are illustrative unless separately required by the applicable RO-Crate or DERRIDAI serialization profile.

    derridai-run-2026-09-22/
    |-- ro-crate-metadata.json
    |-- derridai-manifest.json
    |-- corpus/
    |   |-- publication-manifest.json
    |   |-- metadata-schema.json
    |   `-- records.jsonl
    |-- evidence/
    |   |-- evidence-packet.json
    |   `-- evidence-text.json
    |-- run/
    |   |-- research-run.json
    |   |-- generation-config.json
    |   `-- prompt-contract.json
    |-- output/
    |   |-- answer.md
    |   |-- claims.json
    |   `-- citations.json
    |-- validation/
    |   |-- validation-results.json
    |   `-- grades.json
    `-- provenance/
        `-- prov.jsonld

#### Authoritative versus derived artifacts

A crate MUST distinguish authoritative research information from derived computational artifacts where both are included. CorpusPublication, RecordRevision, MetadataSchema, and human-confirmed assertions may be authoritative; embeddings, vector indexes, search rankings, reranker scores, cached responses, and temporary model contexts are normally derived. A consumer SHOULD NOT have to infer authority merely from file names.

#### Record identity within a crate

Records contained in or referenced by a crate MUST preserve their stable DERRIDAI identifiers. If a crate contains only the Records used in a ResearchRun rather than the complete corpus, it MUST NOT imply that those Records constitute the complete CorpusPublication. The crate SHOULD preserve the parent publication identifier.

#### Evidence package requirements

Evidence used by a ResearchRun SHOULD be packaged so that the evidence set can be reconstructed independently of the retrieval engine. For each EvidenceRef, a crate SHOULD preserve the evidence identifier, Record identifier, Record revision, source span or Record offsets, exact supplied evidence text where permitted, citation, acquisition method, and truncation state.

This requirement prevents reproducibility from depending on rerunning a changing retrieval system merely to rediscover which passages the model originally saw.

#### Reproducibility in a crate

A Research Run Crate SHOULD preserve enough information to distinguish corpus reproducibility, process reproducibility, and output reproducibility. Corpus reproducibility identifies the exact research corpus state. Process reproducibility identifies the procedure, evidence-acquisition settings, evidence, model/provider, prompt contract, validators, and graders. Output reproducibility concerns whether the exact generated wording can be regenerated.

DERRIDAI does not assume that exact output regeneration is always possible. Remote models may change; stochastic inference, hardware, quantization, sampling implementations, or provider behavior may differ. A crate SHOULD therefore preserve the original output even when exact regeneration cannot be guaranteed.

#### Source-document inclusion and restricted material

A SourceDocument MAY be embedded, externally referenced, identified by persistent identifier, identified by digest, described bibliographically, or omitted with an availability statement. This flexibility is necessary because research materials may be copyrighted, licensed, confidential, unpublished, embargoed, subject to NDA, or too large for redistribution.

A crate MUST NOT imply that a SourceDocument is redistributed when it is merely referenced. Omission of source bytes MUST NOT require omission of stable source identity, digest, bibliographic description, or provenance relationship where those may be retained.

#### Local and confidential research

RO-Crate export MUST NOT require public publication or network transmission. A Local Sovereign implementation MUST be able to construct a DERRIDAI research package entirely within researcher-controlled infrastructure. Packaging and publication are distinct operations.

#### External-service disclosure

If a ResearchRun transmitted research content to an external provider, a reproducibility package SHOULD preserve that fact where known. It SHOULD identify the provider, operation, class of data transmitted, and model where relevant. Credentials such as API keys, passwords, session tokens, and encryption keys MUST NOT be included merely for reproducibility.

#### Software environment

A Research Run Crate MAY preserve software-environment information such as DerridAI version, DERRIDAI specification version, operating system, runtime version, dependency snapshot, model runtime, container digest, or hardware class where those details materially affect reproducibility.

#### Relationship to other RO-Crate profiles

A DERRIDAI implementation MAY reuse compatible workflow- or provenance-oriented RO-Crate conventions where they improve interoperability. It SHOULD extend or compose with a suitable generic profile rather than duplicate it, provided that research-specific DERRIDAI semantics remain preserved.

#### RO-Crate validation

A DERRIDAI RO-Crate exporter SHOULD support machine validation against the declared RO-Crate version, the DERRIDAI RO-Crate Profile, and applicable DERRIDAI schema versions. Validation errors SHOULD distinguish RO-Crate structural failure, DERRIDAI profile failure, missing referenced artifact, and DERRIDAI semantic inconsistency.

### Claim-Level Publication and Nanopublication Compatibility

#### Status and rationale

Nanopublication interoperability is OPTIONAL in DERRIDAI Core 1.0 and is not required for Core, Publication, Retrieval, Evidence, Reproducible Research, or Local Sovereign conformance. A future DERRIDAI Nanopublication Profile MAY define a normative serialization once GeneratedClaim and SupportBinding semantics are sufficiently stable.

Nanopublications are relevant because DERRIDAI increasingly models research output at the level of individual claims. Conceptually, GeneratedClaim can correspond to an assertion, SupportBinding plus EvidenceRef can contribute assertion provenance, and ResearchRun plus agent/model information can contribute publication provenance.

#### Why nanopublications are not Core

Not every generated scholarly answer has been reliably decomposed into atomic claims. A paragraph may contain several propositions, qualification, contrast, negation, citation scope, and interpretive synthesis. Premature publication as independent nanopublications may create false precision.

Before a GeneratedClaim is exported through a future nanopublication profile, the implementation SHOULD establish stable claim identity, claim text or structured proposition, source output span, support bindings, evidence references, Record revisions, citation information, ResearchRun identity, and validation status. A claim whose support is unresolved SHOULD retain that unresolved state.

#### Support and contradiction relations

A future claim-publication profile MAY distinguish relations such as support, partial support, qualification, contrast, contradiction, and background. A serialization MAY assign compact machine-readable identifiers to those relations. The relation MUST NOT be inferred solely from the presence of a citation. Citation and evidentiary relation remain distinct.

### Interoperability and the DERRIDAI Traceability Matrix

#### Preservation of the source-to-claim chain

The principal reason for interoperability is not merely data export. It is preservation of the DERRIDAI traceability matrix outside a single application. At its fullest extent, the lineage is:

`SourceDocument -> SourceSpan -> Record -> RecordRevision -> FieldAssertions/Relations -> EvidenceAcquisition -> EvidenceRef -> EvidencePacket -> GenerationRun -> GeneratedClaim -> SupportBinding.`

A portable representation SHOULD preserve enough of this chain for its declared interoperability purpose.

#### Traceability questions

Where the information exists, an interoperable research object SHOULD permit another researcher or system to answer questions such as: What source document did this claim depend on? Which exact passage was used? Which RecordRevision represented that passage? Was the position attributed to the document author or to another position holder? Was the relevant metadata model-inferred, deterministic, or human-confirmed? How did the evidence enter the ResearchRun? Which evidence did the model actually receive? Which model generated the claim? Which validation process examined it? Which citation was rendered from the underlying source information?

#### Bidirectional traceability

Where practical, implementations SHOULD support both forward and reverse traceability. Forward traceability permits a researcher to move from SourceDocument to Records, evidence uses, and claims. Reverse traceability permits a researcher to move from GeneratedClaim to EvidenceRef, RecordRevision, SourceSpan, and SourceDocument.

### Interoperability Conformance and Validation

#### Profile-specific conformance

DERRIDAI interoperability SHOULD be implemented through explicit profiles rather than through an undifferentiated claim of compatibility. A formal conformance statement MUST identify the profile to which the claim applies.

A statement such as _DERRIDAI compatible_ is insufficient for formal conformance. A formal statement SHOULD instead identify, for example, DERRIDAI Core 1.0, DERRIDAI Evidence 1.0, DERRIDAI PROV Mapping 1.0, and DERRIDAI RO-Crate 1.0.

#### Partial support

An implementation MAY support only some interoperability profiles. A system may conform to DERRIDAI Core and produce PROV exports without supporting RO-Crate, or may produce RO-Crate packages without implementing claim-level SupportBinding. Partial support MUST NOT be described as conformance with unsupported profiles.

#### Validation report

An interoperability exporter SHOULD be capable of producing a validation report containing export identifier, export time, DERRIDAI version, profile versions, external-standard versions, validation status, warnings, lossy-mapping declarations, missing optional information, and failed requirements.

#### Loss report

If an export cannot preserve all relevant DERRIDAI semantics, it SHOULD produce a loss report identifying what was preserved, what was not represented, and why. Silent degradation SHOULD be treated as a conformance failure where the omitted information is material to the claimed profile.

#### Round-trip behavior

A lossless interoperability profile SHOULD define expected round-trip behavior from native DERRIDAI object to external representation and back. Round-trip conformance need not reproduce database row IDs, cache state, UI state, serialization order, or whitespace. It SHOULD preserve material research semantics.

#### Unknown extensions

Consumers SHOULD preserve unknown extension terms where practical. A consumer MUST NOT reinterpret an unknown DERRIDAI extension as a known field with different semantics. Forward-compatible parsing SHOULD prefer preservation over destructive normalization.

#### Security and secrets

Interoperability packages MUST NOT include secrets solely because those secrets existed during execution. API keys, session tokens, passwords, authentication cookies, database credentials, and encryption keys MUST NOT be exported for reproducibility.

#### Personal, confidential, and restricted information

An exporter SHOULD permit research-sensitive information to be excluded or redacted while preserving explicit notice that the package is incomplete in that respect. Removal of sensitive material MUST NOT silently produce a package that appears complete. An omitted SourceDocument may retain its stable identifier, digest, bibliographic metadata, and an explicit availability status where appropriate.

#### Local interoperability

External-standard support MUST NOT imply cloud dependence. A Local Sovereign implementation SHOULD be able to generate PROV locally, generate RO-Crate locally, validate exported packages locally, and inspect resulting metadata locally without contacting an external service.

### Relationship of DERRIDAI to External Standards

#### Division of responsibility

The standards addressed in this section solve related but different problems.

|                               |                                                                                  |
| :---------------------------- | :------------------------------------------------------------------------------- |
| **DERRIDAI**                  | Scholarly-AI research semantics and traceability.                                |
| **W3C PROV**                  | General provenance relationships among entities, activities, and agents.         |
| **RO-Crate**                  | Portable research-object packaging and contextual metadata.                      |
| **Nanopublications**          | Potential publication of small, independently identifiable scholarly assertions. |
| **JSON, JSONL, JSON-LD, RDF** | Serialization and exchange technologies.                                         |

PROV does not replace DERRIDAI concepts such as speaker, quoted speaker, position holder, stance, target, discourse role, proposition status, EvidenceRef, SupportBinding, assertion status, or review state. RO-Crate does not define what constitutes a DERRIDAI Record, how a RecordRevision differs from a Record, how evidence is bound to a claim, or which corpus state is authoritative. Nanopublications do not replace the corpus, evidence-acquisition system, Record model, or ResearchRun model.

#### What DERRIDAI contributes

DERRIDAI’s contribution is not a new generic provenance vocabulary or generic archive format. It specifies the scholarly information chain that more general standards can carry.

A generic provenance graph might state that Entity A was derived from Entity B and that Activity C used A to generate Entity D. A DERRIDAI representation can additionally establish that B is a specific SourceDocument; A is revision 3 of a Record representing pages 97–98; the document author is Derrida; the current speaker is Derrida; the represented position is attributed to Levinas; the attribution was first model-inferred and later human-confirmed; the Record entered a ResearchRun through researcher-selected evidence rather than vector search; EvidenceRef E7 identified the exact supplied passage; GenerationRun G9 used the EvidencePacket; GeneratedClaim C12 was produced; SupportBinding SB8 states that E7 supports C12; and a deterministic citation resolver generated the scholarly citation from bibliographic and page metadata.

> **Interoperability design principle.** Use established standards for the general problems they already solve; preserve DERRIDAI for the scholarly and AI-research semantics that remain domain-specific. Interoperability SHOULD preserve traceability, packaging SHOULD preserve reproducibility, local export SHOULD remain possible, and any loss of meaning MUST be explicit rather than silent.

## Extensibility, Conformance, and Reference Schemas

### Extensions and Versioning

#### Extension mechanism

DERRIDAI is extensible. Implementations MAY define domain-specific fields, relations, validators, acquisition methods, retrieval methods, evidence relations, or profiles. Extensions MUST NOT redefine DERRIDAI Core semantics without declaring an incompatible specification version.

Implementations SHOULD use namespaced extension identifiers when interoperability is expected. A reader encountering an unknown optional extension SHOULD preserve it when practical and MUST NOT treat it as known. An unknown required extension MUST cause the reader to report that it cannot fully interpret the object.

#### Independent version domains

Application version, DERRIDAI specification version, interchange schema version, metadata schema version, prompt contract version, processing profile version, collection manifest version, and model/provider revision MUST remain conceptually distinct.

Changing an application version does not necessarily change the specification version. Changing a prompt does not necessarily change the public Record schema.

#### Specification versioning

DERRIDAI specifications use `MAJOR.MINOR`. A major change indicates incompatible semantics. A minor change may add backward-compatible fields, entities, profiles, or clarifications. Editorial corrections MAY be tracked separately when normative semantics do not change.

Persisted data MUST NOT be silently reinterpreted under a newer incompatible contract. Objects whose semantics depend on a specification, schema, prompt contract, or processing profile SHOULD retain the applicable version identifiers.

### Conformance Profiles

A conformance profile is a named bundle of requirements. An implementation can therefore state precisely which parts of DERRIDAI it supports rather than making an all-or-nothing claim about the entire specification. Core conformance establishes the common information model; the other profiles add capabilities such as publication, retrieval, evidence binding, reproducibility, or fully local operation.

#### DERRIDAI Core 1.0

A system claiming Core conformance MUST represent SourceDocuments and stable logical Records; preserve source provenance; distinguish Record identity from storage identity; represent revisions when authoritative text changes; preserve source-text fidelity; represent unresolved state; distinguish scholarly data from operational state; and validate required Record structure.

#### DERRIDAI Publication 1.0

Publication conformance additionally requires immutable corpus snapshots; identification of applicable schema or specification version; validation before publication; exclusion of undeclared transient operational state; and enough source identity to trace published Records to documents.

#### DERRIDAI Retrieval 1.0

Retrieval conformance additionally requires retrieval results to be represented as envelopes around Records or RecordRefs; retrieval scores to remain outside authoritative Record semantics; retrieval method and score semantics to be identified; logical Record identity to survive storage and retrieval; and reranking to remain separate from Record content.

#### DERRIDAI Evidence 1.0

Evidence conformance additionally requires EvidenceRefs; evidence-to-Record and evidence-to-source provenance; distinction between evidence IDs and Record IDs; declared truncation; and citation derivation or validation against authoritative metadata.

#### DERRIDAI Claim-Binding 1.0

Claim-Binding conformance additionally requires explicit or reproducibly derived GeneratedClaims; explicit SupportBindings; bindings from supported claims to EvidenceRefs; preservation of the claim-to-source chain; rejection of unknown evidence bindings; and avoidance of treating mere context presence as evidentiary support.

#### DERRIDAI Reproducible Research 1.0

Reproducible Research conformance additionally requires sufficient run information to identify source corpus snapshot, evidence-acquisition configuration, evidence used, generation model, generation configuration, prompt contract, output, and validation results. Candidate sets SHOULD be retained when practical.

#### DERRIDAI PROV Mapping 1.0

PROV Mapping conformance additionally requires preservation of the applicable DERRIDAI identifier and lineage semantics in a PROV representation; distinction between human and computational agents where known; preservation of RecordRevision and SourceSpan where material; preservation of DERRIDAI-specific epistemic status rather than flattening it into generic derivation; and explicit declaration of lossy mappings.

#### DERRIDAI RO-Crate 1.0

RO-Crate conformance additionally requires a declared RO-Crate version and DERRIDAI profile identity; stable references to included or externally referenced DERRIDAI objects; distinction between authoritative and derived artifacts; preservation of ResearchRun and EvidencePacket information sufficient for the claimed reproducibility level; and validation against both RO-Crate structural requirements and DERRIDAI profile semantics.

#### DERRIDAI Local Sovereign 1.0

Local Sovereign conformance is defined in the Local Sovereign Profile section and may be claimed in combination with the other profiles. Local Sovereign implementations supporting interoperability SHOULD be able to create and validate PROV and RO-Crate exports without mandatory external network services.

### Canonical Conceptual Schemas

The following examples show one concrete serialization of the information model. They are intended to make the abstract entities easier to recognize in software. Field order is not significant, and conforming implementations may use other programming languages or storage formats as long as they preserve the required semantics. The following JSON forms are illustrative serializations of the normative concepts. Field order is non-normative and profiles MAY add fields.

#### Canonical Record

    {
      "record_id": "record-00142",
      "record_revision": 3,
      "source_document_id": "doc-9f4c",
      "source_spans": [{
        "source_document_id": "doc-9f4c",
        "source_unit_ids": ["block-401", "block-402"],
        "physical_page_start": 113,
        "physical_page_end": 114,
        "printed_page_start": 97,
        "printed_page_end": 98
      }],
      "text": "...",
      "work": "Example Work",
      "document_author": "Example Author",
      "document_language": "en",
      "speaker": "Example Author",
      "position_holder": "Other Thinker",
      "stance": "questions",
      "discourse_role": "analysis",
      "proposition_status": "attributed"
    }

#### Canonical FieldAssertion

    {
      "field": "position_holder",
      "value": "Other Thinker",
      "status": "model_inferred",
      "method": "llm",
      "checked": true,
      "confidence": 0.87,
      "reason": "Passage attributes the proposition to another thinker.",
      "evidence_refs": ["evref-81"],
      "model": "model-x"
    }

An evaluated field whose confidence is explicitly unavailable may use `"confidence": null`; omission of the field MUST NOT be silently conflated with such a result.

#### Canonical RetrievalCandidate

    {
      "candidate_id": "candidate-27",
      "record_ref": {
        "publication_id": "pub-2026-09",
        "record_id": "record-00142",
        "record_revision": 3
      },
      "collection": "corpus_en",
      "distance": 0.194,
      "rrf_score": 0.0481,
      "rerank_score": 6.42,
      "retrieval_hits": [
        {"search_type": "semantic", "rank": 2},
        {"search_type": "lexical", "rank": 7}
      ]
    }

#### Canonical EvidenceItem

    {
      "evidence_id": "E3",
      "evidence_ref": {
        "evidence_ref_id": "evref-81",
        "record_id": "record-00142",
        "record_revision": 3,
        "source_document_id": "doc-9f4c",
        "record_character_start": 212,
        "record_character_end": 911
      },
      "inline_citation": "Author 1997: 97-98",
      "full_citation": "Author, Example. Example Work. ...",
      "text_truncated": false
    }

#### Canonical SupportBinding

    {
      "claim_id": "claim-4",
      "evidence_refs": ["evref-81", "evref-93"],
      "relation": "supports",
      "validation_status": "validated"
    }

### Required Invariants

Every conforming implementation MUST preserve the following invariants within the profiles it claims.

- **Identity invariant.** Logical Record identity remains distinguishable from storage identity.

- **Source invariant.** A Record can be traced to its SourceDocument.

- **Span invariant.** Evidence can be traced to the Record or source span from which it derives.

- **Revision invariant.** Evidence depending on mutable text can identify the relevant RecordRevision.

- **Conservation invariant.** Segmentation does not silently lose, invent, duplicate, or reorder source material.

- **Epistemic invariant.** Unresolved, absent, inferred, deterministic, and human-confirmed states are not silently collapsed.

- **Assertion invariant.** Interpretive provenance remains distinguishable from the value being asserted.

- **Retrieval invariant.** Retrieval properties describe retrieval events, not intrinsic Record properties.

- **Derived-store invariant.** Rebuildable indexes do not silently replace authoritative corpus state.

- **Citation invariant.** Citation facts are derived from authoritative metadata where deterministically possible.

- **Evidence invariant.** Evidence identifiers do not replace persistent Record identity.

- **Generation invariant.** Context inclusion alone does not constitute evidence-to-claim binding.

- **Failure invariant.** Failures affecting provenance or correctness are not silently converted into confident success.

- **Model-independence invariant.** Replacing a computational model does not by itself redefine authoritative Record identity, documentary provenance, or human-confirmed assertions.

- **Version invariant.** Persisted objects retain sufficient version information to avoid silent reinterpretation under incompatible semantics.

### Reference Implementation Mapping

The DerridAI reference implementation maps naturally onto the specification. Its provenance-record structure corresponds to the Record concept; source blocks and source spans correspond to SourceUnit and SourceSpan; and record revision corresponds to RecordRevision. Metadata field status and evidence correspond to FieldAssertion provenance. Chroma record encoding corresponds to StorageProjection, while collection manifests correspond to CollectionManifest. RetrievalCandidate and EvidenceItem correspond to their DERRIDAI counterparts. Selected evidence corresponds to EvidenceRef or directly selected candidates. RAG runs correspond to ResearchRunManifest plus GenerationRun. Evidence labels such as E0 are run-local evidence IDs, deterministic citation binding corresponds to Citation Binding, and `derridai-corpus-jsonl-v1` is an implementation-specific publication profile.

This mapping is informative unless separately adopted as a normative compatibility profile. The reference implementation MAY expose the same native objects through PROV and RO-Crate adapters; such adapters SHOULD remain projections of the authoritative DERRIDAI model rather than alternate sources of truth.

### Non-Normative Rationale

_This section is non-normative._

The Record is central because chunks are usually implementation artifacts while Records are intended to survive changes in retrieval infrastructure. Evidence is modeled as a role because the same Record can support one inquiry and be irrelevant to another. Attribution remains first-class because document author, speaker, position holder, target, and quoted source can differ. Operational state and vector infrastructure remain separate because they change more readily than documentary identity.

DERRIDAI is therefore compatible with a future in which vector retrieval becomes less central. The durable abstraction is `Record -> Evidence Acquisition -> Evidence -> AI reasoning -> claim`; the acquisition mechanism may be vector, lexical, human, long-context, agentic, or another method as long as the resulting evidence resolves to the Durable Research Layer.

### Specification Summary

The minimal DERRIDAI model is: `SourceDocument -> SourceSpan -> Record -> Evidence -> GeneratedClaim`

with explicit intermediate objects added when required by the claimed profile.

For audit, the direction is reversed: `GeneratedClaim -> EvidenceRef -> RecordRevision -> Record -> SourceSpan -> SourceDocument`.

DERRIDAI keeps documentary identity and provenance durable while models, retrieval systems, execution environments, and interoperability formats remain replaceable.
