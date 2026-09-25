<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

A DerridAI egy helyi futtatásra összpontosító Docker-alkalmazás filozófiai szövegek tudományos korpuszainak létrehozására, auditálására és lekérdezésére. PDF-, szöveg/RTF/DOCX-, kép-, hang-, URL- és Project Gutenberg-forrásokat dolgoz fel eredetmegőrző tudományos rekordokká; támogatja az emberi és LLM-alapú ellenőrzést, valamint a bizonyítékhoz kötött metaadat-gazdagítást; származtatott ChromaDB keresési vetületeket hoz létre; és az eredményen bizonyítékalapú retrieval-augmented generation (RAG) folyamatot futtat.

Jelenlegi verzió: **0.80.0 — Beverly** ([kiadási megjegyzések](docs/notes/0.80.0.md)).

## Funkciók

- **Corpus Builder** — szekvenciális Forrás → Struktúra/átirat → LLM és gazdagítás → Rekordépítés → Ellenőrzés munkafolyamat, amelynek vezérlői a kiválasztott médiatípushoz igazodnak. A kinyerés korlátozott és megőrzi az eredetet; az ellenőr által kezelt szerkezeti/szöveges módosítások és bizonyítékok auditálhatók maradnak.
- **Rekordellenőrzés** — JSONL munkaterületek auditnaplóval, tömeges vagy műszintű metaadat-szerkesztéssel, diffekkel, forrás-/bizonyítéknavigációval, valamint emberi/LLM mezőtulajdonlással. A kanonikus `FieldAssertion` rekordok megőrzik az érték eredetét, a jogosultsági/tekintélyi állapotot, a bizonyítékot és a stabil mezőazonosságot, miközben a séma által definiált metaadatok végighaladnak az ellenőrzésen, a Search, Record Inspector, touch-up és Research felületeken.
- **LLM-ellenőrzés és eszközök** — előtérben, háttérben és háttérbeli Auto-improve módban futó műveletek névvel ellátott Ollama- vagy OpenAI-kompatibilis szolgáltatói profilokkal, profilonként saját párhuzamossági korláttal és bemelegítési állapottal.
- **Vektortárak** — tartós ChromaDB-gyűjtemények a helyi fájlrendszeren vagy futó Chroma-kiszolgálón, angol/francia nyelvi tükrökkel, háttérbeli upsertekkel és JSONL oda-vissza konverzióval.
- **RAG Research** — hibrid visszakeresés, cross-encoder újrarangsorolás, nyelvi útválasztás, kiválasztott bizonyíték mód, streamelt/megszakítható generálás, válasz- és állításproveniencia-memória, gyorsítótárazott Response Library és LLM-alapú értékelés.
- **Szerepkörök** — Admin és Researcher fiókok; a kutatók összefoglalt bizonyítékszöveget látnak, és nem módosíthatják a korpuszokat.
- **Biztonsági mentés és visszaállítás** — egyetlen ZIP-fájl, amely munkaterületeket, auditnaplót, szolgáltatói profilokat, korpuszforrás-eszközöket és minden Chroma-gyűjteményt tartalmaz az embeddingjeivel együtt.
- **Kétnyelvű és akadálymentes** — az angol és a kanadai francia első osztályú lokalizációk, kötelező kulcsparitással. A billentyűzetes használat, a látható fókusz, a reszponzív/reflow viselkedés, a forced-colors támogatás és a WCAG 2.2 AA megfelelés elfogadási kritérium.

A teljes funkcióreferenciáért lásd a [Felhasználói útmutatót](docs/USER_GUIDE.md).

## Architektúra

<!-- prettier-ignore -->
| Szolgáltatás | Technológia                                                        | Megjegyzések                                                                                                                                 |
| ------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`        | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, nginx szolgálja ki | A `/api/` kéréseket az API felé továbbítja; a Storybook opcionális fejlesztői szolgáltatásként érhető el                                  |
| `api`        | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers     | A hiteles korpusz/build fájlok és az SQLite auth/rendszer/proveniencia állapot a `./data` alatt található; a Chroma származtatott keresési/eredmény-vetületeket tárol |
| LLM backend  | Ollama (alapértelmezett) vagy bármely OpenAI-kompatibilis végpont  | A gazdagépen vagy máshol fut; nem része az alapértelmezett Compose stacknek                                                                |

A kódfelelősségi és perzisztenciahatárokról lásd az [Architektúra](docs/ARCHITECTURE.md) dokumentumot.

## Első lépések

Az alábbi lépések a támogatott, tiszta checkoutból induló útvonalat írják le. Szándékosan részletesek, hogy egy új fejlesztő meglévő DerridAI-adatkönyvtár vagy shell-környezet nélkül is meg tudja ismételni őket.

### 1. Előfeltételek

Telepítse a Gitet, a Docker Engine/Desktopot a `docker compose` paranccsal, valamint egy LLM-végpontot. Az alapértelmezett konfiguráció a gazdagépen futó Ollamát várja.

Az alapértelmezett Ollama-modellek:

```text
gemma4:e2b
bge-m3:latest
```

Ha más Ollama-modellt vagy OpenAI-kompatibilis szolgáltatót használ, a DerridAI indítása előtt módosítsa a `.env` fájlt.

### 2. Klónozás és konfigurálás

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell megfelelője:

```powershell
Copy-Item .env.example .env
```

Docker Desktop + WSL esetén állítsa a `HOST_UID` és `HOST_GID` értékét a `.env` fájlban az `id -u` és `id -g` kimenetére. Így a bind mounttal csatolt Chroma/SQLite fájlok a gazdagép felhasználójának tulajdonában maradnak.

Ne exportálja globálisan a shellben a DerridAI teszttárolási változóit, például a `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` vagy `CHROMA_PATH` változókat. A Compose az exportált változókat még azelőtt behelyettesíti, hogy a fájlból származó értékek a konténerbe kerülnének.

### 3. A konfigurált modellek elérhetővé tétele

Ha az Ollama már fut a gazdagépen:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Az alapértelmezett `.env.example` ezt használja:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Alternatívaként használható az opcionális Ollama Compose-szolgáltatás:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Ezután állítsa be az `OLLAMA_BASE_URL=http://ollama:11434` értéket a `.env` fájlban.

### 4. A Compose konfiguráció ellenőrzése és a DerridAI indítása

```bash
docker compose config --quiet
docker compose up -d --build
```

Az alapértelmezett címek: alkalmazás <http://localhost:8181>, API <http://127.0.0.1:8000>, API-dokumentáció <http://127.0.0.1:8000/docs>.

Az első indításkor a DerridAI kéri a kezdeti rendszergazdai fiók létrehozását. Nincsenek beépített alapértelmezett hitelesítő adatok.

### 5. A telepítés ellenőrzése

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

A live végpontnak olyan JSON-t kell visszaadnia, amely tartalmazza a `"ok": true` értéket, az alkalmazás verzióját és – ha elérhető – a buildbe égetett Git commitot. A `web` és `api` szolgáltatásoknak healthy állapotban kell megjelenniük a `docker compose ps` kimenetében.

Részletesebb helyi diagnosztikához:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Leállítás vagy újraépítés

Állítsa le az alkalmazást a bind mounttal csatolt `./data` könyvtár törlése nélkül:

```bash
docker compose down
```

Módosítások lehúzása után építse újra:

```bash
docker compose down
docker compose up -d --build
```

Ha egy korábbi kiadás root tulajdonú fájlokat hagyott a `data/` alatt, támogatott Unix-szerű rendszereken futtassa a `./scripts/fix-data-permissions.sh` parancsfájlt.

## Fejlesztői környezet

A CI Python 3.12-t és Node 22-t használ; hibák helyi reprodukálásakor ugyanezeket a verziókat használja.

Backend/teszt környezet:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Frontend környezet:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

A gyors helyi minőségi ellenőrzéseket a repository gyökeréből futtassa:

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

A `web/` könyvtárból futtatott `npm run format:repo` paranccsal formázható a repository minden, Prettier által támogatott forrás-, konfigurációs és dokumentációs fájlja. A generált, örökölt DOM snapshot HTML szándékosan ki van zárva.

A böngészős lefedettségről, Storybookról, CI-paritásról és hozzájárulási szabályokról lásd a [CONTRIBUTING.md](CONTRIBUTING.md) fájlt.

## Repository-térkép

- `api/app/` — FastAPI alkalmazás, korpuszbetöltés/-ellenőrzés, proveniencia, perzisztencia, RAG, szolgáltatók és háttérfeladatok.
- `web/src/` — Vue alkalmazás, újrafelhasználható komponensek, doménmodulok, store-ok és a fokozatosan csökkenő legacy runtime kompatibilitási réteg.
- `tests/` — backend-, regressziós és szerződéstesztek.
- `web/tests/frontend/` — Vitest komponens-/doméntesztek.
- `web/tests/e2e/` — Playwright lefedettség az alkalmazáshoz, Storybookhoz, akadálymentességhez és legacy karakterizációhoz.
- `docs/` — aktuális architektúra-/doménszerződések, valamint történeti kiadási megjegyzések a `docs/notes/` alatt.
- `data/` — helyi futásidejű állapot; a helyőrzők kivételével Git által figyelmen kívül hagyva. A tartalmát soha ne commitolja.

## Dokumentáció

Kezdje az aktuális működést leíró dokumentumokkal:

- [Felhasználói útmutató](docs/USER_GUIDE.md) — funkcióreferencia, üzemeltetés, biztonsági mentés és korlátozások
- [Architektúra](docs/ARCHITECTURE.md) — futásidejű határok, autoritás, perzisztencia és adatáramlás
- [Projektkontextus](docs/PROJECT_CONTEXT.md) — tudományos indoklás, valamint a megvalósított és tervezett képességek
- [Közreműködés](CONTRIBUTING.md) — emberi fejlesztői környezet, minőségi ellenőrzések és módosítási szabályok
- [AGENTS.md](AGENTS.md) — további szabályok kódoló ágensek számára
- Célzott szerződések: [forrásbetöltés](docs/INGESTION_VALIDATION.md), [metaadatsémák](docs/METADATA_SCHEMAS.md), [FieldAssertion-migráció](docs/FIELD_ASSERTION_MIGRATION.md), [metaadatmemória](docs/METADATA_MEMORY.md), [design tokenek](docs/DESIGN_TOKENS.md) és [fr-CA lokalizáció](docs/LOCALIZATION_FR_CA.md)

A kiadási előzmények a [CHANGELOG.md](CHANGELOG.md) fájlban és a `docs/notes/<version>.md` alatt találhatók. A verzióspecifikus kiadási megjegyzések történeti feljegyzések; nem az aktuális architektúra vagy backlog dokumentumai.

## Licenc

Jelenleg nincs licencfájl a repositoryban. A forrásfájlok a `Copyright 2026 Aaron John Schlosser, PhD.` jelölést viselik. A bejelentkezési képernyő, a fiókmenü és a Beállítások → A DerridAI névjegye felület a `© 2026 The New England Transcendental Club of California` szöveget jeleníti meg.
