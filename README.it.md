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

![Logo DerridAI](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [العربية](README.ar.md) · [简体中文](README.zh-CN.md)

DerridAI è un ambiente di ricerca local-first che preserva la provenienza per costruire, revisionare, cercare e interrogare corpora accademici. Riunisce acquisizione delle fonti, costruzione del corpus con supervisione umana, arricchimento dei metadati legato alle evidenze, indici vettoriali/di ricerca derivati e retrieval-augmented generation (RAG) fondata sulle evidenze in un'unica applicazione Docker.

DerridAI è inoltre l'implementazione di riferimento originaria di **cELF 1.0 — Capta-Enriched Lexical Format**, un'architettura informativa che preserva la provenienza per la ricerca documentaria assistita dall'IA. L'implementazione mantiene separatamente ispezionabili identità della fonte, identità e revisione del record, asserzioni di metadati, evidenze, claim generati e legami di supporto, invece di appiattirli in un unico archivio vettoriale opaco.

Versione corrente: **0.81.0 — Fall River** ([note di rilascio](docs/notes/0.81.0.md)). La versione dell’applicazione non è stata incrementata dopo Fall River; questo README descrive il ramo `master` corrente, incluso il lavoro successivo a 0.81.0 che non fa parte della release con tag.

## Stato corrente di `master`

Il ramo corrente è avanzato in modo sostanziale rispetto al tag 0.81.0 pur mantenendo la versione applicativa 0.81.0. Il riepilogo seguente descrive il prodotto attuale, non nuove note di rilascio.

- **Corpus Builder è ora un flusso progressivo Configurazione → Build → Revisione → Pubblicazione.** Supporta enrichment concorrente e limitato, scelte esplicite di topologia del corpus e dimensione dei Record, revisione riprendibile e consapevole delle revisioni, code persistenti locali al Record, sessioni mirate per risolvere i blocchi di pubblicazione, gruppi di metadati ripetibili, assegnazioni dei parlanti audio e revisione sicura del testo durante una preparazione verificata.
- **L’elaborazione di metadati ed evidenze richiede meno lavoro del modello e conserva semantiche più forti.** Routing deterministico e candidate-first, identità semantica ed equivalenza dei valori, evidence cascade v2 validata dal supporto, riparazione/classificazione dell’output strutturato e riconciliazione incrementale della Metadata Memory riducono la latenza senza trasformare la rilevanza del retrieval o un output malformato in evidenza.
- **Pipeline Studio modella esplicitamente il calcolo eseguibile.** Scopi gestiti dal server, famiglie di strategie, effetti accademici, porte tipizzate, wiring risolto, trace degli stage, metriche di scala/complessità, parametri di retrieval regolabili e confronti non persistenti coprono più percorsi di Search, Research, evidenza di revisione, recovery, segmentazione ed enrichment.
- **Works può pubblicare siti di ricerca portabili.** Gli export statici combinano il DerridAI SDK con un runtime Vue dedicato per navigazione, annotazioni, indicizzazione semantica nel browser, provider configurati dal lettore e Research con citazioni collegate alle evidenze, senza trasformare l’export nello stato canonico del corpus.
- **Invalidazione realtime e caricamento progressivo sostituiscono più polling e refresh a pagina vuota.** Works, Record, Search, Research, Response Library, Languages, Relationships, Accounts/Roles, Metadata Memory e altre superfici mantengono contenuti utili, isolano gli errori, offrono retry locali e scartano risposte obsolete.
- **Il frontend continua a ritirare il runtime legacy.** Navigazione controllata dal router, dialoghi e notifiche Vue, moduli condivisi di dominio/stato, slice Pinia e helper estratti riducono l’accoppiamento mentre il codice di compatibilità restante rimane isolato.
- **cELF e l’infrastruttura di sviluppo sono stati rafforzati.** La specifica è neutrale rispetto al prodotto e orientata a profili/provenienza, con semantica generalizzata dei locator `EvidenceRef`; mappe di architettura documentano i confini critici; selezione CI/pre-push, igiene del repository e applicazione del copyright sono state consolidate.

## Cosa fa DerridAI

- **Acquisisce e importa fonti eterogenee.** Carica PDF, testo semplice, RTF, DOCX, immagini e audio; importa URL e materiale Project Gutenberg; oppure usa Corpus Capture per scoprire e acquisire opere tramite adattatori come Wikidata, Project Gutenberg e Wikisource. L'ingestione applica limiti di sicurezza/risorse specifici per il mezzo e conserva la provenienza di estrattore, strumento e versione.
- **Costruisce corpora con workflow sensibili al mezzo.** Corpus Builder separa registrazione della fonte, estrazione/trascrizione, mappatura delle unità di fonte, struttura/segmentazione, arricchimento, costruzione dei record, revisione e pubblicazione. Controlli e coordinate dell'evidenza si adattano al mezzo invece di applicare concetti PDF/pagina a tutto.
- **Preserva provenienza cELF e autorità dei campi.** I `FieldAssertion` canonici distinguono derivazione, esito della valutazione, autorità, stato del valore, confidenza, evidenza, attore/modello, identità stabile del campo e revisione del record. La conferma umana non cancella la provenienza del modello o di una procedura deterministica.
- **Revisiona i record con l'evidenza nel contesto.** I revisori possono modificare testo e metadati, ispezionare `SourceSpan` ed evidenze provenienti da altri record, confrontare revisioni, esplorare mappe semantiche e relazioni, accettare/rifiutare suggerimenti e pubblicare decisioni auditabili. I salvataggi ottimistici mantengono l'interfaccia reattiva mentre le scritture conflittuali sullo stesso record vengono serializzate.
- **Usa schemi di metadati configurabili e precedenti revisionati.** Gli schemi definiscono campi stabili, tipi, valori controllati, regole di evidenza/revisione, suggerimenti POS/NER, ambito del campo, istruzioni al modello e policy di retrieval. Gli esempi revisionati diventano precedenti limitati e legati all'evidenza per arricchimenti successivi senza sostituire le decisioni canoniche del revisore.
- **Aggiunge Document Intelligence opzionale.** Un livello di analisi derivato e indipendente dal provider può aggiungere entità, coreferenza, parlanti delle citazioni e relazioni di contenuto semantico. I language pack spaCy forniscono la base multilingue; un worker BookNLP isolato è disponibile come potenziamento opzionale per l'inglese. Queste annotazioni restano analisi ricostruibili, non evidenza di fonte né autorità del corpus.
- **Cerca in proiezioni derivate senza confonderle con il corpus.** ChromaDB memorizza proiezioni semantiche/di ricerca e cache ricostruibili, in modalità embedded o server HTTP. Sono disponibili retrieval denso, lessicale e MMR, RRF, filtri, routing linguistico e reranking cross-encoder limitato dove appropriato.
- **Esegue Research/RAG fondato sulle evidenze.** Research supporta retrieval ibrido, reranking, modalità a evidenze selezionate, budget di evidenza, generazione in streaming e annullabile, rendering deterministico delle citazioni, persistenza claim/support, validazione dei claim, memoria di risposte/claim e valutazione LLM. I record con provenienza incompleta vengono esclusi dall'evidenza invece di essere trattati silenziosamente come supporto valido.
- **Ispeziona e configura pipeline IA.** Pipeline Studio espone definizioni versionate, assegnazioni, trace di esecuzione, metriche per fase di latenza/errore/fallback, trace nel punto d'uso, confronto A/B Research non persistente e benchmark Research a casi fissi. Le fasi di retrieval, memoria, precedenti di metadati ed evidenza del revisore possono diventare esplicite, mentre i gate di provenienza/autorità restano vincoli strutturali.
- **Separa i trasporti API per responsabilità.** REST gestisce comandi e mutazioni; una facciata GraphQL cELF di sola lettura compone query tipizzate; un piano WebSocket autenticato invia notifiche realtime sulle operazioni. I messaggi realtime non sono mai stato canonico e i client possono risincronizzarsi da REST/GraphQL.
- **Supporta ricerca multiutente controllata.** I ruoli integrati Administrator e Researcher, insieme a ruoli personalizzati sicuri per i ricercatori, sono applicati sia dall'UI sia dall'API. Il testo di fonte visibile al ricercatore viene sintetizzato al confine API, i job sono associati al proprietario e le mutazioni corpus/sistema riservate agli amministratori restano inaccessibili.
- **Rende osservabili le operazioni lunghe.** Build del corpus, revisione LLM, RAG, grading, import, lavoro su modelli/language pack e upsert vettoriali appaiono come operazioni annullabili con snapshot/storico durevoli e progresso realtime. Il lavoro in-process interrotto da un riavvio viene marcato come fallito invece di essere rieseguito silenziosamente.
- **Fornisce un'interfaccia accessibile e multilingue.** Inglese e francese canadese sono locale di prima classe con parità delle chiavi verificata; la copertura README è più ampia. WCAG 2.2 AA, tastiera, focus visibile, reflow, movimento ridotto, forced colors/high contrast e test di localizzazione/stringhe lunghe sono criteri di rilascio. L'Help Center offre guide per pagina, FAQ di workflow e un glossario in linguaggio chiaro.
- **Esegue backup dell'ambiente di ricerca.** Backup/restore copre workspace, cronologia di audit, profili provider, asset sorgente, stato sistema/provenienza e collezioni Chroma con gli embedding.

Consultare la [Guida utente](docs/USER_GUIDE.md) per il riferimento completo delle funzionalità.

## Modello di tracciabilità cELF

Il modello dei dati accademici di DerridAI segue la distinzione cELF tra stato documentario/accademico autoritativo e proiezioni computazionali ricostruibili. Con tracciabilità completa, il percorso concettuale è:

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

In questo modo un claim generato può essere auditato all'indietro fino a supporto, evidenza, revisione del record, segmento di fonte e documento sorgente. Embedding, rank di retrieval, score di reranking, cache, stato UI e altri valori specifici dell'operazione restano stato derivato; non diventano proprietà intrinseche del record sorgente.

Vedere [SPECIFICATION.md](SPECIFICATION.md) per la specifica normativa cELF 1.0.

## Architettura

### Servizi runtime

- `web` — Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js e nginx. È l’applicazione browser; fa da proxy a `/api/` e usa REST, GraphQL e notifiche realtime. Storybook è un profilo di sviluppo opzionale.
- `api` — Python 3.12, FastAPI, Strawberry GraphQL, client ChromaDB, PyMuPDF, sentence-transformers e spaCy. È il confine applicativo autoritativo per autenticazione, fonti/corpus, letture cELF, provenienza, RAG, pipeline, job e stato di sistema.
- `document-nlp` — worker BookNLP opzionale e isolato per Document Intelligence in inglese. Riceve testo revisionato e limitato e non ha autorità sul corpus.
- `chroma` — server HTTP Chroma opzionale. `PersistentClient` embedded resta il default; entrambe le modalità memorizzano proiezioni di ricerca/vettoriali derivate.
- `ollama` — servizio Ollama locale opzionale. DerridAI può usare in alternativa Ollama già in esecuzione sull’host o qualunque endpoint compatibile OpenAI configurato.

Lo stack Compose predefinito avvia `web` e `api`; gli altri servizi sono profili opzionali o provider esterni.

### Autorità e persistenza

DerridAI non considera intenzionalmente tutti gli store come ugualmente autoritativi:

- **Stato accademico canonico** — asset/identità delle fonti, record e revisioni, field assertion, decisioni di revisione, legami esatti di evidenza/supporto e stato di pubblicazione.
- **Stato durevole del server** — autenticazione e stato sistema/provenienza/job/pipeline in SQLite sotto `./data`.
- **Stato derivato/ricostruibile** — indici Chroma, embedding, proiezioni di esempi di metadati, score di retrieval, proiezioni di contenuto semantico, output Document Intelligence e cache.
- **Stato workspace del browser** — preferenze locali e lavoro non salvato, separati dall'autorità del corpus.

### Separazione dei trasporti

- **REST**: tutti i comandi e le mutazioni, inclusi upload, decisioni di revisione, job, pubblicazione, amministrazione, backup e restore.
- **GraphQL**: facciata tipizzata cELF di sola lettura a `POST /api/graphql`; nessuna radice Mutation o Subscription.
- **WebSocket**: piano autenticato di notifiche a `WS /api/ws/events`; mai fonte di verità.

Per ownership dei moduli, confini di persistenza e flusso dati vedere [Architecture](docs/ARCHITECTURE.md), [GraphQL](docs/GRAPHQL.md) e [Realtime](docs/REALTIME.md).

## Per iniziare

### 1. Prerequisiti

Installare Git, Docker Engine/Desktop con `docker compose` e un endpoint LLM. La configurazione predefinita si aspetta Ollama sull'host.

Modelli predefiniti:

```text
gemma4:e2b
bge-m3:latest
```

### 2. Clonare e configurare

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Con Docker Desktop su WSL, impostare `HOST_UID` e `HOST_GID` in `.env` usando l'output di `id -u` e `id -g`.

Non esportare globalmente variabili di storage di test come `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` o `CHROMA_PATH`; Compose interpola prima le variabili già esportate.

### 3. Preparare i modelli

Con Ollama già in esecuzione sull'host:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Valori predefiniti:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Oppure usare il servizio Compose Ollama opzionale:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Poi impostare `OLLAMA_BASE_URL=http://ollama:11434`.

### 4. Avviare DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

Endpoint predefiniti:

- Applicazione: <http://localhost:8181>
- API: <http://127.0.0.1:8000>
- Documentazione OpenAPI: <http://127.0.0.1:8000/docs>

Al primo avvio, creare nel browser l'account amministratore iniziale. Non vengono fornite credenziali predefinite.

### 5. Verificare l'installazione

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

La risposta di liveness dovrebbe contenere `"ok": true`, la versione dell'applicazione e, se disponibile, il commit Git integrato.

Diagnostica più ampia:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Servizi opzionali

```bash
# Ollama locale
docker compose --profile ollama up -d ollama

# Server HTTP Chroma (poi impostare CHROMA_MODE=http)
docker compose --profile chroma up -d chroma

# Estensione inglese BookNLP per Document Intelligence
docker compose --profile document-nlp up -d document-nlp

# Superficie di sviluppo Storybook
docker compose --profile dev up storybook
```

Consultare [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) prima di abilitare o installare language pack NLP.

### 7. Arrestare o ricostruire

```bash
docker compose down

# dopo aver aggiornato il repository
docker compose down
docker compose up -d --build
```

Se una release precedente ha lasciato file di proprietà root sotto `data/`, eseguire `./scripts/fix-data-permissions.sh` su sistemi Unix supportati.

## Sviluppo

La CI usa Python 3.12 e Node 22.

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

Controlli locali rapidi:

```bash
ruff check api/app tests scripts/check_frontend_api_contract.py scripts/check_frontend_graphql_contract.py
mypy
pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py --ignore=tests/test_frontend_graphql_contract.py
pytest -q -m contract tests/test_frontend_api_contract.py
pytest -q -m contract tests/test_frontend_graphql_contract.py

cd web
npm run format:repo:check
npm run lint
npm run typecheck
npm run typecheck:tests
npm run test:unit
npm run build
```

Usare `npm run format:repo` da `web/` per formattare tutti i file supportati da Prettier. Gli snapshot HTML DOM legacy generati sono volutamente esclusi.

Per copertura browser, Storybook, parità CI e regole di contribuzione vedere [CONTRIBUTING.md](CONTRIBUTING.md).

## Mappa del repository

- `api/app/` — backend FastAPI: fonti/corpus, servizi di lettura cELF, GraphQL, realtime, provenienza, pipeline, RAG, provider, persistenza e job.
- `web/src/` — applicazione Vue 3: view, componenti, store Pinia, routing, client API, client realtime, moduli di dominio e compatibilità legacy rimanente.
- `booknlp-worker/` — worker BookNLP opzionale e isolato.
- `tests/` — test backend, regressione, contract, consistenza release e architettura.
- `web/tests/frontend/` — test Vitest.
- `web/tests/e2e/` — Playwright, Storybook, accessibilità e caratterizzazione.
- `docs/` — contratti correnti di architettura/dominio e note di rilascio storiche.
- `data/` — stato runtime locale; ignorato da Git salvo placeholder. Non commetterne mai il contenuto.

## Documentazione

- [Guida utente](docs/USER_GUIDE.md) — funzioni e workflow
- [Architettura](docs/ARCHITECTURE.md) — runtime, autorità, persistenza e flusso dati
- [Specifica cELF 1.0](SPECIFICATION.md) — modello normativo e requisiti di conformità
- [Contesto del progetto](docs/PROJECT_CONTEXT.md) — motivazione accademica e capacità implementate/previste
- [GraphQL](docs/GRAPHQL.md) — facciata di lettura cELF
- [Realtime](docs/REALTIME.md) — protocollo WebSocket e risincronizzazione
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — analisi linguistica derivata e language pack
- [Ingestione delle fonti](docs/INGESTION_VALIDATION.md) — sicurezza, limiti e fedeltà di estrazione
- [Schemi di metadati](docs/METADATA_SCHEMAS.md) — contratti di campo configurabili
- [Memoria dei metadati](docs/METADATA_MEMORY.md) — precedenti revisionati e confini di autorità
- [Migrazione FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md) — modello canonico delle asserzioni
- [CONTRIBUTING.md](CONTRIBUTING.md) e [AGENTS.md](AGENTS.md) — regole di sviluppo

La cronologia dei rilasci è in [CHANGELOG.md](CHANGELOG.md) e `docs/notes/<version>.md`. Le note di versione sono documenti storici, non la descrizione dell'architettura corrente.

## Licenza

DerridAI è distribuito secondo la [GNU Affero General Public License v3.0](LICENSE).

Copyright © 2026 Aaron John Schlosser, PhD. L'applicazione mostra anche © 2026 The New England Transcendental Club of California.
