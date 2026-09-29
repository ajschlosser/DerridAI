<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

![Логотип DerridAI](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI — локальная исследовательская среда с сохранением происхождения данных для построения, проверки, поиска и запросов по научным корпусам. В одном Docker-приложении она объединяет загрузку источников, построение корпуса с участием исследователя, обогащение метаданных с привязкой к доказательствам, производные векторные/поисковые индексы и retrieval-augmented generation (RAG), основанную на доказательствах.

DerridAI также является исходной референсной реализацией **cELF 1.0 — Capta-Enriched Lexical Format**, архитектуры данных для ИИ-ассистированной документальной работы, сохраняющей происхождение и трассируемость. Система отдельно хранит и позволяет проверять идентичность источника, идентичность и ревизию записи, утверждения метаданных, доказательства, сгенерированные утверждения и связи поддержки, не сводя всё это к непрозрачной векторной базе.

Текущая версия: **0.80.7 — Exeter** ([примечания к выпуску](docs/notes/0.80.7.md)). Этот README описывает актуальную архитектуру ветки `master`, включая уже влитые изменения после Exeter.

## Что умеет DerridAI

- **Получение и загрузка разнородных источников.** Поддерживаются PDF, обычный текст, RTF, DOCX, изображения и аудио; импорт URL и Project Gutenberg; Corpus Capture для обнаружения и получения произведений через адаптеры Wikidata, Project Gutenberg и Wikisource. При загрузке применяются ограничения безопасности и ресурсов с учётом типа носителя, а также сохраняются данные об экстракторе, инструменте и версии.
- **Построение корпуса с учётом типа носителя.** Corpus Builder разделяет регистрацию источника, извлечение/транскрипцию, сопоставление source units, структуру/сегментацию, обогащение, создание записей, проверку и публикацию. Элементы управления и координаты доказательств соответствуют конкретному носителю, а не навязывают понятия PDF/страниц всем типам источников.
- **Сохранение cELF-происхождения и авторитетности полей.** Канонические `FieldAssertion` различают происхождение значения, результат оценки, авторитетность, состояние значения, уверенность, доказательства, автора/модель, стабильную идентичность поля и ревизию записи. Подтверждение человеком не стирает исходное происхождение значения.
- **Проверка записей вместе с контекстом доказательств.** Рецензент может редактировать текст и метаданные, просматривать `SourceSpan` и доказательства из других записей, сравнивать ревизии, переходить по семантическим картам и связям, принимать/отклонять предложения и публиковать аудируемые решения. Оптимистические сохранения сохраняют отзывчивость интерфейса, а конфликтующие изменения одной записи сериализуются.
- **Настраиваемые схемы метаданных и проверенные прецеденты.** Схемы задают стабильные поля, типы, контролируемые значения, требования к доказательствам/проверке, POS/NER-подсказки, область действия поля, инструкции модели и политику retrieval. Проверенные примеры могут использоваться как ограниченные, привязанные к доказательствам прецеденты для последующего обогащения, не заменяя канонические решения рецензента.
- **Опциональный Document Intelligence.** Независимый от провайдера производный слой анализа может добавлять сущности, кореференцию, говорящих в цитатах и семантические связи содержания. Пакеты spaCy дают многоязычную основу; изолированный BookNLP worker доступен как дополнительный английский анализатор. Эти аннотации остаются перестраиваемым анализом, а не доказательством источника или авторитетным состоянием корпуса.
- **Поиск по производным проекциям без смешения их с корпусом.** ChromaDB хранит перестраиваемые семантические/поисковые проекции и кэши в embedded- или HTTP-режиме. Доступны dense, lexical и MMR retrieval, RRF, фильтры, языковая маршрутизация и ограниченный cross-encoder reranking.
- **Research/RAG, основанный на доказательствах.** Research поддерживает гибридный retrieval, reranking, режим выбранных доказательств, бюджеты доказательств, потоковую/отменяемую генерацию, детерминированное оформление цитат, сохранение claim/support-связей, проверку утверждений, память ответов/утверждений и LLM grading. Записи с неполной provenance исключаются из доказательств, а не считаются молча допустимой поддержкой.
- **Просмотр и настройка ИИ-конвейеров.** Pipeline Studio показывает версионируемые определения pipeline, назначения, трассы запусков, метрики latency/error/fallback по стадиям, point-of-use traces, непостоянное A/B-сравнение Research и фиксированные benchmark-запуски Research. Стадии retrieval, memory, metadata precedent и reviewer evidence могут быть явными, при этом provenance/authority gates остаются структурными ограничениями.
- **Разделение API-транспортов по ответственности.** REST отвечает за команды и мутации; read-only cELF-aware GraphQL façade — за типизированные чтения; аутентифицированный WebSocket — за realtime-уведомления об операциях. Realtime-сообщения никогда не являются каноническим состоянием, а клиент может пересинхронизироваться через REST/GraphQL.
- **Контролируемая многопользовательская работа.** Встроенные роли Administrator и Researcher и настраиваемые безопасные роли применяются и в UI, и в API. Текст источника, выдаваемый исследователю, суммируется на границе API, задания scoped по владельцу, а административные мутации корпуса/системы недоступны.
- **Наблюдаемость долгих операций.** Построение корпуса, LLM review, RAG, grading, импорт, работа с моделями/языковыми пакетами и vector upsert отображаются как отменяемые операции с долговечными snapshot/history и realtime progress. Прерванная перезапуском локальная работа помечается failed, а не запускается незаметно повторно.
- **Доступный и многоязычный интерфейс.** Английский и канадский французский — первичные UI-locale с обязательной паритетностью ключей; README доступны на большем числе языков. WCAG 2.2 AA, клавиатура, видимый фокус, reflow, reduced motion, forced colors/high contrast и проверки длинных строк/локализации являются критериями релиза. Help Center содержит руководства по страницам, FAQ по рабочим процессам и понятный глоссарий.
- **Резервное копирование исследовательской среды.** Backup/restore охватывает workspace, историю аудита, профили провайдеров, source assets, системное/provenance-состояние и коллекции Chroma с embeddings.

Полное описание функций см. в [Руководстве пользователя](docs/USER_GUIDE.md).

## Модель трассируемости cELF

Научная модель данных DerridAI следует различию cELF между авторитетным документальным/научным состоянием и перестраиваемыми вычислительными проекциями. При полной трассируемости концептуальная цепочка выглядит так:

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

Это позволяет аудировать сгенерированное утверждение в обратном направлении до его support, evidence, revision записи, source span и source document. Embeddings, retrieval rank, reranker score, кэши, UI state и другие значения конкретной операции остаются производным состоянием и не становятся собственными свойствами исходной записи.

Нормативная спецификация cELF 1.0 и ненормативный white paper DerridAI находятся в [SPECIFICATION.md](SPECIFICATION.md).

## Архитектура

### Сервисы выполнения


- `web` — Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js и nginx. Браузерное приложение; проксирует `/api/` и использует REST, GraphQL и realtime-уведомления. Storybook — опциональный dev-профиль.
- `api` — Python 3.12, FastAPI, Strawberry GraphQL, ChromaDB client, PyMuPDF, sentence-transformers и spaCy. Авторитетная граница приложения для authentication, источников/corpus, cELF reads, provenance, RAG, pipelines, jobs и состояния системы.
- `document-nlp` — опциональный изолированный BookNLP worker для английского Document Intelligence. Получает ограниченный проверенный текст и не имеет авторитета над corpus.
- `chroma` — опциональный HTTP Chroma server. Embedded `PersistentClient` остаётся режимом по умолчанию; оба режима хранят производные поисковые/векторные projections.
- `ollama` — опциональный локальный Ollama service. DerridAI также может использовать Ollama, уже работающий на host, или любой настроенный OpenAI-compatible endpoint.

Стандартный Compose запускает `web` и `api`; остальные сервисы — опциональные профили или внешние провайдеры.

### Авторитетность и хранение

DerridAI сознательно не считает все хранилища одинаково авторитетными:

- **Каноническое научное состояние** — source assets/identity, записи и ревизии, field assertions, решения рецензентов, точные evidence/support bindings и состояние публикации.
- **Долговечное серверное состояние** — auth и system/provenance/job/pipeline state в SQLite под `./data`.
- **Производное/перестраиваемое состояние** — индексы Chroma, embeddings, metadata exemplar projections, retrieval scores, semantic-content projections, Document Intelligence output и кэши.
- **Состояние workspace браузера** — локальные настройки и несохранённая работа отдельно от авторитетного состояния корпуса.

### Разделение транспортов

- **REST**: все команды и мутации — uploads, review decisions, jobs, публикация, администрирование, backup и restore.
- **GraphQL**: read-only типизированная cELF query façade по `POST /api/graphql`; без Mutation и Subscription root.
- **WebSocket**: аутентифицированный realtime notification plane по `WS /api/ws/events`; никогда не source of truth.

Подробнее: [Architecture](docs/ARCHITECTURE.md), [GraphQL](docs/GRAPHQL.md), [Realtime](docs/REALTIME.md).

## Начало работы

### 1. Требования

Установите Git, Docker Engine/Desktop с командой `docker compose` и LLM endpoint. По умолчанию ожидается Ollama на хосте.

Модели по умолчанию:

```text
gemma4:e2b
bge-m3:latest
```

### 2. Клонирование и настройка

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

При Docker Desktop + WSL задайте `HOST_UID` и `HOST_GID` в `.env` по выводу `id -u` и `id -g`.

Не экспортируйте глобально тестовые переменные хранения `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` или `CHROMA_PATH`: Compose сначала интерполирует уже экспортированные переменные shell.

### 3. Подготовка моделей

Если Ollama уже работает на хосте:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Значения по умолчанию:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Или используйте опциональный Compose-профиль Ollama:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

После этого установите `OLLAMA_BASE_URL=http://ollama:11434`.

### 4. Запуск DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

Адреса по умолчанию:

- Приложение: <http://localhost:8181>
- API: <http://127.0.0.1:8000>
- OpenAPI: <http://127.0.0.1:8000/docs>

При первом запуске создайте в браузере первую учётную запись администратора. Стандартные credentials не поставляются.

### 5. Проверка установки

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

Liveness-ответ должен содержать `"ok": true`, версию приложения и, если доступно, встроенный Git commit.

Расширенная диагностика:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Опциональные сервисы

```bash
# Локальный Ollama
docker compose --profile ollama up -d ollama

# Chroma HTTP server (затем CHROMA_MODE=http)
docker compose --profile chroma up -d chroma

# Английское дополнение BookNLP для Document Intelligence
docker compose --profile document-nlp up -d document-nlp

# Среда разработки Storybook
docker compose --profile dev up storybook
```

Перед включением или установкой NLP language packs см. [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md).

### 7. Остановка или пересборка

```bash
docker compose down

# после получения обновлений
docker compose down
docker compose up -d --build
```

Если старая версия оставила root-owned файлы в `data/`, выполните `./scripts/fix-data-permissions.sh` на поддерживаемой Unix-подобной системе.

## Разработка

CI использует Python 3.12 и Node 22.

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

Быстрые локальные проверки:

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

`npm run format:repo` из `web/` форматирует все поддерживаемые Prettier исходники, конфигурацию и документацию. Сгенерированные legacy DOM snapshot HTML намеренно исключены.

Правила contribution, Storybook, browser coverage и CI parity: [CONTRIBUTING.md](CONTRIBUTING.md).

## Структура репозитория

- `api/app/` — FastAPI backend: sources/corpus, cELF read services, GraphQL, realtime, provenance, pipelines, RAG, providers, persistence и jobs.
- `web/src/` — приложение Vue 3: views, components, Pinia stores, routing, API clients, realtime client, domain modules и оставшийся legacy compatibility layer.
- `booknlp-worker/` — опциональный изолированный BookNLP worker.
- `tests/` — backend, regression, contract, release-consistency и architecture tests.
- `web/tests/frontend/` — Vitest tests.
- `web/tests/e2e/` — Playwright, Storybook, accessibility и characterization coverage.
- `docs/` — актуальные architecture/domain contracts и исторические release notes.
- `data/` — локальное runtime state; игнорируется Git, кроме placeholders. Не коммитьте содержимое.

## Документация

- [User Guide](docs/USER_GUIDE.md) — функции и workflows
- [Architecture](docs/ARCHITECTURE.md) — runtime boundaries, authority, persistence и data flow
- [cELF 1.0 specification](SPECIFICATION.md) — нормативная модель и white paper референсной реализации
- [Project context](docs/PROJECT_CONTEXT.md) — научная мотивация и implemented/intended capabilities
- [GraphQL](docs/GRAPHQL.md) — read-only cELF query façade
- [Realtime](docs/REALTIME.md) — WebSocket protocol и resynchronization
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — производный лингвистический анализ и language packs
- [Source ingestion](docs/INGESTION_VALIDATION.md) — безопасность, лимиты и extraction fidelity
- [Metadata schemas](docs/METADATA_SCHEMAS.md) — настраиваемые field contracts
- [Metadata memory](docs/METADATA_MEMORY.md) — проверенные прецеденты и границы authority
- [FieldAssertion migration](docs/FIELD_ASSERTION_MIGRATION.md) — каноническая модель assertions
- [CONTRIBUTING.md](CONTRIBUTING.md) и [AGENTS.md](AGENTS.md) — правила разработки

История релизов находится в [CHANGELOG.md](CHANGELOG.md) и `docs/notes/<version>.md`. Версионные заметки — исторические документы, а не описание текущей архитектуры.

## Лицензия

DerridAI распространяется по лицензии [GNU Affero General Public License v3.0](LICENSE).

Copyright © 2026 Aaron John Schlosser, PhD. В приложении также указано © 2026 The New England Transcendental Club of California.
