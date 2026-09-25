<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI es una aplicación Docker orientada al uso local para construir, auditar y consultar corpus académicos de textos filosóficos. Ingiere fuentes PDF, texto/RTF/DOCX, imagen, audio, URL y Project Gutenberg para convertirlas en registros académicos que preservan la procedencia; admite revisión humana o mediante LLM y enriquecimiento de metadatos vinculado a evidencia; construye proyecciones de búsqueda derivadas en ChromaDB; y ejecuta sobre el resultado una canalización de generación aumentada por recuperación (RAG) fundamentada en evidencia.

Versión actual: **0.80.0 — Beverly** ([notas de la versión](docs/notes/0.80.0.md)).

## Funciones

- **Corpus Builder** — un flujo secuenciado Fuente → Estructura/transcripción → LLM y enriquecimiento → Construcción de registros → Revisión, cuyos controles se adaptan al medio seleccionado. La extracción tiene límites y preserva la procedencia; las revisiones de estructura o texto y la evidencia bajo responsabilidad del revisor siguen siendo auditables.
- **Revisión de registros** — espacios de trabajo JSONL con historial de auditoría, edición de metadatos por lotes o a nivel de obra, diferencias, navegación hacia la fuente o la evidencia y propiedad de campos por parte de personas o LLM. Los registros canónicos `FieldAssertion` preservan la procedencia del valor, la autoridad, la evidencia y la identidad estable del campo, mientras que los metadatos definidos por el esquema fluyen por revisión, Search, Record Inspector, retoque y la presentación de Research.
- **Revisión y herramientas LLM** — ejecuciones en primer plano, en segundo plano y Auto-improve en segundo plano contra perfiles con nombre de proveedores Ollama o compatibles con OpenAI, cada uno con su propio límite de concurrencia y estado de calentamiento.
- **Almacenes vectoriales** — colecciones persistentes de ChromaDB en el sistema de archivos local o en un servidor Chroma en ejecución, con espejos lingüísticos en inglés/francés, upserts en segundo plano y conversión de ida y vuelta con JSONL.
- **Investigación RAG** — recuperación híbrida, reranking mediante cross-encoder, enrutamiento por idioma, modo de evidencia seleccionada, generación transmitida y cancelable, memoria de procedencia de respuestas y afirmaciones, una biblioteca de respuestas en caché y calificación mediante LLM.
- **Roles** — cuentas de Administrador e Investigador; los investigadores ven texto de evidencia resumido y no pueden modificar los corpus.
- **Respaldo y restauración** — un solo ZIP que contiene espacios de trabajo, historial de auditoría, perfiles de proveedores, activos fuente del corpus y cada colección Chroma con sus embeddings.
- **Bilingüe y accesible** — inglés y francés canadiense son idiomas de primera clase con paridad de claves obligatoria. El acceso mediante teclado, el foco visible, el comportamiento adaptable y de redistribución, la compatibilidad con colores forzados y WCAG 2.2 AA son criterios de aceptación.

Consultá la [Guía del usuario](docs/USER_GUIDE.md) para ver la referencia completa de funciones.

## Arquitectura

<!-- prettier-ignore -->
| Servicio    | Stack                                                               | Notas                                                                                                                                          |
| ----------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, servido por nginx | Redirige `/api/` hacia la API; Storybook está disponible como servicio de desarrollo opcional                                                 |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | Los archivos autoritativos del corpus/build y el estado SQLite de autenticación/sistema/procedencia viven bajo `./data`; Chroma contiene proyecciones derivadas de búsqueda/resultados |
| Backend LLM | Ollama (predeterminado) o cualquier endpoint compatible con OpenAI  | Se ejecuta en el host o en otro lugar; no forma parte del stack Compose predeterminado                                                         |

Para conocer los límites de responsabilidad del código y la persistencia, consultá [Arquitectura](docs/ARCHITECTURE.md).

## Cómo empezar

Estos pasos son la ruta compatible desde una clonación limpia. Son deliberadamente explícitos para que una persona desarrolladora nueva pueda repetirlos sin depender de un directorio de datos de DerridAI existente ni de un entorno de shell previo.

### 1. Requisitos previos

Instalá Git, Docker Engine/Desktop con el comando `docker compose` y un endpoint LLM. La configuración predeterminada espera Ollama en el host.

Los modelos Ollama predeterminados son:

```text
gemma4:e2b
bge-m3:latest
```

Si usás un modelo Ollama diferente o un proveedor compatible con OpenAI, cambiá `.env` antes de iniciar DerridAI.

### 2. Clonar y configurar

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

Equivalente en PowerShell:

```powershell
Copy-Item .env.example .env
```

En Docker Desktop con WSL, definí `HOST_UID` y `HOST_GID` en `.env` con la salida de `id -u` e `id -g`. Esto mantiene los archivos Chroma/SQLite montados mediante bind bajo la propiedad de tu usuario del host.

No exportés globalmente en tu shell variables de almacenamiento de pruebas de DerridAI como `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` o `CHROMA_PATH`. Compose interpola las variables exportadas antes de que los valores del archivo se pasen al contenedor.

### 3. Hacer disponibles los modelos configurados

Para Ollama ya en ejecución en el host:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

El archivo `.env.example` predeterminado usa:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Como alternativa, usá el servicio Ollama opcional de Compose:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Luego definí `OLLAMA_BASE_URL=http://ollama:11434` en `.env`.

### 4. Validar la configuración de Compose e iniciar DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

Las direcciones predeterminadas son la aplicación <http://localhost:8181>, la API <http://127.0.0.1:8000> y la documentación de la API <http://127.0.0.1:8000/docs>.

En el primer inicio, DerridAI solicita crear la cuenta administradora inicial. No se incluyen credenciales predeterminadas.

### 5. Verificar la instalación

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

El endpoint live debería devolver JSON que contenga `"ok": true`, la versión de la aplicación y el commit Git incorporado cuando esté disponible. Los servicios `web` y `api` deberían aparecer como saludables en `docker compose ps`.

Para un diagnóstico local más amplio:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Detener o reconstruir

Detené la aplicación sin borrar el directorio `./data` montado mediante bind:

```bash
docker compose down
```

Reconstruí después de traer cambios:

```bash
docker compose down
docker compose up -d --build
```

Si una versión anterior dejó archivos propiedad de root bajo `data/`, ejecutá `./scripts/fix-data-permissions.sh` en hosts tipo Unix compatibles.

## Configuración para desarrollo

CI usa Python 3.12 y Node 22; usá esas versiones localmente al reproducir fallos.

Entorno de backend/pruebas:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Entorno de frontend:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Ejecutá las verificaciones locales rápidas de calidad desde la raíz del repositorio:

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

Usá `npm run format:repo` desde `web/` para dar formato a todos los archivos fuente, de configuración y documentación compatibles con Prettier en el repositorio. El HTML generado de snapshots DOM heredados se excluye intencionalmente.

Para cobertura de navegador, Storybook, paridad con CI y reglas de contribución, consultá [CONTRIBUTING.md](CONTRIBUTING.md).

## Mapa del repositorio

- `api/app/` — aplicación FastAPI, ingestión/revisión del corpus, procedencia, persistencia, RAG, proveedores y trabajos en segundo plano.
- `web/src/` — aplicación Vue, componentes reutilizables, módulos de dominio, stores y una capa de compatibilidad heredada del runtime que se está reduciendo.
- `tests/` — pruebas de backend, regresión y contrato.
- `web/tests/frontend/` — pruebas Vitest de componentes y dominio.
- `web/tests/e2e/` — cobertura Playwright de la aplicación, Storybook, accesibilidad y caracterización heredada.
- `docs/` — contratos actuales de arquitectura/dominio más notas históricas de versiones bajo `docs/notes/`.
- `data/` — estado local de ejecución; ignorado por Git salvo marcadores de posición. Nunca hagás commit de su contenido.

## Documentación

Empezá por los documentos que describen el comportamiento actual:

- [Guía del usuario](docs/USER_GUIDE.md) — referencia de funciones, operaciones, respaldo y limitaciones
- [Arquitectura](docs/ARCHITECTURE.md) — límites de ejecución, autoridad, persistencia y flujo de datos
- [Contexto del proyecto](docs/PROJECT_CONTEXT.md) — fundamento académico y capacidades implementadas frente a las previstas
- [Contribuir](CONTRIBUTING.md) — configuración para desarrollo humano, verificaciones de calidad y reglas de cambio
- [AGENTS.md](AGENTS.md) — reglas adicionales para agentes de programación
- Contratos específicos: [ingestión de fuentes](docs/INGESTION_VALIDATION.md), [esquemas de metadatos](docs/METADATA_SCHEMAS.md), [migración de FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md), [memoria de metadatos](docs/METADATA_MEMORY.md), [tokens de diseño](docs/DESIGN_TOKENS.md) y [localización fr-CA](docs/LOCALIZATION_FR_CA.md)

El historial de versiones está en [CHANGELOG.md](CHANGELOG.md) y `docs/notes/<version>.md`. Las notas específicas de cada versión son registros históricos; no son documentos de arquitectura actual ni del backlog.

## Licencia

Actualmente no se incluye ningún archivo de licencia. Los archivos fuente llevan `Copyright 2026 Aaron John Schlosser, PhD.`. La pantalla de inicio de sesión, el menú de cuenta y Configuración → Acerca de DerridAI muestran `© 2026 The New England Transcendental Club of California`.
