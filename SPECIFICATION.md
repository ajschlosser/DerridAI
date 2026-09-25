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
- [Appendix A - Normative Entity Model and Object Glossary](#appendix-a---normative-entity-model-and-object-glossary)
- [Appendix B - Extensibility and Conformance](#appendix-b---extensibility-and-conformance)
- [Appendix C - Reference Interchange, Vocabularies, and Schemas](#appendix-c---reference-interchange-vocabularies-and-schemas)
- [Appendix D - Relationship to External Standards](#appendix-d---relationship-to-external-standards)
- [Appendix E - Reference Implementation](#appendix-e---reference-implementation)
- [Appendix F - Rationale and Summary](#appendix-f---rationale-and-summary)

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

DERRIDAI standardizes scholarly identities and distinctions that must remain recoverable across implementations. It intentionally keeps the first-class semantic object model small. Extraction blocks, generic relations, schema-editor objects, storage projections, retrieval candidates, packet-item wrappers, validation-result classes, and grading-result classes MAY exist in an implementation without becoming DERRIDAI semantic objects.

#### Four scholarly layers

The DERRIDAI source-to-claim architecture is organized into four conceptual layers:

1. **Documentary Layer** - SourceDocument, SourceSpan, Record, and RecordRevision preserve documentary identity and source location.
2. **Scholarly Assertion and Attribution Layer** - FieldAssertion preserves derivation, evaluation, authority, value state, confidence, and interpretive attribution without flattening those distinctions.
3. **Evidence Layer** - Evidence Acquisition, EvidenceRef, and EvidencePacket represent how identified documentary material enters a particular research operation as evidence.
4. **AI Research-Output Layer** - GenerationRun, GeneratedClaim, and SupportBinding preserve the relationship between supplied evidence and generated research output.

Profiles add CorpusPublication, RetrievalRun, and ResearchRun where publication, computational retrieval, or reproducible research capability is claimed.

#### Durable and derived state

Authoritative documentary and scholarly state MUST remain distinguishable from derived computational state. Embeddings, vector indexes, lexical indexes, query decompositions, retrieval rankings, reranker scores, caches, temporary evidence ordering, response projections, and similar rebuildable artifacts MUST NOT silently become more authoritative than the corpus or source data from which they derive.

#### Conceptual flow

At its fullest extent, the scholarly traceability chain is:

`SourceDocument -> SourceSpan -> Record -> RecordRevision -> FieldAssertion -> Evidence Acquisition -> EvidenceRef -> EvidencePacket -> GenerationRun -> GeneratedClaim -> SupportBinding`

These are semantic roles, not mandatory class or table names. Not every capability profile requires every role to be separately materialized.

The principal reverse audit paths are:

`GeneratedClaim -> SupportBinding -> EvidenceRef(record) -> RecordRevision -> SourceSpan -> SourceDocument`

or:

`GeneratedClaim -> SupportBinding -> EvidenceRef(source_span) -> SourceSpan -> SourceDocument`

A system MUST NOT claim full claim traceability merely because a human-readable citation is present when the internal evidence-to-source relationship cannot be resolved.

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


#### Extraction units (implementation-specific)

An implementation MAY use addressable extraction units such as PDF blocks, OCR regions, paragraph candidates, XML nodes, line groups, media segments, or page regions. Such units MAY carry stable local IDs, extracted text, source-document identity, location, extraction method, and extraction confidence.

Extraction units are not first-class DERRIDAI semantic objects. They MUST NOT acquire scholarly significance merely because they are physical or technical extraction units. When they participate in provenance, they do so as locator material inside a SourceSpan or another DERRIDAI object.

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

A revision identifier MUST change whenever authoritative Record text changes and whenever another mutation can invalidate a pinned evidence locator or SupportBinding. It MAY also advance for broader authoritative concurrency control.

Evidence whose locator depends on mutable Record text or reviewed state MUST identify the applicable RecordRevision. An implementation MUST NOT silently resolve an EvidenceRef against a different revision when doing so changes the evidence represented.

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

A value stored on a Record and an assertion concerning that value are distinct concepts. A **FieldAssertion** represents one assertion about one field value in Record or RecordRevision context.

DERRIDAI requires four independently recoverable semantics:

- **derivation** - how the assertion or asserted value entered the research model;
- **evaluation outcome** - whether and how the field was assessed;
- **authority** - the review or resolution authority currently attached to the assertion;
- **value state** - whether the value is present, absent, invalid, or unresolved.

The canonical interchange representation uses `derivation_method`, `evaluation_status`, `authority_status`, and `value_status`. A native implementation MAY encode the same semantics through another lossless structure, but a Boolean such as `checked` by itself is not sufficient.

A materialized FieldAssertion SHOULD support `assertion_id`, `record_id`, `record_revision`, stable field identity, field name, value, the four state dimensions or their lossless equivalent, specific method, confidence, reason, evidence references, actor or model, metadata-contract identity, and creation time where relevant.

An implementation MAY materialize the currently authoritative value directly on the Record for convenience. Provenance of interpretive, disputed, superseded, rejected, or human-confirmed assertions SHOULD remain available separately. Human confirmation MUST NOT erase the assertion's original derivation, model, method, evidence, or confidence provenance.

#### Derivation method

`derivation_method` identifies how the assertion or asserted value entered the research model. DERRIDAI defines the base values `deterministic`, `model`, `human`, `inherited`, `imported`, and `other`. Profiles MAY add namespaced values.

Derivation method MUST NOT substitute for authority. A model-derived assertion can later be human-confirmed without becoming human-derived; a deterministic assertion can remain unreviewed; and a human override is both human-derived and an authority event.

#### Evaluation status

`evaluation_status` identifies whether the relevant field was evaluated and what the evaluation produced. DERRIDAI defines `not_evaluated`, `value_supported`, `no_supported_value`, and `evaluation_failed`.

`not_evaluated` means the applicable evaluator did not assess the field. `value_supported` means the evaluation produced at least one supported value or candidate. `no_supported_value` means the evaluation completed but did not support a value. `evaluation_failed` means an attempted evaluation failed operationally or structurally and therefore MUST NOT by itself establish a semantic conclusion.

An implementation MUST NOT infer evaluation success merely because another field or stage was processed.

#### Authority status

`authority_status` identifies the review or resolution authority currently attached to the assertion. DERRIDAI defines `unreviewed`, `human_confirmed`, `human_override`, and `disputed`.

`human_confirmed` means a human reviewer explicitly accepted the assertion without changing its derivation history. `human_override` means a human supplied or selected a replacement authoritative value. `disputed` means materially incompatible assertions remain unresolved or a previously authoritative assertion has been reopened because of contradictory evidence.

Authority status MUST NOT erase derivation history.

#### Value status

`value_status` identifies the semantic state of the asserted value. DERRIDAI defines `present`, `confirmed_absent`, `invalid`, and `unresolved`.

`confirmed_absent` MUST NOT be treated as equivalent to `unresolved`. A failure, missing model response, or omitted confidence MUST NOT by itself establish `confirmed_absent`, `invalid`, or any other semantic conclusion.

#### Confidence

Confidence is metadata about an evaluation or assertion, not an intrinsic property of the source fact. Numeric confidence MUST use a documented scale and SHOULD normally use the interval 0 to 1.

When `evaluation_status` is `not_evaluated`, confidence MUST be omitted. When an evaluation occurred, confidence MUST be present: it MAY be numeric when the evaluator supplied a meaningful value, or `null` when evaluation occurred but confidence is explicitly unavailable. A system MUST NOT fabricate numeric zero or numeric one merely because confidence was omitted.

Implementations MUST NOT present confidence as a calibrated probability unless calibration has actually been established.

#### Disagreement and authority

A system MAY retain multiple FieldAssertions for the same field. When deterministic, inherited, model-derived, imported, and human-derived assertions disagree, the implementation SHOULD retain the disagreement rather than overwrite it without trace.

The implementation MUST have a declared authority or resolution policy for selecting a materialized current value. Human confirmation and human override MUST be explicit and auditable. If contradictory later evidence reopens a human-confirmed value, the prior confirmation SHOULD remain historical provenance rather than being rewritten as though it never occurred.

### Attribution and Semantic Relations


#### Scholarly attribution

When the distinctions are relevant, an implementation SHOULD support fields such as `speaker`, `quoted_speaker`, `quoted_author`, `quoted_work`, `quoted_position_holder`, `quoted_addressee`, `quoted_referent`, `quotation_chain`, `position_holder`, `target`, `stance`, `discourse_role`, and `proposition_status`.

A passage written by an author does not entail that every proposition within it is held by that author. An implementation claiming scholarly-attribution support MUST be able to distinguish document author or textual speaker from proposition holder when the source requires that distinction.

DERRIDAI intentionally does not define a universal generic Relation object. Domain-specific semantic relationships MAY be represented as fields, namespaced predicates, linked-data relations, or extension objects. Such representations MUST preserve the relevant FieldAssertion or equivalent epistemic provenance when interpretation is material.

#### Metadata contracts

Implementations MAY support configurable metadata contracts defining fields, types, controlled values, validation rules, evidence requirements, review requirements, and model instructions. DERRIDAI does not require a first-class MetadataSchema object.

A processing run that depends on a configurable metadata contract MUST retain the exact contract snapshot or an immutable identifier for that exact version. Editing or deleting a later saved schema MUST NOT reinterpret an earlier run or publication. A content hash, immutable schema version, or equivalent evidence SHOULD be retained.

A schema-defined field whose assertions persist beyond one transient operation SHOULD have a stable field identity distinct from its display label or mutable field name. Renaming a field SHOULD preserve that identity when the scholarly meaning is unchanged; changing its meaning SHOULD create a new identity or explicitly declared compatibility mapping.

Reserved identity, source, provenance, and operational semantics MUST NOT be silently shadowed by a custom field. Implementations that permit schema editing SHOULD publish which fields are locked and which fields require evidence, evaluation, or human review.

A run MAY apply temporary guidance, requiredness, linguistic hints, or review policy without modifying the saved metadata contract. When such run-specific guidance changes what must be evaluated or reviewed, the effective guidance MUST be retained with the run so the result can be interpreted later.

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

#### Storage projections (implementation-specific)

An implementation MAY maintain technology-specific storage projections of a Record containing a storage ID, Record reference, document text, metadata, embedding, or other index-specific values. Such projections are not first-class DERRIDAI semantic objects.

A storage ID MAY differ from `record_id`, but the mapping MUST remain recoverable. A storage projection MUST NOT silently alter semantic Record values. Storage-specific encoding is permitted only when decoding is lossless for the declared contract.

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

#### Retrieval diagnostics and candidate envelopes (implementation-specific)

An implementation MAY represent route-level retrieval hits containing collection, search type, rank, raw score, and score semantics. A distance or similarity value MUST NOT be described as confidence or probability unless the retrieval system actually defines it that way.

An implementation MAY also use candidate envelopes that reference a Record and add retrieval-specific information such as collection, distance, fusion score, rerank score, MMR score, route diagnostics, and selection state. Retrieval-hit and candidate-envelope classes are not first-class DERRIDAI semantic objects.

Retrieval diagnostics MUST NOT mutate the authoritative Record merely to attach computational information. The same logical Record found through multiple routes SHOULD be deduplicated by logical identity while retaining contributing route diagnostics.

#### Fusion and reranking

When multiple retrieval routes contribute to a candidate, the fusion method MUST be recorded and route-specific ranks SHOULD remain available. Reranking MUST be represented as an operation on RetrievalCandidates, not as a change to Record metadata.

If a preferred reranker fails and a fallback is used, the fallback MUST be reported.

#### User-selected evidence

A user MAY designate a Record or RecordSpan as evidence independently of retrieval rank. Selected evidence MUST retain authoritative Record identity. A client SHOULD transmit a RecordRef rather than a complete Record when the server can safely rehydrate the authoritative source.

Selected evidence MAY bypass retrieval entirely and SHOULD be normalized into the same evidence model used by retrieved evidence so downstream citation and validation do not depend on acquisition method.

## Evidence, Claims, Traceability, and Reproducibility


### Evidence Profile

The Evidence layer defines how documentary material acquires an evidentiary role in a particular research operation. Its normative requirements are required for the DERRIDAI Evidence profile and for profiles that depend on EvidenceRef semantics.

#### Evidence Acquisition

**Evidence Acquisition** is the process by which Records or source spans become candidates for evidentiary use. It is mechanism-neutral. Acquisition MAY occur through semantic or lexical retrieval, metadata filtering, database query, human selection, direct reference, long-context inspection, agentic search, model-located source spans, or another declared method.

Every acquired item intended for downstream audit SHOULD resolve to a persistent Record or SourceSpan regardless of acquisition method.

An acquisition event SHOULD record its method, query or selection condition where applicable, source corpus or publication, parameters, time, and actor or computational component. Acquisition diagnostics MUST NOT become intrinsic Record metadata.

#### Evidence as a role

Evidence is a contextual role played by identified documentary material in a particular research operation; it is not a separate authoritative copy of that material. The same Record, RecordRevision, or SourceSpan MAY be evidence in one inquiry and irrelevant in another.

#### EvidenceRef

An **EvidenceRef** is the DERRIDAI semantic locator for exact source material used to support, contextualize, contrast with, quote, attribute, or otherwise bear on a downstream claim. It does not have to be a standalone database row: a packet entry or SupportBinding MAY embed the equivalent locator fields directly.

Every EvidenceRef semantic locator MUST declare exactly one authoritative `locator_kind`: `record` or `source_span`.

A record-backed locator (`locator_kind: record`) MUST identify `record_id`. It MAY additionally identify `publication_id`, `corpus_id`, or another namespace needed to resolve the Record. If its meaning depends on mutable Record text or reviewed state, it MUST identify the applicable `record_revision`. When the evidence is a strict subset of the Record, it SHOULD contain exact Record-relative offsets or another reproducible locator. The SourceDocument resolved through the Record MUST remain identifiable.

A direct-source locator (`locator_kind: source_span`) MUST identify one `source_document_id` and one or more SourceSpans. Every SourceSpan in that locator MUST identify the same SourceDocument. It does not require a Record or RecordRevision. If the material is later associated with a Record, that association MUST NOT silently change the authoritative locator.

A locator MAY include a quote hash or content digest for integrity checking. A run-local label such as `E0` MUST NOT replace the durable documentary identity represented by its Record/RecordRevision or SourceDocument/SourceSpan locator.

#### EvidencePacket

An **EvidencePacket** is the logical ordered evidence context selected or supplied for a research operation. It MAY be a standalone object or an embedded part of a retained ResearchRun or generation result. It SHOULD identify creation time, source publication or corpus where applicable, context limit, truncation policy, and an ordered array of entries.

Each packet entry SHOULD identify a run-local entry ID, an EvidenceRef semantic locator, the text actually supplied or enough deterministic information to reproduce that exact supplied text, whether truncation occurred, citation text where useful, and acquisition or selection provenance. A deterministic transformation is sufficient only when its input, parameters, and applicable transformation version are retained.

Evidence supplied to a model MAY be truncated. If it is, truncation MUST be declared; the authoritative EvidenceRef MUST remain unchanged; and the full authorized source SHOULD remain recoverable to an auditor. Truncated text MUST NOT be represented as the complete Record or complete SourceSpan content. Reordering packet entries MUST NOT change underlying evidence identity.

Packet entries are composite implementation structures, not independent DERRIDAI first-class objects.

#### Packet integrity and evidence sufficiency

Implementations SHOULD distinguish packet integrity from semantic evidence sufficiency.

Packet integrity is normally deterministic: does each supplied item resolve to documentary identity, contain or reproduce the actual supplied text, and have required source and citation metadata? Semantic sufficiency asks whether the evidence actually answers, supports, qualifies, or contradicts a research question or claim and may require human or model judgment.

A system MAY block generation when deterministic packet-integrity requirements fail. Passing those checks MUST NOT be described as proof that the evidence semantically supports a later claim. Missing provenance MUST NOT be manufactured merely to satisfy a check.

### Citation

Citations SHOULD be generated deterministically from authoritative bibliographic and location metadata when those facts are available. An LLM MUST NOT be treated as authoritative for citation facts that can be generated from structured corpus data.

If required citation metadata is unavailable, the system SHOULD report incompleteness rather than invent missing bibliographic facts. Citation formatting MAY vary by style guide, but underlying source identity MUST remain stable across styles.

Human-readable citation rendering and machine evidence binding are different operations. A renderer MAY replace a temporary marker such as `[[E0]]` with a formatted citation, but the structured marker-to-evidence relation MUST be captured before or independently of that replacement when Claim-Binding conformance is claimed. A formatted citation alone MUST NOT be treated as the machine SupportBinding.

### Generation, Claims, and Support Bindings

#### GenerationRun

A **GenerationRun** represents an AI generation operation using DERRIDAI evidence. It SHOULD identify run ID, prompt, instructions, provider, model, model revision where available, generation parameters, prompt-contract version, evidence packet, execution locality, timestamps, and answer.

Secrets such as API keys MUST NOT be stored in a public GenerationRun.

#### Evidence-bounded generation

A DERRIDAI Evidence-Grounded Generation implementation MUST instruct the generator that supplied evidence is the basis for substantive source claims. The generator MUST NOT be instructed to fabricate supporting citations. When evidence is insufficient, the system SHOULD permit or require an explicit statement of insufficiency.

#### GeneratedClaim

A **GeneratedClaim** is a substantive assertion identified within generated output. It SHOULD contain claim ID, generation-run ID, claim text, answer offsets where available, derivation or segmentation method, support bindings, and claim status.

Claim granularity MUST be declared or inferable from the derivation method. A sentence-level extraction MAY be used as a conservative reproducible claim unit, but a sentence MUST NOT automatically be described as one atomic scholarly proposition when it contains multiple propositions, qualifications, contrasts, or citation scopes.

A system MAY omit explicit GeneratedClaim objects if it does not claim proposition-level traceability. A system claiming DERRIDAI Claim-Binding conformance MUST materialize or reproducibly derive them.

#### SupportBinding

A **SupportBinding** associates exactly one GeneratedClaim with one or more EvidenceRef semantic locators. It MAY reference named EvidenceRefs or embed equivalent authoritative locator fields directly. It SHOULD identify the relation between claim and evidence - for example, support, contrast, qualification, contextualization, quotation, or attribution - together with validation status and results where available.

A GeneratedClaim MUST NOT be described as supported merely because evidence appeared in model context or because a human-readable citation appears nearby. Machine support binding SHOULD be captured from structured generation output, evidence markers, answer spans, or another reproducible relation before citation formatting can erase that structure.

A binding that pins a RecordRevision or SourceSpan MUST be re-resolved before reuse when the underlying Record or source changes. Revision mismatch, missing source units, or source-identity mismatch MUST produce a visible stale or unresolved state rather than silently rebinding to current material.

#### Evidence markers and exact quotation

Temporary evidence markers such as `[[E0]]` MAY be used during generation and SHOULD be resolved deterministically afterward. Unknown evidence markers MUST NOT silently resolve to unrelated sources.

When a GeneratedClaim contains a purported exact quotation, a Claim-Binding implementation SHOULD verify that the quoted text exists in the cited authoritative source or declared normalized equivalent. A failed exact-quote check MUST NOT be silently treated as successful support.

#### High-severity relational failures

Validation systems SHOULD treat wrong-person attribution, fabricated quotation, wrong source binding, wrong page or span binding, support where evidence states the opposite, dropped proposition-bearing negation, and confusion of editorial or translator text with primary-author position as high-severity failures.

### Advisory Research Memory

Research systems MAY retain prior responses, generated claims, reviewed metadata decisions, editorial examples, or other memory to guide later work. DERRIDAI does not make such memory a first-class semantic object.

Prior memory is advisory context unless it is re-resolved as current evidence. A previously generated claim, cached answer, or remembered reviewer decision MUST NOT become an EvidenceRef or SupportBinding merely because it is placed in a prompt.

If prior material is promoted into current evidence or claim support, the implementation MUST resolve it back to current authoritative Record/RecordRevision or SourceSpan state and make stale or incompatible versions visible.

Memory access SHOULD preserve applicable owner, visibility, and authorization constraints. Vector indexes, similarity projections, response caches, and exemplar-search indexes built over memory SHOULD remain rebuildable derived state rather than the sole authoritative copy of reviewed decisions or claim provenance.

### Traceability Matrix

A DERRIDAI **traceability matrix** is the logical set of relations connecting research output to the documentary and computational state on which it depends. It MAY be implemented as relational tables, graph edges, structured JSON, event records, or another representation; a literal table is not required.

For a GeneratedClaim represented as evidentially supported, a Claim-Binding conforming implementation MUST identify the applicable SupportBinding and EvidenceRef.

A record-backed EvidenceRef MUST resolve through the applicable Record or RecordRevision to its SourceDocument and SourceSpan at the precision claimed by the implementation. A direct-source EvidenceRef MUST resolve directly to its declared SourceSpan or SourceSpans and SourceDocument.

Where a claim depends materially on interpretive metadata, the implementation SHOULD retain the FieldAssertion or equivalent provenance that established the relevant value. Where a claim depends on a particular research operation, the implementation SHOULD retain or reference the ResearchRun describing corpus state, acquisition configuration, evidence supplied, generation configuration, and validation state.

The principal audit paths are:

`GeneratedClaim -> SupportBinding -> EvidenceRef(record) -> RecordRevision -> SourceSpan -> SourceDocument`

or:

`GeneratedClaim -> SupportBinding -> EvidenceRef(source_span) -> SourceSpan -> SourceDocument`

with optional branches to FieldAssertions, RetrievalRuns, GenerationRuns, and validation or evaluation reports.

A system MUST NOT describe a claim as fully traceable merely because it contains a human-readable citation if the internal evidence-to-source relationship cannot be resolved.

### Reproducibility and Evaluation

#### Reproducibility levels

DERRIDAI distinguishes three levels of reproducibility. **Corpus reproducibility** identifies the source documents, publication snapshot, Record revisions, schemas, and other durable research state. **Process reproducibility** identifies the query, evidence-acquisition or retrieval configuration, candidate and selected evidence where retained, model/provider, prompt contract, generation parameters, validators, and graders. **Output reproducibility** concerns whether the same execution produces identical generated wording.

Core and Reproducible Research conformance MUST NOT imply byte-identical output reproduction from a stochastic or externally mutable model. The required goal is preservation of the research state and process information needed to reconstruct and evaluate the operation, with the limitations of the original execution environment made explicit.

#### ResearchRun

A **ResearchRun** is the coherent retained audit view of one research operation. It MAY be one object or a resolvable composition of durable run records. It SHOULD identify specification version, corpus publication or snapshot, original and derived queries, evidence-acquisition and retrieval configuration, candidate identifiers where relevant, selected evidence, EvidencePacket, GenerationRun or generation configuration, prompt contract, execution locality, validation results, output, grader information, advisory-memory use, and timestamps.

A ResearchRun MUST retain enough information for the reproducibility profile it claims. DERRIDAI does not require bit-identical regeneration from nondeterministic models; it requires a distinction between reproducibility of inputs and configuration and deterministic reproduction of output.

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

A translation used as evidence MUST remain distinguishable from the source-language text from which it derives. A translated Record or EvidencePacket entry SHOULD reference the source Record or SourceSpan when available. Machine translation MUST be identified as such.

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

A PROV graph may be interoperable but insufficient for reproducing a ResearchRun if the EvidencePacket or model configuration is missing. Conversely, a complete local ResearchRun may support substantial reproducibility even if it has not been exported through any external standard.

### DERRIDAI PROV Mapping Profile

#### Scope and purpose

The DERRIDAI PROV Mapping Profile defines how DERRIDAI research lineage can be expressed using the W3C PROV family of standards. W3C PROV supplies a general-purpose model based on **Entity**, **Activity**, and **Agent**. DERRIDAI uses this framework to expose the history of scholarly and computational objects without replacing DERRIDAI’s domain semantics.

In simplified terms, PROV addresses questions such as: What depended on what? What process occurred? Which person, organization, or software agent participated? DERRIDAI adds questions such as: What scholarly object was involved? Who was speaking? Whose position was represented? What was the epistemic status of a metadata assertion? Which exact source span supported the claim?

A DERRIDAI implementation MAY support this profile without using RDF, PROV-O, or PROV internally.

#### Entity mapping

The first-class DERRIDAI objects SHOULD be exportable as PROV Entities when present: SourceDocument, SourceSpan, Record, RecordRevision, FieldAssertion, CorpusPublication, RetrievalRun, EvidenceRef, EvidencePacket, GenerationRun, GeneratedClaim, SupportBinding, and ResearchRun.

Implementation-specific extraction units, metadata-contract objects, retrieval candidates, validation records, grading records, and similar artifacts MAY also be represented in PROV when useful, but they MUST NOT be misrepresented as additional normative DERRIDAI semantic object classes.

Where both Record and RecordRevision are exported, the persistent logical Record MUST remain distinguishable from a particular revision of that Record. A consumer MUST be able to determine which exact RecordRevision was used as evidence when the native ResearchRun preserves that information.

| DERRIDAI object | PROV-oriented representation |
|---|---|
| SourceDocument, SourceSpan | Entity representing documentary material or an identified reproducible portion of it |
| Record, RecordRevision | Entity representing persistent scholarly identity and a particular state of that identity |
| FieldAssertion | Entity whose lineage records derivation, evaluation, confirmation, override, or dispute |
| CorpusPublication | Entity representing an immutable/versioned corpus release |
| RetrievalRun | Entity or associated Activity state representing one declared computational retrieval operation |
| EvidenceRef, EvidencePacket | Entity representing evidentiary locator semantics or the ordered evidence context supplied to a run |
| GenerationRun | Associated Activity or retained run entity representing an AI generation operation |
| GeneratedClaim | Entity representing an identified claim produced by generation |
| SupportBinding | Entity representing the claim-scoped evidentiary relation |
| ResearchRun | Entity describing the coherent retained audit view of a research operation |

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

- A **Corpus Crate** represents a portable CorpusPublication and SHOULD contain or reference the corpus manifest, applicable metadata-contract snapshot, public Records, source-document descriptors, bibliographic metadata, and publication/version information. It MAY contain source documents, annotations, validation reports, PROV representation, and derived index manifests.

- A **Research Run Crate** represents a particular AI-assisted research operation and SHOULD contain or reference the ResearchRun, corpus/publication identity, query, evidence-acquisition configuration, EvidencePacket, model configuration, prompt-contract identity, generated output, citations, validation results, grades, and warnings.

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

A crate MUST distinguish authoritative research information from derived computational artifacts where both are included. CorpusPublication, RecordRevision, retained metadata-contract snapshots, and human-confirmed assertions may be authoritative; embeddings, vector indexes, search rankings, reranker scores, cached responses, and temporary model contexts are normally derived. A consumer SHOULD NOT have to infer authority merely from file names.

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

## Appendix A - Normative Entity Model and Object Glossary

Appendix A is normative. DERRIDAI intentionally keeps the first-class object model small. Generic implementation artifacts MAY exist, but they do not become DERRIDAI semantic objects unless they preserve a distinction DERRIDAI itself needs to standardize.

### Normative entity and cardinality model

The central cardinality rules are:

1. A SourceSpan belongs to exactly one SourceDocument.
2. A Record belongs to exactly one SourceDocument and derives from one or more SourceSpans, all from that same SourceDocument.
3. A Record may have zero or more explicitly materialized RecordRevisions; authoritative text and other evidence-affecting changes MUST advance the applicable revision identifier.
4. An EvidenceRef semantic locator has exactly one authoritative locator mode: record-backed or direct-source-span-backed. Both modes resolve to exactly one SourceDocument; the locator MAY be named or embedded in another retained object.
5. An EvidencePacket contains ordered composite entries that carry or refer to EvidenceRef locators; those packet entries are not independent DERRIDAI objects.
6. A SupportBinding binds exactly one GeneratedClaim to one or more named or embedded EvidenceRef locators.
7. Run-local diagnostics, transport references, storage encodings, validation reports, and external-standard objects MUST NOT replace the durable DERRIDAI identities to which they refer.

A compact cardinality view is:

```text
SourceDocument 1 -------- 0..* SourceSpan
SourceDocument 1 -------- 0..* Record
Record         1 -------- 1..* SourceSpan
Record         1 -------- 0..* RecordRevision
Record/Revision --------- 0..* FieldAssertion

CorpusPublication -------- 1..* Records or immutable Record locators
RetrievalRun -------------- may acquire evidence
EvidencePacket ------------ 0..* ordered composite EvidenceRef entries
GenerationRun ------------- uses 0..1 EvidencePacket
GenerationRun 1 ---------- 0..* GeneratedClaim
GeneratedClaim 1 --------- 0..* SupportBinding
SupportBinding 1 --------- 1..* EvidenceRef locators
ResearchRun --------------- references publication/evidence/generation/validation state
```

### Normative Object Glossary

| Object | Identity and persistence | Cardinality and owning profile |
|---|---|---|
| **SourceDocument** | Stable documentary representation; durable | 1 SourceDocument -> 0..* SourceSpans and Records. Profile: Core |
| **SourceSpan** | Reproducible region within one SourceDocument; durable locator | Exactly 1 SourceDocument; may contribute to 0..* Records/EvidenceRefs. Profile: Core |
| **Record** | Logical research unit; durable | Exactly 1 SourceDocument; 1..* SourceSpans; 0..* RecordRevisions. Profile: Core |
| **RecordRevision** | Specific state of one Record; durable/versioned | Exactly 1 Record; 0..* EvidenceRefs may reference it. Profile: Core |
| **FieldAssertion** | Assertion about one stable field identity/value in Record context; durable when retained | Belongs to a Record or RecordRevision context; native encoding may vary if required epistemic dimensions remain recoverable. Profile: Core |
| **CorpusPublication** | Immutable corpus snapshot identity; durable/immutable | Publishes 1..* Records or immutable Record locators. Profile: Publication |
| **RetrievalRun** | One computational retrieval operation; run/audit state | May record 0..* result diagnostics and acquisition links. Profile: Retrieval |
| **EvidenceRef** | Exact evidentiary locator semantics; durable for audit | Exactly 1 locator_kind; resolves to exactly 1 SourceDocument; may be named or embedded. Profile: Evidence |
| **EvidencePacket** | Exact or deterministically reproducible ordered model context; run-specific/audit-retainable | 0..* composite entries carrying/referring to EvidenceRef locators. Profile: Evidence |
| **GenerationRun** | One AI generation operation; run-specific/audit-retainable | Uses 0..1 EvidencePacket; produces 0..* GeneratedClaims. Profile: Claim-Binding |
| **GeneratedClaim** | Identifiable claim within generated output; run-specific/audit-retainable | Exactly 1 GenerationRun; 0..* SupportBindings. Profile: Claim-Binding |
| **SupportBinding** | Claim-scoped evidentiary relation; run-specific/audit-retainable | Exactly 1 GeneratedClaim; 1..* named or embedded EvidenceRef locators. Profile: Claim-Binding |
| **ResearchRun** | Coherent retained research-operation audit view; run/audit state | May be one object or a resolvable composition of durable run records; references publication, evidence, generation, validation, and advisory-memory state. Profile: Reproducible Research |

DERRIDAI intentionally does **not** define first-class semantic objects for extraction units, generic relations, metadata schemas, generic transformations, storage projections, collection manifests, retrieval hits or candidates, packet items, transport RecordRefs, validation results, or grade results. Implementations MAY use such artifacts. Their semantics are governed by the relevant DERRIDAI identity, provenance, evidence, or interoperability rules rather than by additional object classes.

## Appendix B - Extensibility and Conformance

### Extensions and Versioning

Implementations MAY define domain-specific fields, validators, acquisition methods, retrieval methods, evidence relations, or profiles. Extensions MUST NOT redefine DERRIDAI Core semantics without declaring an incompatible contract.

Namespaced extension identifiers SHOULD be used when interoperability is expected. Unknown optional extensions SHOULD be preserved where practical and MUST NOT be reinterpreted as known fields with different semantics.

Application version, DERRIDAI specification version, interchange schema version, metadata-contract version, prompt-contract version, processing-profile version, publication version, and model/provider revision MUST remain conceptually distinct. Persisted data MUST NOT be silently reinterpreted under an incompatible newer contract.

### Conformance Profiles

A conformance profile is a named bundle of requirements.

- **DERRIDAI Core 1.0** establishes documentary identity, Record identity, revision, assertion provenance, validation, visible uncertainty, model independence, and version integrity.
- **DERRIDAI Publication 1.0** adds immutable validated corpus publication.
- **DERRIDAI Retrieval 1.0** adds explicit computational retrieval-run semantics while keeping retrieval diagnostics outside authoritative Record state.
- **DERRIDAI Evidence 1.0** adds EvidenceRef, EvidencePacket, evidence-to-source provenance, declared truncation, and citation integrity.
- **DERRIDAI Claim-Binding 1.0** depends on Core + Evidence and adds GeneratedClaim, SupportBinding, and the claim-to-source chain.
- **DERRIDAI Reproducible Research 1.0** depends on Core + Evidence and adds retained ResearchRun state sufficient for substantial process reconstruction.
- **DERRIDAI Local Sovereign 1.0** adds the ability to perform the declared essential operations within researcher-controlled infrastructure without mandatory remote dependencies.
- **DERRIDAI PROV Mapping 1.0** and **DERRIDAI RO-Crate 1.0** are interoperability adapter profiles.

### Normative Conformance Requirement Catalog

The following identifiers are the tracked conformance requirements for DERRIDAI 1.0. The catalog is limited to requirements that protect DERRIDAI's scholarly semantics, identity, evidence, or declared capability boundaries.

#### Core requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **CORE-ID-001 MUST** | SourceDocument has a stable `source_document_id` not based solely on transient storage or application identifiers. | schema+semantic |
| **CORE-ID-002 MUST** | Each SourceSpan refers to exactly one SourceDocument. | schema+semantic |
| **CORE-ID-003 MUST** | Each Record contains `record_id`, `source_document_id`, `text`, and one or more SourceSpans. | schema |
| **CORE-ID-004 MUST** | Every SourceSpan used by a Record identifies the same SourceDocument as that Record. | semantic |
| **CORE-ID-005 MUST** | Logical Record identity remains distinguishable from storage identity and derived storage cannot silently become authoritative. | semantic |
| **CORE-ID-006 MUST** | The RecordRevision identifier changes whenever authoritative Record text changes and whenever another mutation can invalidate a pinned evidence locator or SupportBinding; it MAY also advance for broader authoritative concurrency control. | behavioral+audit |
| **CORE-ID-007 MUST** | Modification of extracted text preserves original extraction, reconstructible immutable source, or an auditable change trail. | behavioral+audit |
| **CORE-ID-008 MUST NOT** | Cleaning does not silently paraphrase, summarize, translate, alter proposition-bearing negation, remove meaningful qualification, or erase material distinctions. | behavioral+audit |
| **CORE-ID-009 MUST NOT** | Segmentation does not silently lose, invent, duplicate, or reorder source material. | semantic+behavioral |
| **CORE-ID-010 MUST** | Unresolved state remains representable and is not conflated with confirmed absence. | schema+semantic |
| **CORE-ID-011 MUST** | A declared authority policy governs materialized current values, and human overrides are explicit and auditable. | behavioral+audit |
| **CORE-ID-012 MUST NOT** | Replacing a model, embedding engine, retrieval engine, or provider does not by itself alter authoritative Record identity, source relationships, or human-confirmed assertions. | behavioral+audit |
| **CORE-ID-013 MUST** | Authoritative boundaries validate required shape/types and model output is separately validated before semantic entry. | schema+behavioral |
| **CORE-ID-014 MUST NOT** | Failures affecting provenance, attribution, evidence, publication, or corpus integrity are not silently converted into confident success. | behavioral+audit |
| **CORE-ID-015 MUST NOT** | Persisted data is not silently reinterpreted under an incompatible newer specification or schema contract. | behavioral+audit |
| **CORE-ID-016 MUST** | A materialized FieldAssertion preserves independently recoverable derivation, evaluation, authority, and value-state semantics; native field names or compact encodings MAY differ if the mapping is lossless. | schema+semantic |
| **CORE-ID-017 MUST** | Confidence is omitted when not evaluated; after evaluation it is present as a documented-scale number or explicit null, and is never fabricated as zero or one. | semantic |
| **CORE-ID-018 SHOULD** | Persisted schema-defined assertions use stable field identity across non-semantic renames, or declare an explicit compatibility mapping. | semantic+audit |

#### Publication requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **PUB-ID-001 MUST NOT** | A final CorpusPublication is not changed in place; corrections create a new publication or revision. | semantic+audit |
| **PUB-ID-002 MUST** | Published Records pass structural/type/vocabulary validation before publication. | schema+semantic |
| **PUB-ID-003 MUST** | Publication fails rather than silently removing required provenance fields. | behavioral |
| **PUB-ID-004 MUST NOT** | Transient operational fields are not published as scholarly Record content unless explicitly defined by the publication contract. | semantic |

#### Retrieval requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **RET-ID-001 MUST** | The original query is preserved and derived queries are identified as derived when decomposition or translation occurs. | semantic |
| **RET-ID-002 MUST NOT** | Distance or similarity is not described as confidence or probability unless the retrieval system defines it that way. | semantic |
| **RET-ID-003 MUST NOT** | Retrieval metadata and scores do not mutate authoritative Record semantics. | semantic |

#### Evidence requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **EVID-ID-001 MUST** | Every EvidenceRef semantic locator, whether named or embedded, declares exactly one authoritative locator kind: `record` or `source_span`. | schema+semantic |
| **EVID-ID-002 MUST** | A record-backed EvidenceRef identifies the applicable RecordRevision whenever its locator depends on mutable Record text. | semantic |
| **EVID-ID-003 MUST** | A direct-source EvidenceRef contains one SourceDocument identity and one or more SourceSpans, all from that SourceDocument. | schema+semantic |
| **EVID-ID-004 MUST NOT** | A run-local EvidenceRef ID does not replace its authoritative documentary identity. | semantic |
| **EVID-ID-005 MUST** | The exact supplied evidence text is retained or deterministically reproducible; truncation is declared and does not change authoritative EvidenceRef identity. | schema+semantic |
| **EVID-ID-006 MUST** | Citation facts use authoritative structured metadata where deterministically available; missing facts are not invented; formatting changes do not alter source identity. | semantic+behavioral |

#### Claim-Binding requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **CLM-ID-001 MUST** | Claim-Binding implementations materialize or reproducibly derive GeneratedClaims. | semantic+audit |
| **CLM-ID-002 MUST** | Claims represented as supported have explicit SupportBindings to one or more named or embedded EvidenceRef semantic locators. | schema+semantic |
| **CLM-ID-003 MUST NOT** | Evidence is not described as supporting a claim merely because it appeared in model context. | behavioral+audit |
| **CLM-ID-004 MUST NOT** | Unknown evidence markers do not resolve silently to unrelated sources, and machine claim/evidence relations are not lost merely because markers are rendered as human-readable citations. | semantic |
| **CLM-ID-005 MUST** | A supported claim resolves through SupportBinding and EvidenceRef to the authoritative Record/RecordRevision or SourceSpan and SourceDocument. | semantic |
| **CLM-ID-006 MUST NOT** | A failed exact-quotation check is not silently treated as successful support. | semantic+behavioral |

#### Reproducible Research requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **REP-ID-001 MUST** | Retained ResearchRun state identifies corpus snapshot, evidence-acquisition configuration, exact supplied evidence or deterministic reconstruction, generation model/configuration, prompt contract, output, and validation results; advisory memory is distinguishable from evidence. | schema+semantic |
| **REP-ID-002 MUST NOT** | Conformance does not imply byte-identical output reproduction from stochastic or externally mutable models. | claim-review |

#### PROV Mapping requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **PROV-ID-001 MUST** | A PROV export preserves applicable DERRIDAI identity/lineage semantics, human/computational distinction where known, material RecordRevision/SourceSpan, FieldAssertion state dimensions, claim/evidence binding where present, and declared loss. | external+semantic |

#### RO-Crate requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **ROCR-ID-001 MUST** | A RO-Crate export declares RO-Crate and DERRIDAI adapter versions, stable object references, authoritative/derived status, sufficient ResearchRun/EvidencePacket state, and validates against both contracts. | external+semantic |

#### Local Sovereign requirements

| Requirement | Normative statement | Test class |
|---|---|---|
| **LOC-ID-001 MUST** | For the declared capability/media scope, essential documentary, evidence, inference, validation, and research-output operations can execute within researcher-controlled infrastructure without mandatory remote storage, embedding, inference, authentication, or telemetry. | deployment-test |

### Profile-to-Requirement Matrix

| Profile | Required dependency | Requirement IDs |
|---|---|---|
| Core | - | CORE-ID-001 through CORE-ID-018 |
| Publication | Core | PUB-ID-001 through PUB-ID-004 |
| Retrieval | Core | RET-ID-001 through RET-ID-003 |
| Evidence | Core | EVID-ID-001 through EVID-ID-006 |
| Claim-Binding | Core + Evidence | CLM-ID-001 through CLM-ID-006 |
| Reproducible Research | Core + Evidence | REP-ID-001, REP-ID-002 |
| Local Sovereign | Core | LOC-ID-001 |
| PROV Mapping adapter | Core | PROV-ID-001 |
| RO-Crate adapter | Core | ROCR-ID-001 |

### Required Invariants and Profile Applicability

| Invariant | Applies to | Requirement IDs | Normative rule |
|---|---|---|---|
| Identity invariant | Core | CORE-ID-005 | Logical Record identity remains distinguishable from storage identity. |
| Source invariant | Core | CORE-ID-002, CORE-ID-004 | A Record and all of its SourceSpans resolve to one and the same SourceDocument. |
| Revision invariant | Core, Evidence | CORE-ID-006, EVID-ID-002 | Evidence pins the applicable RecordRevision when mutable text or reviewed state can affect the evidence represented; evidence-affecting changes advance the revision. |
| Conservation invariant | Core | CORE-ID-009 | Segmentation does not silently lose, invent, duplicate, or reorder source material. |
| Epistemic invariant | Core | CORE-ID-010, CORE-ID-016, CORE-ID-017 | Derivation, evaluation, authority, value state, and confidence availability remain distinguishable. |
| Assertion invariant | Core | CORE-ID-011, CORE-ID-016, CORE-ID-018 | Interpretive provenance remains distinguishable from the materialized value; durable fields retain stable identity; current-value resolution follows a declared authority policy. |
| Retrieval invariant | Retrieval | RET-ID-002, RET-ID-003 | Retrieval diagnostics describe retrieval operations, not intrinsic Record properties. |
| Citation invariant | Evidence | EVID-ID-006 | Citation facts preserve authoritative source identity and are not fabricated to fill missing metadata. |
| Evidence invariant | Evidence | EVID-ID-001 through EVID-ID-005 | Evidence resolves through one declared authoritative locator and run-local labels do not replace documentary identity. |
| Generation invariant | Claim-Binding | CLM-ID-003 | Context inclusion alone does not constitute evidence-to-claim support. |
| Failure invariant | Core; all claimed profiles | CORE-ID-014 | Failures affecting provenance or correctness are not silently converted into confident success. |
| Model-independence invariant | Core | CORE-ID-012 | Model substitution does not redefine authoritative documentary or human-confirmed state. |
| Version invariant | Core; all versioned profiles | CORE-ID-015 | Persisted objects retain enough contract identity to avoid silent incompatible reinterpretation. |

## Appendix C - Reference Interchange, Vocabularies, and Schemas

### Reference Interchange and Automated Conformance

DERRIDAI defines a reference JSON interchange profile, `derridai-reference-json-v1`, so conformance can be tested independently of an implementation's native database or programming language. Native storage MAY differ. For automated assessment, an implementation MUST be able to emit equivalent reference-interchange data or a documented lossless mapping for the claimed profile.

The principal top-level first-class collections are:

`source_documents`, `source_spans`, `records`, `record_revisions`, `field_assertions`, `corpus_publications`, `retrieval_runs`, `evidence_refs`, `evidence_packets`, `generation_runs`, `generated_claims`, `support_bindings`, and `research_runs`.

Implementation-specific extraction units, storage projections, collection manifests, retrieval candidates, validation records, and similar artifacts MAY appear as namespaced extensions, but they are not required DERRIDAI object collections.

Automated conformance distinguishes:

1. **Structural conformance** - JSON Schema shape and types.
2. **Semantic conformance** - cross-object identity, cardinality, reference, and binding rules.
3. **Behavioral or deployment conformance** - requirements that need audit evidence, execution harnesses, history, or deployment inspection.

An artifact-level report establishes only the machine-evident subset visible in the supplied artifact. A full implementation conformance report MUST additionally provide evidence for every applicable MUST or MUST NOT requirement that cannot be established from static serialization.

### Controlled Vocabulary Registries

The machine-readable registry package defines the base values for FieldAssertion derivation, evaluation, authority, and value state; EvidenceRef locator kind; support relation; acquisition method; mapping fidelity; and validation severity where used by reports. Implementations MAY extend open vocabularies with namespaced values when the owning profile permits extension.

Base FieldAssertion values include:

- `derivation_method`: `deterministic`, `model`, `human`, `inherited`, `imported`, `other`;
- `evaluation_status`: `not_evaluated`, `value_supported`, `no_supported_value`, `evaluation_failed`;
- `authority_status`: `unreviewed`, `human_confirmed`, `human_override`, `disputed`;
- `value_status`: `present`, `confirmed_absent`, `invalid`, `unresolved`;
- EvidenceRef `locator_kind`: `record`, `source_span`.

### Canonical Conceptual Schemas

The following examples are illustrative serializations of the normative concepts. Field order is non-normative and profiles MAY add fields.

#### Canonical Record

```json
{
  "record_id": "record-00142",
  "record_revision": 3,
  "source_document_id": "doc-9f4c",
  "source_spans": [{
    "source_span_id": "span-401-402",
    "source_document_id": "doc-9f4c",
    "physical_page_start": 113,
    "physical_page_end": 114,
    "printed_page_start": 97,
    "printed_page_end": 98
  }],
  "text": "...",
  "speaker": "Example Author",
  "position_holder": "Other Thinker",
  "stance": "questions"
}
```

#### Canonical FieldAssertion

```json
{
  "assertion_id": "fa-81",
  "record_id": "record-00142",
  "record_revision": 3,
  "field_id": "core.position_holder",
  "field": "position_holder",
  "metadata_contract": "scholarly-attribution-v4",
  "value": "Other Thinker",
  "derivation_method": "model",
  "evaluation_status": "value_supported",
  "authority_status": "human_confirmed",
  "value_status": "present",
  "method": "semantic-attribution-v3",
  "confidence": 0.87,
  "reason": "Passage attributes the proposition to another thinker.",
  "evidence_refs": ["evref-81"]
}
```

#### Canonical SupportBinding

```json
{
  "binding_id": "sb-8",
  "claim_id": "claim-12",
  "evidence_refs": ["evref-81"],
  "relation": "supports",
  "derived_from_marker": "E0",
  "validation_status": "verified"
}
```

#### Canonical RetrievalRun

```json
{
  "retrieval_run_id": "ret-17",
  "original_query": "hospitality and sovereignty",
  "methods": ["hybrid"],
  "source_publication_id": "pub-2026-09",
  "results": [{
    "record_id": "record-00142",
    "record_revision": 3,
    "rank": 1,
    "score": 0.31,
    "score_semantics": "cosine_distance"
  }]
}
```

#### Canonical EvidenceRef

```json
{
  "evidence_ref_id": "evref-81",
  "locator_kind": "record",
  "publication_id": "pub-2026-09",
  "record_id": "record-00142",
  "record_revision": 3,
  "record_character_start": 0,
  "record_character_end": 742
}
```

#### Canonical ResearchRun

```json
{
  "run_id": "research-44",
  "specification_version": "1.0",
  "publication_ids": ["pub-2026-09"],
  "evidence_packet_ids": ["packet-12"],
  "advisory_memory": {"prior_claim_ids": ["claim-old-7"]},
  "generation_run_ids": ["gen-9"],
  "prompt_contract_version": "research-answer-v4",
  "output": "..."
}
```

#### Canonical EvidencePacket

```json
{
  "packet_id": "packet-12",
  "entries": [{
    "entry_id": "E0",
    "evidence_ref_id": "evref-81",
    "text": "...",
    "text_truncated": false,
    "text_transform": {"kind": "record-prefix", "character_limit": 12000},
    "selection_reason": "researcher selected"
  }]
}
```

## Appendix D - Relationship to External Standards

DERRIDAI's contribution is not a new generic provenance vocabulary, workflow engine, archive format, or serialization technology. It specifies scholarly-AI semantics that general standards can carry.

| Standard or technology | Primary responsibility relative to DERRIDAI |
|---|---|
| **DERRIDAI** | Documentary identity, scholarly attribution and epistemic state, evidentiary use, and source-to-claim traceability |
| **W3C PROV** | General provenance relationships among entities, activities, and agents |
| **RO-Crate** | Portable packaging and contextual metadata for research objects |
| **JSON / JSON-LD / RDF** | Serialization and exchange technologies |

PROV does not by itself define DERRIDAI distinctions such as SourceSpan precision, Record versus RecordRevision, speaker versus position holder, FieldAssertion authority, exact EvidenceRef locator mode, or SupportBinding. RO-Crate does not define what constitutes a DERRIDAI Record, which corpus state is authoritative, or how evidence supports a GeneratedClaim.

> **Interoperability design principle.** Use established standards for the general problems they already solve; use DERRIDAI only for the scholarly and AI-research semantics that remain domain-specific. Any loss of those semantics MUST be explicit rather than silent.

## Appendix E - Reference Implementation

_This appendix is non-normative._

The published DERRIDAI Core Specification 1.0 PDF records a pre-publication audit of DerridAI `master` at commit `724bef420a404fb2bc24182d8218f7a56d0ed84f` on 24 September 2026. That audit is a historical implementation snapshot, not part of the normative contract. The repository may advance beyond it while remaining governed by the normative requirements above.

The DerridAI application is the originating reference implementation. Its practical scholarly-provenance shorthand is:

`SOURCE -> PASSAGE -> SPEAKER -> POSITION HOLDER -> STANCE -> PROPOSITION -> EXACT EVIDENCE -> CITATION -> CLAIM`

Implementation lessons incorporated into DERRIDAI 1.0 include:

- **Pinned metadata contracts.** A run/build is bound to the metadata-contract snapshot it actually used; later schema edits do not reinterpret prior work. Stable field identity is recommended across non-semantic renames.
- **Protected segmentation.** Source conservation includes avoiding attribution- and quotation-sensitive splits merely to satisfy engineering size targets.
- **Server-side evidence rehydration.** Compact evidence references may be resolved back to authoritative Records instead of round-tripping stale full records through a client.
- **Packet integrity before generation.** Structural provenance checks are distinct from the semantic question of whether evidence truly supports a claim.
- **Rendered citations are not SupportBindings.** Machine evidence-marker relations must survive independently of human-readable citation formatting.
- **Advisory memory is not evidence.** Prior responses, claims, and reviewed decisions may guide later work, but current support requires re-resolution against current documentary state.

Reference-implementation coverage MUST NOT be treated as a conformance score unless each applicable requirement ID has been tested and documented under the relevant conformance profile.

## Appendix F - Rationale and Summary

_This section is non-normative._

DERRIDAI deliberately standardizes fewer objects than a complete application may contain. The Record is central because retrieval chunks, database rows, and cache entries are implementation artifacts while Records are intended to survive changes in retrieval infrastructure.

Evidence is a role rather than a copy because the same documentary material may support one inquiry and be irrelevant in another. Attribution remains first-class because document author, speaker, position holder, target, and quoted source can differ. FieldAssertion remains first-class because derivation, evaluation, authority, and value state are scholarly distinctions that generic provenance alone does not capture.

By contrast, extraction blocks, generic relations, schema-editor objects, storage projections, collection manifests, retrieval-candidate classes, packet-item wrapper classes, validation-result classes, and grading-result classes are not necessary to define DERRIDAI's scholarly semantics. Implementations may use them freely without making them part of the DERRIDAI conceptual model.

### Specification Summary

The DERRIDAI conceptual model is the scholarly source-to-claim chain:

`SourceDocument -> SourceSpan -> Record -> RecordRevision -> FieldAssertion -> Evidence Acquisition -> EvidenceRef -> EvidencePacket -> GenerationRun -> GeneratedClaim -> SupportBinding`

These are semantic roles, not mandatory class names. EvidenceRef and EvidencePacket may be embedded in retained run data, and a native FieldAssertion representation may use different field names when the required epistemic dimensions are recoverable without loss. Advisory memory remains outside the evidence chain until it is re-resolved against current documentary state.

The minimum DERRIDAI Core conformance profile requires the durable documentary substrate:

`SourceDocument -> SourceSpan -> Record`

with revision and assertion provenance preserved when applicable. Evidence, generation, and claim-binding requirements become mandatory when those capabilities are claimed; they remain part of the conceptual architecture whether or not a particular implementation instantiates them.

For audit, the essential chain reverses from GeneratedClaim through SupportBinding and EvidenceRef to the exact RecordRevision or SourceSpan and ultimately to the SourceDocument.

The scope rule follows directly: **DERRIDAI standardizes an object only when the object preserves a scholarly identity or distinction that must survive across implementations; generic infrastructure remains implementation-specific and is constrained only where it can damage that scholarly traceability.**

