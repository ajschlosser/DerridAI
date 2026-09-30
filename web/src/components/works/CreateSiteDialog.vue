<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { WorksItem } from "../../types/works";
import AppIcon from "../AppIcon.vue";

const props = defineProps<{
  works: WorksItem[];
  storeName: string;
  initialWork?: string;
  busy?: boolean;
  error?: string;
}>();

const emit = defineEmits<{
  cancel: [];
  create: [payload: { title: string; description: string; works: string[] }];
}>();

const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const selected = ref<string[]>(props.initialWork ? [props.initialWork] : []);
const title = ref(props.initialWork || "");
const description = ref("");

const selectedCount = computed(() => selected.value.length);
const canCreate = computed(() => Boolean(selectedCount.value && props.storeName && !props.busy));

function toggle(work: string, checked: boolean) {
  selected.value = checked
    ? [...new Set([...selected.value, work])]
    : selected.value.filter((item) => item !== work);
  if (!title.value.trim() && selected.value.length === 1) title.value = selected.value[0] || "";
}

function selectAll() {
  selected.value = props.works.map((item) => item.work);
}

function clearSelection() {
  selected.value = [];
}

function submit() {
  if (!canCreate.value) return;
  emit("create", {
    title: title.value.trim() || selected.value[0] || "",
    description: description.value.trim(),
    works: [...selected.value],
  });
}

onMounted(async () => {
  await nextTick();
  dialog.value?.showModal();
});
</script>

<template>
  <dialog
    ref="dialog"
    class="create-site-dialog"
    aria-labelledby="create-site-title"
    @cancel.prevent="emit('cancel')"
    @close="emit('cancel')"
  >
    <form method="dialog" class="create-site-shell" @submit.prevent="submit">
      <header class="create-site-header">
        <div>
          <span class="section-label">{{ i18n.t("works.workspace_kicker") }}</span>
          <h2 id="create-site-title">{{ i18n.t("site.create_dialog_title") }}</h2>
          <p>{{ i18n.t("site.create_dialog_help") }}</p>
        </div>
        <button
          type="button"
          class="btn icon-button"
          :aria-label="i18n.t('common.close')"
          @click="emit('cancel')"
        >
          <AppIcon name="close" aria-hidden="true" />
        </button>
      </header>

      <div class="create-site-body">
        <section class="create-site-fields" :aria-label="i18n.t('site.create_dialog_title')">
          <label class="field">
            <span>{{ i18n.t("site.create_title") }}</span>
            <input
              v-model="title"
              class="control"
              maxlength="300"
              :placeholder="i18n.t('site.create_title_placeholder')"
            />
          </label>
          <label class="field">
            <span>{{ i18n.t("site.create_description") }}</span>
            <textarea
              v-model="description"
              class="control"
              maxlength="4000"
              rows="3"
              :placeholder="i18n.t('site.create_description_placeholder')"
            />
          </label>
          <div class="site-store-summary">
            <span>{{ i18n.t("site.create_store") }}</span>
            <strong>{{ props.storeName }}</strong>
            <small>{{ i18n.t("site.create_store_help") }}</small>
          </div>
        </section>

        <fieldset class="site-work-picker">
          <legend>{{ i18n.t("site.create_select_works") }}</legend>
          <div class="site-work-picker-toolbar">
            <span>{{ i18n.tf("site.create_selected_count", { count: selectedCount }) }}</span>
            <div>
              <button type="button" class="btn small" @click="selectAll">
                {{ i18n.t("site.create_select_all") }}
              </button>
              <button type="button" class="btn small" @click="clearSelection">
                {{ i18n.t("site.create_clear") }}
              </button>
            </div>
          </div>
          <div class="site-work-list">
            <label v-for="work in props.works" :key="work.work" class="site-work-option">
              <input
                type="checkbox"
                :checked="selected.includes(work.work)"
                @change="toggle(work.work, ($event.target as HTMLInputElement).checked)"
              />
              <span>
                <strong>{{ work.work }}</strong>
                <small>
                  {{ work.authors.join(", ") }}
                  <template v-if="work.year_label"> · {{ work.year_label }}</template>
                  · {{ work.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records") }}
                </small>
              </span>
            </label>
          </div>
        </fieldset>

        <aside class="site-feature-summary">
          <AppIcon name="spark" aria-hidden="true" />
          <span>
            <strong>{{ i18n.t("site.create_features_title") }}</strong>
            <small>{{ i18n.t("site.create_features_help") }}</small>
          </span>
        </aside>

        <p v-if="props.error" class="site-create-error" role="alert">{{ props.error }}</p>
      </div>

      <footer class="create-site-actions">
        <button type="button" class="btn" :disabled="props.busy" @click="emit('cancel')">
          {{ i18n.t("common.cancel") }}
        </button>
        <button type="submit" class="btn primary" :disabled="!canCreate">
          <AppIcon name="download" aria-hidden="true" />
          {{ props.busy ? i18n.t("site.create_busy") : i18n.t("site.create_action") }}
        </button>
      </footer>
    </form>
  </dialog>
</template>

<style scoped>
.create-site-dialog {
  width: min(58rem, calc(100vw - 2rem));
  max-height: min(90vh, 52rem);
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-card);
  color: var(--text);
  box-shadow: var(--shadow-overlay);
}

.create-site-dialog::backdrop {
  background: color-mix(in srgb, var(--text) 38%, transparent);
}

.create-site-shell {
  display: grid;
  max-height: inherit;
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.create-site-header,
.create-site-actions {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1rem 1.15rem;
  background: var(--surface-raised);
}

.create-site-header {
  border-bottom: 1px solid var(--border);
}

.create-site-header h2 {
  margin: 0.2rem 0 0;
  font-size: 1.45rem;
}

.create-site-header p {
  max-width: 44rem;
  margin: 0.45rem 0 0;
  color: var(--muted);
  line-height: 1.5;
}

.create-site-body {
  display: grid;
  gap: 1rem;
  padding: 1rem 1.15rem;
  overflow: auto;
}

.create-site-fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 0.75fr);
  gap: 0.8rem;
}

.create-site-fields .field:first-child {
  grid-column: 1;
}

.create-site-fields .field:nth-child(2) {
  grid-column: 1;
}

.create-site-fields textarea {
  resize: vertical;
}

.site-store-summary {
  grid-column: 2;
  grid-row: 1 / span 2;
  display: grid;
  align-content: start;
  gap: 0.35rem;
  padding: 0.85rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-raised);
}

.site-store-summary > span,
.site-feature-summary strong {
  font-size: 0.82rem;
  font-weight: 800;
}

.site-store-summary small,
.site-feature-summary small,
.site-work-option small {
  color: var(--muted);
  line-height: 1.45;
}

.site-work-picker {
  min-width: 0;
  margin: 0;
  padding: 0.85rem;
  border: 1px solid var(--border);
  border-radius: 10px;
}

.site-work-picker legend {
  padding: 0 0.35rem;
  font-weight: 800;
}

.site-work-picker-toolbar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
  color: var(--muted);
  font-size: 0.84rem;
}

.site-work-picker-toolbar > div {
  display: flex;
  gap: 0.4rem;
}

.site-work-list {
  display: grid;
  max-height: 18rem;
  gap: 0.35rem;
  overflow: auto;
}

.site-work-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.65rem;
  align-items: start;
  padding: 0.65rem;
  border-radius: 8px;
}

.site-work-option:hover {
  background: var(--surface-raised);
}

.site-work-option input {
  width: 1rem;
  height: 1rem;
  margin-top: 0.2rem;
}

.site-work-option span {
  display: grid;
  min-width: 0;
  gap: 0.15rem;
}

.site-feature-summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.7rem;
  align-items: start;
  padding: 0.85rem;
  border-radius: 10px;
  background: color-mix(in srgb, var(--accent) 7%, var(--surface-raised));
}

.site-feature-summary > svg {
  width: 1.15rem;
  margin-top: 0.15rem;
}

.site-feature-summary span {
  display: grid;
  gap: 0.2rem;
}

.site-create-error {
  margin: 0;
  color: var(--danger);
}

.create-site-actions {
  align-items: center;
  justify-content: flex-end;
  border-top: 1px solid var(--border);
}

@media (max-width: 720px) {
  .create-site-fields {
    grid-template-columns: 1fr;
  }

  .create-site-fields .field,
  .site-store-summary {
    grid-column: 1;
    grid-row: auto;
  }

  .site-work-picker-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
