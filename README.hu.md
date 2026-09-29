<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

![DerridAI logó](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

A DerridAI helyi futtatásra épülő, provenienciát megőrző kutatási környezet tudományos korpuszok létrehozásához, ellenőrzéséhez, kereséséhez és lekérdezéséhez. Egyetlen Docker-alkalmazásban egyesíti a forrásbevitelt, az ember által felügyelt korpuszépítést, a bizonyítékhoz kötött metaadat-gazdagítást, a származtatott vektoros/keresési indexeket és a bizonyítékalapú retrieval-augmented generation (RAG) folyamatot.

A DerridAI egyben a **cELF 1.0 — Capta-Enriched Lexical Format** eredeti referencia-implementációja, amely provenienciát megőrző információs architektúrát határoz meg MI-támogatott dokumentumkutatáshoz. A rendszer külön és ellenőrizhetően kezeli a forrásazonosságot, a rekordazonosságot és revíziót, a metaadat-állításokat, a bizonyítékot, a generált állításokat és a támogatási kapcsolatokat, ahelyett hogy mindezt egy átláthatatlan vektoradatbázisba lapítaná.

Aktuális verzió: **0.80.7 — Exeter** ([kiadási jegyzetek](docs/notes/0.80.7.md)). Ez a README az aktuális `master` architektúrát írja le, beleértve az Exeter utáni, már beolvasztott változásokat is.

## Mit tud a DerridAI?

- **Heterogén források beszerzése és betöltése.** PDF, egyszerű szöveg, RTF, DOCX, kép és hang feltöltése; URL-ek és Project Gutenberg-anyagok importálása; illetve Corpus Capture használata művek felfedezésére és beszerzésére Wikidata-, Project Gutenberg- és Wikisource-adaptereken keresztül. A betöltés médiumspecifikus biztonsági és erőforráskorlátokat alkalmaz, és megőrzi az extractor/eszköz/verzió provenienciáját.
- **Médiumhoz igazodó korpuszépítés.** A Corpus Builder elkülöníti a forrás regisztrációját, kinyerést/átírást, source-unit leképezést, struktúrát/szegmentálást, gazdagítást, rekordépítést, felülvizsgálatot és publikálást. A vezérlők és bizonyítékkoordináták a forrás médiumához igazodnak, nem erőltetnek PDF-/oldalfogalmakat mindenre.
- **cELF-proveniencia és mezőautorítás megőrzése.** A kanonikus `FieldAssertion` rekordok külön kezelik a származtatást, értékelést, autoritást, értékállapotot, konfidenciát, bizonyítékot, szereplőt/modellt, stabil mezőazonosságot és rekordrevíziót. Az emberi megerősítés nem törli a modell vagy determinisztikus eljárás eredeti provenienciáját.
- **Rekordok felülvizsgálata kontextusba helyezett bizonyítékokkal.** A reviewer szerkesztheti a szöveget és metaadatokat, megvizsgálhatja a `SourceSpan`-okat és más rekordok bizonyítékait, összehasonlíthat revíziókat, bejárhat szemantikus térképeket és kapcsolatokat, elfogadhat/elutasíthat javaslatokat, és auditálható döntésekkel publikálhat. Az optimista mentés reszponzívvá teszi a felületet, miközben azonos rekord ütköző írásai sorosítva futnak.
- **Konfigurálható metaadatsémák és ellenőrzött precedensek.** A sémák stabil mezőket, típusokat, kontrollált értékeket, bizonyíték-/review-szabályokat, POS/NER-tippek, mezőhatókört, modellutasításokat és retrieval policy-t definiálnak. Az ellenőrzött példák korlátozott, bizonyítékhoz kötött precedensekké válhatnak a későbbi gazdagításhoz anélkül, hogy felülírnák a kanonikus reviewer-döntéseket.
- **Opcionális Document Intelligence.** Egy szolgáltatófüggetlen, származtatott elemzési réteg entitásokat, koreferenciát, idézetbeszélőket és szemantikus tartalmi kapcsolatokat adhat. A spaCy nyelvi csomagok adják a többnyelvű alapot; az izolált BookNLP worker opcionális angol kiegészítés. Ezek az annotációk újraépíthető elemzések maradnak, nem forrásbizonyítékok és nem korpuszautorítás.
- **Keresés származtatott projekciókban a korpusz összekeverése nélkül.** A ChromaDB újraépíthető szemantikus/keresési projekciókat és cache-eket tárol embedded vagy HTTP-szerver módban. Elérhető dense, lexical és MMR retrieval, RRF, szűrés, nyelvi routing és korlátozott cross-encoder reranking.
- **Bizonyítékalapú Research/RAG.** A Research támogatja a hibrid retrievalt, rerankinget, kiválasztott bizonyíték módot, evidence budgeteket, streamelt/megszakítható generálást, determinisztikus hivatkozás-renderelést, claim/support perzisztenciát, claim-validálást, response/claim memóriát és LLM-gradinget. A hiányos provenienciájú rekordok kizáródnak a bizonyítékok közül ahelyett, hogy csendben érvényes supportként jelennének meg.
- **MI-pipeline-ok vizsgálata és konfigurálása.** A Pipeline Studio verziózott pipeline-definíciókat, hozzárendeléseket, futási trace-eket, fázisonkénti latency/error/fallback metrikákat, point-of-use trace-eket, nem perzisztens Research A/B összehasonlítást és fix esetekből álló Research benchmark futásokat mutat. A retrieval-, memória-, metaadat-precedens- és reviewer-evidence szakaszok explicit módon konfigurálhatók, miközben a proveniencia-/autoritás-gate-ek strukturális korlátok maradnak.
- **API-transzportok elkülönítése felelősség szerint.** A REST kezeli a parancsokat és mutációkat; egy csak olvasható, cELF-tudatos GraphQL façade tipizált olvasásokat állít össze; egy hitelesített WebSocket-sík valós idejű műveleti értesítéseket küld. A realtime üzenetek soha nem kanonikus állapotok, a kliens REST/GraphQL alapján újraszinkronizálhat.
- **Kontrollált többfelhasználós kutatás.** A beépített Administrator és Researcher szerepköröket, valamint a kutatók számára biztonságos egyedi szerepköröket a UI és az API is kikényszeríti. A kutató számára látható forrásszöveg az API-határon összegzésre kerül, a jobok tulajdonoshoz kötöttek, az adminisztrátori korpusz-/rendszermódosítások pedig nem érhetők el.
- **Hosszú műveletek megfigyelhetősége.** Korpuszépítés, LLM-review, RAG, grading, importok, modell-/nyelvi csomag műveletek és vektor-upsertek megszakítható műveletként jelennek meg tartós snapshot/history és realtime progress mellett. Újraindításkor a megszakadt process-local munka hibásként jelölődik meg, nem fut le csendben újra.
- **Akadálymentes, többnyelvű felület.** Az angol és kanadai francia elsődleges UI-lokálék, kikényszerített kulcsparitással; a README-k ennél több nyelvet fednek le. WCAG 2.2 AA, billentyűzetes kezelés, látható fókusz, reflow, reduced motion, forced colors/high contrast és hosszú szöveges/lokalizációs tesztek kiadási kritériumok. A Help Center oldalspecifikus útmutatókat, workflow-FAQ-kat és közérthető fogalomtárat biztosít.
- **A kutatási környezet biztonsági mentése.** A backup/restore lefedi a workspace-eket, audit history-t, providerprofilokat, forrásasseteket, rendszer-/provenienciaállapotot és a Chroma-gyűjteményeket az embeddingekkel együtt.

A teljes funkcióleírásért lásd a [Felhasználói útmutatót](docs/USER_GUIDE.md).

## cELF nyomonkövetési modell

A DerridAI tudományos adatmodellje a cELF megkülönböztetését követi az autoritatív dokumentáris/tudományos állapot és az újraépíthető számítási projekciók között. Teljes nyomonkövetés esetén a fogalmi lánc:

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

Így egy generált állítás visszafelé auditálható a támogatásán, bizonyítékán, rekordrevízióján és source span-jén keresztül egészen a source documentig. Az embedding, retrieval rank, reranker score, cache, UI-állapot és más műveletspecifikus érték származtatott állapot marad; nem válik a forrásrekord belső tulajdonságává.

A normatív cELF 1.0 specifikációt és a DerridAI nem normatív white paperét lásd a [SPECIFICATION.md](SPECIFICATION.md) fájlban.

## Architektúra

### Futásidejű szolgáltatások


- `web` — Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js és nginx. Böngészős alkalmazás; proxyzza az `/api/` útvonalat, és REST-et, GraphQL-t valamint realtime értesítéseket használ. A Storybook opcionális fejlesztői profil.
- `api` — Python 3.12, FastAPI, Strawberry GraphQL, ChromaDB kliens, PyMuPDF, sentence-transformers és spaCy. Autoritatív alkalmazási határ a hitelesítés, forrás/korpusz műveletek, cELF-olvasások, proveniencia, RAG, pipeline-ok, jobok és rendszerállapot számára.
- `document-nlp` — opcionális izolált BookNLP worker angol Document Intelligence céljára. Korlátozott, ellenőrzött szöveget kap, és nincs korpuszautorítása.
- `chroma` — opcionális HTTP Chroma szerver. Az embedded `PersistentClient` az alapértelmezés; mindkét mód származtatott keresési/vektorprojekciókat tárol.
- `ollama` — opcionális helyi Ollama szolgáltatás. A DerridAI használhat a hoston már futó Ollamát vagy bármely konfigurált OpenAI-kompatibilis endpointot.

Az alapértelmezett Compose stack a `web` és `api` szolgáltatást indítja; a többi opcionális profil vagy külső provider.

### Autoritás és perzisztencia

A DerridAI szándékosan nem kezel minden tárolót egyformán autoritatívként:

- **Kanonikus tudományos állapot** — forrásassetek/-azonosság, rekordok és revíziók, field assertionök, review-döntések, pontos evidence/support bindok és publikációs állapot.
- **Tartós szerverállapot** — hitelesítés és rendszer-/proveniencia-/job-/pipeline-állapot SQLite-ban a `./data` alatt.
- **Származtatott/újraépíthető állapot** — Chroma-indexek, embeddingek, metaadat-exemplar projekciók, retrieval score-ok, szemantikus tartalomprojekciók, Document Intelligence output és cache-ek.
- **Böngésző-workspace állapot** — helyi beállítások és nem mentett munka, külön a korpusz autoritásától.

### Transzportok szétválasztása

- **REST**: minden parancs és mutáció, többek között feltöltés, review-döntés, job, publikálás, adminisztráció, backup és restore.
- **GraphQL**: csak olvasható cELF-tudatos tipizált query façade a `POST /api/graphql` végponton; nincs Mutation vagy Subscription root.
- **WebSocket**: hitelesített realtime értesítési sík a `WS /api/ws/events` címen; soha nem source of truth.

Részletes modulfelelősség, perzisztenciahatárok és adatfolyam: [Architecture](docs/ARCHITECTURE.md), [GraphQL](docs/GRAPHQL.md), [Realtime](docs/REALTIME.md).

## Első lépések

### 1. Előfeltételek

Telepítse a Gitet, Docker Engine/Desktopot `docker compose` támogatással és egy LLM-endpointot. Az alapértelmezett konfiguráció a hoston futó Ollamát várja.

Alapértelmezett modellek:

```text
gemma4:e2b
bge-m3:latest
```

### 2. Klónozás és konfigurálás

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Docker Desktop + WSL esetén állítsa be a `HOST_UID` és `HOST_GID` értékét a `id -u`, illetve `id -g` kimenetére.

Ne exportálja globálisan a teszt-storage változókat, például `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` vagy `CHROMA_PATH`; a Compose előbb a shellből exportált változókat interpolálja.

### 3. Modellek előkészítése

Ha az Ollama már fut a hoston:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Alapértelmezett értékek:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Vagy használja az opcionális Compose Ollama szolgáltatást:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Ezután: `OLLAMA_BASE_URL=http://ollama:11434`.

### 4. DerridAI indítása

```bash
docker compose config --quiet
docker compose up -d --build
```

Alapértelmezett végpontok:

- Alkalmazás: <http://localhost:8181>
- API: <http://127.0.0.1:8000>
- OpenAPI dokumentáció: <http://127.0.0.1:8000/docs>

Első indításkor a böngészőben hozza létre a kezdeti adminisztrátori fiókot. Nincsenek csomagolt alapértelmezett hitelesítő adatok.

### 5. Telepítés ellenőrzése

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

A liveness válasznak tartalmaznia kell az `"ok": true` értéket, az alkalmazás verzióját és – ha elérhető – a buildbe ágyazott Git commitot.

Bővebb diagnosztika:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Opcionális szolgáltatások

```bash
# Helyi Ollama
docker compose --profile ollama up -d ollama

# Chroma HTTP szerver (utána CHROMA_MODE=http)
docker compose --profile chroma up -d chroma

# Angol BookNLP Document Intelligence kiegészítés
docker compose --profile document-nlp up -d document-nlp

# Storybook fejlesztői felület
docker compose --profile dev up storybook
```

NLP nyelvi csomagok engedélyezése vagy telepítése előtt olvassa el a [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) dokumentumot.

### 7. Leállítás vagy újraépítés

```bash
docker compose down

# frissítés után
docker compose down
docker compose up -d --build
```

Ha régi kiadás root tulajdonú fájlokat hagyott a `data/` alatt, futtassa a `./scripts/fix-data-permissions.sh` szkriptet támogatott Unix-szerű rendszeren.

## Fejlesztői környezet

A CI Python 3.12-t és Node 22-t használ.

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

Gyors helyi minőségkapuk:

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

A `web/` könyvtárból futtatott `npm run format:repo` minden Prettier által támogatott forrás-, konfigurációs és dokumentációs fájlt formáz. A generált legacy DOM snapshot HTML szándékosan kizárt.

Böngészős lefedettséghez, Storybookhoz, CI-paritáshoz és hozzájárulási szabályokhoz lásd a [CONTRIBUTING.md](CONTRIBUTING.md) fájlt.

## Repository-térkép

- `api/app/` — FastAPI backend: forrás/korpusz, cELF read service-ek, GraphQL, realtime, proveniencia, pipeline-ok, RAG, providerek, perzisztencia és jobok.
- `web/src/` — Vue 3 alkalmazás: view-k, komponensek, Pinia store-ok, routing, API-kliensek, realtime kliens, domainmodulok és a megmaradt legacy kompatibilitási réteg.
- `booknlp-worker/` — opcionális izolált BookNLP worker.
- `tests/` — backend, regresszió, contract, release-consistency és architektúratesztek.
- `web/tests/frontend/` — Vitest tesztek.
- `web/tests/e2e/` — Playwright, Storybook, accessibility és characterization lefedettség.
- `docs/` — aktuális architektúra-/domain-szerződések és történeti kiadási jegyzetek.
- `data/` — helyi futásidejű állapot; a placeholder fájlok kivételével Git által ignorált. Tartalmát ne commitolja.

## Dokumentáció

- [Felhasználói útmutató](docs/USER_GUIDE.md) — funkciók és workflow-k
- [Architektúra](docs/ARCHITECTURE.md) — futásidejű határok, autoritás, perzisztencia és adatfolyam
- [cELF 1.0 specifikáció](SPECIFICATION.md) — normatív információs modell és referencia-implementációs white paper
- [Projektkontekstus](docs/PROJECT_CONTEXT.md) — tudományos indoklás és implementált/tervezett képességek
- [GraphQL](docs/GRAPHQL.md) — csak olvasható cELF query façade
- [Realtime](docs/REALTIME.md) — WebSocket protokoll és reszinkronizáció
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — származtatott nyelvészeti elemzés és nyelvi csomagok
- [Forrásingesztió](docs/INGESTION_VALIDATION.md) — biztonság, korlátok és kivonatolási hűség
- [Metaadatsémák](docs/METADATA_SCHEMAS.md) — konfigurálható mezőszerződések
- [Metaadatmemória](docs/METADATA_MEMORY.md) — ellenőrzött precedensek és autoritáshatárok
- [FieldAssertion migráció](docs/FIELD_ASSERTION_MIGRATION.md) — kanonikus assertion-modell
- [CONTRIBUTING.md](CONTRIBUTING.md) és [AGENTS.md](AGENTS.md) — fejlesztési szabályok

A kiadási előzmények a [CHANGELOG.md](CHANGELOG.md) és `docs/notes/<version>.md` alatt találhatók. A verzióspecifikus jegyzetek történeti dokumentumok, nem az aktuális architektúra leírásai.

## Licenc

A DerridAI a [GNU Affero General Public License v3.0](LICENSE) alatt érhető el.

Copyright © 2026 Aaron John Schlosser, PhD. Az alkalmazás ezt is megjeleníti: © 2026 The New England Transcendental Club of California.
