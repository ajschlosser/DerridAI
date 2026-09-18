<script setup lang="ts">
import { computed } from "vue";
import type { ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";

const props=withDefaults(defineProps<{
  profiles:ProviderProfile[];
  activeProfileId:string;
  activeModel?:string;
  disabled?:boolean;
  history?:Array<{at?:string;provider_profile_id?:string;provider?:string;model?:string;metadata_completed?:number;note?:string}>;
}>(),{activeModel:"",disabled:false,history:()=>[]});
const emit=defineEmits<{change:[profileId:string]}>();
const i18n=useI18nStore();
const activeProfile=computed(()=>props.profiles.find(profile=>profile.id===props.activeProfileId)||null);
const label=computed(()=>activeProfile.value?.name||props.activeProfileId||i18n.t("pdf_corpus.provider_default","Provider default"));
function onChange(event:Event){const value=(event.target as HTMLSelectElement).value;if(value&&value!==props.activeProfileId)emit("change",value)}
</script>

<template>
<section class="provider-switcher" aria-labelledby="corpus-provider-switcher-title">
  <div class="provider-switcher-copy">
    <span class="eyebrow">{{i18n.t('pdf_corpus.live_enrichment','Live enrichment')}}</span>
    <b id="corpus-provider-switcher-title">{{i18n.t('pdf_corpus.enrichment_profile','Enrichment profile')}}</b>
    <span>{{i18n.t('pdf_corpus.enrichment_profile_help','Changing profiles affects newly scheduled metadata tasks. Requests already running finish with the model that started them.')}}</span>
  </div>
  <label class="provider-switcher-control">
    <span class="sr-only">{{i18n.t('pdf_corpus.enrichment_profile','Enrichment profile')}}</span>
    <select class="control" :value="activeProfileId" :disabled="disabled||profiles.length<2" @change="onChange">
      <option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{profile.name||profile.id}} · {{profile.model||i18n.t('pdf_corpus.model_not_set','model not set')}}</option>
    </select>
    <small><b>{{label}}</b><template v-if="activeModel"> · <code>{{activeModel}}</code></template></small>
  </label>
  <details v-if="history.length>1" class="provider-history">
    <summary>{{i18n.t('pdf_corpus.provider_history','Profile history')}}</summary>
    <ol>
      <li v-for="(item,index) in history.slice().reverse().slice(0,8)" :key="`${item.at||index}-${item.provider_profile_id||index}`">
        <b>{{item.provider_profile_id||item.provider||'—'}}</b>
        <span v-if="item.model">{{item.model}}</span>
        <span v-if="item.metadata_completed!==undefined">{{i18n.tf('pdf_corpus.profile_switched_after_records','after {count} enriched record(s)',{count:item.metadata_completed})}}</span>
      </li>
    </ol>
  </details>
</section>
</template>

<style scoped>
.provider-switcher{display:grid;grid-template-columns:minmax(220px,1fr) minmax(260px,420px) auto;align-items:center;gap:14px;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.provider-switcher-copy{display:grid;gap:3px;min-width:0}.provider-switcher-copy>b{font-size:.9375rem}.provider-switcher-copy>span:last-child{color:var(--muted);font-size:.8125rem;line-height:1.45;max-width:72ch}.eyebrow{font-size:.8125rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:800}.provider-switcher-control{display:grid;gap:4px}.provider-switcher-control small{font-size:.8125rem;color:var(--muted);overflow-wrap:anywhere}.provider-history{font-size:.8125rem}.provider-history summary{min-height:40px;display:flex;align-items:center;cursor:pointer;font-weight:750}.provider-history ol{position:absolute;z-index:20;right:18px;width:min(420px,calc(100vw - 36px));margin:6px 0 0;padding:12px 12px 12px 30px;border:1px solid var(--line);border-radius:10px;background:var(--card);box-shadow:0 14px 38px rgb(0 0 0/.18)}.provider-history li{padding:4px 0}.provider-history li span{display:block;color:var(--muted)}.provider-switcher :is(select,summary):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:900px){.provider-switcher{grid-template-columns:1fr}.provider-history ol{position:static;width:auto}}
</style>
