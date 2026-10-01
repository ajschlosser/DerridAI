<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Document Intelligence and Semantic Content Graph

DerridAI's Document Intelligence subsystem analyzes a complete reviewed document before record-level metadata enrichment. Its purpose is to recover document-scale linguistic structure that is difficult to reconstruct from isolated Records: entity aliases, coreference clusters, quotations, candidate quotation speakers, and optional event annotations.

Document Intelligence is **derived, rebuildable state**. It does not change the cELF authority model:

- an entity mention is not evidence that the entity is a speaker, position holder, target, author, or referent;
- a BookNLP quotation-speaker prediction is a model-derived prompt hint, not a confirmed attribution;
- a graph edge is not documentary evidence;
- human confirmation never rewrites the derivation history of the model output that prompted it;
- canonical Records, FieldAssertions, EvidenceRefs, reviewed decisions, and publications remain authoritative.

The implementation deliberately separates the **Semantic Content Graph** from the cELF **Research Object Graph**. The Research Object Graph shows provenance and scholarly-object relationships such as SourceDocument → RecordRevision → FieldAssertion → evidence/claims. The Semantic Content Graph is a rebuildable analytical projection over the content of a corpus: characters, people, concepts, works, topics, organizations, places, and relationships among them.

## Corpus Builder pipeline

The relevant build sequence is:

```text
source acquisition
  → bounded extraction/transcription
  → source structure
  → semantic segmentation / Record construction
  → deterministic reviewed-text cleanup
  → Document Intelligence
  → record-local annotation projection
  → metadata-family enrichment
  → review
  → publication
```

Document Intelligence runs after deterministic cleanup so every offset is bound to the same reviewed text used by metadata enrichment. It operates on one conserved whole-document text assembled from the Records, not on one Record at a time.

The build records a SHA-256 of that complete text. Each Record projection also records a SHA-256 of its text. Human text edits immediately discard the affected record-local NLP projection. The retained document analysis remains available for audit but is reported as **stale** until rerun. A stale run is never projected into the current Semantic Content Graph.

Record split/merge operations do not make a provider result authoritative. A rerun remaps fresh whole-document annotations to the current topology.

## Providers

`api/app/document_intelligence.py` owns the provider-neutral contract. Provider-native output is normalized before the Corpus Builder or metadata prompts can use it.

### spaCy (universal baseline)

spaCy runs inside the API for every language and is what **Automatic** (the default) uses unless BookNLP is set up for an English document. It provides whole-document named-entity observations and conservative surface-form clusters. A language resolves to, in order: a configured/installed package (`SPACY_MODEL_<LANG>`; English, French and German `lg` models ship in the image), an administrator-installed spaCy language pack, then the multilingual `xx_ent_wiki_sm` entity model. The reported model name says which was used, including `(multilingual fallback)`; with none available the analysis is `unavailable`, never silently empty. It does **not** pretend to provide BookNLP-style pronominal coreference or quotation attribution.

### BookNLP

BookNLP is an optional **English-only** enhancement (BookNLP 1.0.8 accepts no other language) that adds pronominal coreference and quotation-speaker attribution. It runs in the optional `document-nlp` Compose service, isolated from the main API Python environment. The worker normalizes:

- entity mentions and BookNLP coreference IDs;
- aliases / canonical display names;
- quotation spans;
- candidate quotation-speaker clusters;
- optional event output when explicitly enabled.

The main API never imports BookNLP.

The worker is intentionally configured with `model="custom"` and never downloads models itself. Approved model artifacts are mounted read-only; they come either from an installed language pack (below) or from explicit `BOOKNLP_*` paths.

Required environment variables for BookNLP are:

```text
BOOKNLP_ENTITY_MODEL
BOOKNLP_COREF_MODEL
BOOKNLP_QUOTE_MODEL
```

Optional integrity pins:

```text
BOOKNLP_ENTITY_SHA256
BOOKNLP_COREF_SHA256
BOOKNLP_QUOTE_SHA256
```

When an expected SHA-256 is supplied, the worker verifies that artifact before loading the BookNLP pipeline; a mismatch makes the worker unready and the provider unavailable. The computed digests are always returned in model provenance even when no expected digest is configured.

Other optional settings:

```text
BOOKNLP_SPACY_MODEL=en_core_web_sm
DOCUMENT_NLP_TIMEOUT_SECONDS=900
```

The paths supplied in the `BOOKNLP_*` variables must point to files visible inside the worker (normally below `/models/booknlp`). The host directory `./data/models/booknlp` is mounted read-only at that location.

To enable it:

```bash
DOCUMENT_NLP_BASE_URL=http://document-nlp:8090 \
docker compose --profile document-nlp up -d --build
```

**Automatic** (the default) uses BookNLP only for a language with a configured worker and otherwise spaCy, without a warning; if a configured worker fails it falls back to spaCy with a warning. **spaCy only** skips BookNLP. **BookNLP only** never falls back: when no ready worker serves the document's language, Document Intelligence is recorded as unavailable with the reason (`provider_not_configured`, `language_unsupported` or `provider_unavailable`), and the corpus build continues.

### Language packs

Administrators install models on demand under **Settings → System → Language packs**. Each install is a cancellable background job that downloads the pack's files over HTTPS, refuses a redirect off HTTPS, stops at the declared size, and checks every SHA-256 before anything becomes active. Files are staged, then swapped in with `<models>/<lang>/active.json`; a failed or cancelled install leaves the previous pack untouched. The worker reads that manifest from its read-only mount (`/models/booknlp`), re-verifies the digests, and reloads when a different pack is installed. Explicit `BOOKNLP_*_MODEL` paths still take precedence.

The built-in catalog (`api/app/document_nlp_packs.py`):

| Pack                                                                                                                                    | Language     | Engine        | Download  | Installable    |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ------------- | --------- | -------------- |
| spaCy `md` / `lg` models (24 languages: ca, da, de, el, en, es, fi, fr, hr, it, ja, ko, lt, mk, nb, nl, pl, pt, ro, ru, sl, sv, uk, zh) | per language | spaCy 3.8     | 33–603 MB | yes            |
| spaCy multilingual entities (`xx_ent_wiki_sm`)                                                                                          | any          | spaCy 3.8     | ~11 MB    | yes            |
| BookNLP English, big models                                                                                                             | en           | BookNLP 1.0.8 | ~1.2 GB   | yes            |
| BookNLP English, small models                                                                                                           | en           | BookNLP 1.0.8 | ~160 MB   | yes            |
| Propp (NER + coreference)                                                                                                               | fr           | `propp_fr`    | ~167 MB   | reference only |
| LLpro                                                                                                                                   | de           | LLpro         | —         | reference only |

spaCy packs install the official 3.8.0 wheels from `explosion/spacy-models`; their SHA-256 digests (not published upstream) were computed from those wheels and live in `api/app/document_nlp_spacy_packs.json`. Only the wheel's model data directory is extracted (bounded size, no path escapes, no Python files) and loaded with `spacy.load(<directory>)`; the package code is never imported. Japanese and Chinese packs need Sudachi and pkuseg, which the API image installs; a pack whose Python requirements are missing is shown as not installable. Russian and Ukrainian packs declare pymorphy3 only for the lemmatizer DerridAI never loads. BookNLP digests were computed from the published artifacts; Propp's are pinned to a Hugging Face revision's LFS metadata. Reference-only entries need a worker for their engine that implements the `/analyze` contract, which DerridAI does not bundle yet. Model files are pickled PyTorch/Python objects, so loading one executes code: install only packs whose source you trust.

Administrators can add catalog entries as JSON (pack ID, ISO 639 language, engine, label, source, license, and `entity`/`coref`/`quote` files with HTTPS URL, SHA-256 and size). Custom entries are stored in `<models>/catalog.custom.json`. An installed BookNLP pack routes its language to the generic worker, but upstream BookNLP only runs English; a pack for another language needs a worker for it (`DOCUMENT_NLP_BASE_URL_<LANG>`).

### Languages

Upstream BookNLP models are English-only, so the bundled worker defaults to `BOOKNLP_LANGUAGE=en`. Languages are routed per worker rather than assumed:

```text
DOCUMENT_NLP_BASE_URL        # generic worker
DOCUMENT_NLP_LANGUAGES=en    # languages the generic worker serves
DOCUMENT_NLP_BASE_URL_FR     # a worker for French (likewise _DE, _ES, ...)
```

A language-specific URL wins over the generic one. Any worker for another language must implement the same `/analyze` request and normalized response contract (entities, coreference clusters, quotations, characters, model provenance) and must be backed by approved, mounted artifacts for that language; set `BOOKNLP_LANGUAGE` on the bundled worker only when its artifacts and BookNLP runtime actually support that language. Without a configured worker, that language's analysis is unavailable under **BookNLP** and uses spaCy under **Auto**. Provider-specific fields never enter Records.

## Build profiles

Corpus Builder exposes four Document Intelligence profiles:

| Profile                 | Intended use                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| Scholarly / non-fiction | People, quotations, aliases/coreference, and inputs for attribution/person/concept/work analysis        |
| Fiction / characters    | Character entities, aliases/coreference, dialogue/quotation speakers, and character-network projections |
| General                 | General entity and quotation analysis without a genre-specific interpretation                           |
| Off                     | Skip whole-document analysis                                                                            |

Provider selection is independent: **BookNLP** (default, no fallback), **Auto**, or **local spaCy**.

BookNLP event annotations are opt-in and experimental. BookNLP's event head is supplied by the same approved entity-tagger artifact, so no separate event-model file is required. Events are not enabled merely because the Fiction profile is selected.

## Normalized annotation state

The retained `document_intelligence` checkpoint contains provider/model/version identity, capabilities, profile, complete-text digest, record offset map, normalized entity clusters, entity mentions, quotations, warnings, and status.

Record-local `document_intelligence` data contains only the compact projection intersecting that Record. It is a prompt/navigation aid and is excluded from canonical publication JSONL. `nlp_candidates` is likewise excluded from publication.

The primary application read interface is GraphQL:

```graphql
query DocumentIntelligence($sourceId: String!, $buildId: String!) {
  source_document(source_document_id: $sourceId) {
    extraction_provenance
    pages {
      total
    }
    source_units(limit: 20) {
      total
    }
  }
  corpus_build(build_id: $buildId) {
    document_intelligence {
      status
      provider
      stale
    }
  }
}
```

`source_document` exposes source identity, extraction provenance, structure, and
bounded extraction-unit reads. `corpus_build.document_intelligence` exposes the
retained whole-document analysis and reports whether current Record text has
made it stale.

The REST read endpoints remain compatibility surfaces and call the same
transport-independent read services:

```text
GET /api/corpus/sources/{source_document_id}
GET /api/pdf/assets/{source_document_id}/blocks
GET /api/pdf/corpus-builds/{build_id}/document-intelligence
```

Commands remain REST. Rerunning Document Intelligence changes persisted derived
state and therefore is deliberately not a GraphQL mutation:

```text
POST /api/pdf/corpus-builds/{build_id}/document-intelligence/rerun
```

The Semantic Content Graph remains a separate derived read surface at
`GET /api/pdf/corpus-builds/{build_id}/semantic-content-graph`. It is materialized
from current reviewer-presented Records so blind-review sealing is preserved, then
saved as rebuildable System Data under a semantic generation token. Corpus writes
advance that token when text or semantic inputs change; interactive reads therefore
do not hash or rescan the whole corpus merely to decide whether the graph is current.
The hydrated graph and its traversal index are reused in process.

Interactive clients use the bounded view instead of the full projection:

```text
GET /api/pdf/corpus-builds/{build_id}/semantic-content-graph/view
    ?q=&types=&relation_kind=all|semantic|observational&focus=<node id>
    &node_limit=(≤250)&edge_limit=(≤1200)&min_mentions=
    &index_offset=&index_limit=(≤200)&index_sort=mentions|degree|records|label
```

It returns type/predicate facets, a ranked node set with the strongest induced
edges (overview) or one entity's neighbourhood with paged relations (focus), a
paged entity index, and explicit `candidate_*`/`truncated_*` counts. Relations
keep `relation_kind`, `authority_status`, supporting fields, and evidence-reference
counts.

Record-centred projections of the same graph support per-Record maps and graph walks:

```text
GET /api/pdf/corpus-builds/{build_id}/records/{record_id}/semantic-map
GET /api/pdf/corpus-builds/{build_id}/semantic-content-graph/nodes/{node_id}
```

Both are bounded (local and neighbour nodes, adjacent relations, linked Records, per-node Record lists). Record maps and node neighbourhoods are materialized on first use and saved as rebuildable System Data. Reopening a current projection is a direct read; a missing or stale projection is regenerated from the shared graph/index and then saved.

## Metadata enrichment

Whole-document annotations are added to metadata prompts only through bounded hints. Typical hints include:

- candidate people present in the Record;
- candidate quotation speakers projected from document-level quotation attribution;
- other named entities relevant to target/referent fields.

The prompt explicitly says these are advisory and are not evidence or proposition ownership. The normal FieldAssertion/evidence/review pipeline remains responsible for any metadata value the LLM proposes.

This is especially important for DerridAI's attribution chain. Coreference can help establish that "he" and "Emmanuel Levinas" are likely the same discourse entity, but it cannot establish that Levinas holds the proposition currently being analyzed.

Entity clusters also feed the semantic identity registry as advisory aliases. A person cluster can resolve an otherwise unresolved reviewer edit (`Derrida` → `Jacques Derrida`) to the same value, but only when the names are compatible. A pronoun in the cluster is never a name, and a cluster never overrides a deterministic difference or a reviewed identity. A Record projection bound to other text is ignored. Provider, model and cluster ids are kept as provenance.

## Semantic Content Graph

`api/app/semantic_content_graph.py` builds a derived graph from current Records plus a non-stale Document Intelligence run.

Node types currently include:

- `character` (PERSON clusters under the Fiction profile);
- `person`;
- `concept`;
- `work`;
- `topic`;
- `organization`;
- `place`;
- generic `entity` when a provider category has no stronger normalized mapping.

Nodes are semantic identities, not strings. Metadata values resolve through the build's semantic identity registry (reviewed alias sets and reviewed values) and each field's value-matching policy, so `J.P. Dingus` and `JP Dingus`, or `pushing the boundaries` and `push the boundaries` when a lemmatizer is installed, share one node. Each node keeps:

- `surface_forms`: every surface observed for it;
- `aliases`;
- `canonical_value_key` and `identity_id` (when a reviewed identity names it);
- `identity_version`;
- `cluster_ids`, for provider provenance.

The display label prefers a reviewed value, then a reviewed alias set's preferred form, then the provider's canonical label, then the most-supported surface. Merging is conservative:

- Two identities a reviewer established as distinct never merge.
- Identities stay scoped by kind: a person is never merged into a concept.
- BookNLP characters that share a name stay apart.
- spaCy's surface clusters merge when they are one identity; the merged cluster's old node id still resolves through `node_aliases`.

Record metadata is never rewritten by the projection.

The graph deliberately distinguishes two kinds of edges.

### Observational edges

Observational edges report a bounded computational pattern, not a scholarly claim.

Examples:

- `co_occurs` — two indexed/document entities occur in the same Record;
- `dialogue_proximity` — multiple candidate quotation speakers occur in the same Record.

These edges remain `unreviewed`, contain no fabricated source evidence, and are visually distinct in the UI.

### Semantic edges

Where existing canonical metadata already expresses a relationship, the graph projects it rather than asking a second model to reinvent it. Current examples include:

- `position_holder --stance/addresses→ target`;
- `speaker --quotes→ quoted_speaker / quoted_author`;
- `quoted_author --quoted_work→ work`.

A semantic edge carries the authority state, supporting field identities, Record IDs, and available metadata evidence that produced it. Aggregate edges are conservative: one unreviewed occurrence prevents a multi-occurrence edge from being displayed as wholly human-confirmed, and any disputed occurrence makes the aggregate disputed.

The `target` field is polymorphic. The graph reuses an already-resolved person/work/entity node with the same canonical label before falling back to a concept node.

## Record semantic maps

`api/app/record_semantic_map.py` projects the Semantic Content Graph around one Record or one node.

A **Record map** contains the Record's local nodes (nodes whose Record coverage includes it, plus endpoints of relations it supports), its in-Record relations, bounded outward relations to neighbouring nodes, and **linked Records**. Linked Records are ranked deterministically by shared nodes weighted by inverse Record frequency, with a shared semantic relation weighted above a node and plain POS terms weighted below entities. The map also returns the Record's annotation mentions as exact offsets into the current Record text, with the layer (`entity`, `quotation`, `ner`, `pos`) and tag that produced each.

A **node neighbourhood** contains the node, its adjacent relations (semantic first), its neighbours, and every Record in which it occurs or takes part in a relation.

The Record-level **POS/NER term layer** is stored in `nlp_candidates.terms` by `nlp_annotations.annotate_record`: named entities plus proper-noun and noun runs, bounded per Record and bound to the Record-text digest. It is computed whenever a spaCy pipeline for the Record language is installed, whether or not a schema field declares POS/NER tags. Each term keeps its exact `text`, `start` and `end`, and may carry a derived `identity_text`: the name identity of a PERSON entity, or the noun/verb lemmas of a POS run. It is omitted when the pipeline produced no lemmas. A term joins a node by surface first, then by that identity (a person's name identity, or a concept's lemma identity); the rest become `term` (POS) or entity-type nodes that link Records only by shared surface or identity text. Terms are navigation aids and never metadata values, prompt authority, or evidence; `nlp_candidates` remains excluded from publication.

Each layer reports `ok`, `stale` (Record text changed after annotation, or the document run is stale), `missing` (not analysed yet), or `unavailable`. Stale or missing layers contribute no mentions or term nodes.

## Fiction workflow

With the **Fiction / characters** profile, PERSON coreference clusters become Character nodes. The review surface provides a searchable complete character/entity index and an interactive graph.

The index exposes canonical character names, aliases, mention counts, and Record coverage. The graph can show observational co-occurrence and dialogue proximity without pretending these automatically mean friendship, kinship, opposition, or conversation addressee.

Stronger literary relationships must be evidence-bound semantic relations rather than inferred from proximity alone.

## Scholarly and non-fiction workflow

The default scholarly schema already indexes `persons`, `concepts`, and `works_referenced`. Document Intelligence contributes document-scale person identity/coreference and quotation context; normal metadata enrichment remains responsible for philosophical concepts and attribution.

The resulting index exposes every current Person, Concept, Work, Topic, and provider-derived entity. Existing scholarly attribution fields project evidence-aware edges into the relationship map.

This design lets DerridAI show, for example, that a Record represents a Heidegger position whose target is a concept, while preserving the distinction between document author, textual speaker, quotation speaker, and position holder.

## Review UI

Record Review includes an **Entities & relationships** panel after the Document Intelligence stage.

It provides:

- server-side search, entity-type facets, relation-kind and minimum-mention filters, and a density control;
- a paged, sortable entity/concept index covering every matching entity, not only nodes visible in the diagram;
- an interactive, zoomable force-directed map with neighbourhood exploration and a breadcrumb trail;
- a selected-node inspector with aliases, mention/Record/connection counts, and relations grouped by semantic versus observational, carrying authority status and evidence-reference counts;
- visually distinct semantic, observational, and disputed edges;
- a stale-analysis warning and explicit **Reanalyse document** action after reviewed-text changes.

The diagram renders at most 250 entities from the bounded view and reports what it omitted; the paged index remains the complete route to every entity.

Each Record's inspector also has a **Semantic map** tab that shows the Record map, its annotated text, and its linked Records, and lets the reviewer walk node → node and node → Record across the corpus with a back-tracking exploration path.

## Publication and interoperability

Normalized provider output and the Semantic Content Graph are implementation artifacts, not additional first-class cELF objects. They therefore remain outside canonical JSONL Records.

The graph can later be exported in JSON/GraphML/JSON-LD/RDF as a derived analytical artifact, but every semantic relationship must remain resolvable to its current Record/revision/evidence provenance when that relationship is presented as a scholarly assertion.

Graph traversal may later assist retrieval. A graph edge must never substitute for EvidenceRef resolution or become a citation source.

## Invariants

Tests and future implementations must preserve these rules:

1. Provider annotations never directly confirm a FieldAssertion.
2. Provider output never becomes documentary evidence merely because offsets match source text.
3. Whole-document and Record-local offsets are hash-bound to the text analyzed.
4. Reviewed-text changes invalidate text-bound projections.
5. Blind second-opinion values cannot leak through graph projections.
6. Observational graph edges are not relabelled as semantic relationships.
7. Semantic edge authority cannot exceed the weakest unresolved/disputed support aggregated into that edge.
8. Canonical publication JSONL excludes `nlp_candidates` and `document_intelligence`.
9. Missing BookNLP is non-fatal to Corpus Builder.
10. The worker and corpus builds never download models; only an administrator's language-pack install does, and only pinned, digest-verified files become active.
