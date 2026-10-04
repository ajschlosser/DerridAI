<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# DerridAI

![DerridAI लोगो](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [العربية](README.ar.md) · [简体中文](README.zh-CN.md)

DerridAI एक local-first, provenance-preserving शोध वातावरण है, जिसका उपयोग विद्वतापूर्ण corpora बनाने, समीक्षा करने, खोजने और उन पर प्रश्न चलाने के लिए किया जाता है। यह एक ही Docker अनुप्रयोग में source ingestion, human-in-the-loop corpus निर्माण, evidence-bound metadata enrichment, derived vector/search indexes और evidence-grounded retrieval-augmented generation (RAG) को एक साथ लाता है।

DerridAI **cELF 1.0 — Capta-Enriched Lexical Format** का मूल reference implementation भी है। cELF AI-सहायित documentary research के लिए provenance-preserving information architecture परिभाषित करता है। DerridAI source identity, record identity और revision, metadata assertions, evidence, generated claims और support bindings को अलग-अलग audit करने योग्य रूप में रखता है, न कि उन्हें एक opaque vector store में मिला देता है।

वर्तमान संस्करण: **0.81.0 — Fall River** ([release notes](docs/notes/0.81.0.md)). Fall River के बाद application version नहीं बढ़ाया गया है; यह README वर्तमान `master` branch का वर्णन करता है, जिसमें 0.81.0 के बाद का वह काम भी शामिल है जो tagged release का हिस्सा नहीं है।

## वर्तमान `master`

मौजूदा branch 0.81.0 tag के बाद काफ़ी आगे बढ़ चुका है, जबकि application version अभी भी 0.81.0 है। नीचे का सार वर्तमान product को बताता है, नई release notes को नहीं।

- **Corpus Builder अब progressive Setup → Build → Review → Publish workflow है।** इसमें bounded concurrent enrichment, स्पष्ट corpus topology और Record-size विकल्प, resumable/revision-aware review, persistent Record-local review queues, publication blockers के लिए focused remediation sessions, repeatable metadata groups, audio speaker assignments और verified preparation के दौरान safe text review शामिल हैं।
- **Metadata और evidence processing कम model work के साथ अधिक मजबूत semantics सुरक्षित रखता है।** Deterministic/candidate-first routing, semantic identity और value equivalence, support-validated evidence cascade v2, structured-output repair/retry classification और incremental Metadata Memory reconciliation latency घटाते हैं, बिना retrieval relevance या malformed output को evidence मानने के।
- **Pipeline Studio executable computation को स्पष्ट रूप से model करता है।** Server-owned purposes, strategy families, scholarly effects, typed ports, resolved wiring, stage traces, scope/complexity metrics, tunable retrieval parameters और non-persistent comparison अब Search, Research, reviewer evidence, recovery, segmentation और enrichment के अधिक paths पर लागू हैं।
- **Works portable research sites publish कर सकता है।** Static exports DerridAI SDK और dedicated Vue runtime को browsing, annotations, browser semantic indexing, reader-configured providers और evidence-linked citations वाले Research के लिए जोड़ते हैं, लेकिन export को canonical corpus state नहीं बनाते।
- **Realtime invalidation और progressive loading अधिक polling और blank-page refreshes की जगह लेते हैं।** Works, Record, Search, Research, Response Library, Languages, Relationships, Accounts/Roles, Metadata Memory और संबंधित surfaces उपयोगी content बनाए रखते हैं, failures को local रखते हैं, retry देते हैं और stale responses को अस्वीकार करते हैं।
- **Frontend legacy runtime को लगातार retire कर रहा है।** Router-owned navigation, Vue-hosted dialogs/notifications, shared domain/state modules, Pinia slices और extracted helpers coupling कम करते हैं; शेष compatibility code जानबूझकर isolated है।
- **cELF और developer infrastructure को कड़ा किया गया है।** Specification product-neutral और profile/provenance-oriented है, generalized `EvidenceRef` locator semantics के साथ; critical code boundaries के architecture maps जोड़े गए हैं; CI/pre-push selection, repository hygiene और copyright enforcement मजबूत किए गए हैं।

## DerridAI क्या करता है

- **विविध स्रोतों को प्राप्त और ingest करता है।** PDF, plain text, RTF, DOCX, images और audio अपलोड करें; URL और Project Gutenberg सामग्री import करें; या Corpus Capture के माध्यम से Wikidata, Project Gutenberg और Wikisource adapters से कार्य खोजें और प्राप्त करें। Ingestion media-specific safety/resource limits लागू करता है और extractor/tool/version provenance सुरक्षित रखता है।
- **माध्यम के अनुसार corpus बनाता है।** Corpus Builder source registration, extraction/transcription, source-unit mapping, structure/segmentation, enrichment, record construction, review और publication को अलग stages में रखता है। Controls और evidence coordinates source medium के अनुसार बदलते हैं; PDF/page semantics हर source पर लागू नहीं किए जाते।
- **cELF provenance और field authority सुरक्षित रखता है।** Canonical `FieldAssertion` records derivation, evaluation, authority, value state, confidence, evidence, actor/model, stable field identity और record revision को अलग-अलग दर्शाते हैं। Human confirmation model या deterministic provenance को मिटाती नहीं है।
- **Evidence को context में रखकर records की समीक्षा करता है।** Reviewer text और metadata संपादित कर सकते हैं, `SourceSpan` और दूसरे records की evidence देख सकते हैं, revisions की तुलना कर सकते हैं, semantic maps और relationships में जा सकते हैं, suggestions स्वीकार/अस्वीकार कर सकते हैं और auditable decisions के साथ publish कर सकते हैं। Optimistic saves UI को responsive रखते हैं और एक ही record पर conflicting writes को serialize किया जाता है।
- **Configurable metadata schemas और reviewed precedents का उपयोग करता है।** Schemas stable fields, types, controlled values, evidence/review rules, POS/NER hints, field scope, model guidance और retrieval policy परिभाषित करते हैं। Reviewed examples सीमित, evidence-linked precedents बन सकते हैं, लेकिन वे canonical reviewer decisions को replace नहीं करते।
- **Optional Document Intelligence जोड़ता है।** Provider-neutral derived analysis layer entities, coreference, quotation speakers और semantic-content relationships प्रदान कर सकती है। spaCy language packs multilingual baseline देते हैं; isolated BookNLP worker optional English enhancement है। ये annotations rebuildable analysis रहते हैं, source evidence या corpus authority नहीं बनते।
- **Derived projections में search करता है, corpus authority से अलग रखते हुए।** ChromaDB embedded या HTTP-server mode में rebuildable semantic/search projections और caches रखता है। Dense, lexical और MMR retrieval, RRF, filters, language routing और bounded cross-encoder reranking उपलब्ध हैं।
- **Evidence-grounded Research/RAG चलाता है।** Research hybrid retrieval, reranking, selected-evidence mode, evidence budgets, streamed/cancellable generation, deterministic citation rendering, claim/support persistence, claim validation, response/claim memory और LLM grading का समर्थन करता है। Incomplete provenance वाले records evidence से बाहर रखे जाते हैं; उन्हें चुपचाप valid support नहीं माना जाता।
- **AI pipelines को inspect और configure करता है।** Pipeline Studio versioned pipeline definitions, assignments, run traces, stage-level latency/error/fallback metrics, point-of-use traces, non-persistent Research A/B comparison और fixed-case Research benchmark runs दिखाता है। Retrieval, memory, metadata-precedent और reviewer-evidence stages स्पष्ट रूप से configure किए जा सकते हैं, जबकि provenance/authority gates structural constraints बने रहते हैं।
- **API transports को जिम्मेदारी के अनुसार अलग करता है।** REST commands और mutations का मालिक है; read-only cELF-aware GraphQL façade typed reads देता है; authenticated WebSocket plane realtime operation notifications भेजता है। Realtime messages कभी canonical state नहीं होते और clients REST/GraphQL से resynchronize कर सकते हैं।
- **Controlled multi-user research का समर्थन करता है।** Built-in Administrator और Researcher roles के साथ researcher-safe custom roles UI और API दोनों में enforce होते हैं। Researcher-visible source text API boundary पर summarize होता है, jobs owner-scoped होते हैं और administrator-only corpus/system mutations उपलब्ध नहीं होते।
- **Long-running work को observable बनाता है।** Corpus builds, LLM review, RAG, grading, imports, model/language-pack work और vector upserts cancellable operations के रूप में durable snapshots/history और realtime progress के साथ दिखाई देते हैं। Restart से interrupted process-local work failed mark होता है; उसे silently replay नहीं किया जाता।
- **Accessible और multilingual interface देता है।** English और Canadian French first-class UI locales हैं और key parity enforce की जाती है; README coverage इससे अधिक भाषाओं में है। WCAG 2.2 AA, keyboard access, visible focus, reflow, reduced motion, forced colors/high contrast और long-string/localization checks release criteria हैं। Help Center route-specific guides, workflow FAQs और plain-language glossary देता है।
- **Research environment का backup रखता है।** Backup/restore workspaces, audit history, provider profiles, source assets, system/provenance state और Chroma collections/embeddings को शामिल करता है।

पूरी feature reference के लिए [User Guide](docs/USER_GUIDE.md) देखें।

## cELF traceability model

DerridAI का scholarly data model authoritative documentary/scholarly state और rebuildable computational projections के बीच cELF distinction का पालन करता है। Full traceability में conceptual path यह है:

```text
SourceDocument
  -> SourceSpan
  -> Record
  -> RecordRevision
  -> FieldAssertion
  -> Evidence Acquisition
  -> EvidenceRef
  -> EvidencePacket
  -> GenerationRun
  -> GeneratedClaim
  -> SupportBinding
```

इससे generated claim को उसके support, evidence, record revision, source span और source document तक पीछे audit किया जा सकता है। Embeddings, retrieval rank, reranker scores, caches, UI state और अन्य operation-specific values derived state रहते हैं; वे source record की intrinsic properties नहीं बनते।

Normative cELF 1.0 specification के लिए [SPECIFICATION.md](SPECIFICATION.md) देखें।

## Architecture

### Runtime services

- `web` — Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js और nginx। यह browser application है; `/api/` को proxy करता है और REST, GraphQL तथा realtime notifications उपयोग करता है। Storybook optional development profile है।
- `api` — Python 3.12, FastAPI, Strawberry GraphQL, ChromaDB client, PyMuPDF, sentence-transformers और spaCy। यह authentication, source/corpus operations, cELF reads, provenance, RAG, pipelines, jobs और system state के लिए authoritative application boundary है।
- `document-nlp` — English Document Intelligence के लिए optional isolated BookNLP worker। यह bounded reviewed text प्राप्त करता है और corpus authority नहीं रखता।
- `chroma` — optional HTTP Chroma server। Embedded `PersistentClient` default है; दोनों modes derived search/vector projections रखते हैं।
- `ollama` — optional local Ollama service। DerridAI host पर पहले से चल रहे Ollama या किसी configured OpenAI-compatible endpoint का उपयोग भी कर सकता है।

Default Compose stack `web` और `api` शुरू करता है; अन्य services optional profiles या external providers हैं।

### Authority और persistence

DerridAI सभी stores को समान authority नहीं देता:

- **Canonical scholarly state** — source assets/identity, records और revisions, field assertions, review decisions, exact evidence/support bindings और publication state।
- **Server-owned durable state** — authentication तथा system/provenance/job/pipeline state SQLite में `./data` के अंतर्गत।
- **Derived/rebuildable state** — Chroma indexes, embeddings, metadata-exemplar projections, retrieval scores, semantic-content projections, Document Intelligence output और caches।
- **Browser workspace state** — local preferences और unsaved workspace state, corpus authority से अलग।

### Transport split

- **REST**: सभी commands और mutations — uploads, review decisions, jobs, publication, administration, backup और restore।
- **GraphQL**: `POST /api/graphql` पर read-only cELF-aware typed query façade; कोई Mutation या Subscription root नहीं।
- **WebSocket**: `WS /api/ws/events` पर authenticated realtime notification plane; कभी source of truth नहीं।

विस्तृत module ownership, persistence boundaries और data flow के लिए [Architecture](docs/ARCHITECTURE.md), [GraphQL](docs/GRAPHQL.md) और [Realtime](docs/REALTIME.md) देखें।

## शुरू करना

### 1. Prerequisites

Git, Docker Engine/Desktop (`docker compose` सहित) और एक LLM endpoint स्थापित करें। Default configuration host पर Ollama अपेक्षित करता है।

Default models:

```text
gemma4:e2b
bge-m3:latest
```

### 2. Clone और configure करें

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Docker Desktop + WSL पर `.env` में `HOST_UID` और `HOST_GID` को क्रमशः `id -u` और `id -g` के output पर सेट करें।

`CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` या `CHROMA_PATH` जैसी test-storage variables को shell में globally export न करें; Compose exported variables को पहले interpolate करता है।

### 3. Models उपलब्ध कराएँ

यदि Ollama host पर चल रहा है:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Default values:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

या optional Compose Ollama service का उपयोग करें:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

फिर `OLLAMA_BASE_URL=http://ollama:11434` सेट करें।

### 4. DerridAI शुरू करें

```bash
docker compose config --quiet
docker compose up -d --build
```

Default endpoints:

- Application: <http://localhost:8181>
- API: <http://127.0.0.1:8000>
- OpenAPI docs: <http://127.0.0.1:8000/docs>

पहली बार launch पर browser में initial administrator account बनाएँ। कोई default credentials ship नहीं किए जाते।

### 5. Installation verify करें

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

Liveness response में `"ok": true`, application version और उपलब्ध होने पर baked Git commit होना चाहिए।

विस्तृत diagnostic:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Optional services

```bash
# Local Ollama
docker compose --profile ollama up -d ollama

# Chroma HTTP server (फिर CHROMA_MODE=http सेट करें)
docker compose --profile chroma up -d chroma

# English BookNLP Document Intelligence enhancement
docker compose --profile document-nlp up -d document-nlp

# Storybook development surface
docker compose --profile dev up storybook
```

NLP language packs enable या install करने से पहले [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) देखें।

### 7. Stop या rebuild

```bash
docker compose down

# repository update के बाद
docker compose down
docker compose up -d --build
```

यदि पुरानी release ने `data/` में root-owned files छोड़ी हों, तो supported Unix-like host पर `./scripts/fix-data-permissions.sh` चलाएँ।

## Developer setup

CI Python 3.12 और Node 22 उपयोग करता है।

Backend/test environment:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Frontend environment:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Fast local quality gates:

```bash
ruff check api/app tests scripts/check_frontend_api_contract.py scripts/check_frontend_graphql_contract.py
mypy
python -m compileall -q api/app
pytest -q -n auto --dist=worksteal \
  --ignore=tests/test_frontend_api_contract.py \
  --ignore=tests/test_frontend_graphql_contract.py
pytest -q -m contract tests/test_frontend_api_contract.py tests/test_frontend_graphql_contract.py

cd web
npm run format:repo:check
npm run lint
npm run typecheck
npm run typecheck:tests
npm run test:unit
npm run build:ci
```

`web/` से `npm run format:repo` चलाकर सभी Prettier-supported source, configuration और documentation files format करें। Generated legacy DOM snapshot HTML जानबूझकर excluded है।

Browser coverage, Storybook, CI parity और contribution rules के लिए [CONTRIBUTING.md](CONTRIBUTING.md) देखें।

## Repository map

- `api/app/` — FastAPI backend: sources/corpus, cELF read services, GraphQL, realtime, provenance, pipelines, RAG, providers, persistence और jobs।
- `web/src/` — Vue 3 application: views, components, Pinia stores, routing, API clients, realtime client, domain modules और remaining legacy compatibility layer।
- `booknlp-worker/` — optional isolated BookNLP worker।
- `tests/` — backend, regression, contract, release-consistency और architecture tests।
- `web/tests/frontend/` — Vitest tests।
- `web/tests/e2e/` — Playwright, Storybook, accessibility और characterization coverage।
- `docs/` — current architecture/domain contracts और historical release notes।
- `data/` — local runtime state; placeholders को छोड़कर git-ignored। इसका content commit न करें।

## Documentation

- [User Guide](docs/USER_GUIDE.md) — features और workflows
- [Architecture](docs/ARCHITECTURE.md) — runtime boundaries, authority, persistence और data flow
- [cELF 1.0 specification](SPECIFICATION.md) — normative information model और conformance requirements
- [Project context](docs/PROJECT_CONTEXT.md) — scholarly rationale और implemented/intended capabilities
- [GraphQL](docs/GRAPHQL.md) — read-only cELF query façade
- [Realtime](docs/REALTIME.md) — WebSocket protocol और resynchronization
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — derived linguistic analysis और language packs
- [Source ingestion](docs/INGESTION_VALIDATION.md) — safety, limits और extraction fidelity
- [Metadata schemas](docs/METADATA_SCHEMAS.md) — configurable field contracts
- [Metadata memory](docs/METADATA_MEMORY.md) — reviewed precedents और authority boundaries
- [FieldAssertion migration](docs/FIELD_ASSERTION_MIGRATION.md) — canonical assertion model
- [CONTRIBUTING.md](CONTRIBUTING.md) और [AGENTS.md](AGENTS.md) — development rules

Release history [CHANGELOG.md](CHANGELOG.md) और `docs/notes/<version>.md` में है। Version-specific release notes historical records हैं, current architecture का वर्णन नहीं।

## License

DerridAI [GNU Affero General Public License v3.0](LICENSE) के तहत licensed है।

Copyright © 2026 Aaron John Schlosser, PhD. Application में © 2026 The New England Transcendental Club of California भी प्रदर्शित होता है।
