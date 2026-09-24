<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiDialog from "./ui/UiDialog.vue";
import UiButton from "./ui/UiButton.vue";

type Convention={value:unknown;confirmed_records:number};
type Example={record_id:string;value:unknown;similarity:number;excerpt:string};
const props=withDefaults(defineProps<{open:boolean;memory?:{conventions?:Record<string,Convention>;examples?:Record<string,Example[]>;reset_at?:string|null;convention_count?:number;example_count?:number};busy?:boolean}>(),{memory:()=>({}),busy:false});
const emit=defineEmits<{close:[];reset:[]}>();
const i18n=useI18nStore();
const conventions=computed(()=>Object.entries(props.memory?.conventions||{}));
const examples=computed(()=>Object.entries(props.memory?.examples||{}));
function display(value:unknown){if(Array.isArray(value))return value.join(", ");if(value===true)return i18n.t("ui.yes");if(value===false)return i18n.t("ui.no");return value==null?"—":String(value)}
</script>
<template>
<UiDialog :open="open" :title="i18n.t('pdf_corpus.editorial_memory_title')" :description="i18n.t('pdf_corpus.editorial_memory_help')" size="large" @close="emit('close')">
  <div class="memory-body">
    <section class="memory-summary" aria-live="polite"><div><b>{{Number(memory?.convention_count||0)}}</b><span>{{i18n.t('pdf_corpus.editorial_conventions')}}</span></div><div><b>{{Number(memory?.example_count||0)}}</b><span>{{i18n.t('pdf_corpus.editorial_examples')}}</span></div></section>
    <section v-if="conventions.length" aria-labelledby="editorial-conventions-title"><h3 id="editorial-conventions-title">{{i18n.t('pdf_corpus.editorial_conventions_title')}}</h3><div class="memory-list"><article v-for="([field,item]) in conventions" :key="field"><div><b>{{i18n.t(`record.${field}`,field.replaceAll('_',' '))}}</b><span>{{display(item.value)}}</span></div><small>{{i18n.tf('pdf_corpus.confirmed_on_records', {count:item.confirmed_records})}}</small></article></div></section>
    <section v-if="examples.length" aria-labelledby="editorial-examples-title"><h3 id="editorial-examples-title">{{i18n.t('pdf_corpus.editorial_examples_title')}}</h3><div class="memory-list"><template v-for="([field,items]) in examples" :key="field"><article v-for="item in items" :key="`${field}-${item.record_id}`"><div><b>{{i18n.t(`record.${field}`,field.replaceAll('_',' '))}}</b><span>{{display(item.value)}}</span></div><p>{{item.excerpt}}</p><small>{{item.record_id}} · {{Math.round(Number(item.similarity||0)*100)}}% {{i18n.t('pdf_corpus.similarity')}}</small></article></template></div></section>
    <p v-if="!conventions.length&&!examples.length" class="empty-note">{{i18n.t('pdf_corpus.editorial_memory_empty')}}</p>
    <p v-if="memory?.reset_at" class="reset-note">{{i18n.tf('pdf_corpus.editorial_memory_reset_at', {time:String(memory.reset_at)})}}</p>
  </div>
  <template #footer><div class="footer-actions"><UiButton :label="i18n.t('ui.close')" @click="emit('close')"/><UiButton variant="danger" :disabled="busy||(!conventions.length&&!examples.length)" :label="i18n.t('pdf_corpus.reset_editorial_memory')" @click="emit('reset')"/></div></template>
</UiDialog>
</template>
<style scoped>
.memory-body{display:grid;gap:18px}.memory-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.memory-summary>div{display:grid;gap:3px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.memory-summary b{font-size:1.25rem}.memory-summary span,.memory-list small,.reset-note,.empty-note{font-size:.8125rem;color:var(--muted);line-height:1.5}.memory-body h3{margin:0 0 8px;font-size:1rem}.memory-list{display:grid;gap:8px}.memory-list article{display:grid;gap:6px;padding:11px;border:1px solid var(--line);border-radius:10px;background:var(--card)}.memory-list article>div{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}.memory-list p{margin:0;font-size:.875rem;line-height:1.5}.footer-actions{display:flex;justify-content:flex-end;gap:8px}@media(max-width:640px){.memory-summary{grid-template-columns:1fr}.memory-list article>div{display:grid}.footer-actions{flex-direction:column-reverse}}
</style>
