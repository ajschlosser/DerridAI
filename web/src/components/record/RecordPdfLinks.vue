<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { RecordPdfLink } from "../../types/record";
const props = withDefaults(
  defineProps<{
    links: RecordPdfLink[];
    canManage?: boolean;
    canOpen?: boolean;
    pdfLoaded?: boolean;
    currentPdf?: string;
  }>(),
  { canManage: false, canOpen: false, pdfLoaded: false, currentPdf: "" },
);
const emit = defineEmits<{
  open: [index: number];
  remove: [index: number];
  removeAll: [];
  explorer: [];
  linkCurrent: [];
}>();
const i18n = useI18nStore();
</script>
<template>
  <section class="record-pdf-panel" aria-labelledby="recordPdfHeading">
    <header>
      <div>
        <p>{{ i18n.t("record.source_documents") }}</p>
        <h3 id="recordPdfHeading">{{ i18n.t("record.pdf_links") }}</h3>
      </div>
      <span>{{ props.links.length }}</span>
    </header>
    <div v-if="props.links.length" class="pdf-link-list">
      <article v-for="(link, index) in props.links" :key="`${link.pdf_file}-${link.pdf_page}`">
        <div class="pdf-link-icon"><AppIcon name="pdf" /></div>
        <div class="pdf-link-copy">
          <strong>{{ link.pdf_file }}</strong
          ><span>{{ i18n.tf("record.pdf_page", { page: link.pdf_page }) }}</span>
        </div>
        <div class="pdf-link-actions">
          <button v-if="props.canOpen" type="button" @click="emit('open', index)">
            {{ i18n.t("record.open_page") }}</button
          ><button
            v-if="props.canManage"
            type="button"
            class="danger"
            @click="emit('remove', index)"
          >
            {{ i18n.t("ui.remove") }}
          </button>
        </div>
      </article>
    </div>
    <div v-else class="pdf-empty">
      <p>{{ i18n.t("record.no_pdf_links") }}</p>
    </div>
    <footer>
      <button v-if="props.canOpen" type="button" @click="emit('explorer')">
        <AppIcon name="pdf" />{{ i18n.t("record.pdf_explorer") }}</button
      ><button v-if="props.canManage && props.pdfLoaded" type="button" @click="emit('linkCurrent')">
        {{ i18n.t("record.link_current_pdf") }}</button
      ><button
        v-if="props.canManage && props.links.length > 1"
        type="button"
        class="danger"
        @click="emit('removeAll')"
      >
        {{ i18n.t("record.remove_all_pdf") }}
      </button>
    </footer>
  </section>
</template>
<style scoped>
.record-pdf-panel {
  display: grid;
  gap: 13px;
}
.record-pdf-panel > header {
  display: flex;
  justify-content: space-between;
  align-items: end;
}
.record-pdf-panel > header p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.record-pdf-panel h3 {
  margin: 2px 0 0;
  font-size: 1rem;
}
.record-pdf-panel > header > span {
  min-width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--soft);
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
}
.pdf-link-list {
  display: grid;
  gap: 8px;
}
.pdf-link-list article {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--card);
}
.pdf-link-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: var(--soft);
  color: var(--text-2);
}
.pdf-link-icon :deep(svg) {
  width: 17px;
  height: 17px;
}
.pdf-link-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.pdf-link-copy strong {
  font-size: 0.78125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pdf-link-copy span {
  color: var(--muted);
  font-size: 0.8125rem;
}
.pdf-link-actions {
  display: flex;
  gap: 5px;
}
.pdf-link-actions button,
.record-pdf-panel footer button {
  min-height: 32px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  padding: 0 8px;
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
}
.pdf-link-actions button.danger,
.record-pdf-panel footer button.danger {
  border-color: var(--tone-danger-edge);
  color: var(--tone-danger-fg);
}
.pdf-empty {
  padding: 14px;
  border: 1px dashed var(--line);
  border-radius: 10px;
  background: var(--card);
  color: var(--muted);
  font-size: 0.78125rem;
}
.pdf-empty p {
  margin: 0;
}
.record-pdf-panel footer {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.record-pdf-panel footer button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.record-pdf-panel footer :deep(svg) {
  width: 15px;
  height: 15px;
}
button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 520px) {
  .pdf-link-list article {
    grid-template-columns: 36px minmax(0, 1fr);
  }
  .pdf-link-actions {
    grid-column: 1/-1;
    justify-content: flex-end;
  }
}
</style>
