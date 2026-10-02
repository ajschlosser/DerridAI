<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Metadata schemas

A metadata schema says which fields a JSONL record has, what each may hold, and what the model is told to look for in each. Builds target a schema. DerridAI ships three read-only built-in profiles: the historical scholarly default, Fiction, and Non-fiction. A built-in profile can be duplicated when a project needs a customized variant.

## Versioning and field identity

Schemas are semantic-versioned independently of the application and corpus contracts. New saved schemas start at `1.0.0`; an unchanged save retains its version; adding fields increments the minor version, removing fields increments the major version, and other definition changes increment the patch version. Each field has a stable `field_id` separate from its display name, so a deliberate rename can retain semantic/provenance identity.

The built-in domain profiles also use stable namespaced identities. Their fields remain ordinary schema-defined `FieldAssertion` targets: choosing Fiction or Non-fiction does not create a second metadata system or hard-code domain fields into Record processing.

## What a schema contains

- **Groups.** Each group is one model call per record. It has opening text, an optional heading for its field list, notes, a trailer, and a footer with the evidence and assessment instructions. The footer may use `{fields}` and `{assessed_fields}`. Groups organize computation; they are not Record fields.
- **Fields.** Each field has a stable semantic identity plus name/label, type (`text`, `number`, `boolean`, `choice`, `list`, or `repeatable`), a group, and the instruction the model receives (`{values}` is replaced by allowed values). A deliberate rename may preserve the stable field identity so compatible reviewed precedents remain attached to the same semantic field. A `choice` field has allowed values, each with an optional definition; `strict` makes them the only values the model may return. `evidence` requires source binding, `assess` requests confidence, and `review` keeps a record from being accepted while the field is unresolved. Fields may also define POS/NER guidance and reviewed-precedent retrieval policy.
- **Scope.** Record-scoped fields describe one research record. Corpus-scoped fields are inferred once for the work/corpus and inherited by its records.
- **Guidance.** Every built-in Fiction and Non-fiction field has an explicit model instruction. Controlled-choice fields additionally define what each allowed value means. Their domain fields are evidence-bound and assessed, so a populated value remains auditable rather than becoming an unqualified model label.

### Repeatable structured fields

A repeatable `SchemaField` stores a bounded list of objects under its stable field
name. Every object has a stable `instance_id` and one value for each typed member
field. For example, `quotation_relations` can associate `quoted_speaker` and
`quoted_addressee` in the same instance. Review surfaces may display those members as
`QUOTED_SPEAKER_1`, `QUOTED_ADDRESSEE_1`, and so on, but the number is only a
presentation index: reordering rows does not change their identity, and numbered
keys are never written into canonical records. This avoids the alignment failures
of parallel lists and permits deterministic, model, and human processes to revise
the same associated instance.

Each member value is also a separate `FieldAssertion` target identified by the
container field, stable instance, and stable member field. Derivation, evaluation,
authority, evidence, confidence, and supersession therefore remain independently
recoverable. A human deletion creates an explicit superseding absence assertion;
it never silently renumbers or erases prior provenance. This lossless structured
projection is the cELF representation, while numbered labels are UI-only.

## Built-in profiles

### Scholarly default (`default`)

This is the historical DerridAI profile and remains the fallback when no profile is selected. It focuses on scholarly discourse and attribution, quotation relations, and semantic indexing. Existing builds and integrations therefore retain their prior behavior.

### Fiction (`derridai-fiction`)

The Fiction profile separates narrative voice, storyworld facts, speech relations, literary interpretation, and work-level classification. Its field guidance is deliberately conservative about narrator/focalizer distinctions, scene presence, symbolic interpretation, and outside plot knowledge.

<!-- prettier-ignore -->
| Field | Scope | Guidance |
| --- | --- | --- |
| `fiction_form` | Corpus | Classify the work as novel, novella, short story, story cycle, drama, narrative poetry, other fiction, or mixed/uncertain from whole-work or paratextual evidence rather than one incidental passage. |
| `fiction_genres` | Corpus | Capture established genres/subgenres such as gothic, detective fiction, romance, historical fiction, science fiction, fantasy, satire, or bildungsroman; do not promote a single motif into a work-wide genre. |
| `narrator` | Record | Identify the narrating voice, using a name when textually supported or a concise role such as “unnamed first-person narrator”; keep narrator distinct from author, focalizer, and speaking characters. |
| `point_of_view` | Record | Classify the local passage as first person, second person, third-person limited/omniscient/objective, mixed/shifting, or indeterminate. |
| `focalizers` | Record | Identify the character/consciousness through whose perception or knowledge the scene is presented; do not automatically equate focalizer with narrator. |
| `narrative_functions` | Record | Capture functions such as scene narration, description, exposition, dialogue, interior monologue, free indirect discourse, summary, reflection, or transition. |
| `temporal_relation` | Record | Distinguish chronological narration, flashback/analepsis, flashforward/prolepsis, iterative/habitual narration, narratively present action, mixed, or indeterminate time. |
| `characters_present` | Record | List fictional characters actually participating in, perceiving, or physically present in the represented scene; exclude merely mentioned off-scene figures. |
| `characters_mentioned` | Record | List characters referred to but not participating in the represented scene, without duplicating present characters unless the text genuinely blurs the distinction. |
| `character_relationships` | Record | Record only relationships established or materially invoked by the passage, using concise relation strings; never fill from outside knowledge. |
| `locations` | Record | Capture places that materially situate the action or narrated setting; exclude incidental comparisons. |
| `setting_time` | Record | Capture text-supported temporal settings such as date, historical period, season, time of day, age, reign, or relative story time without inventing precision. |
| `events` | Record | Capture principal fictional events as concise actor-action descriptions while preserving negation and uncertainty and avoiding trivial micro-actions. |
| `objects_of_significance` | Record | Capture narratively salient objects that organize the scene, recur, or carry supported plot/symbolic importance; do not list every concrete noun. |
| `direct_speech` | Record | Mark true only for words directly represented as an utterance; distinguish direct speech from summarized/reported speech. |
| `dialogue_speakers` | Record | Identify speakers of direct dialogue when local context supports them; do not substitute the document author for an unresolved character speaker. |
| `dialogue_addressees` | Record | Identify directly addressed characters/groups only when textually supported; use an empty list instead of guessing an implied listener. |
| `reported_speech_sources` | Record | Identify characters or narrating sources whose speech, thought, letter, message, or prior utterance is indirectly reported or paraphrased. |
| `themes` | Record | Capture broad ideas/problems the passage substantively develops rather than nouns that merely occur. |
| `motifs` | Record | Capture recurring images, situations, phrases, objects, or patterns only when recurrence is supported by context or reviewed precedent. |
| `symbols` | Record | Capture objects/images/places/gestures/figures with a supported symbolic function beyond literal reference; salience alone is not symbolism. |
| `tone` | Record | Use one or two concise labels for textual attitude/register (for example ironic, elegiac, comic, menacing, detached, tender) grounded in linguistic evidence. |
| `literary_devices` | Record | Capture materially used techniques such as irony, foreshadowing, metaphor, simile, free indirect discourse, unreliable narration, stream of consciousness, or dramatic irony; avoid speculative over-labeling. |

The profile groups these fields as **Narrative voice and perspective**, **Characters, setting, and events**, **Dialogue and reported speech**, **Literary interpretation**, and **Work-level fiction profile**.

### Non-fiction (`derridai-nonfiction`)

The Non-fiction profile separates propositions and attribution from the evidence used to support them, semantic entities from rhetorical/document structure, and local record metadata from work-level genre/audience metadata.

<!-- prettier-ignore -->
| Field | Scope | Guidance |
| --- | --- | --- |
| `nonfiction_genre` | Corpus | Classify the work as scholarly article, monograph, essay, journalism, history, biography, memoir, report, textbook, reference, technical documentation, legal/policy, speech/lecture, correspondence, other, or mixed/uncertain from whole-document evidence. |
| `subject_domains` | Corpus | Capture principal disciplines, subject areas, or professional domains using established concise labels; do not elevate one incidental topic to the work level. |
| `intended_audience` | Corpus | Describe the intended readership only when paratext, register, or publication context supports it; avoid demographic speculation. |
| `speaker` | Record | Identify a distinct textual/grammatical speaker when one exists; ordinary unsigned authorial prose need not invent a separate speaker. |
| `position_holder` | Record | Identify the person, institution, group, or source holding the principal proposition; distinguish holder from grammatical speaker and from mentioned/criticized entities. |
| `claim` | Record | State the principal substantive proposition concisely and source-faithfully, preserving negation, modality, quantities, and attribution; do not force headings, raw data, or references into claims. |
| `claim_type` | Record | Classify the primary proposition as empirical, causal, interpretive, normative, definitional, methodological, predictive, procedural, anecdotal, descriptive, or other. |
| `target` | Record | Identify the proposition, policy, interpretation, practice, entity, or concept toward which the holder's stance is directed, using a short noun phrase rather than an explanatory sentence. |
| `stance` | Record | Capture the holder's orientation toward the target (affirm, reject, criticize, question, qualify, suspend, neutral, describe) from explicit wording. |
| `certainty_level` | Record | Preserve epistemic modality by distinguishing direct assertion, qualified, tentative, speculative, hypothetical, reported/attributed, or not-applicable claims. |
| `claim_scope` | Record | Capture the population, place, period, corpus, case, jurisdiction, or other domain to which the claim explicitly applies; never broaden the source's qualifiers. |
| `evidence_types` | Record | Label kinds of support actually used (for example statistical, documentary, archival, experimental, observational, testimonial, citation, logical, comparative, case evidence). |
| `evidence_items` | Record | Capture concrete support such as measurements, documents, quotations, observations, findings, datasets, witness accounts, or cited results, retaining material numbers/source names. |
| `sources_cited` | Record | Capture named documents, authors, organizations, datasets, reports, studies, archives, or other explicitly cited/attributed sources; do not infer uncited sources. |
| `statistics` | Record | Preserve material quantitative statements with quantity, unit, population/denominator, and time frame when present rather than storing contextless numbers. |
| `examples_or_cases` | Record | Capture examples, case studies, anecdotes, episodes, or instances used to illustrate/support the point; do not call the main subject an example unless the text does. |
| `methods_or_procedures` | Record | Capture explicitly described research methods, analytical procedures, experimental steps, documentary methods, technical procedures, or operational instructions without inferring unstated methodology. |
| `topics` | Record | Capture materially developed topics as short precise noun phrases; exclude incidental mentions. |
| `persons` | Record | Capture people materially discussed, quoted, studied, or otherwise relevant; resolve names only when supported. |
| `organizations` | Record | Capture materially relevant organizations, institutions, companies, agencies, movements, or organized bodies; do not turn generic nouns into named organizations. |
| `places` | Record | Capture substantively relevant geographic/geopolitical/facility locations at the most specific supported level. |
| `dates` | Record | Capture dates, years, eras, periods, or intervals anchoring claims/events/evidence while retaining the source's degree of precision. |
| `events` | Record | Capture named or clearly delimited real-world events; do not convert every action into an event entity. |
| `works_referenced` | Record | Capture identifiable books, articles, reports, laws, media works, titled datasets, or other works as named in the source without inventing bibliographic details. |
| `laws_or_policies` | Record | Capture named laws, regulations, court decisions, standards, treaties, policies, programs, or formal rules, including jurisdiction when supplied. |
| `section_function` | Record | Classify what the record primarily does: introduction, background, definition, claim, evidence, analysis, method, result, example/case, counterargument, recommendation, conclusion, reference, transition, or other. |
| `terms_defined` | Record | Capture terms/categories/measures/concepts explicitly defined, stipulated, operationalized, or materially clarified; ordinary descriptive wording is not a definition. |
| `questions_addressed` | Record | Capture explicit or clearly framed research/practical questions or problems the record asks or directly addresses; do not invent a question from topic alone. |
| `counterpositions` | Record | Capture opposing, alternative, or limiting positions materially presented or answered, retaining the holder when identified. |
| `recommendations` | Record | Capture explicit actions, policies, practices, or next steps the record recommends/advises/requires/proposes, preserving conditions and intended actors. |
| `conclusions` | Record | Capture conclusions or implications explicitly drawn from prior reasoning/evidence, distinguishing them from premises, raw results, or recommendations. |

The profile groups these fields as **Claims and attribution**, **Evidence and methods**, **Topics and entities**, **Rhetorical and documentary structure**, and **Work-level non-fiction profile**.

## The locked core

`region_type`, `primary_text` and `discourse_role` are in every schema, in the `discourse` group, and cannot be changed or removed: DerridAI's page-range and document-layout logic depends on them. Their prompt lines and values come from the code. Names DerridAI itself uses (the record's source fields, the document-level fields records inherit, computed fields) cannot be field names either.

The generic `discourse_role` vocabulary remains cross-domain for compatibility. Domain profiles do not redefine it. Fiction uses dedicated fields such as `narrative_functions` and `point_of_view`; Non-fiction uses `claim_type` and `section_function` for more precise domain classifications.

## NLP hints

Schema fields can provide deterministic autocomplete for Universal POS tags and the supported NER tag vocabulary. These tags are prompt/search guidance about what linguistic forms to notice; they do not themselves populate metadata, prove that a value applies, or replace evidence requirements.

The built-in Fiction and Non-fiction profiles include curated POS/NER hints where surface-form candidate generation is useful, while interpretive classifications such as point of view or claim type rely on passage-level evaluation rather than token labels. Non-fiction `evidence_types` and `evidence_items` likewise rely on passage-level evaluation: raw noun/name/number candidates are not offered as possible values because evidence kind and concrete evidentiary support are semantic relations, not token classes.

## Reviewed-precedent retrieval

A field or group can allow evidence-bound reviewed precedents to guide later enrichment. A field-level profile overrides its group's profile; otherwise the group profile applies, including to locked core fields. The active retrieval profile contains:

- `enabled`;
- `max_items` (maximum ordinary precedents);
- `max_corrections` (a separate correction quota);
- `min_similarity`;
- `include_corrections`;
- `include_confirmed_absence`;
- `match_field_ids` (optional stable field identities whose reviewed values should agree before a precedent is preferred).

Corrections keep the rejected model value as negative evidence; it must never be taught as the correct answer. Confirmed absence is reusable only when a reviewer explicitly bound source evidence to that no-value decision. Locked core fields can inherit group policy.

These controls affect advisory enrichment context only. They do not modify canonical reviewed records, change assertion authority, or route metadata exemplars into Research response/claim memory. See [METADATA_MEMORY.md](METADATA_MEMORY.md).

## Value matching

A field's optional `equivalence_profile` sets when two differently written values count as the same semantic value. It is used for review feedback, correction and precedent grouping, pre-fill votes, and the Semantic Content Graph, and is set under **Value matching** in the schema editor. The stored value and its evidence are never rewritten.

<!-- prettier-ignore -->
| `mode` | Treats as the same |
| --- | --- |
| `exact` | only identical values |
| `text` | Unicode, whitespace, case, quote and dash variants |
| `entity_name` | `text` plus initials and their punctuation, and `Surname, Given` order (`J. P. Dingus` = `J.P. Dingus` = `JP Dingus`). `J. Dingus` and `John Dingus` stay unresolved unless a reviewed alias or Document Intelligence links them. |
| `lexical_phrase` | `text` plus noun and verb lemmas from the installed spaCy pipeline for the record's language (`pushing the boundaries` = `push the boundaries`). Negation, prepositions and modifiers are kept. With no lemmatizer the result is unresolved, never guessed. |
| `controlled` | `text` variants of a controlled value; aliases are never invented |

`collection_semantics` is `set` (the default) or `ordered`. A list is the same value only when every member pairs one-to-one with an equivalent member; partial overlap is a difference. `identity_kind` scopes identities (`person`, `character`, `concept`, ...), so fields that declare the same kind share identities.

A field without a profile resolves by its semantic compatibility id and then by its type. Person-bearing core fields (`speaker`, `position_holder`, quoted speaker/author/position holder/addressee, `persons`) use `entity_name` with kind `person`. `concepts` and `topics` use `lexical_phrase`. `quotation_chain` is ordered. Strict choices are `controlled`, while booleans and numbers are `exact`. Anything else is `text`. The Fiction profile declares `entity_name` with kind `character` for narrator, focalizer, character and dialogue fields, and `lexical_phrase` for themes, motifs and symbols. An unset profile does not change a schema's content hash. A build keeps the schema copy it started with, so earlier Fiction builds keep type-based matching.

## Run-specific field guidance

Corpus Builder can add per-build guidance after schema selection: an instruction and/or names, titles, concepts, or variants to watch for. This guidance is saved with the build, not the schema. Exact phrase matches may become review cues and prompt context, but they do not change allowed values or count as evidence.

## One schema per build, fixed

A build copies its schema when it starts. Editing or deleting a saved schema afterwards cannot change it, and a build is never re-run against another schema.

## Sharing

Export writes one JSON file: `{"derridai_metadata_schema": 3, "sha256": …, "schema": …}`. Import validates the file like anything typed into an editor; the checksum catches damage or edits after export, and is not a signature. Format 1 and 2 schemas remain readable and are migrated in memory.

## API (administrators)

`GET/POST /api/pdf/metadata-schemas`, `GET/PUT/DELETE /api/pdf/metadata-schemas/{id}`, `GET …/{id}/export`, `POST /api/pdf/metadata-schemas/import`.

## Using it

- **Choose one for a build:** step 5 of the build setup ("Metadata schema"). The build keeps its own copy. The built-in scholarly, Fiction, and Non-fiction profiles appear alongside project-created schemas.
- **Customize a built-in profile:** built-ins are read-only so their identities remain stable. Duplicate one, then edit and save the copy.
- **Edit schemas:** administrators use **System → Metadata schemas**. "Manage schemas…" in Corpus Builder opens the same editor in a dialog, with a link to that page. The editor lists built-in and saved schemas, groups/instructions, fields, allowed values, evidence/assessment/review requirements, NLP hints, and Memory & retrieval controls, plus duplicate/delete/export/import actions. Researcher accounts cannot open the page or change schemas.
- **Try one:** the editor's "Try it on a passage" shows the prompt a group produces, or runs it on a passage with a model. A real build adds the document details, editorial memory and neighbouring records to that prompt.

## What follows the schema

Prompts and the shape of the model's answer; which fields the model may set and which need cited evidence; which fields keep a record from being accepted; what a person may edit and how it is checked; the review panel (fields, labels, controls) and bulk edit; the enrichment dialog's groups. The historical scholarly default continues to reproduce the previous DerridAI behavior, while Fiction and Non-fiction use the same generic schema/FieldAssertion pipeline with different contracts.

## Compatibility

- Fixed fields that sit outside the schema (the document-level ones records inherit) remain unchanged.
- A build made before schema snapshots existed has no schema copy and falls back to the historical scholarly `default` profile.
- Compatibility loaders may accept older schema representations, but new documentation/code should use the current field identity and retrieval-profile contract rather than reviving migrated legacy flags.
