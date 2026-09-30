<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

![Logo de DerridAI](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI es un entorno de investigación local-first que preserva la procedencia para construir, revisar, buscar y consultar corpus académicos. Integra ingestión de fuentes, construcción de corpus con revisión humana, enriquecimiento de metadatos vinculado a evidencia, índices vectoriales/de búsqueda derivados y generación aumentada por recuperación (RAG) basada en evidencia dentro de una sola aplicación Docker.

DerridAI también es la implementación de referencia original de **cELF 1.0 — Capta-Enriched Lexical Format**, una arquitectura de información que preserva la procedencia para investigación documental asistida por IA. La implementación mantiene separadas e inspeccionables la identidad de la fuente, la identidad y revisión del registro, las afirmaciones de metadatos, la evidencia, las afirmaciones generadas y sus vínculos de soporte, en vez de aplanarlas dentro de una base vectorial opaca.

Versión actual: **0.81.0 — Fall River** ([notas de versión](docs/notes/0.81.0.md)). Este README describe la arquitectura actual de `master`, incluido el trabajo posterior a Exeter ya fusionado en el repositorio.

## Qué hace DerridAI

- **Adquiere e ingiere fuentes heterogéneas.** Cargue PDF, texto plano, RTF, DOCX, imágenes y audio; importe URL y material de Project Gutenberg; o use Corpus Capture para descubrir y adquirir obras mediante adaptadores como Wikidata, Project Gutenberg y Wikisource. La ingestión aplica límites de seguridad y recursos específicos del medio y conserva la procedencia del extractor, herramienta y versión.
- **Construye corpus con flujos adaptados al medio.** Corpus Builder separa registro de la fuente, extracción/transcripción, mapeo de unidades fuente, estructura/segmentación, enriquecimiento, construcción de registros, revisión y publicación. Los controles y coordenadas de evidencia se adaptan al medio en lugar de imponer conceptos de PDF/página a todo.
- **Preserva procedencia cELF y autoridad de campos.** Los `FieldAssertion` canónicos distinguen derivación, evaluación, autoridad, estado del valor, confianza, evidencia, actor/modelo, identidad estable del campo y revisión del registro. La confirmación humana no borra la procedencia del modelo ni de procedimientos deterministas.
- **Permite revisar registros con evidencia en contexto.** Los revisores pueden editar texto y metadatos, inspeccionar `SourceSpan` y evidencia de otros registros, comparar revisiones, recorrer mapas semánticos y relaciones, aceptar o rechazar sugerencias y publicar decisiones auditables. Los guardados optimistas mantienen la interfaz ágil mientras se serializan escrituras conflictivas sobre el mismo registro.
- **Usa esquemas de metadatos configurables y precedentes revisados.** Los esquemas definen campos estables, tipos, valores controlados, reglas de evidencia/revisión, pistas POS/NER, alcance del campo, instrucciones al modelo y políticas de recuperación. Los ejemplos revisados se convierten en precedentes acotados y vinculados a evidencia para enriquecimientos posteriores sin sustituir las decisiones canónicas del revisor.
- **Añade Document Intelligence opcional.** Una capa de análisis derivada e independiente del proveedor puede aportar entidades, correferencia, hablantes de citas y relaciones de contenido semántico. Los paquetes spaCy proporcionan la base multilingüe; un worker BookNLP aislado está disponible como mejora opcional en inglés. Estas anotaciones siguen siendo análisis reconstruibles, no evidencia de fuente ni autoridad del corpus.
- **Busca en proyecciones derivadas sin confundirlas con el corpus.** ChromaDB almacena proyecciones semánticas/de búsqueda y cachés reconstruibles en modo embebido o servidor HTTP. Hay recuperación densa, léxica y MMR, fusión RRF, filtros, enrutamiento por idioma y reranking acotado con cross-encoder donde corresponde.
- **Ejecuta Research/RAG basado en evidencia.** Research admite recuperación híbrida, reranking, modo de evidencia seleccionada, presupuestos de evidencia, generación en streaming y cancelable, renderizado determinista de citas, persistencia de afirmaciones/soportes, validación de afirmaciones, memoria de respuestas/afirmaciones y evaluación por LLM. Los registros con procedencia incompleta se excluyen de la evidencia en vez de tratarlos silenciosamente como soporte válido.
- **Inspecciona y configura pipelines de IA.** Pipeline Studio expone definiciones versionadas, asignaciones, trazas de ejecución, métricas por etapa de latencia/error/fallback, trazas en el punto de uso, comparación A/B de Research no persistente y benchmarks de Research con casos fijos. Las etapas de recuperación, memoria, precedentes de metadatos y evidencia del revisor pueden hacerse explícitas mientras las compuertas de procedencia/autoridad siguen siendo restricciones estructurales.
- **Separa los transportes de API por responsabilidad.** REST controla comandos y mutaciones; una fachada GraphQL cELF de solo lectura compone lecturas tipadas; un plano WebSocket autenticado envía notificaciones de operaciones en tiempo real. Los mensajes realtime nunca son estado canónico y los clientes pueden resincronizarse desde REST/GraphQL.
- **Soporta investigación multiusuario controlada.** Los roles integrados Administrador e Investigador, además de roles personalizados seguros para investigadores, se aplican tanto en la UI como en la API. El texto fuente visible al investigador se resume en el límite de la API, los jobs quedan asociados a su propietario y las mutaciones de corpus/sistema reservadas al administrador permanecen inaccesibles.
- **Hace observables las operaciones largas.** Construcciones de corpus, revisión LLM, RAG, grading, importaciones, trabajo con modelos/paquetes lingüísticos y upserts vectoriales aparecen como operaciones cancelables con instantáneas/historial duraderos y progreso en tiempo real. El trabajo en proceso interrumpido por un reinicio se marca como fallido en vez de reproducirse silenciosamente.
- **Ofrece una interfaz accesible y multilingüe.** Inglés y francés canadiense son locales de primera clase con paridad de claves obligatoria; la cobertura de README es más amplia. WCAG 2.2 AA, teclado, foco visible, reflow, reducción de movimiento, colores forzados/alto contraste y pruebas de cadenas largas/localización son criterios de aceptación. El Centro de ayuda incluye guías por página, FAQ de flujos de trabajo y un glosario en lenguaje claro.
- **Respalda el entorno de investigación.** Backup/restore cubre espacios de trabajo, historial de auditoría, perfiles de proveedores, activos de fuentes, estado de sistema/procedencia y colecciones Chroma con sus embeddings.

Consulte la [Guía del usuario](docs/USER_GUIDE.md) para la referencia completa de funciones.

## Modelo de trazabilidad cELF

El modelo académico de DerridAI sigue la distinción de cELF entre estado documental/académico autoritativo y proyecciones computacionales reconstruibles. Con trazabilidad completa, la ruta conceptual es:

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

Así, una afirmación generada puede auditarse hacia atrás hasta su soporte, evidencia, revisión de registro, tramo de fuente y documento fuente. Embeddings, rango de recuperación, scores de reranking, cachés, estado de UI y otros valores específicos de una operación permanecen como estado derivado; no se convierten en propiedades intrínsecas del registro fuente.

Consulte [SPECIFICATION.md](SPECIFICATION.md) para la especificación normativa cELF 1.0 y el white paper no normativo de DerridAI.

## Arquitectura

### Servicios de ejecución

- `web` — Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js y nginx. Es la aplicación del navegador; hace proxy de `/api/` y consume REST, GraphQL y notificaciones realtime. Storybook es un perfil de desarrollo opcional.
- `api` — Python 3.12, FastAPI, Strawberry GraphQL, cliente ChromaDB, PyMuPDF, sentence-transformers y spaCy. Es el límite autoritativo de aplicación para autenticación, fuentes/corpus, lecturas cELF, procedencia, RAG, pipelines, jobs y estado del sistema.
- `document-nlp` — worker BookNLP opcional y aislado para Document Intelligence en inglés. Recibe texto revisado y acotado; no tiene autoridad sobre el corpus.
- `chroma` — servidor HTTP Chroma opcional. `PersistentClient` embebido sigue siendo el modo predeterminado; ambos modos almacenan proyecciones de búsqueda/vectoriales derivadas.
- `ollama` — servicio Ollama local opcional. DerridAI también puede usar Ollama ya activo en el host o cualquier endpoint compatible con OpenAI configurado.

La pila Compose predeterminada inicia `web` y `api`; los demás servicios son perfiles opcionales o proveedores externos.

### Autoridad y persistencia

DerridAI no considera todos los almacenamientos igualmente autoritativos:

- **Estado académico canónico** — activos/identidad de fuentes, registros y revisiones, afirmaciones de campos, decisiones de revisión, vínculos exactos de evidencia/soporte y estado de publicación.
- **Estado durable del servidor** — autenticación y estado de sistema/procedencia/jobs/pipelines en SQLite bajo `./data`.
- **Estado derivado/reconstruible** — índices Chroma, embeddings, proyecciones de ejemplos de metadatos, scores de recuperación, proyecciones de contenido semántico, salida de Document Intelligence y cachés.
- **Estado del espacio de trabajo del navegador** — preferencias y trabajo no guardado, separado de la autoridad del corpus.

### Separación de transportes

- **REST**: todos los comandos y mutaciones, incluidos uploads, decisiones de revisión, jobs, publicación, administración, backup y restore.
- **GraphQL**: fachada tipada cELF de solo lectura en `POST /api/graphql`; sin raíz Mutation ni Subscription.
- **WebSocket**: plano autenticado de notificaciones en `WS /api/ws/events`; nunca una fuente de verdad.

Para límites de módulos, persistencia y flujo de datos, consulte [Arquitectura](docs/ARCHITECTURE.md), [GraphQL](docs/GRAPHQL.md) y [Realtime](docs/REALTIME.md).

## Inicio rápido

### 1. Requisitos previos

Instale Git, Docker Engine/Desktop con `docker compose` y un endpoint LLM. La configuración predeterminada espera Ollama en el host.

Modelos predeterminados:

```text
gemma4:e2b
bge-m3:latest
```

### 2. Clonar y configurar

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Con Docker Desktop sobre WSL, defina `HOST_UID` y `HOST_GID` en `.env` usando la salida de `id -u` e `id -g`.

No exporte globalmente variables de almacenamiento de pruebas como `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH` o `CHROMA_PATH`; Compose interpola primero las variables ya exportadas.

### 3. Preparar los modelos

Con Ollama ya ejecutándose en el host:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

Valores predeterminados:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

O use el servicio Ollama opcional de Compose:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Después configure `OLLAMA_BASE_URL=http://ollama:11434`.

### 4. Iniciar DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

Endpoints predeterminados:

- Aplicación: <http://localhost:8181>
- API: <http://127.0.0.1:8000>
- Documentación OpenAPI: <http://127.0.0.1:8000/docs>

En el primer inicio, cree la cuenta inicial de administrador en el navegador. No se incluyen credenciales predeterminadas.

### 5. Verificar la instalación

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

La respuesta de liveness debe incluir `"ok": true`, la versión de la aplicación y, cuando esté disponible, el commit Git integrado.

Diagnóstico más amplio:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Servicios opcionales

```bash
# Ollama local
docker compose --profile ollama up -d ollama

# Servidor HTTP Chroma (después configure CHROMA_MODE=http)
docker compose --profile chroma up -d chroma

# Mejora inglesa de Document Intelligence con BookNLP
docker compose --profile document-nlp up -d document-nlp

# Superficie de desarrollo Storybook
docker compose --profile dev up storybook
```

Consulte [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) antes de habilitar o instalar paquetes NLP.

### 7. Detener o reconstruir

```bash
docker compose down

# después de actualizar el repositorio
docker compose down
docker compose up -d --build
```

Si una versión anterior dejó archivos propiedad de root dentro de `data/`, ejecute `./scripts/fix-data-permissions.sh` en sistemas Unix compatibles.

## Desarrollo

CI usa Python 3.12 y Node 22.

Entorno backend/tests:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Entorno frontend:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Controles locales rápidos:

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

Use `npm run format:repo` desde `web/` para formatear todos los archivos compatibles con Prettier. Los snapshots HTML del DOM legacy generados se excluyen intencionalmente.

Para cobertura del navegador, Storybook, paridad con CI y reglas de contribución, consulte [CONTRIBUTING.md](CONTRIBUTING.md).

## Mapa del repositorio

- `api/app/` — backend FastAPI: fuentes/corpus, servicios de lectura cELF, GraphQL, realtime, procedencia, pipelines, RAG, proveedores, persistencia y jobs.
- `web/src/` — aplicación Vue 3: vistas, componentes, stores Pinia, router, clientes API, cliente realtime, módulos de dominio y capa de compatibilidad legacy restante.
- `booknlp-worker/` — worker BookNLP opcional y aislado.
- `tests/` — pruebas de backend, regresión, contratos, consistencia de versión y arquitectura.
- `web/tests/frontend/` — pruebas Vitest.
- `web/tests/e2e/` — Playwright, Storybook, accesibilidad y caracterización.
- `docs/` — contratos actuales de arquitectura/dominio y notas históricas de versión.
- `data/` — estado local de ejecución; ignorado por Git salvo placeholders. Nunca confirme su contenido.

## Documentación

- [Guía del usuario](docs/USER_GUIDE.md) — funciones y flujos de trabajo
- [Arquitectura](docs/ARCHITECTURE.md) — límites de ejecución, autoridad, persistencia y flujo
- [Especificación cELF 1.0](SPECIFICATION.md) — modelo normativo y white paper de la implementación de referencia
- [Contexto del proyecto](docs/PROJECT_CONTEXT.md) — justificación académica y capacidades implementadas/intencionadas
- [GraphQL](docs/GRAPHQL.md) — fachada de consultas cELF de solo lectura
- [Realtime](docs/REALTIME.md) — protocolo WebSocket y resincronización
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — análisis lingüístico derivado y paquetes
- [Ingestión de fuentes](docs/INGESTION_VALIDATION.md) — seguridad, límites y fidelidad de extracción
- [Esquemas de metadatos](docs/METADATA_SCHEMAS.md) — contratos configurables de campos
- [Memoria de metadatos](docs/METADATA_MEMORY.md) — precedentes revisados y límites de autoridad
- [Migración FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md) — modelo canónico de afirmaciones
- [CONTRIBUTING.md](CONTRIBUTING.md) y [AGENTS.md](AGENTS.md) — reglas de desarrollo

El historial de versiones está en [CHANGELOG.md](CHANGELOG.md) y `docs/notes/<version>.md`. Las notas de versión son registros históricos, no la descripción de la arquitectura actual.

## Licencia

DerridAI se distribuye bajo la [GNU Affero General Public License v3.0](LICENSE).

Copyright © 2026 Aaron John Schlosser, PhD. La aplicación también muestra © 2026 The New England Transcendental Club of California.
