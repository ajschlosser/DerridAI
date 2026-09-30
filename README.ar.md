<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

![شعار DerridAI](https://repository-images.githubusercontent.com/1336867942/1ef2d928-ee57-480e-addb-5caf6acc1754)

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI بيئة بحث محلية أولاً وتحافظ على المصدرية (provenance)، مخصّصة لبناء المدوّنات البحثية ومراجعتها والبحث فيها والاستعلام عنها. يجمع التطبيق في حاوية Docker واحدة بين استيعاب المصادر، وبناء corpus بمراجعة بشرية، وإثراء metadata مرتبط بالأدلة، وفهارس بحث/متجهات مشتقة، وخط توليد معزّز بالاسترجاع (RAG) قائم على الأدلة.

DerridAI هو أيضاً التطبيق المرجعي الأصلي لمعيار **cELF 1.0 — Capta-Enriched Lexical Format**، وهو بنية معلومات تحفظ المصدرية للبحث الوثائقي المدعوم بالذكاء الاصطناعي. يحافظ التطبيق على هوية المصدر، وهوية السجل ومراجعته، وادعاءات metadata، والأدلة، والادعاءات المولدة وروابط الدعم ككيانات منفصلة قابلة للتدقيق، بدلاً من تسطيحها داخل مخزن متجهي مبهم.

الإصدار الحالي: **0.81.0 — Fall River** ([ملاحظات الإصدار](docs/notes/0.81.0.md)). يصف هذا README بنية فرع `master` الحالية، بما في ذلك الأعمال اللاحقة لـ Exeter التي دُمجت بالفعل في المستودع.

## ما الذي يفعله DerridAI؟

- **اكتساب مصادر غير متجانسة واستيعابها.** يدعم رفع PDF والنص العادي وRTF وDOCX والصور والصوت، واستيراد URL ومحتوى Project Gutenberg، أو استخدام Corpus Capture لاكتشاف الأعمال واكتسابها عبر موائمات مثل Wikidata وProject Gutenberg وWikisource. يطبق الاستيعاب حدود أمان وموارد مناسبة لنوع الوسيط ويحفظ provenance الخاصة بأداة الاستخراج وإصدارها.
- **بناء corpus وفقاً لنوع الوسيط.** يفصل Corpus Builder بين تسجيل المصدر، والاستخراج/النسخ، وربط source units، والبنية/التقسيم، والإثراء، وبناء السجلات، والمراجعة، والنشر. تتكيف عناصر التحكم وإحداثيات الدليل مع الوسيط بدلاً من فرض مفاهيم PDF/الصفحات على كل المصادر.
- **حفظ provenance الخاصة بـ cELF وسلطة الحقول.** تميز سجلات `FieldAssertion` القياسية بين طريقة الاشتقاق، ونتيجة التقييم، والسلطة، وحالة القيمة، والثقة، والدليل، والفاعل/النموذج، وهوية الحقل الثابتة، ومراجعة السجل. لا يمحو التأكيد البشري provenance الأصلية للنموذج أو الإجراء الحتمي.
- **مراجعة السجلات مع إبقاء الأدلة في سياقها.** يستطيع المراجع تعديل النص وmetadata، وفحص `SourceSpan` والأدلة من سجلات أخرى، ومقارنة المراجعات، والتنقل في الخرائط الدلالية والعلاقات، وقبول الاقتراحات أو رفضها، ثم النشر بقرارات قابلة للتدقيق. تستخدم الواجهة حفظاً متفائلاً سريعاً مع تسلسل الكتابات المتعارضة على السجل نفسه.
- **استخدام metadata schemas قابلة للتهيئة وسوابق مراجعة.** تحدد schemas الحقول الثابتة، والأنواع، والقيم المضبوطة، وقواعد الأدلة/المراجعة، وتلميحات POS/NER، ونطاق الحقل، وتعليمات النموذج وسياسة retrieval. تتحول الأمثلة التي راجعها الإنسان إلى سوابق محدودة ومرتبطة بالأدلة للإثراء اللاحق دون أن تستبدل قرارات المراجع القياسية.
- **إضافة Document Intelligence اختيارية.** يمكن لطبقة تحليل مشتقة ومحايدة تجاه المزوّد أن تضيف الكيانات، وcoreference، ومتحدثي الاقتباسات، وعلاقات المحتوى الدلالي. توفر حزم spaCy خط الأساس متعدد اللغات، بينما يتوفر worker معزول من BookNLP كتحسين اختياري للإنجليزية. تبقى هذه التعليقات تحليلاً قابلاً لإعادة البناء، وليست دليلاً مصدرياً أو سلطة على corpus.
- **البحث في projections مشتقة من دون الخلط بينها وبين corpus.** يخزن ChromaDB إسقاطات بحث/دلالة وذاكرات مؤقتة قابلة لإعادة البناء في وضع embedded أو HTTP server. تتوفر آليات dense وlexical وMMR retrieval وRRF والفلاتر وتوجيه اللغة وbounded cross-encoder reranking عند الحاجة.
- **تشغيل Research/RAG قائم على الأدلة.** يدعم Research الاسترجاع الهجين، وreranking، ووضع الأدلة المختارة، وميزانيات الأدلة، والتوليد المتدفق القابل للإلغاء، وعرض الاستشهادات بصورة حتمية، وحفظ claim/support، والتحقق من claims، وذاكرة الاستجابات/الادعاءات، وLLM grading. تُستبعد السجلات ناقصة provenance من الأدلة بدلاً من معاملتها بصمت كدعم صالح.
- **فحص AI pipelines وتهيئتها.** يعرض Pipeline Studio تعريفات pipelines ذات إصدارات، وassignments، وrun traces، ومقاييس latency/error/fallback على مستوى المراحل، وpoint-of-use traces، ومقارنة A/B غير دائمة لـ Research، وتشغيل benchmarks ثابتة الحالات. يمكن جعل مراحل retrieval والذاكرة وmetadata precedents وأدلة المراجع صريحة، مع بقاء حواجز provenance/authority قيوداً بنيوية.
- **فصل وسائل نقل API بحسب المسؤولية.** تتولى REST الأوامر وmutations؛ وتوفر واجهة GraphQL متوافقة مع cELF وللقراءة فقط استعلامات typed؛ ويرسل WebSocket موثّق إشعارات العمليات في الوقت الحقيقي. رسائل realtime ليست أبداً حالة قياسية، ويمكن للعميل إعادة المزامنة عبر REST/GraphQL.
- **دعم بحث متعدد المستخدمين بضوابط واضحة.** تُفرض أدوار Administrator وResearcher المدمجة والأدوار المخصصة الآمنة للباحثين في UI وAPI معاً. يُلخَّص نص المصدر الظاهر للباحث على حدود API، وتكون jobs مقيدة بمالكها، ولا تتاح تعديلات corpus/system الإدارية لغير المسؤولين.
- **جعل العمليات الطويلة قابلة للمراقبة.** تظهر عمليات بناء corpus، ومراجعة LLM، وRAG، وgrading، والاستيراد، والعمل على النماذج/حزم اللغات، وvector upserts كعمليات قابلة للإلغاء مع snapshots/history دائمة وتقدم realtime. إذا انقطع عمل process-local عند إعادة التشغيل يُعلَّم failed بدلاً من إعادة تشغيله سراً.
- **واجهة ميسّرة ومتعددة اللغات.** الإنجليزية والفرنسية الكندية هما واجهتا اللغة الأساسيتان مع فرض تطابق المفاتيح؛ وتتوفر README بلغات أكثر. تشمل معايير الإصدار WCAG 2.2 AA، ولوحة المفاتيح، والتركيز المرئي، وreflow، وتقليل الحركة، وforced colors/high contrast، واختبارات السلاسل الطويلة والترجمة. يقدم Help Center أدلة لكل صفحة، وأسئلة شائعة لسير العمل، ومسرداً بلغة واضحة.
- **نسخ بيئة البحث احتياطياً.** يشمل backup/restore مساحات العمل، وسجل التدقيق، وملفات تعريف المزوّدين، وأصول المصادر، وحالة النظام/provenance، ومجموعات Chroma مع embeddings.

للمرجع الكامل للميزات راجع [دليل المستخدم](docs/USER_GUIDE.md).

## نموذج التتبّع في cELF

يتبع نموذج البيانات البحثي في DerridAI تمييز cELF بين الحالة الوثائقية/البحثية ذات السلطة وبين الإسقاطات الحسابية القابلة لإعادة البناء. عند التتبّع الكامل يكون المسار المفاهيمي:

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

وهذا يسمح بتدقيق الادعاء المولد رجوعاً إلى support والدليل ومراجعة السجل وsource span ثم source document. أما embeddings وretrieval rank وreranker scores وcaches وحالة UI وغيرها من القيم الخاصة بالعملية فتبقى حالة مشتقة، ولا تصبح خصائص ذاتية للسجل المصدر.

راجع [SPECIFICATION.md](SPECIFICATION.md) للاطلاع على مواصفة cELF 1.0 المعيارية والورقة التقنية التفسيرية غير المعيارية الخاصة بـ DerridAI.

## البنية

### خدمات التشغيل

- `web` — Vue 3 وTypeScript وPinia وVue Router وVite وPDF.js وnginx. تطبيق المتصفح؛ يعمل proxy لـ `/api/` ويستهلك REST وGraphQL وإشعارات realtime. Storybook ملف تطوير اختياري.
- `api` — Python 3.12 وFastAPI وStrawberry GraphQL وChromaDB client وPyMuPDF وsentence-transformers وspaCy. الحد التطبيقي ذو السلطة للمصادقة وعمليات المصادر/corpus وcELF reads وprovenance وRAG وpipelines وjobs وحالة النظام.
- `document-nlp` — worker BookNLP اختياري ومعزول لـ Document Intelligence باللغة الإنجليزية. يستقبل نصاً محدوداً ومراجعاً ولا يملك سلطة على corpus.
- `chroma` — خادم HTTP Chroma اختياري. يبقى `PersistentClient` المضمن هو الافتراضي؛ ويخزن الوضعان projections بحث/متجهات مشتقة.
- `ollama` — خدمة Ollama محلية اختيارية. يمكن لـ DerridAI استخدام Ollama العامل مسبقاً على المضيف أو أي endpoint متوافق مع OpenAI.

تبدأ مجموعة Compose الافتراضية خدمتي `web` و`api`؛ أما بقية الخدمات فملفات اختيارية أو مزوّدون خارجيون.

### السلطة والاستمرارية

لا يعامل DerridAI جميع المخازن على أنها متساوية في السلطة:

- **الحالة البحثية القياسية** — أصول المصادر وهويتها، والسجلات ومراجعاتها، وfield assertions، وقرارات المراجعة، وروابط evidence/support الدقيقة، وحالة النشر.
- **حالة الخادم الدائمة** — المصادقة وحالة system/provenance/job/pipeline في SQLite تحت `./data`.
- **الحالة المشتقة القابلة لإعادة البناء** — فهارس Chroma، وembeddings، وإسقاطات metadata examples، وretrieval scores، وإسقاطات المحتوى الدلالي، ومخرجات Document Intelligence، وcaches.
- **حالة workspace في المتصفح** — التفضيلات المحلية والعمل غير المحفوظ، منفصلان عن سلطة corpus.

### فصل وسائل النقل

- **REST**: جميع الأوامر وmutations، بما في ذلك uploads وقرارات المراجعة وjobs والنشر والإدارة وbackup وrestore.
- **GraphQL**: واجهة typed للقراءة فقط ومتوافقة مع cELF على `POST /api/graphql`؛ لا توجد Mutation أو Subscription root.
- **WebSocket**: قناة إشعارات realtime موثّقة على `WS /api/ws/events`؛ ليست أبداً source of truth.

للتفاصيل راجع [Architecture](docs/ARCHITECTURE.md) و[GraphQL](docs/GRAPHQL.md) و[Realtime](docs/REALTIME.md).

## البدء

### 1. المتطلبات

ثبّت Git وDocker Engine/Desktop مع أمر `docker compose`، ووفّر LLM endpoint. تتوقع الإعدادات الافتراضية Ollama على المضيف.

النماذج الافتراضية:

```text
gemma4:e2b
bge-m3:latest
```

### 2. الاستنساخ والإعداد

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

عند استخدام Docker Desktop مع WSL، اضبط `HOST_UID` و`HOST_GID` في `.env` إلى ناتج `id -u` و`id -g`.

لا تصدّر متغيرات تخزين الاختبارات مثل `CHROMA_DATA_ROOT` و`AUTH_DB_PATH` و`SYSTEM_DB_PATH` و`CHROMA_PATH` على مستوى shell؛ لأن Compose يفسر المتغيرات المصدّرة أولاً.

### 3. تجهيز النماذج

إذا كان Ollama يعمل مسبقاً على المضيف:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

القيم الافتراضية:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

أو استخدم خدمة Ollama الاختيارية في Compose:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

ثم اضبط `OLLAMA_BASE_URL=http://ollama:11434`.

### 4. تشغيل DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

العناوين الافتراضية:

- التطبيق: <http://localhost:8181>
- API: <http://127.0.0.1:8000>
- وثائق OpenAPI: <http://127.0.0.1:8000/docs>

عند التشغيل الأول أنشئ حساب المسؤول الأول في المتصفح. لا توجد بيانات دخول افتراضية مرفقة.

### 5. التحقق من التثبيت

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

يجب أن تتضمن استجابة liveness القيمة `"ok": true` وإصدار التطبيق وGit commit المضمّن عند توفره.

للتشخيص الأوسع:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. الخدمات الاختيارية

```bash
# Ollama محلي
docker compose --profile ollama up -d ollama

# خادم Chroma عبر HTTP (ثم اضبط CHROMA_MODE=http)
docker compose --profile chroma up -d chroma

# تحسين BookNLP الإنجليزي لـ Document Intelligence
docker compose --profile document-nlp up -d document-nlp

# بيئة تطوير Storybook
docker compose --profile dev up storybook
```

راجع [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) قبل تفعيل أو تثبيت حزم NLP.

### 7. الإيقاف أو إعادة البناء

```bash
docker compose down

# بعد سحب التحديثات
docker compose down
docker compose up -d --build
```

إذا ترك إصدار قديم ملفات مملوكة لـ root تحت `data/`، شغّل `./scripts/fix-data-permissions.sh` على نظام Unix مدعوم.

## إعداد التطوير

تستخدم CI إصدار Python 3.12 وNode 22.

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

اختبارات الجودة المحلية السريعة:

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

استخدم `npm run format:repo` من `web/` لتنسيق كل ملفات المصدر والإعدادات والوثائق التي يدعمها Prettier. تُستثنى لقطات legacy DOM HTML المولدة عمداً.

للتغطية عبر المتصفح وStorybook والتوافق مع CI وقواعد المساهمة راجع [CONTRIBUTING.md](CONTRIBUTING.md).

## خريطة المستودع

- `api/app/` — FastAPI backend: المصادر/corpus، وخدمات قراءة cELF، وGraphQL، وrealtime، وprovenance، وpipelines، وRAG، والمزوّدون، والاستمرارية، وjobs.
- `web/src/` — تطبيق Vue 3: views وcomponents وPinia stores وrouting وAPI clients وrealtime client ووحدات المجال وطبقة التوافق legacy المتبقية.
- `booknlp-worker/` — BookNLP worker اختياري ومعزول.
- `tests/` — اختبارات backend وregression وcontract وrelease-consistency وarchitecture.
- `web/tests/frontend/` — اختبارات Vitest.
- `web/tests/e2e/` — Playwright وStorybook وaccessibility وcharacterization coverage.
- `docs/` — عقود architecture/domain الحالية وملاحظات الإصدارات التاريخية.
- `data/` — حالة التشغيل المحلية؛ يتجاهلها Git باستثناء placeholders. لا ترفع محتوياتها.

## الوثائق

- [User Guide](docs/USER_GUIDE.md) — الميزات وسير العمل
- [Architecture](docs/ARCHITECTURE.md) — حدود التشغيل والسلطة والاستمرارية وتدفق البيانات
- [cELF 1.0 specification](SPECIFICATION.md) — نموذج المعلومات المعياري وwhite paper للتطبيق المرجعي
- [Project context](docs/PROJECT_CONTEXT.md) — الأساس البحثي والقدرات المنفذة/المقصودة
- [GraphQL](docs/GRAPHQL.md) — واجهة قراءة cELF فقط
- [Realtime](docs/REALTIME.md) — بروتوكول WebSocket وإعادة المزامنة
- [Document Intelligence](docs/DOCUMENT_INTELLIGENCE.md) — التحليل اللغوي المشتق وحزم اللغات
- [Source ingestion](docs/INGESTION_VALIDATION.md) — الأمان والحدود ودقة الاستخراج
- [Metadata schemas](docs/METADATA_SCHEMAS.md) — عقود حقول قابلة للتهيئة
- [Metadata memory](docs/METADATA_MEMORY.md) — السوابق المراجعة وحدود السلطة
- [FieldAssertion migration](docs/FIELD_ASSERTION_MIGRATION.md) — نموذج assertions القياسي
- [CONTRIBUTING.md](CONTRIBUTING.md) و[AGENTS.md](AGENTS.md) — قواعد التطوير

يوجد سجل الإصدارات في [CHANGELOG.md](CHANGELOG.md) و`docs/notes/<version>.md`. ملاحظات الإصدارات سجلات تاريخية وليست وصفاً للبنية الحالية.

## الترخيص

DerridAI مرخّص بموجب [GNU Affero General Public License v3.0](LICENSE).

Copyright © 2026 Aaron John Schlosser, PhD. ويعرض التطبيق أيضاً © 2026 The New England Transcendental Club of California.
