<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI è un'applicazione Docker orientata all'esecuzione locale per creare, verificare e interrogare corpora accademici di testi filosofici. Acquisisce fonti PDF, testo/RTF/DOCX, immagini, audio, URL e Project Gutenberg trasformandole in record accademici che preservano la provenienza; supporta la revisione umana o tramite LLM e l'arricchimento dei metadati vincolato alle evidenze; costruisce proiezioni di ricerca derivate in ChromaDB; ed esegue sul risultato una pipeline di retrieval-augmented generation (RAG) basata sulle evidenze.

Versione corrente: **0.80.0 — Beverly** ([note di rilascio](docs/notes/0.80.0.md)).

## Funzionalità

- **Corpus Builder** — un flusso sequenziale Sorgente → Struttura/trascrizione → LLM e arricchimento → Costruzione dei record → Revisione, con controlli che si adattano al supporto selezionato. L'estrazione è limitata e preserva la provenienza; le revisioni di struttura/testo e le evidenze sotto responsabilità del revisore restano verificabili.
- **Revisione dei record** — spazi di lavoro JSONL con cronologia di audit, modifica dei metadati in blocco o a livello di opera, diff, navigazione verso sorgente/evidenze e titolarità dei campi umana o LLM. I record canonici `FieldAssertion` preservano provenienza del valore, autorità, evidenze e identità stabile del campo, mentre i metadati definiti dallo schema attraversano revisione, Search, Record Inspector, ritocco e presentazione Research.
- **Revisione e strumenti LLM** — esecuzioni in primo piano, in background e Auto-improve in background contro profili nominati di provider Ollama o compatibili con OpenAI, ciascuno con il proprio limite di concorrenza e stato di warmup.
- **Archivi vettoriali** — collezioni ChromaDB persistenti sul filesystem locale o su un server Chroma in esecuzione, con mirror linguistici inglese/francese, upsert in background e round-trip JSONL.
- **RAG Research** — recupero ibrido, reranking con cross-encoder, instradamento linguistico, modalità evidenze selezionate, generazione in streaming e annullabile, memoria della provenienza di risposte e affermazioni, una Response Library in cache e valutazione tramite LLM.
- **Ruoli** — account Admin e Researcher; i ricercatori vedono testo delle evidenze riassunto e non possono modificare i corpora.
- **Backup e ripristino** — un unico ZIP contenente spazi di lavoro, cronologia di audit, profili dei provider, asset sorgente del corpus e ogni collezione Chroma con i relativi embedding.
- **Bilingue e accessibile** — inglese e francese canadese sono locale di prima classe con parità delle chiavi obbligatoria. Accesso da tastiera, focus visibile, comportamento responsive/reflow, supporto ai colori forzati e WCAG 2.2 AA sono criteri di accettazione.

Consulta la [Guida utente](docs/USER_GUIDE.md) per il riferimento completo delle funzionalità.

## Architettura

<!-- prettier-ignore -->
| Servizio    | Stack                                                               | Note                                                                                                                                           |
| ----------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, servito da nginx | Inoltra `/api/` all'API; Storybook è disponibile come servizio di sviluppo opzionale                                                         |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | I file autorevoli del corpus/build e lo stato SQLite di autenticazione/sistema/provenienza risiedono sotto `./data`; Chroma contiene proiezioni derivate di ricerca/risultati |
| Backend LLM | Ollama (predefinito) o qualsiasi endpoint compatibile con OpenAI    | Viene eseguito sull'host o altrove; non fa parte dello stack Compose predefinito                                                              |

Per i confini di responsabilità del codice e della persistenza, consulta [Architettura](docs/ARCHITECTURE.md).

## Per iniziare

Questi passaggi costituiscono il percorso supportato a partire da un checkout pulito. Sono volutamente espliciti, così un nuovo sviluppatore può ripeterli senza dipendere da una directory dati DerridAI esistente o da un ambiente shell preconfigurato.

### 1. Prerequisiti

Installa Git, Docker Engine/Desktop con il comando `docker compose` e un endpoint LLM. La configurazione predefinita prevede Ollama sull'host.

I modelli Ollama predefiniti sono:

```text
gemma4:e2b
bge-m3:latest
```

Se usi un modello Ollama diverso o un provider compatibile con OpenAI, modifica `.env` prima di avviare DerridAI.

### 2. Clonare e configurare

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

Equivalente PowerShell:

```powershell
Copy-Item .env.example .env
```

Su Docker Desktop con WSL, imposta `HOST_UID` e `HOST_GID` in `.env` usando l'output di `id -u` e `id -g`. In questo modo i file Chroma/SQLite montati tramite bind restano di proprietà dell'utente host.

Non esportare globalmente nella shell variabili di storage di test DerridAI come `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` o `CHROMA_PATH`. Compose interpola le variabili esportate prima che i valori del file vengano passati al container.

### 3. Rendere disponibili i modelli configurati

Per Ollama già in esecuzione sull'host:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Il file `.env.example` predefinito usa:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

In alternativa, usa il servizio Ollama opzionale di Compose:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Poi imposta `OLLAMA_BASE_URL=http://ollama:11434` in `.env`.

### 4. Validare la configurazione Compose e avviare DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

I binding predefiniti sono applicazione <http://localhost:8181>, API <http://127.0.0.1:8000> e documentazione API <http://127.0.0.1:8000/docs>.

Al primo avvio DerridAI chiede di creare l'account amministratore iniziale. Non vengono fornite credenziali predefinite.

### 5. Verificare l'installazione

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

L'endpoint live dovrebbe restituire JSON contenente `"ok": true`, la versione dell'applicazione e il commit Git incorporato quando disponibile. I servizi `web` e `api` dovrebbero risultare healthy in `docker compose ps`.

Per una diagnostica locale più ampia:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Arrestare o ricostruire

Arresta l'applicazione senza eliminare la directory `./data` montata tramite bind:

```bash
docker compose down
```

Ricostruisci dopo aver recuperato modifiche:

```bash
docker compose down
docker compose up -d --build
```

Se una versione precedente ha lasciato file di proprietà di root sotto `data/`, esegui `./scripts/fix-data-permissions.sh` sugli host Unix-like supportati.

## Configurazione per sviluppatori

La CI usa Python 3.12 e Node 22; usa queste versioni localmente quando riproduci errori.

Ambiente backend/test:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Ambiente frontend:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Esegui i controlli locali rapidi di qualità dalla radice del repository:

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

Usa `npm run format:repo` da `web/` per formattare tutti i file sorgente, di configurazione e di documentazione supportati da Prettier nel repository. L'HTML generato degli snapshot DOM legacy è escluso intenzionalmente.

Per copertura browser, Storybook, parità con CI e regole di contribuzione, consulta [CONTRIBUTING.md](CONTRIBUTING.md).

## Mappa del repository

- `api/app/` — applicazione FastAPI, ingestione/revisione del corpus, provenienza, persistenza, RAG, provider e job in background.
- `web/src/` — applicazione Vue, componenti riutilizzabili, moduli di dominio, store e il livello di compatibilità runtime legacy in riduzione.
- `tests/` — test backend, di regressione e di contratto.
- `web/tests/frontend/` — test Vitest di componenti e dominio.
- `web/tests/e2e/` — copertura Playwright dell'applicazione, Storybook, accessibilità e caratterizzazione legacy.
- `docs/` — contratti correnti di architettura/dominio più note di rilascio storiche sotto `docs/notes/`.
- `data/` — stato runtime locale; ignorato da Git salvo i placeholder. Non eseguire mai il commit del suo contenuto.

## Documentazione

Inizia dai documenti che descrivono il comportamento corrente:

- [Guida utente](docs/USER_GUIDE.md) — riferimento delle funzionalità, operazioni, backup e limitazioni
- [Architettura](docs/ARCHITECTURE.md) — confini runtime, autorità, persistenza e flusso dei dati
- [Contesto del progetto](docs/PROJECT_CONTEXT.md) — motivazione accademica e capacità implementate rispetto a quelle previste
- [Contribuire](CONTRIBUTING.md) — configurazione per sviluppatori umani, controlli di qualità e regole di modifica
- [AGENTS.md](AGENTS.md) — regole aggiuntive per gli agenti di programmazione
- Contratti specifici: [ingestione delle sorgenti](docs/INGESTION_VALIDATION.md), [schemi di metadati](docs/METADATA_SCHEMAS.md), [migrazione FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md), [memoria dei metadati](docs/METADATA_MEMORY.md), [design token](docs/DESIGN_TOKENS.md) e [localizzazione fr-CA](docs/LOCALIZATION_FR_CA.md)

La cronologia delle versioni è in [CHANGELOG.md](CHANGELOG.md) e `docs/notes/<version>.md`. Le note specifiche di una versione sono registrazioni storiche; non sono documenti dell'architettura corrente né del backlog.

## Licenza

Copyright © 2026 Aaron John Schlosser, PhD. DerridAI è distribuito secondo i termini della [GNU Affero General Public License, versione 3](LICENSE) (`AGPL-3.0-only`). La schermata di accesso, il menu account e Impostazioni → Informazioni su DerridAI mostrano `© 2026 The New England Transcendental Club of California`.
