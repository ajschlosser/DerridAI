<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI एक स्थानीय-प्रथम Docker अनुप्रयोग है, जिसका उपयोग दार्शनिक ग्रंथों के विद्वतापूर्ण कॉर्पस बनाने, उनका ऑडिट करने और उन पर क्वेरी चलाने के लिए किया जाता है। यह PDF, टेक्स्ट/RTF/DOCX, चित्र, ऑडियो, URL और Project Gutenberg स्रोतों को ऐसे विद्वतापूर्ण रिकॉर्ड में ग्रहण करता है जो provenance को सुरक्षित रखते हैं; मानव/LLM समीक्षा और साक्ष्य-बद्ध metadata enrichment का समर्थन करता है; व्युत्पन्न ChromaDB search projections बनाता है; और परिणाम पर साक्ष्य-आधारित retrieval-augmented generation (RAG) pipeline चलाता है।

वर्तमान संस्करण: **0.80.0 — Beverly** ([रिलीज़ नोट्स](docs/notes/0.80.0.md))।

## विशेषताएँ

- **Corpus Builder** — एक क्रमबद्ध Source → Structure/transcription → LLM & enrichment → Record construction → Review workflow, जिसके नियंत्रण चुने गए माध्यम के अनुसार बदलते हैं। Extraction सीमाबद्ध है और provenance सुरक्षित रखता है; reviewer के स्वामित्व वाले structure/text संशोधन और evidence audit योग्य बने रहते हैं।
- **Record review** — audit history, bulk/work-level metadata editing, diffs, source/evidence navigation और human/LLM field ownership वाले JSONL workspaces। Canonical `FieldAssertion` records value provenance, authority, evidence और stable field identity को सुरक्षित रखते हैं, जबकि schema-defined metadata review, Search, Record Inspector, touch-up और Research presentation के माध्यम से प्रवाहित होता है।
- **LLM review और tools** — named Ollama या OpenAI-compatible provider profiles के विरुद्ध foreground, background और background Auto-improve runs, जिनमें प्रत्येक का अपना concurrency limit और warmup state होता है।
- **Vector stores** — स्थानीय filesystem या चल रहे Chroma server पर persistent ChromaDB collections, English/French language mirrors, background upserts और JSONL round-tripping के साथ।
- **RAG Research** — hybrid retrieval, cross-encoder reranking, language routing, selected-evidence mode, streamed/cancellable generation, response/claim provenance memory, cached Response Library और LLM grading।
- **Roles** — Admin और Researcher accounts; researchers को summarized evidence text दिखाई देता है और वे corpora में बदलाव नहीं कर सकते।
- **Backup & restore** — एक ZIP जिसमें workspaces, audit history, provider profiles, corpus source assets और embeddings सहित प्रत्येक Chroma collection शामिल है।
- **Bilingual और accessible** — English और Canadian French first-class locales हैं और key parity लागू की जाती है। Keyboard access, visible focus, responsive/reflow व्यवहार, forced-colors support और WCAG 2.2 AA acceptance criteria हैं।

पूरी feature reference के लिए [User Guide](docs/USER_GUIDE.md) देखें।

## आर्किटेक्चर

<!-- prettier-ignore -->
| सेवा        | स्टैक                                                               | नोट्स                                                                                                                                          |
| ----------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, nginx द्वारा served | `/api/` को API तक proxy करता है; Storybook एक optional dev service के रूप में उपलब्ध है                                                      |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | Authoritative corpus/build files और SQLite auth/system/provenance state `./data` के अंतर्गत रहते हैं; Chroma derived search/result projections रखता है |
| LLM backend | Ollama (default) या कोई OpenAI-compatible endpoint                 | Host या किसी अन्य स्थान पर चलता है; default compose stack का हिस्सा नहीं है                                                                  |

Code ownership और persistence boundaries के लिए [Architecture](docs/ARCHITECTURE.md) देखें।

## आरंभ करना

ये चरण clean checkout के लिए समर्थित मार्ग हैं। इन्हें जानबूझकर स्पष्ट रखा गया है ताकि नया developer किसी मौजूदा DerridAI data directory या shell environment पर निर्भर हुए बिना इन्हें दोहरा सके।

### 1. पूर्वापेक्षाएँ

Git, `docker compose` command सहित Docker Engine/Desktop और एक LLM endpoint स्थापित करें। Default configuration host पर Ollama की अपेक्षा करता है।

Default Ollama models हैं:

```text
gemma4:e2b
bge-m3:latest
```

यदि आप कोई अलग Ollama model या OpenAI-compatible provider उपयोग करते हैं, तो DerridAI शुरू करने से पहले `.env` बदलें।

### 2. Clone और configure करें

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
```

Docker Desktop with WSL पर `.env` में `HOST_UID` और `HOST_GID` को `id -u` और `id -g` के output पर सेट करें। इससे bind-mounted Chroma/SQLite files आपके host user के स्वामित्व में रहती हैं।

`CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` या `CHROMA_PATH` जैसी DerridAI test-storage variables को अपने shell में globally export न करें। Compose exported variables को file से values container तक पहुँचने से पहले interpolate करता है।

### 3. Configured models उपलब्ध कराएँ

Host पर पहले से चल रहे Ollama के लिए:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Default `.env.example` यह उपयोग करता है:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

वैकल्पिक रूप से optional compose Ollama service उपयोग करें:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

फिर `.env` में `OLLAMA_BASE_URL=http://ollama:11434` सेट करें।

### 4. Compose configuration validate करें और DerridAI शुरू करें

```bash
docker compose config --quiet
docker compose up -d --build
```

Default bindings हैं: application <http://localhost:8181>, API <http://127.0.0.1:8000> और API documentation <http://127.0.0.1:8000/docs>।

पहली बार launch करने पर DerridAI initial administrator account बनाने को कहता है। कोई default credentials शामिल नहीं किए जाते।

### 5. Installation verify करें

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

Live endpoint को ऐसा JSON लौटाना चाहिए जिसमें `"ok": true`, application version और उपलब्ध होने पर baked git commit हो। `docker compose ps` में `web` और `api` services healthy दिखनी चाहिए।

अधिक व्यापक local diagnostic के लिए:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Stop या rebuild करें

Bind-mounted `./data` directory हटाए बिना application रोकें:

```bash
docker compose down
```

Changes pull करने के बाद rebuild करें:

```bash
docker compose down
docker compose up -d --build
```

यदि किसी पुराने release ने `data/` के अंतर्गत root-owned files छोड़ी हों, तो supported Unix-like hosts पर `./scripts/fix-data-permissions.sh` चलाएँ।

## Developer setup

CI Python 3.12 और Node 22 उपयोग करता है; failures reproduce करते समय स्थानीय रूप से यही versions उपयोग करें।

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

Repository root से तेज़ local quality gates चलाएँ:

```bash
ruff check api/app tests scripts/check_frontend_api_contract.py
mypy
pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py
pytest -q -m contract tests/test_frontend_api_contract.py

cd web
npm run format:repo:check
npm run lint
npm run typecheck
npm run typecheck:tests
npm run test:unit
npm run build
```

Repository में Prettier-supported source, configuration और documentation files को format करने के लिए `web/` से `npm run format:repo` उपयोग करें। Generated legacy DOM snapshot HTML जानबूझकर बाहर रखा गया है।

Browser coverage, Storybook, CI parity और contribution rules के लिए [CONTRIBUTING.md](CONTRIBUTING.md) देखें।

## Repository map

- `api/app/` — FastAPI application, corpus ingestion/review, provenance, persistence, RAG, providers और background jobs।
- `web/src/` — Vue application, reusable components, domain modules, stores और घटती हुई legacy runtime compatibility layer।
- `tests/` — backend/regression/contract tests।
- `web/tests/frontend/` — Vitest component/domain tests।
- `web/tests/e2e/` — Playwright application, Storybook, accessibility और legacy characterization coverage।
- `docs/` — current architecture/domain contracts और `docs/notes/` के अंतर्गत historical release notes।
- `data/` — local runtime state; placeholders को छोड़कर git-ignored। इसकी contents कभी commit न करें।

## Documentation

उन documents से शुरू करें जो current behavior का वर्णन करते हैं:

- [User Guide](docs/USER_GUIDE.md) — feature reference, operations, backup और limitations
- [Architecture](docs/ARCHITECTURE.md) — runtime boundaries, authority, persistence और data flow
- [Project context](docs/PROJECT_CONTEXT.md) — scholarly rationale और implemented-versus-intended capabilities
- [Contributing](CONTRIBUTING.md) — human developer setup, quality gates और change rules
- [AGENTS.md](AGENTS.md) — coding agents के लिए अतिरिक्त नियम
- Focused contracts: [source ingestion](docs/INGESTION_VALIDATION.md), [metadata schemas](docs/METADATA_SCHEMAS.md), [FieldAssertion migration](docs/FIELD_ASSERTION_MIGRATION.md), [metadata memory](docs/METADATA_MEMORY.md), [design tokens](docs/DESIGN_TOKENS.md) और [fr-CA localization](docs/LOCALIZATION_FR_CA.md)

Release history [CHANGELOG.md](CHANGELOG.md) और `docs/notes/<version>.md` में है। Version-specific release notes historical records हैं; वे current architecture या backlog documents नहीं हैं।

## लाइसेंस

Copyright © 2026 Aaron John Schlosser, PhD. DerridAI [GNU Affero General Public License, संस्करण 3](LICENSE) (`AGPL-3.0-only`) के अंतर्गत लाइसेंस प्राप्त है। Sign-in screen, account menu और Settings → About DerridAI पर `© 2026 The New England Transcendental Club of California` दिखाया जाता है।
