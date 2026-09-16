<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
const props = defineProps<{ hostPath: string; containerPath: string }>();
const i18n = useI18nStore();
</script>
<template>
  <section class="storybook-storage-card">
    <header><div><h3>{{ i18n.t("storage.settings","Storage settings") }}</h3><p>{{ i18n.t("storage.review_chroma","Review where Chroma data is stored.") }}</p></div><span>{{ i18n.t("storage.persistent","Persistent storage") }}</span></header>
    <div class="storybook-storage-grid"><div><small>{{ i18n.t("storage.host_folder","Host folder") }}</small><code>{{ props.hostPath }}</code><p>{{ i18n.t("storage.host_folder_help","Persistent folder on the machine running DerridAI.") }}</p></div><div><small>{{ i18n.t("storage.container_path","Container path") }}</small><code>{{ props.containerPath }}</code><p>{{ i18n.t("storage.container_path_help","Corresponding path inside the DerridAI service.") }}</p></div></div>
    <details><summary>{{ i18n.t("storage.change_location","Change data location") }} <span>{{ i18n.t("ui.advanced","Advanced") }}</span></summary><div><label>{{ i18n.t("storage.new_container_path","New container path") }}<input :value="props.containerPath"></label><button type="button">{{ i18n.t("storage.apply_path","Apply path") }}</button></div></details>
  </section>
</template>
