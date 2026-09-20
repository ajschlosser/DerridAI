<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import type { LanguageInfo } from "../../api/system";
import type { UiMenuItem } from "../ui/UiMenu.vue";
import { useI18nStore } from "../../stores/i18n";
import { useMatchMedia } from "../../composables/useMatchMedia";
import TopbarAccount from "./TopbarAccount.vue";
import TopbarHelp from "./TopbarHelp.vue";
import TopbarLocale from "./TopbarLocale.vue";
import TopbarWorkspace from "./TopbarWorkspace.vue";

const props = withDefaults(
  defineProps<{
    isAdmin?: boolean;
    canFaq?: boolean;
    canSettings?: boolean;
    username: string;
    role: string;
    roleName?: string;
    fileCount?: number;
    flagged?: number;
    languages?: LanguageInfo[];
    locale?: string;
    localeLoading?: boolean;
  }>(),
  {
    isAdmin: false,
    canFaq: false,
    canSettings: true,
    roleName: "",
    fileCount: 0,
    flagged: 0,
    languages: () => [],
    locale: "en-US",
    localeLoading: false,
  },
);
const emit = defineEmits<{
  import: [files: FileList];
  action: [id: string];
  navigate: [view: string];
  logout: [];
  locale: [code: string];
}>();

const i18n = useI18nStore();
const compact = useMatchMedia("(max-width: 650px)");
const helpOpen = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const workspaceItems = computed<UiMenuItem[]>(() => {
  if (!props.isAdmin) return [];
  const needFiles = (key: string, fallback: string) =>
    props.fileCount ? undefined : i18n.t(key, fallback);
  const items: UiMenuItem[] = [
    { id: "open", label: i18n.t("ui.open_jsonl", "Open JSONL"), icon: "upload" },
    {
      id: "merge",
      label: i18n.t("ui.merge_tabs", "Merge tabs"),
      icon: "plus",
      reason:
        props.fileCount < 2
          ? i18n.t("ui.need_two_tabs_merge", "Load at least two JSONL tabs to merge them.")
          : undefined,
    },
    {
      id: "subset",
      label: i18n.t("ui.create_subset", "Create subset"),
      icon: "filter",
      reason: needFiles("ui.need_records_subset", "Load JSONL records before creating a subset."),
    },
    {
      id: "bulk",
      label: i18n.t("ui.bulk_edit", "Bulk edit field"),
      icon: "edit",
      reason: needFiles("ui.need_records_bulk_edit", "Load JSONL records before bulk editing."),
    },
    {
      id: "ocr",
      label: i18n.t("ui.clean_ocr", "Clean OCR Artifacts"),
      icon: "broom",
      reason: needFiles("ui.need_records_ocr", "Load JSONL records before cleaning OCR artifacts."),
    },
  ];
  if (props.flagged) {
    items.push({
      id: "flagged",
      label: i18n.t("ui.review_flagged", "Review flagged"),
      icon: "spark",
    });
  }
  items.push({
    id: "export",
    label: i18n.t("ui.export", "Export"),
    icon: "download",
    reason: needFiles("ui.need_records_export", "Load JSONL records before exporting."),
  });
  return items;
});

function onWorkspace(id: string) {
  if (id === "open") {
    fileInput.value?.click();
    return;
  }
  emit("action", id);
}
function onFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files?.length) emit("import", input.files);
  input.value = "";
}
</script>
<template>
  <div class="topbar-chrome">
    <input
      id="fileInput"
      ref="fileInput"
      type="file"
      accept=".jsonl,.ndjson,.json"
      multiple
      hidden
      @change="onFiles"
    />
    <TopbarWorkspace v-if="isAdmin && !compact" :items="workspaceItems" @select="onWorkspace" />
    <TopbarHelp
      v-model:open="helpOpen"
      :show-trigger="!compact"
      :can-faq="canFaq"
      :can-settings="canSettings"
      @navigate="emit('navigate', $event)"
    />
    <TopbarLocale
      v-if="!compact"
      :languages="languages"
      :locale="locale"
      :loading="localeLoading"
      @select="emit('locale', $event)"
    />
    <TopbarAccount
      :username="username"
      :role="role"
      :role-name="roleName"
      :is-admin="isAdmin"
      :compact="compact"
      :can-settings="canSettings"
      :languages="languages"
      :locale="locale"
      :locale-loading="localeLoading"
      :workspace-items="workspaceItems"
      @logout="emit('logout')"
      @help="helpOpen = true"
      @navigate="emit('navigate', $event)"
      @locale="emit('locale', $event)"
      @workspace="onWorkspace"
    />
  </div>
</template>
<style scoped>
.topbar-chrome {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
