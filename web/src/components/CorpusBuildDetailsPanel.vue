<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, ref, useId, watch } from 'vue';
import { useI18nStore } from '../stores/i18n';
import UiDialog from './ui/UiDialog.vue';
const props=defineProps<{buildId:string;sourceFilename:string;warningCount:number;dockTarget?:HTMLElement|null}>();
const emit=defineEmits<{openChange:[open:boolean]}>();
const i18n=useI18nStore();
const open=ref(false);
const selected=ref<'activity'|'issues'|'settings'>('activity');
const tabs=['activity','issues','settings'] as const;
const visited=ref(new Set<string>());
const id=useId();
const tablist=ref<HTMLElement|null>(null);
function label(tab:typeof tabs[number]){return i18n.t(`pdf_corpus.details_${tab}`,{activity:'Activity',issues:'Issues',settings:'Settings'}[tab])}
function setOpen(value:boolean){open.value=value;if(!value)visited.value.clear();emit('openChange',value)}
function selectTab(tab:typeof tabs[number]){selected.value=tab;visited.value.add(tab)}
function show(tab:typeof tabs[number]){selectTab(tab);setOpen(true)}
async function navigate(event:KeyboardEvent){
  const index=tabs.indexOf(selected.value);
  const next=event.key==='Home'?0:event.key==='End'?2:event.key==='ArrowRight'?(index+1)%3:event.key==='ArrowLeft'?(index+2)%3:-1;
  if(next<0)return;
  event.preventDefault();selectTab(tabs[next]);
  await nextTick();tablist.value?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
}
defineExpose({close:()=>setOpen(false)});
watch(()=>props.buildId,()=>{setOpen(false);selected.value='activity';visited.value.clear()});
</script>
<template>
  <div class="build-details-launchers">
    <button type="button" class="btn" :aria-haspopup="dockTarget ? undefined : 'dialog'" :aria-expanded="open" @click="show('activity')">{{i18n.t('pdf_corpus.details_title','Build details')}}</button>
    <button v-if="warningCount" type="button" class="btn issues-trigger" :aria-haspopup="dockTarget ? undefined : 'dialog'" :aria-expanded="open&&selected==='issues'" @click="show('issues')">{{i18n.tf('pdf_corpus.warnings_count','{count} build warning(s)',{count:warningCount})}}</button>
  </div>
  <UiDialog v-if="open" :dock-target="dockTarget" placement="side" :title="i18n.t('pdf_corpus.details_title','Build details')" :description="sourceFilename" :close-label="i18n.t('common.close','Close')" @close="setOpen(false)">
    <div ref="tablist" role="tablist" :aria-label="i18n.t('pdf_corpus.details_title','Build details')" class="details-tabs" @keydown="navigate">
      <button v-for="tab in tabs" :id="`${id}-${tab}`" :key="tab" type="button" role="tab" :aria-selected="selected===tab" :aria-controls="`${id}-${tab}-panel`" :tabindex="selected===tab?0:-1" @click="selectTab(tab)">{{label(tab)}}</button>
    </div>
    <template v-for="tab in tabs" :key="tab">
      <section :hidden="selected!==tab" :id="`${id}-${tab}-panel`" role="tabpanel" :aria-labelledby="`${id}-${tab}`" tabindex="0" class="details-content">
        <slot v-if="visited.has(tab)" :name="tab" />
      </section>
    </template>
  </UiDialog>
</template>
<style scoped>
.build-details-launchers{display:flex;gap:8px;flex-wrap:wrap}.btn{min-height:40px;white-space:normal}.issues-trigger{background:var(--tone-warn-bg);color:var(--tone-warn-fg);border-color:var(--tone-warn-border)}
.details-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}.details-tabs button{flex:1;min-height:44px;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--text);font-size:.875rem;cursor:pointer}.details-tabs button[aria-selected="true"]{border-color:var(--accent);font-weight:700;background:var(--soft)}
.details-content[hidden]{display:none}.details-content{display:grid;gap:14px;min-width:0;overflow-wrap:anywhere;font-size:.875rem}.details-content :deep(>* ){min-width:0;max-width:100%}.details-content :deep(pre){white-space:pre-wrap;overflow-wrap:anywhere}.btn:focus-visible,.details-tabs button:focus-visible,.details-content:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.details-content :deep(.provider-switcher),.details-content :deep(.switch-controls){grid-template-columns:minmax(0,1fr)}.details-content :deep(.switch-controls input),.details-content :deep(.switch-controls select){width:100%;min-width:0}.details-content :deep(.provider-history ol){position:static;width:auto}
</style>
