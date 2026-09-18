<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
const props=withDefaults(defineProps<{sourceFilename?:string;model?:string|null;buildId?:string;accepted?:number;reviewable?:number;remaining?:number;issues?:number;focusDisabled?:boolean}>(),{sourceFilename:"",model:"",buildId:"",accepted:0,reviewable:0,remaining:0,issues:0,focusDisabled:false});
const emit=defineEmits<{focus:[]} >();const i18n=useI18nStore();
</script>
<template>
<section class="review-session" aria-labelledby="review-session-title">
  <div class="review-identity"><span class="eyebrow">{{i18n.t('pdf_corpus.review_mode','Record review')}}</span><b id="review-session-title">{{props.sourceFilename}}</b><small>{{props.model||i18n.t('pdf_corpus.provider_default','Provider default')}}<template v-if="props.buildId"> · {{props.buildId}}</template></small></div>
  <dl class="review-stats">
    <div><dd>{{props.accepted}}</dd><dt>{{i18n.t('pdf_corpus.accepted_label','accepted')}}</dt></div>
    <div><dd>{{props.reviewable}}</dd><dt>{{i18n.t('pdf_corpus.queue_ready','Reviewable')}}</dt></div>
    <div><dd>{{props.remaining}}</dd><dt>{{i18n.t('pdf_corpus.remaining','remaining')}}</dt></div>
    <div><dd>{{props.issues}}</dd><dt>{{i18n.t('pdf_corpus.need_attention','need attention')}}</dt></div>
  </dl>
  <UiButton size="small" :label="i18n.t('pdf_corpus.focus_view','Focus view')" :disabled="props.focusDisabled" @click="emit('focus')"/>
</section>
</template>
<style scoped>
.review-session{position:sticky;top:0;z-index:12;display:grid;grid-template-columns:minmax(220px,1fr) auto auto;gap:18px;align-items:center;padding:12px 16px;border:1px solid var(--line);border-radius:12px;background:color-mix(in srgb,var(--panel) 97%,transparent);backdrop-filter:blur(8px);box-shadow:var(--shadow-sm,0 4px 16px rgb(0 0 0/.04))}.review-identity{display:grid;gap:2px;min-width:0}.review-identity b{font-size:.9375rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.review-identity small{font-size:.8125rem;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.eyebrow{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}.review-stats{display:flex;gap:4px;margin:0}.review-stats>div{min-width:74px;padding:6px 9px;text-align:center;border-inline-start:1px solid var(--line)}.review-stats dd{margin:0;font-size:1rem;font-weight:850}.review-stats dt{font-size:.75rem;color:var(--muted);line-height:1.25}@media(max-width:1100px){.review-session{grid-template-columns:1fr auto}.review-stats{grid-column:1/-1;justify-content:flex-start}.review-stats>div:first-child{border-inline-start:0}}@media(max-width:700px){.review-session{position:static;grid-template-columns:1fr;gap:10px}.review-stats{display:grid;grid-template-columns:repeat(2,1fr)}.review-stats>div{border:0;background:var(--panel-2,var(--soft));border-radius:8px}.review-identity b,.review-identity small{white-space:normal}}
</style>
