<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI هو تطبيق Docker يعطي الأولوية للتشغيل المحلي من أجل بناء مجموعات نصية بحثية للفلسفة وتدقيقها والاستعلام عنها. يستوعب مصادر PDF والنصوص/RTF/DOCX والصور والصوت وعناوين URL ومصادر Project Gutenberg ويحوّلها إلى سجلات بحثية تحفظ المصدر والمنشأ؛ ويدعم المراجعة البشرية أو بواسطة نماذج اللغة الكبيرة (LLM) وإثراء البيانات الوصفية المرتبط بالأدلة؛ ويبني إسقاطات بحث مشتقة في ChromaDB؛ ويشغّل فوق النتيجة مسار توليد معزَّز بالاسترجاع (RAG) قائمًا على الأدلة.

الإصدار الحالي: **0.80.0 — Beverly** ([ملاحظات الإصدار](docs/notes/0.80.0.md)).

## الميزات

- **Corpus Builder** — سير عمل متسلسل: المصدر → البنية/النسخ → LLM والإثراء → إنشاء السجلات → المراجعة، وتتكيف عناصر التحكم فيه مع نوع الوسيط المحدد. الاستخراج محدود ويحافظ على المصدر والمنشأ؛ كما تظل تعديلات البنية/النص والأدلة التي يملكها المراجع قابلة للتدقيق.
- **مراجعة السجلات** — مساحات عمل JSONL تتضمن سجل تدقيق، وتحرير بيانات وصفية على دفعات أو على مستوى العمل، وفروقًا، وتنقلًا إلى المصدر/الدليل، وملكية للحقول من قِبل الإنسان أو LLM. تحفظ سجلات `FieldAssertion` القانونية مصدر القيمة وسلطتها والأدلة وهوية الحقل المستقرة، بينما تنتقل البيانات الوصفية المعرّفة بالمخطط عبر المراجعة وSearch وRecord Inspector وعمليات touch-up وعرض Research.
- **مراجعة وأدوات LLM** — عمليات في الواجهة وفي الخلفية وعمليات Auto-improve في الخلفية باستخدام ملفات تعريف مسماة لموفري Ollama أو مزودين متوافقين مع OpenAI، ولكل ملف حد تزامن وحالة تهيئة خاصة به.
- **مخازن المتجهات** — مجموعات ChromaDB دائمة على نظام الملفات المحلي أو على خادم Chroma قيد التشغيل، مع مرايا لغوية إنجليزية/فرنسية وعمليات upsert في الخلفية ودعم التحويل ذهابًا وإيابًا مع JSONL.
- **RAG Research** — استرجاع هجين، وإعادة ترتيب باستخدام cross-encoder، وتوجيه لغوي، ووضع الأدلة المحددة، وتوليد متدفق قابل للإلغاء، وذاكرة لمصدر الإجابات والادعاءات، وResponse Library مخزنة مؤقتًا، وتقييم بواسطة LLM.
- **الأدوار** — حسابات Admin وResearcher؛ يرى الباحثون نصًا موجزًا للأدلة ولا يمكنهم تعديل المجموعات النصية.
- **النسخ الاحتياطي والاستعادة** — ملف ZIP واحد يضم مساحات العمل وسجل التدقيق وملفات تعريف الموفرين وأصول مصادر المجموعة النصية وكل مجموعة Chroma مع embeddings الخاصة بها.
- **ثنائي اللغة ومتاح** — الإنجليزية والفرنسية الكندية لغتان من الدرجة الأولى مع فرض تطابق المفاتيح. ويُعد الوصول بلوحة المفاتيح ووضوح التركيز والسلوك المتجاوب وإعادة التدفق ودعم forced-colors وWCAG 2.2 AA من معايير القبول.

راجع [دليل المستخدم](docs/USER_GUIDE.md) للحصول على مرجع كامل للميزات.

## البنية

<!-- prettier-ignore -->
| الخدمة      | التقنيات                                                            | ملاحظات                                                                                                                                          |
| ----------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js، ويقدمه nginx    | يمرر `/api/` إلى API؛ ويتوفر Storybook كخدمة تطوير اختيارية                                                                                    |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | توجد ملفات corpus/build الموثوقة وحالة SQLite للمصادقة/النظام/المصدر تحت `./data`؛ ويحتفظ Chroma بإسقاطات البحث/النتائج المشتقة                    |
| خلفية LLM   | Ollama (افتراضيًا) أو أي endpoint متوافق مع OpenAI                  | تعمل على المضيف أو في مكان آخر؛ وليست جزءًا من حزمة Compose الافتراضية                                                                           |

لحدود ملكية الشفرة والتخزين الدائم، راجع [البنية](docs/ARCHITECTURE.md).

## البدء

هذه الخطوات هي المسار المدعوم انطلاقًا من نسخة checkout نظيفة. وقد كُتبت بتفصيل متعمد حتى يتمكن مطور جديد من تكرارها من دون الاعتماد على دليل بيانات DerridAI موجود مسبقًا أو بيئة shell مهيأة.

### 1. المتطلبات المسبقة

ثبّت Git وDocker Engine/Desktop مع الأمر `docker compose` ونقطة نهاية LLM. تتوقع الإعدادات الافتراضية تشغيل Ollama على المضيف.

نماذج Ollama الافتراضية هي:

```text
gemma4:e2b
bge-m3:latest
```

إذا كنت تستخدم نموذج Ollama مختلفًا أو موفرًا متوافقًا مع OpenAI، فعدّل `.env` قبل تشغيل DerridAI.

### 2. الاستنساخ والإعداد

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

المكافئ في PowerShell:

```powershell
Copy-Item .env.example .env
```

على Docker Desktop مع WSL، عيّن `HOST_UID` و`HOST_GID` في `.env` إلى ناتج `id -u` و`id -g`. يضمن ذلك بقاء ملفات Chroma/SQLite المركبة بواسطة bind مملوكة لمستخدم المضيف.

لا تصدّر متغيرات تخزين اختبار DerridAI مثل `CHROMA_DATA_ROOT` أو `AUTH_DB_PATH` أو `SYSTEM_DB_PATH` أو `CHROMA_PATH` بصورة عامة في shell. يقوم Compose بإحلال المتغيرات المصدرة قبل تمرير القيم من الملف إلى الحاوية.

### 3. إتاحة النماذج المضبوطة

إذا كان Ollama يعمل بالفعل على المضيف:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

يستخدم ملف `.env.example` الافتراضي:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

بدلًا من ذلك، استخدم خدمة Ollama الاختيارية في Compose:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

ثم عيّن `OLLAMA_BASE_URL=http://ollama:11434` في `.env`.

### 4. التحقق من إعدادات Compose وتشغيل DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

العناوين الافتراضية هي: التطبيق <http://localhost:8181>، وAPI على <http://127.0.0.1:8000>، ووثائق API على <http://127.0.0.1:8000/docs>.

عند التشغيل لأول مرة، يطلب DerridAI إنشاء حساب المسؤول الأول. ولا تُشحن أي بيانات اعتماد افتراضية.

### 5. التحقق من التثبيت

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

ينبغي أن تعيد نقطة النهاية live بيانات JSON تحتوي على `"ok": true` وإصدار التطبيق وGit commit المضمَّن عند توفره. كما ينبغي أن تظهر خدمتا `web` و`api` بحالة healthy في `docker compose ps`.

لتشخيص محلي أوسع:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. الإيقاف أو إعادة البناء

أوقف التطبيق من دون حذف دليل `./data` المركب بواسطة bind:

```bash
docker compose down
```

أعد البناء بعد جلب التغييرات:

```bash
docker compose down
docker compose up -d --build
```

إذا ترك إصدار أقدم ملفات مملوكة للمستخدم root تحت `data/`، فشغّل `./scripts/fix-data-permissions.sh` على المضيفات الشبيهة بـ Unix والمدعومة.

## إعداد التطوير

تستخدم CI الإصدار Python 3.12 وNode 22؛ استخدم هذه الإصدارات محليًا عند إعادة إنتاج الأعطال.

بيئة backend/tests:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

بيئة frontend:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

شغّل فحوصات الجودة المحلية السريعة من جذر المستودع:

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

استخدم `npm run format:repo` من `web/` لتنسيق جميع ملفات المصدر والإعداد والوثائق التي يدعمها Prettier في المستودع. ويُستبعد عمدًا HTML المُنشأ الخاص بلقطات DOM القديمة.

لتغطية المتصفح وStorybook والتطابق مع CI وقواعد المساهمة، راجع [CONTRIBUTING.md](CONTRIBUTING.md).

## خريطة المستودع

- `api/app/` — تطبيق FastAPI، واستيعاب/مراجعة المجموعة النصية، والمصدر، والتخزين الدائم، وRAG، والموفرون، والمهام الخلفية.
- `web/src/` — تطبيق Vue، ومكونات قابلة لإعادة الاستخدام، ووحدات المجال، وstores، وطبقة توافق runtime القديمة الآخذة في التقلص.
- `tests/` — اختبارات backend/regression/contract.
- `web/tests/frontend/` — اختبارات Vitest للمكونات/المجال.
- `web/tests/e2e/` — تغطية Playwright للتطبيق وStorybook وإمكانية الوصول واختبارات characterization القديمة.
- `docs/` — عقود البنية/المجال الحالية إضافة إلى ملاحظات الإصدارات التاريخية تحت `docs/notes/`.
- `data/` — حالة التشغيل المحلية؛ يتجاهلها Git باستثناء العناصر النائبة. لا تقم أبدًا بعمل commit لمحتوياتها.

## الوثائق

ابدأ بالمستندات التي تصف السلوك الحالي:

- [دليل المستخدم](docs/USER_GUIDE.md) — مرجع الميزات والعمليات والنسخ الاحتياطي والقيود
- [البنية](docs/ARCHITECTURE.md) — حدود التشغيل والسلطة والتخزين الدائم وتدفق البيانات
- [سياق المشروع](docs/PROJECT_CONTEXT.md) — الأساس البحثي والقدرات المنفذة مقارنة بالقدرات المقصودة
- [المساهمة](CONTRIBUTING.md) — إعداد المطور البشري وفحوصات الجودة وقواعد التغيير
- [AGENTS.md](AGENTS.md) — قواعد إضافية لوكلاء البرمجة
- عقود متخصصة: [استيعاب المصادر](docs/INGESTION_VALIDATION.md)، و[مخططات البيانات الوصفية](docs/METADATA_SCHEMAS.md)، و[ترحيل FieldAssertion](docs/FIELD_ASSERTION_MIGRATION.md)، و[ذاكرة البيانات الوصفية](docs/METADATA_MEMORY.md)، و[رموز التصميم](docs/DESIGN_TOKENS.md)، و[توطين fr-CA](docs/LOCALIZATION_FR_CA.md)

يوجد سجل الإصدارات في [CHANGELOG.md](CHANGELOG.md) و`docs/notes/<version>.md`. ملاحظات الإصدارات الخاصة بكل نسخة هي سجلات تاريخية؛ وليست وثائق للبنية الحالية أو قائمة العمل المتراكم.

## الترخيص

لا يوجد حاليًا ملف ترخيص مضمَّن. تحمل ملفات المصدر النص `Copyright 2026 Aaron John Schlosser, PhD.`. وتعرض شاشة تسجيل الدخول وقائمة الحساب والإعدادات → حول DerridAI النص `© 2026 The New England Transcendental Club of California`.
