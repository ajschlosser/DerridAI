<script setup lang="ts">
import { ref } from "vue";
import { useI18nStore } from "../stores/i18n";
const props = defineProps<{ quote:string; recordLabel?:string }>();
const emit = defineEmits<{ save:[payload:{note:string;tags:string[]}]; cancel:[] }>();
const i18n=useI18nStore();
const note=ref(""); const tags=ref("");
function save(){emit("save",{note:note.value.trim(),tags:tags.value.split(",").map(v=>v.trim()).filter(Boolean)})}
</script>
<template>
  <aside class="annotation-selection-component" role="dialog" :aria-label="i18n.t('annotations.annotate_selection','Annotate selection')">
    <header><div><b>{{ i18n.t('annotations.annotate_selection','Annotate selection') }}</b><small v-if="props.recordLabel">{{ props.recordLabel }}</small></div><button type="button" class="btn icon-only" :aria-label="i18n.t('ui.close','Close')" @click="emit('cancel')">×</button></header>
    <blockquote>{{ props.quote }}</blockquote>
    <label class="field"><span>{{ i18n.t('annotations.note','Note') }}</span><textarea v-model="note" class="control" :placeholder="i18n.t('annotations.note_placeholder','Add a note about this selection…')"></textarea></label>
    <label class="field"><span>{{ i18n.t('annotations.tags','Tags') }}</span><input v-model="tags" class="control" :placeholder="i18n.t('annotations.tags_placeholder','Comma-separated tags')"></label>
    <footer><button type="button" class="btn" @click="emit('cancel')">{{ i18n.t('ui.cancel','Cancel') }}</button><button type="button" class="btn primary" @click="save">{{ i18n.t('annotations.save','Save annotation') }}</button></footer>
  </aside>
</template>
