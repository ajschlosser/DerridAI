<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";
const props=defineProps<{status?:string;method?:string;audit?:boolean}>();
const i18n=useI18nStore();
const kind=computed(()=>{const status=String(props.status||"");if(status==="human_override")return "override";if(status==="human_confirmed")return "human";if(status==="inherited")return "inherited";if(status==="deterministic")return "deterministic";if(status==="llm_inferred")return "llm";if(status==="unresolved"||status==="invalid")return "attention";return "unknown"});
const label=computed(()=>i18n.t(`pdf_corpus.ownership.${kind.value}`,({override:"Override",human:"Human confirmed",inherited:"Inherited",deterministic:"Source derived",llm:"LLM inferred",attention:"Needs review",unknown:"Unclassified"} as Record<string,string>)[kind.value]));
const help=computed(()=>i18n.t(`pdf_corpus.ownership_help.${kind.value}`,({override:"This record deliberately overrides document-level metadata.",human:"A reviewer confirmed this record-level value.",inherited:"Inherited from the document manifest; it may be overridden for this record.",deterministic:"Derived from source structure or deterministic rules.",llm:"Proposed by the language model and retained with provenance.",attention:"This field requires a human decision.",unknown:"No ownership provenance has been recorded."} as Record<string,string>)[kind.value]));
const tone=computed(()=>kind.value==="human"||kind.value==="override"?"success":kind.value==="llm"?"info":kind.value==="attention"?"warning":"neutral");
</script>
<template>
  <span class="ownership-badges">
    <UiStatusBadge :label="label" :help="help" :tone="tone"/>
    <UiStatusBadge v-if="audit&&kind==='llm'" :label="i18n.t('pdf_corpus.ownership.spot_check','Spot check')" :help="i18n.t('pdf_corpus.ownership_help.spot_check','This value was filled in automatically and was picked at random for a quick check. Confirm or correct it.')" tone="warning"/>
  </span>
</template>
<style scoped>.ownership-badges{display:inline-flex;flex-wrap:wrap;gap:.25rem;align-items:center}</style>
