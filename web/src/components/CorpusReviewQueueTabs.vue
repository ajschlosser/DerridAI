<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";

export type ReviewQueue = "all"|"pending"|"attention"|"metadata"|"accepted"|"rejected";
const props=defineProps<{modelValue:ReviewQueue;total:number;pending:number;attention:number;metadata:number;accepted:number;rejected:number;disabled?:boolean}>();
const emit=defineEmits<{"update:modelValue":[value:ReviewQueue]}>();
const i18n=useI18nStore();
const tabs:Array<{id:ReviewQueue;key:string;fallback:string;count:keyof Pick<typeof props,"total"|"pending"|"attention"|"metadata"|"accepted"|"rejected">}>=[
  {id:"all",key:"pdf_corpus.queue_all",fallback:"All",count:"total"},
  {id:"pending",key:"pdf_corpus.queue_pending",fallback:"Pending",count:"pending"},
  {id:"attention",key:"pdf_corpus.queue_attention",fallback:"Needs attention",count:"attention"},
  {id:"metadata",key:"pdf_corpus.queue_metadata",fallback:"Metadata",count:"metadata"},
  {id:"accepted",key:"pdf_corpus.queue_accepted",fallback:"Accepted",count:"accepted"},
  {id:"rejected",key:"pdf_corpus.queue_rejected",fallback:"Rejected",count:"rejected"},
];
</script>

<template>
  <div class="queue-tabs" role="tablist" :aria-label="i18n.t('pdf_corpus.review_queue','Review queue')">
    <button v-for="tab in tabs" :key="tab.id" type="button" role="tab" class="queue-tab"
      :aria-selected="modelValue===tab.id" :tabindex="modelValue===tab.id?0:-1" :disabled="disabled"
      @click="emit('update:modelValue',tab.id)">
      <span>{{i18n.t(tab.key,tab.fallback)}}</span><strong>{{props[tab.count]}}</strong>
    </button>
  </div>
</template>

<style scoped>
.queue-tabs{display:flex;align-items:center;gap:4px;flex-wrap:wrap}.queue-tab{min-height:34px;border:1px solid transparent;border-radius:999px;background:transparent;color:var(--muted);padding:5px 9px;display:flex;align-items:center;gap:6px;cursor:pointer;font-size:10px;font-weight:700}.queue-tab strong{min-width:20px;padding:1px 5px;border-radius:999px;background:var(--soft);color:var(--text);font-size:9px;text-align:center}.queue-tab[aria-selected="true"]{background:var(--card);border-color:var(--line);color:var(--text);box-shadow:0 1px 2px rgb(0 0 0/.04)}.queue-tab:focus-visible{outline:3px solid var(--accent);outline-offset:2px}.queue-tab:disabled{opacity:.55;cursor:not-allowed}
</style>
