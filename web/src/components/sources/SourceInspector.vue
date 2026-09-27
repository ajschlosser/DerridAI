<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { corpusSourcesApi, type SourceDetail } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { languageList, languageName } from "../../domain/languages";
import { enumLabel, enumTone } from "../../domain/sourceLabels";
import { hasPages } from "../../domain/sourceMedia";
import AppIcon from "../AppIcon.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

/**
 * Side panel describing one source from `GET /api/corpus/sources/{id}`: identity, language,
 * provider, provenance and processing. It never loads the source text. Page facts are shown
 * only for paged media.
 */
const props = withDefaults(
  defineProps<{
    sourceId: string;
    /** A preloaded detail (stories/tests); skips the request. */
    detail?: SourceDetail | null;
    captureLabels?: Record<string, string>;
  }>(),
  { detail: null, captureLabels: () => ({}) },
);
const emit = defineEmits<{ close: [] }>();
const i18n = useI18nStore();
const t = (key: string, fallback?: string) => i18n.t(key, fallback);
const loaded = ref<SourceDetail | null>(null);
const loading = ref(false);
const error = ref("");
const copied = ref(false);

const source = computed(() => props.detail || loaded.value);
const catalog = computed<Record<string, unknown>>(() => source.value?.catalog_metadata || {});
const initial = computed<Record<string, unknown>>(() => source.value?.initial_metadata || {});
const paged = computed(() => hasPages(source.value?.media_kind || "pdf"));

function text(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (typeof value === "object") return "";
  return String(value);
}
function formatDate(value: unknown) {
  const raw = text(value);
  if (!raw) return "";
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(raw));
  } catch {
    return raw;
  }
}
function codes(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : text(value) ? [text(value)] : [];
}

type Row = { key: string; label: string; value: string; mono?: boolean; href?: string };
const sections = computed<Array<{ id: string; title: string; rows: Row[] }>>(() => {
  const s = source.value;
  if (!s) return [];
  const c = catalog.value;
  const row = (key: string, value: string, extra: Partial<Row> = {}): Row => ({
    key,
    label: i18n.t(`sources.inspector.${key}`),
    value,
    ...extra,
  });
  const provider = text(c.provider) || (s.source_url ? "web" : "upload");
  const documentLanguages = codes(c.document_languages).length
    ? codes(c.document_languages)
    : codes(c.language || initial.value.language);
  const extraction = s.extraction_provenance || {};
  const identity = [
    row("source_title", text(c.title || initial.value.title) || s.filename),
    row("author", text(c.document_author || initial.value.document_author)),
    row("filename", s.filename),
    row("work", text(c.canonical_work_id || c.wikidata_work_id)),
    row("edition_item", text(c.wikidata_edition_id)),
    row(
      "relationship",
      c.relationship_to_work ? enumLabel(t, "relationship", text(c.relationship_to_work)) : "",
    ),
    row("role", c.contribution_role ? enumLabel(t, "role", text(c.contribution_role)) : ""),
    row("translator", text(c.translator)),
    row("edition", text(c.edition || initial.value.edition)),
  ];
  const language = [
    row("document_languages", languageList(documentLanguages, i18n.locale)),
    row(
      "original_language",
      c.original_language ? languageName(text(c.original_language), i18n.locale) : "",
    ),
    row(
      "project",
      c.source_project_language ? languageName(text(c.source_project_language), i18n.locale) : "",
    ),
  ];
  const providerRows = [
    row("provider", enumLabel(t, "provider", provider)),
    row("provider_item", text(c.provider_item_id || c.gutenberg_id)),
    row("source_url", text(s.source_url), { href: text(s.source_url) || undefined }),
    row("rights", text(c.rights_status)),
    row("retrieved_at", formatDate(c.retrieved_at)),
  ];
  const provenance = [
    row("sha256", s.sha256, { mono: true }),
    row("added", formatDate(s.created_at)),
    row("discovery_method", text(c.discovery_method)),
    row("extractor", text(extraction.extractor || extraction.tool)),
    row("extractor_version", text(extraction.version || extraction.tool_version)),
    row("revision", text(c.wikisource_revision_id)),
    row("derived_from", text(s.derived_from_asset_id)),
  ];
  const processing = [
    row("media", s.media_kind ? i18n.t(`pdf_corpus.media_kind.${s.media_kind}`, s.media_kind) : ""),
    row("units", s.block_count != null ? Number(s.block_count).toLocaleString(i18n.locale) : ""),
    ...(paged.value
      ? [
          row(
            "pages",
            s.page_count != null ? Number(s.page_count).toLocaleString(i18n.locale) : "",
          ),
          row(
            "ocr_pages",
            s.ocr_pages != null ? Number(s.ocr_pages).toLocaleString(i18n.locale) : "",
          ),
        ]
      : []),
  ];
  return [
    { id: "identity", title: i18n.t("sources.inspector.identity"), rows: identity },
    { id: "language", title: i18n.t("sources.inspector.language"), rows: language },
    { id: "provider", title: i18n.t("sources.inspector.provider_section"), rows: providerRows },
    { id: "provenance", title: i18n.t("sources.inspector.provenance"), rows: provenance },
    { id: "processing", title: i18n.t("sources.inspector.processing"), rows: processing },
  ].map((section) => ({ ...section, rows: section.rows.filter((item) => item.value) }));
});

/** A build's raw status as the Sources build state (the same mapping the source list uses). */
function buildState(status: string) {
  if (["completed", "published"].includes(status)) return "built";
  if (status === "failed") return "failed";
  if (status === "cancelled") return "not_built";
  return "building";
}

async function load() {
  if (props.detail || !props.sourceId) return;
  loading.value = true;
  error.value = "";
  try {
    loaded.value = await corpusSourcesApi.sourceDetail(props.sourceId);
  } catch (cause) {
    loaded.value = null;
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    loading.value = false;
  }
}
async function copyHash() {
  if (!source.value) return;
  try {
    await navigator.clipboard.writeText(source.value.sha256);
    copied.value = true;
    setTimeout(() => (copied.value = false), 1600);
  } catch {
    copied.value = false;
  }
}
watch(() => props.sourceId, load, { immediate: true });
</script>

<template>
  <aside class="source-inspector" :aria-labelledby="`inspector-${sourceId}`" :aria-busy="loading">
    <header class="si-head">
      <h3 :id="`inspector-${sourceId}`">
        {{ source ? text(catalog.title) || source.filename : i18n.t("sources.inspector.title") }}
      </h3>
      <button
        type="button"
        class="btn small icon-only"
        :aria-label="i18n.t('common.close')"
        @click="emit('close')"
      >
        <AppIcon name="close" />
      </button>
    </header>
    <p v-if="loading" role="status" class="si-state">{{ i18n.t("sources.loading") }}</p>
    <p v-else-if="error" role="alert" class="si-error">
      <AppIcon name="warning" />{{ i18n.tf("sources.load_failed", { error }) }}
    </p>
    <template v-else-if="source">
      <section v-for="section in sections" :key="section.id" class="si-section">
        <h4>{{ section.title }}</h4>
        <dl>
          <div v-for="item in section.rows" :key="item.key" :data-fact="item.key">
            <dt>{{ item.label }}</dt>
            <dd :class="{ mono: item.mono }">
              <a v-if="item.href" :href="item.href" target="_blank" rel="noopener noreferrer">{{
                item.value
              }}</a>
              <template v-else>{{ item.value }}</template>
              <button
                v-if="item.key === 'sha256'"
                type="button"
                class="btn small quiet"
                @click="copyHash"
              >
                {{ copied ? i18n.t("sources.inspector.copied") : i18n.t("sources.inspector.copy") }}
              </button>
            </dd>
          </div>
        </dl>
        <p v-if="section.id === 'language' && !section.rows.length" class="si-muted">
          {{ i18n.t("sources.language_unknown") }}
        </p>
        <template v-if="section.id === 'provenance'">
          <h5>{{ i18n.t("sources.inspector.captures") }}</h5>
          <ul v-if="source.captures.length" class="si-list">
            <li v-for="link in source.captures" :key="`${link.capture_id}-${link.candidate_id}`">
              <strong>{{
                captureLabels[link.capture_id] ||
                link.author_name ||
                i18n.t("sources.filter.capture_unnamed")
              }}</strong>
              <small
                >{{ enumLabel(t, "provider", link.provider) }} · {{ link.provider_item_id }} ·
                {{ formatDate(link.acquired_at) }}</small
              >
            </li>
          </ul>
          <p v-else class="si-muted">{{ i18n.t("sources.inspector.no_captures") }}</p>
        </template>
        <template v-if="section.id === 'processing'">
          <h5>{{ i18n.t("sources.inspector.builds") }}</h5>
          <ul v-if="source.builds.length" class="si-list">
            <li v-for="build in source.builds" :key="build.build_id">
              <UiStatusBadge
                :label="enumLabel(t, 'build_status', buildState(build.status))"
                :tone="enumTone('build_status', buildState(build.status))"
              />
              <small
                >{{ formatDate(build.created_at) }}
                <template v-if="build.record_count != null">
                  · {{ i18n.tf("sources.inspector.records", { count: build.record_count }) }}
                </template></small
              >
            </li>
          </ul>
          <p v-else class="si-muted">{{ i18n.t("sources.inspector.no_builds") }}</p>
        </template>
      </section>
    </template>
  </aside>
</template>

<style scoped>
.source-inspector {
  display: grid;
  align-content: start;
  gap: 14px;
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-raised);
  color: var(--text-primary);
}
.si-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.si-head h3 {
  margin: 0;
  font-size: var(--fs-lg);
  overflow-wrap: anywhere;
}
.si-section h4 {
  margin: 0 0 6px;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.si-section h5 {
  margin: 10px 0 4px;
  font-size: var(--fs-sm);
}
.si-section dl {
  display: grid;
  gap: 6px;
  margin: 0;
}
.si-section dl > div {
  display: grid;
  grid-template-columns: minmax(110px, 40%) minmax(0, 1fr);
  gap: 8px;
}
.si-section dt {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.si-section dd {
  margin: 0;
  font-size: var(--fs-sm);
  overflow-wrap: anywhere;
}
.si-section dd.mono {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}
.si-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.si-list li {
  display: grid;
  gap: 2px;
}
.si-list small,
.si-muted,
.si-state {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.si-error {
  display: flex;
  gap: 6px;
  color: var(--tone-danger-fg);
}
</style>
