<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI ist eine lokal ausgerichtete Docker-Anwendung zum Erstellen, Prüfen und Abfragen wissenschaftlicher Korpora philosophischer Texte. Sie importiert PDF-, Text-/RTF-/DOCX-, Bild-, Audio-, URL- und Project-Gutenberg-Quellen in wissenschaftliche Datensätze, die die Provenienz bewahren; unterstützt menschliche und LLM-gestützte Prüfung sowie evidenzgebundene Metadatenanreicherung; erstellt abgeleitete ChromaDB-Suchprojektionen; und führt über dem Ergebnis eine evidenzbasierte Retrieval-Augmented-Generation-Pipeline (RAG) aus.

Aktuelle Version: **0.80.0 — Beverly** ([Versionshinweise](docs/notes/0.80.0.md)).

## Funktionen

- **Corpus Builder** — ein sequenzieller Ablauf Quelle → Struktur/Transkription → LLM & Anreicherung → Datensatzkonstruktion → Prüfung, dessen Steuerelemente sich an das ausgewählte Medium anpassen. Die Extraktion ist begrenzt und bewahrt die Provenienz; vom Prüfer verantwortete Struktur-/Textänderungen und Evidenz bleiben auditierbar.
- **Datensatzprüfung** — JSONL-Arbeitsbereiche mit Auditverlauf, Metadatenbearbeitung in großen Mengen oder auf Werkebene, Diffs, Navigation zu Quelle/Evidenz sowie menschlicher bzw. LLM-Feldverantwortung. Kanonische `FieldAssertion`-Datensätze bewahren Wertprovenienz, Autorität, Evidenz und stabile Feldidentität, während schemadefinierte Metadaten durch Prüfung, Search, Record Inspector, Touch-up und Research-Darstellung fließen.
- **LLM-Prüfung und -Werkzeuge** — Vordergrund-, Hintergrund- und Auto-improve-Hintergrundläufe gegen benannte Ollama- oder OpenAI-kompatible Anbieterprofile, jeweils mit eigenem Nebenläufigkeitslimit und Warm-up-Status.
- **Vektorspeicher** — persistente ChromaDB-Sammlungen im lokalen Dateisystem oder auf einem laufenden Chroma-Server, mit englisch/französischen Sprachspiegeln, Hintergrund-Upserts und JSONL-Roundtripping.
- **RAG Research** — hybride Suche, Cross-Encoder-Reranking, Sprachrouting, Modus für ausgewählte Evidenz, gestreamte/abbrechbare Generierung, Provenienzspeicher für Antworten und Claims, eine zwischengespeicherte Response Library und LLM-Bewertung.
- **Rollen** — Admin- und Researcher-Konten; Forschende sehen zusammengefassten Evidenztext und können Korpora nicht verändern.
- **Sicherung & Wiederherstellung** — eine ZIP-Datei mit Arbeitsbereichen, Auditverlauf, Anbieterprofilen, Corpus-Quelldateien und jeder Chroma-Sammlung samt Embeddings.
- **Zweisprachig und barrierefrei** — Englisch und kanadisches Französisch sind vollwertige Locales mit erzwungener Schlüsselparität. Tastaturzugriff, sichtbarer Fokus, responsives/Reflow-Verhalten, Unterstützung erzwungener Farben und WCAG 2.2 AA sind Abnahmekriterien.

Die vollständige Funktionsreferenz finden Sie im [Benutzerhandbuch](docs/USER_GUIDE.md).

## Architektur

| Dienst      | Stack                                                               | Hinweise                                                                                                                                       |
| ----------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, bereitgestellt durch nginx | Leitet `/api/` an die API weiter; Storybook ist als optionaler Entwicklungsdienst verfügbar                                                   |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | Autoritative Corpus-/Build-Dateien und SQLite-Authentifizierungs-/System-/Provenienzstatus liegen unter `./data`; Chroma enthält abgeleitete Such-/Ergebnisprojektionen |
| LLM-Backend | Ollama (Standard) oder beliebiger OpenAI-kompatibler Endpunkt       | Läuft auf dem Host oder anderswo; ist nicht Teil des standardmäßigen Compose-Stacks                                                            |

Informationen zu Code-Zuständigkeiten und Persistenzgrenzen finden Sie unter [Architektur](docs/ARCHITECTURE.md).

## Erste Schritte

Diese Schritte bilden den unterstützten Weg für einen sauberen Checkout. Sie sind bewusst ausführlich, damit neue Entwickler sie wiederholen können, ohne von einem vorhandenen DerridAI-Datenverzeichnis oder einer bestehenden Shell-Umgebung abhängig zu sein.

### 1. Voraussetzungen

Installieren Sie Git, Docker Engine/Desktop mit dem Befehl `docker compose` sowie einen LLM-Endpunkt. Die Standardkonfiguration erwartet Ollama auf dem Host.

Die standardmäßigen Ollama-Modelle sind:

```text
gemma4:e2b
bge-m3:latest
```

Wenn Sie ein anderes Ollama-Modell oder einen OpenAI-kompatiblen Anbieter verwenden, ändern Sie vor dem Start von DerridAI die Datei `.env`.

### 2. Klonen und konfigurieren

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell-Entsprechung:

```powershell
Copy-Item .env.example .env
```

Setzen Sie unter Docker Desktop mit WSL `HOST_UID` und `HOST_GID` in `.env` auf die Ausgabe von `id -u` und `id -g`. So bleiben per Bind-Mount eingebundene Chroma-/SQLite-Dateien im Besitz Ihres Host-Benutzers.

Exportieren Sie DerridAI-Test-Speichervariablen wie `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` oder `CHROMA_PATH` nicht global in Ihrer Shell. Compose interpoliert exportierte Variablen, bevor Werte aus der Datei an den Container übergeben werden.

### 3. Konfigurierte Modelle verfügbar machen

Für Ollama, das bereits auf dem Host läuft:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Die standardmäßige `.env.example` verwendet:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Alternativ können Sie den optionalen Ollama-Compose-Dienst verwenden:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Setzen Sie anschließend `OLLAMA_BASE_URL=http://ollama:11434` in `.env`.

### 4. Compose-Konfiguration prüfen und DerridAI starten

```bash
docker compose config --quiet
docker compose up -d --build
```

Die Standardbindungen sind Anwendung <http://localhost:8181>, API <http://127.0.0.1:8000> und API-Dokumentation <http://127.0.0.1:8000/docs>.

Beim ersten Start fordert DerridAI Sie auf, das erste Administratorkonto anzulegen. Es werden keine Standardzugangsdaten ausgeliefert.

### 5. Installation prüfen

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

Der Live-Endpunkt sollte JSON mit `"ok": true`, der Anwendungsversion und, sofern verfügbar, dem eingebetteten Git-Commit zurückgeben. Die Dienste `web` und `api` sollten in `docker compose ps` als healthy angezeigt werden.

Für eine umfassendere lokale Diagnose:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Stoppen oder neu bauen

Stoppen Sie die Anwendung, ohne das per Bind-Mount eingebundene Verzeichnis `./data` zu löschen:

```bash
docker compose down
```

Nach dem Abrufen von Änderungen neu bauen:

```bash
docker compose down
docker compose up -d --build
```

Falls eine ältere Version root-eigene Dateien unter `data/` hinterlassen hat, führen Sie auf unterstützten Unix-ähnlichen Hosts `./scripts/fix-data-permissions.sh` aus.

## Entwicklungsumgebung

CI verwendet Python 3.12 und Node 22; nutzen Sie diese Versionen lokal, wenn Sie Fehler reproduzieren.

Backend-/Testumgebung:

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

Führen Sie die schnellen lokalen Qualitätsprüfungen vom Repository-Stamm aus:

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

Verwenden Sie `npm run format:repo` aus `web/`, um alle von Prettier unterstützten Quell-, Konfigurations- und Dokumentationsdateien im Repository zu formatieren. Generiertes Legacy-DOM-Snapshot-HTML ist absichtlich ausgeschlossen.

Informationen zu Browser-Abdeckung, Storybook, CI-Parität und Beitragsregeln finden Sie in [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository-Übersicht

- `api/app/` — FastAPI-Anwendung, Corpus-Ingestion/-Prüfung, Provenienz, Persistenz, RAG, Anbieter und Hintergrundjobs.
- `web/src/` — Vue-Anwendung, wiederverwendbare Komponenten, Domänenmodule, Stores und die schrumpfende Legacy-Runtime-Kompatibilitätsschicht.
- `tests/` — Backend-, Regressions- und Vertragstests.
- `web/tests/frontend/` — Vitest-Komponenten-/Domänentests.
- `web/tests/e2e/` — Playwright-Abdeckung für Anwendung, Storybook, Barrierefreiheit und Legacy-Charakterisierung.
- `docs/` — aktuelle Architektur-/Domänenverträge sowie historische Versionshinweise unter `docs/notes/`.
- `data/` — lokaler Laufzeitstatus; bis auf Platzhalter von Git ignoriert. Inhalte niemals committen.

## Dokumentation

Beginnen Sie mit den Dokumenten, die das aktuelle Verhalten beschreiben:

- [Benutzerhandbuch](docs/USER_GUIDE.md) — Funktionsreferenz, Betrieb, Sicherung und Einschränkungen
- [Architektur](docs/ARCHITECTURE.md) — Laufzeitgrenzen, Autorität, Persistenz und Datenfluss
- [Projektkontext](docs/PROJECT_CONTEXT.md) — wissenschaftliche Begründung und implementierte gegenüber beabsichtigten Fähigkeiten
- [Mitwirken](CONTRIBUTING.md) — Einrichtung für menschliche Entwickler, Qualitätsprüfungen und Änderungsregeln
- [AGENTS.md](AGENTS.md) — zusätzliche Regeln für Coding-Agents
- Spezifische Verträge: [Quellen-Ingestion](docs/INGESTION_VALIDATION.md), [Metadatenschemata](docs/METADATA_SCHEMAS.md), [FieldAssertion-Migration](docs/FIELD_ASSERTION_MIGRATION.md), [Metadatenspeicher](docs/METADATA_MEMORY.md), [Design-Tokens](docs/DESIGN_TOKENS.md) und [fr-CA-Lokalisierung](docs/LOCALIZATION_FR_CA.md)

Die Versionshistorie steht in [CHANGELOG.md](CHANGELOG.md) und `docs/notes/<version>.md`. Versionsspezifische Hinweise sind historische Aufzeichnungen; sie sind weder aktuelle Architektur- noch Backlog-Dokumente.

## Lizenz

Derzeit ist keine Lizenzdatei enthalten. Quelldateien tragen `Copyright 2026 Aaron John Schlosser, PhD.`. Der Anmeldebildschirm, das Kontomenü und Einstellungen → Über DerridAI zeigen `© 2026 The New England Transcendental Club of California`.
