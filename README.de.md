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

![DerridAI-Logo](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [العربية](README.ar.md) · [简体中文](README.zh-CN.md)

DerridAI ist eine lokal ausgerichtete, provenanzerhaltende Forschungsumgebung zum Erstellen, Prüfen, Durchsuchen und Abfragen wissenschaftlicher Korpora. Die Docker-Anwendung verbindet Quellenaufnahme, Human-in-the-loop-Korpusaufbau, evidenzgebundene Metadatenanreicherung, abgeleitete Vektor-/Suchindizes und evidenzbasierte Retrieval-Augmented Generation (RAG).

DerridAI ist außerdem die ursprüngliche Referenzimplementierung von **cELF 1.0 — Capta-Enriched Lexical Format**, einer provenanzerhaltenden Informationsarchitektur für KI-gestützte Dokumentforschung. Quellenidentität, Record-Identität und Revision, Metadaten-Assertions, Evidenz, generierte Claims und Support-Bindungen bleiben getrennt prüfbar, statt in einem undurchsichtigen Vektorspeicher zusammenzufallen.

Aktuelle Version: **0.82.0 — Gloucester** ([Release Notes](docs/notes/0.82.0.md)). Dieses README beschreibt die Gloucester-Version.

## Aktueller Stand von `master`

Die folgende Zusammenfassung beschreibt die Gloucester-Version.

- **Corpus Builder ist jetzt ein progressiver Ablauf Einrichtung → Build → Review → Veröffentlichung.** Unterstützt werden begrenzte parallele Anreicherung, explizite Entscheidungen zu Korpus-Topologie und Record-Größe, fortsetzbares revisionsbewusstes Review, persistente Record-lokale Review-Warteschlangen, fokussierte Sitzungen zur Behebung von Publikationsblockern, wiederholbare Metadatengruppen, Audio-Sprecherzuordnungen und sicheres Text-Review während verifizierter Vorbereitung.
- **Metadaten- und Evidenzverarbeitung benötigt weniger Modellarbeit und bewahrt stärkere Semantik.** Deterministisches/kandidatenorientiertes Routing, semantische Identität und Wertäquivalenz, support-validierte Evidenzkaskade v2, Reparatur/Klassifikation strukturierter Ausgaben und inkrementelle Metadata-Memory-Abgleiche senken die Latenz, ohne Retrieval-Relevanz oder fehlerhafte Ausgaben zu Evidenz zu erheben.
- **Pipeline Studio modelliert ausführbare Berechnung explizit.** Serverseitig definierte Zwecke, Strategiefamilien, wissenschaftliche Effekte, typisierte Ports, aufgelöste Verdrahtung, Stage-Traces, Umfangs-/Komplexitätsmetriken, einstellbare Retrieval-Parameter und nicht persistente Vergleiche decken mehr Pfade für Search, Research, Reviewer-Evidenz, Recovery, Segmentierung und Anreicherung ab.
- **Works kann portable Forschungswebsites veröffentlichen.** Statische Exporte kombinieren das DerridAI SDK mit einer eigenen Vue-Laufzeit für Navigation, Annotationen, semantische Browser-Indizierung, vom Leser konfigurierte Provider und evidenzgebundenes Research mit verlinkten Zitaten, ohne den Export zum kanonischen Korpuszustand zu machen.
- **Realtime-Invalidierung und progressives Laden ersetzen mehr Polling und leere Vollseiten-Reloads.** Works, Record, Search, Research, Response Library, Languages, Relationships, Accounts/Roles, Metadata Memory und weitere Oberflächen behalten nutzbare Inhalte, kapseln Fehler, bieten lokale Wiederholungen und verwerfen veraltete Antworten.
- **Das Frontend baut den Legacy-Runtime weiter zurück.** Router-gesteuerte Navigation, Vue-Dialogs/Benachrichtigungen, gemeinsame Domain-/State-Module, Pinia-Slices und extrahierte Helfer reduzieren Kopplung; verbleibender Kompatibilitätscode bleibt isoliert.
- **cELF und die Entwicklungsinfrastruktur wurden geschärft.** Die Spezifikation ist produktneutral und profil-/provenienzorientiert mit verallgemeinerter `EvidenceRef`-Locator-Semantik; Architekturpläne dokumentieren kritische Grenzen; CI-/Pre-Push-Auswahl, Repository-Hygiene und Copyright-Durchsetzung wurden verstärkt.

## Was DerridAI bietet

- **Heterogene Quellen erfassen und importieren.** PDF, Klartext, RTF, DOCX, Bilder und Audio hochladen; URLs und Project-Gutenberg-Material importieren; oder Corpus Capture zur Entdeckung und Beschaffung über Adapter wie Wikidata, Project Gutenberg und Wikisource verwenden. Die Aufnahme wendet medienspezifische Sicherheits- und Ressourcenlimits an und bewahrt Extraktor-/Werkzeug-/Versionsprovenienz.
- **Mediengerechte Korpora bauen.** Corpus Builder trennt Quellenregistrierung, Extraktion/Transkription, Source-Unit-Mapping, Struktur/Segmentierung, Anreicherung, Record-Erzeugung, Review und Veröffentlichung. Bedienelemente und Evidenzkoordinaten richten sich nach dem Medium, statt PDF-/Seitenbegriffe auf alles anzuwenden.
- **cELF-Provenienz und Feldautorität bewahren.** Kanonische `FieldAssertion`-Records unterscheiden Herleitung, Evaluation, Autorität, Wertestatus, Konfidenz, Evidenz, Akteur/Modell, stabile Feldidentität und Record-Revision. Menschliche Bestätigung löscht Modell- oder deterministische Provenienz nicht.
- **Records mit Evidenz im Kontext prüfen.** Reviewer können Text und Metadaten bearbeiten, `SourceSpan`- und Fremd-Record-Evidenz inspizieren, Revisionen vergleichen, semantische Karten und Beziehungen durchlaufen, Vorschläge annehmen/ablehnen und mit auditierbaren Entscheidungen veröffentlichen. Optimistische Saves halten die UI reaktionsschnell, während konkurrierende Writes desselben Records serialisiert werden.
- **Konfigurierbare Metadatenschemata und geprüfte Präzedenzfälle nutzen.** Schemata definieren stabile Felder, Typen, kontrollierte Werte, Evidenz-/Reviewregeln, POS-/NER-Hinweise, Feldscope, Modellinstruktionen und Retrieval-Policies. Geprüfte Beispiele werden zu begrenzten, evidenzgebundenen Präzedenzfällen für spätere Anreicherung, ohne kanonische Reviewer-Entscheidungen zu ersetzen.
- **Optionale Document Intelligence hinzufügen.** Eine provider-neutrale, abgeleitete Analyseschicht kann Entitäten, Koreferenz, Zitatsprecher und semantische Inhaltsbeziehungen liefern. spaCy-Sprachpakete bilden die mehrsprachige Basis; ein isolierter BookNLP-Worker ist als optionale englische Erweiterung verfügbar. Diese Annotationen bleiben rekonstruierbare Analyse, nicht Quellenevidenz oder Korpusautorität.
- **Abgeleitete Suchprojektionen verwenden, ohne sie mit dem Korpus zu verwechseln.** ChromaDB speichert rekonstruierbare semantische/Suchprojektionen und Caches im eingebetteten oder HTTP-Server-Modus. Dichtes, lexikalisches und MMR-Retrieval, RRF, Filter, Sprachrouting und begrenztes Cross-Encoder-Reranking stehen dort zur Verfügung, wo sie sinnvoll sind.
- **Evidenzbasiertes Research/RAG ausführen.** Research unterstützt hybrides Retrieval, Reranking, ausgewählte Evidenz, Evidenzbudgets, gestreamte/abbrechbare Generierung, deterministische Zitationsdarstellung, Claim-/Support-Persistenz, Claim-Validierung, Response-/Claim-Memory und LLM-Grading. Records mit unvollständiger Provenienz werden aus der Evidenz ausgeschlossen, statt stillschweigend als gültige Unterstützung zu gelten.
- **KI-Pipelines inspizieren und konfigurieren.** Pipeline Studio zeigt versionierte Pipeline-Definitionen, Zuweisungen, Run-Traces, stufenbezogene Latenz-/Fehler-/Fallback-Metriken, Point-of-use-Traces, nicht persistente Research-A/B-Vergleiche und feste Research-Benchmarkfälle. Retrieval-, Memory-, Metadatenpräzedenz- und Reviewer-Evidenzstufen können explizit gemacht werden, während Provenienz-/Autoritätsgates strukturelle Constraints bleiben.
- **API-Transporte nach Verantwortung trennen.** REST besitzt Commands und Mutationen; eine read-only, cELF-bewusste GraphQL-Fassade komponiert typisierte Reads; eine authentifizierte WebSocket-Ebene liefert Realtime-Operationsmeldungen. Realtime-Nachrichten sind niemals kanonischer Zustand und Clients können aus REST/GraphQL neu synchronisieren.
- **Kontrollierte Mehrbenutzerforschung unterstützen.** Eingebaute Administrator- und Researcher-Rollen sowie anpassbare researcher-sichere Rollen werden in UI und API durchgesetzt. Researcher-sichtbarer Quelltext wird an der API-Grenze zusammengefasst, Jobs sind eigentümergebunden und Admin-only Korpus-/Systemmutationen bleiben gesperrt.
- **Lange Operationen beobachtbar machen.** Korpus-Builds, LLM-Review, RAG, Grading, Imports, Modell-/Sprachpaketarbeit und Vector-Upserts erscheinen als abbrechbare Operationen mit dauerhaften Snapshots/History und Realtime-Fortschritt. Bei Neustart unterbrochene In-Process-Arbeit wird als fehlgeschlagen markiert, nicht still erneut ausgeführt.
- **Barrierefreie, mehrsprachige Oberfläche bereitstellen.** Englisch und kanadisches Französisch sind First-class-Lokalisierungen mit erzwungener Schlüsselparität; die README-Abdeckung ist breiter. WCAG 2.2 AA, Tastaturzugriff, sichtbarer Fokus, Reflow, reduzierte Bewegung, Forced Colors/High Contrast sowie Long-string-/Lokalisierungstests sind Freigabekriterien. Das Help Center bietet seitenspezifische Guides, Workflow-FAQs und ein verständliches Glossar.
- **Forschungsumgebung sichern.** Backup/Restore umfasst Workspaces, Audit-Historie, Providerprofile, Quellenassets, System-/Provenienzstatus und Chroma-Collections inklusive Embeddings.

Der [User Guide](docs/USER_GUIDE.md) enthält die vollständige Funktionsreferenz.

## cELF-Traceability-Modell

DerridAIs wissenschaftliches Datenmodell folgt der cELF-Unterscheidung zwischen autoritativem dokumentarischem/wissenschaftlichem Zustand und rekonstruierbaren Rechenprojektionen. Bei vollständiger Nachverfolgbarkeit lautet der konzeptionelle Pfad:

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

Damit kann ein generierter Claim rückwärts über Support, Evidenz, Record-Revision und SourceSpan bis zum SourceDocument auditiert werden. Embeddings, Retrieval-Ränge, Reranker-Scores, Caches, UI-Zustand und andere operationsspezifische Werte bleiben abgeleiteter Zustand und werden nicht zu intrinsischen Eigenschaften des Quell-Records.

Siehe [SPECIFICATION.md](SPECIFICATION.md) für die normative cELF-1.0-Spezifikation.

## Architektur

### Laufzeitdienste

- `web` — Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js und nginx. Browseranwendung; proxyt `/api/` und nutzt REST, GraphQL sowie Realtime-Benachrichtigungen. Storybook ist ein optionales Dev-Profil.
- `api` — Python 3.12, FastAPI, Strawberry GraphQL, ChromaDB-Client, PyMuPDF, sentence-transformers und spaCy. Autoritative Anwendungsgrenze für Authentifizierung, Quellen/Korpus, cELF-Reads, Provenienz, RAG, Pipelines, Jobs und Systemzustand.
- `document-nlp` — optionaler isolierter BookNLP-Worker für englische Document Intelligence. Er erhält begrenzten, geprüften Text und besitzt keine Korpusautorität.
- `chroma` — optionaler HTTP-Chroma-Server. Der eingebettete `PersistentClient` bleibt Standard; beide Modi speichern abgeleitete Such-/Vektorprojektionen.
- `ollama` — optionaler lokaler Ollama-Dienst. DerridAI kann stattdessen bereits auf dem Host laufendes Ollama oder jeden konfigurierten OpenAI-kompatiblen Endpoint verwenden.

Der Standard-Compose-Stack startet `web` und `api`; die übrigen Dienste sind optionale Profile oder externe Provider.

### Autorität und Persistenz

DerridAI behandelt absichtlich nicht jeden Store als gleich autoritativ:

- **Kanonischer wissenschaftlicher Zustand** — Quellenassets/-identität, Records und Revisionen, Field Assertions, Reviewentscheidungen, exakte Evidenz-/Support-Bindungen und Veröffentlichungszustand.
- **Dauerhafter Serverzustand** — Authentifizierung sowie System-/Provenienz-/Job-/Pipeline-Zustand in SQLite unter `./data`.
- **Abgeleiteter/rekonstruierbarer Zustand** — Chroma-Indizes, Embeddings, Metadaten-Exemplarprojektionen, Retrieval-Scores, semantische Inhaltsprojektionen, Document-Intelligence-Ausgaben und Caches.
- **Browser-Workspace-Zustand** — lokale Präferenzen und ungespeicherter Workspace-Zustand, getrennt von Korpusautorität.

### Transportaufteilung

- **REST**: alle Commands und Mutationen, einschließlich Uploads, Reviewentscheidungen, Jobs, Veröffentlichung, Administration, Backup und Restore.
- **GraphQL**: read-only cELF-Query-Fassade unter `POST /api/graphql`; keine Mutation- oder Subscription-Root.
- **WebSocket**: authentifizierte Realtime-Benachrichtigungsebene unter `WS /api/ws/events`; niemals Source of Truth.

Details zu Modulverantwortung, Persistenzgrenzen und Datenfluss: [Architecture](docs/ARCHITECTURE.md), [GraphQL](docs/GRAPHQL.md) und [Realtime](docs/REALTIME.md).

## Erste Schritte

### 1. Voraussetzungen

Installieren Sie Git, Docker Engine/Desktop mit `docker compose` und einen LLM-Endpoint. Standardmäßig wird Ollama auf dem Host erwartet.

Standardmodelle:

```text
gemma4:e2b
bge-m3:latest
```

### 2. Klonen und konfigurieren

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Unter Docker Desktop mit WSL setzen Sie `HOST_UID` und `HOST_GID` in `.env` auf die Ausgabe von `id -u` und `id -g`.

Exportieren Sie Test-Storage-Variablen wie `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` oder `CHROMA_PATH` nicht global; Compose interpoliert exportierte Shell-Variablen zuerst.

### 3. Modelle bereitstellen

Mit bereits auf dem Host laufendem Ollama:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Standardwerte:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Oder das optionale Compose-Ollama-Profil verwenden:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Danach `OLLAMA_BASE_URL=http://ollama:11434` setzen.

### 4. DerridAI starten

```bash
docker compose config --quiet
docker compose up -d --build
```

Standardendpunkte:

- Anwendung: <http://localhost:8181>
- API: <http://127.0.0.1:8000>
- OpenAPI-Dokumentation: <http://127.0.0.1:8000/docs>

Beim ersten Start erstellen Sie im Browser das initiale Administratorkonto. Es werden keine Standardzugangsdaten ausgeliefert.

### 5. Installation prüfen

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

Die Liveness-Antwort sollte `"ok": true`, die Anwendungsversion und, wenn verfügbar, den eingebauten Git-Commit enthalten.

Erweiterte Diagnose:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Optionale Dienste

```bash
# Lokales Ollama
docker compose --profile ollama up -d ollama

# Chroma-HTTP-Server (anschließend CHROMA_MODE=http setzen)
docker compose --profile chroma up -d chroma

# Englische BookNLP-Erweiterung für Document Intelligence
docker compose --profile document-nlp up -d document-nlp

# Storybook-Entwicklungsoberfläche
docker compose --profile dev up storybook
```

Vor Aktivierung oder Installation von NLP-Sprachpaketen [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) lesen.

### 7. Stoppen oder neu bauen

```bash
docker compose down

# nach dem Pull neuer Änderungen
docker compose down
docker compose up -d --build
```

Falls ältere Releases root-eigene Dateien unter `data/` hinterlassen haben, führen Sie auf unterstützten Unix-Systemen `./scripts/fix-data-permissions.sh` aus.

## Entwickler-Setup

CI verwendet Python 3.12 und Node 22.

Backend/Test-Umgebung:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Frontend-Umgebung:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Schnelle lokale Qualitätsprüfungen:

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

`npm run format:repo` aus `web/` formatiert alle von Prettier unterstützten Repository-Dateien. Generierte Legacy-DOM-Snapshot-HTML-Dateien sind absichtlich ausgeschlossen.

Für Browser-Coverage, Storybook, CI-Parität und Beitragsregeln siehe [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository-Übersicht

- `api/app/` — FastAPI-Backend: Quellen/Korpus, cELF-Read-Services, GraphQL, Realtime, Provenienz, Pipelines, RAG, Provider, Persistenz und Jobs.
- `web/src/` — Vue-3-Anwendung: Views, Komponenten, Pinia-Stores, Routing, API-Clients, Realtime-Client, Domainmodule und verbleibende Legacy-Kompatibilität.
- `booknlp-worker/` — optionaler isolierter BookNLP-Worker.
- `tests/` — Backend-, Regression-, Contract-, Release-Consistency- und Architekturtests.
- `web/tests/frontend/` — Vitest-Tests.
- `web/tests/e2e/` — Playwright-, Storybook-, Accessibility- und Characterization-Coverage.
- `docs/` — aktuelle Architektur-/Domainverträge und historische Release Notes.
- `data/` — lokaler Laufzeitzustand; bis auf Platzhalter git-ignored. Inhalte niemals committen.

## Dokumentation

- [User Guide](docs/USER_GUIDE.md) — Funktionen und Workflows
- [Architecture](docs/ARCHITECTURE.md) — Laufzeitgrenzen, Autorität, Persistenz und Datenfluss
- [cELF-1.0-Spezifikation](SPECIFICATION.md) — normatives Informationsmodell und Konformitätsanforderungen
- [Project Context](docs/PROJECT_CONTEXT.md) — wissenschaftliche Begründung und implementierte/geplante Fähigkeiten
- [GraphQL](docs/GRAPHQL.md) — read-only cELF-Abfragefassade
- [Realtime](docs/REALTIME.md) — WebSocket-Protokoll und Resynchronisierung
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — abgeleitete linguistische Analyse und Sprachpakete
- [Source Ingestion](docs/INGESTION_VALIDATION.md) — Sicherheit, Limits und Extraktionstreue
- [Metadata Schemas](docs/METADATA_SCHEMAS.md) — konfigurierbare Feldverträge
- [Metadata Memory](docs/METADATA_MEMORY.md) — geprüfte Präzedenzfälle und Autoritätsgrenzen
- [FieldAssertion Migration](docs/FIELD_ASSERTION_MIGRATION.md) — kanonisches Assertion-Modell
- [CONTRIBUTING.md](CONTRIBUTING.md) und [AGENTS.md](AGENTS.md) — Entwicklungsregeln

Releasehistorie: [CHANGELOG.md](CHANGELOG.md) und `docs/notes/<version>.md`. Versionsspezifische Release Notes sind historische Aufzeichnungen, nicht die Beschreibung der aktuellen Architektur.

## Lizenz

DerridAI steht unter der [GNU Affero General Public License v3.0](LICENSE).

Copyright © 2026 Aaron John Schlosser, PhD. Die Anwendung zeigt außerdem © 2026 The New England Transcendental Club of California.
