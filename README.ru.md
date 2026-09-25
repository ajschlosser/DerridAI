<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI — это Docker-приложение с приоритетом локального запуска для создания, аудита и поиска по научным корпусам философских текстов. Оно загружает источники PDF, текст/RTF/DOCX, изображения, аудио, URL и материалы Project Gutenberg в научные записи с сохранением происхождения; поддерживает проверку человеком или LLM и обогащение метаданных, привязанное к доказательствам; строит производные поисковые проекции ChromaDB; и запускает по результату конвейер retrieval-augmented generation (RAG), основанный на доказательствах.

Текущая версия: **0.80.0 — Beverly** ([примечания к выпуску](docs/notes/0.80.0.md)).

## Возможности

- **Corpus Builder** — последовательный рабочий процесс Источник → Структура/транскрипция → LLM и обогащение → Формирование записей → Проверка, элементы управления которого адаптируются к выбранному типу носителя. Извлечение ограничено и сохраняет происхождение; изменения структуры/текста и доказательства, находящиеся под контролем рецензента, остаются пригодными для аудита.
- **Проверка записей** — рабочие пространства JSONL с историей аудита, массовым редактированием метаданных или редактированием на уровне произведения, diff-представлениями, навигацией к источнику/доказательствам и принадлежностью полей человеку или LLM. Канонические записи `FieldAssertion` сохраняют происхождение значения, статус авторитетности, доказательства и стабильную идентичность поля, а определённые схемой метаданные проходят через проверку, Search, Record Inspector, touch-up и представление Research.
- **Проверка и инструменты LLM** — запуски в переднем плане, в фоне и фоновые Auto-improve-запуски с именованными профилями поставщиков Ollama или OpenAI-совместимых API, каждый со своим лимитом параллелизма и состоянием прогрева.
- **Векторные хранилища** — постоянные коллекции ChromaDB в локальной файловой системе или на работающем сервере Chroma, с английскими/французскими языковыми зеркалами, фоновыми upsert-операциями и двусторонним преобразованием JSONL.
- **RAG Research** — гибридный поиск, reranking с помощью cross-encoder, маршрутизация по языку, режим выбранных доказательств, потоковая/отменяемая генерация, память происхождения ответов и утверждений, кэшированная Response Library и оценивание с помощью LLM.
- **Роли** — учётные записи Admin и Researcher; исследователи видят краткое изложение доказательств и не могут изменять корпуса.
- **Резервное копирование и восстановление** — один ZIP-файл, содержащий рабочие пространства, историю аудита, профили поставщиков, исходные ресурсы корпуса и каждую коллекцию Chroma с её embeddings.
- **Двуязычность и доступность** — английский и канадский французский являются полноценными локалями с обязательным совпадением ключей. Доступ с клавиатуры, видимый фокус, адаптивное/reflow-поведение, поддержка forced-colors и соответствие WCAG 2.2 AA входят в критерии приёмки.

Полный перечень возможностей см. в [Руководстве пользователя](docs/USER_GUIDE.md).

## Архитектура

| Сервис      | Стек                                                                | Примечания                                                                                                                                     |
| ----------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, обслуживается nginx | Проксирует `/api/` к API; Storybook доступен как необязательный сервис разработки                                                            |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | Авторитетные файлы корпуса/build и состояние SQLite для auth/system/provenance находятся в `./data`; Chroma хранит производные поисковые/результатные проекции |
| LLM backend | Ollama (по умолчанию) или любой OpenAI-совместимый endpoint         | Работает на хосте или в другом месте; не входит в стандартный стек Compose                                                                    |

Границы ответственности кода и хранения описаны в документе [Архитектура](docs/ARCHITECTURE.md).

## Начало работы

Ниже приведён поддерживаемый путь для чистого checkout. Шаги намеренно подробны, чтобы новый разработчик мог повторить их без зависимости от уже существующего каталога данных DerridAI или настроенного shell-окружения.

### 1. Требования

Установите Git, Docker Engine/Desktop с командой `docker compose` и LLM-endpoint. Конфигурация по умолчанию ожидает Ollama на хосте.

Модели Ollama по умолчанию:

```text
gemma4:e2b
bge-m3:latest
```

Если используется другая модель Ollama или OpenAI-совместимый поставщик, измените `.env` до запуска DerridAI.

### 2. Клонирование и настройка

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

Эквивалент для PowerShell:

```powershell
Copy-Item .env.example .env
```

При использовании Docker Desktop с WSL задайте `HOST_UID` и `HOST_GID` в `.env` равными выводу `id -u` и `id -g`. Это сохраняет владельцем bind-mounted файлов Chroma/SQLite пользователя хоста.

Не экспортируйте глобально в shell тестовые переменные хранения DerridAI, такие как `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` или `CHROMA_PATH`. Compose подставляет экспортированные переменные до передачи значений из файла в контейнер.

### 3. Подготовка настроенных моделей

Если Ollama уже запущена на хосте:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Стандартный `.env.example` использует:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

В качестве альтернативы можно использовать необязательный сервис Ollama в Compose:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

После этого задайте `OLLAMA_BASE_URL=http://ollama:11434` в `.env`.

### 4. Проверка конфигурации Compose и запуск DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

Адреса по умолчанию: приложение <http://localhost:8181>, API <http://127.0.0.1:8000>, документация API <http://127.0.0.1:8000/docs>.

При первом запуске DerridAI предложит создать начальную учётную запись администратора. Учётные данные по умолчанию не поставляются.

### 5. Проверка установки

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

Live-endpoint должен вернуть JSON с `"ok": true`, версией приложения и встроенным Git-коммитом, если он доступен. Сервисы `web` и `api` должны отображаться как healthy в `docker compose ps`.

Для более широкой локальной диагностики:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Остановка или пересборка

Остановите приложение, не удаляя bind-mounted каталог `./data`:

```bash
docker compose down
```

После получения изменений выполните пересборку:

```bash
docker compose down
docker compose up -d --build
```

Если более старая версия оставила в `data/` файлы, принадлежащие root, запустите `./scripts/fix-data-permissions.sh` на поддерживаемых Unix-подобных системах.

## Настройка среды разработчика

CI использует Python 3.12 и Node 22; используйте те же версии локально при воспроизведении ошибок.

Среда backend/тестов:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Среда frontend:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Запустите быстрые локальные проверки качества из корня репозитория:

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

Используйте `npm run format:repo` из `web/`, чтобы форматировать все исходные, конфигурационные и документационные файлы репозитория, поддерживаемые Prettier. Сгенерированный legacy DOM snapshot HTML намеренно исключён.

Сведения о браузерном покрытии, Storybook, соответствии CI и правилах внесения изменений см. в [CONTRIBUTING.md](CONTRIBUTING.md).

## Карта репозитория

- `api/app/` — приложение FastAPI, загрузка/проверка корпуса, provenance, persistence, RAG, поставщики и фоновые задачи.
- `web/src/` — приложение Vue, переиспользуемые компоненты, доменные модули, stores и сокращающийся слой совместимости с legacy runtime.
- `tests/` — backend-, regression- и contract-тесты.
- `web/tests/frontend/` — компонентные и доменные тесты Vitest.
- `web/tests/e2e/` — покрытие Playwright для приложения, Storybook, доступности и legacy-characterization.
- `docs/` — текущие контракты архитектуры/домена и исторические примечания к выпускам в `docs/notes/`.
- `data/` — локальное runtime-состояние; игнорируется Git, кроме файлов-заполнителей. Никогда не коммитьте его содержимое.

## Документация

Начните с документов, описывающих текущее поведение:

- [Руководство пользователя](docs/USER_GUIDE.md) — справочник функций, эксплуатация, резервное копирование и ограничения
- [Архитектура](docs/ARCHITECTURE.md) — runtime-границы, авторитетность, persistence и поток данных
- [Контекст проекта](docs/PROJECT_CONTEXT.md) — научное обоснование и реализованные по сравнению с планируемыми возможностями
- [Участие в разработке](CONTRIBUTING.md) — настройка для разработчиков, проверки качества и правила изменений
- [AGENTS.md](AGENTS.md) — дополнительные правила для coding agents
- Специализированные контракты: [загрузка источников](docs/INGESTION_VALIDATION.md), [схемы метаданных](docs/METADATA_SCHEMAS.md), [миграция FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md), [память метаданных](docs/METADATA_MEMORY.md), [design tokens](docs/DESIGN_TOKENS.md) и [локализация fr-CA](docs/LOCALIZATION_FR_CA.md)

История выпусков находится в [CHANGELOG.md](CHANGELOG.md) и `docs/notes/<version>.md`. Примечания к конкретным версиям являются историческими записями; они не являются документами текущей архитектуры или backlog.

## Лицензия

Файл лицензии в настоящее время не включён. Исходные файлы содержат `Copyright 2026 Aaron John Schlosser, PhD.`. Экран входа, меню учётной записи и Настройки → О DerridAI показывают `© 2026 The New England Transcendental Club of California`.
