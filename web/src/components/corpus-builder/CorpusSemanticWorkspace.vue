<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
/**
 * One entry point for the build's semantic views: the entities-and-relationships map and the
 * reviewer-stated identities that shape it. A slim trigger sits where the two disclosures used to,
 * so opening it never pushes the review queue down; the panels live in a dialog and load only when
 * their tab is first shown. The server serves repeat reads from its cached graph, so reopening is quick.
 */
import { computed, ref } from "vue";
import type { SemanticContentGraph } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";
import UiTabs from "../ui/UiTabs.vue";
import CorpusSemanticAliasPanel from "./CorpusSemanticAliasPanel.vue";
import CorpusSemanticGraphPanel from "./CorpusSemanticGraphPanel.vue";

const props = defineProps<{
  buildId: string;
  summary?: SemanticContentGraph["summary"] | null;
  disabled?: boolean;
}>();
const emit = defineEmits<{ refreshed: []; changed: [] }>();
const i18n = useI18nStore();

const open = ref(false);
const tab = ref("graph");
// A tab's panel is mounted the first time it is shown and then kept (v-show) while the dialog
// is open, so its filters, focus and loaded data survive switching tabs.
const visited = ref(new Set<string>());
const tabs = computed(() => [
  { id: "graph", label: i18n.t("pdf_corpus.semantic_graph_title") },
  { id: "identities", label: i18n.t("pdf_corpus.semantic_aliases.title") },
]);
const counts = computed(() =>
  props.summary
    ? i18n.tf("pdf_corpus.semantic_graph_summary", {
        nodes: Number(props.summary.nodes || 0).toLocaleString(i18n.locale || undefined),
        edges: Number(props.summary.edges || 0).toLocaleString(i18n.locale || undefined),
      })
    : "",
);

function show(next: string) {
  tab.value = next;
  visited.value.add(next);
  visited.value = new Set(visited.value);
}
function openDialog() {
  visited.value = new Set();
  show(tab.value);
  open.value = true;
}
</script>

<template>
  <div class="semantic-workspace-bar">
    <UiButton
      size="small"
      :label="i18n.t('pdf_corpus.semantic_workspace_open')"
      aria-haspopup="dialog"
      @click="openDialog"
    />
    <span v-if="counts" class="semantic-workspace-counts">{{ counts }}</span>
  </div>
  <UiDialog
    v-if="open"
    open
    size="xlarge"
    :title="i18n.t('pdf_corpus.semantic_workspace_title')"
    :close-label="i18n.t('ui.close')"
    @close="open = false"
  >
    <UiTabs
      :model-value="tab"
      :tabs="tabs"
      :tablist-label="i18n.t('pdf_corpus.semantic_workspace_title')"
      id-prefix="semantic-workspace"
      @update:model-value="show"
    />
    <div
      v-if="visited.has('graph')"
      v-show="tab === 'graph'"
      id="semantic-workspace-panel-graph"
      class="semantic-workspace-panel"
      role="tabpanel"
      aria-labelledby="semantic-workspace-tab-graph"
    >
      <CorpusSemanticGraphPanel
        embedded
        :build-id="props.buildId"
        :summary="props.summary"
        :disabled="props.disabled"
        @refreshed="emit('refreshed')"
      />
    </div>
    <div
      v-if="visited.has('identities')"
      v-show="tab === 'identities'"
      id="semantic-workspace-panel-identities"
      class="semantic-workspace-panel"
      role="tabpanel"
      aria-labelledby="semantic-workspace-tab-identities"
    >
      <CorpusSemanticAliasPanel
        embedded
        :build-id="props.buildId"
        :disabled="props.disabled"
        @changed="emit('changed')"
      />
    </div>
  </UiDialog>
</template>

<style scoped>
.semantic-workspace-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}
.semantic-workspace-counts {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.semantic-workspace-panel {
  min-height: 24rem;
  padding-top: var(--space-3);
}
</style>
