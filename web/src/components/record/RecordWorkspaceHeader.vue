<script setup lang="ts">
import { computed, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  work: string;
  author?: string;
  year?: string | number | null;
  pages?: string;
  recordId?: string;
  position?: string;
  evidenceSelected?: boolean;
  reviewSelected?: boolean;
  canEdit?: boolean;
  canEvidence?: boolean;
  canReview?: boolean;
  canUpsert?: boolean;
  canLlm?: boolean;
  canHistory?: boolean;
  canPdf?: boolean;
  hasHistory?: boolean;
  hasPrevious?: boolean;
  hasNext?: boolean;
}>();
const emit = defineEmits<{
  previous: [];
  next: [];
  edit: [];
  evidence: [];
  review: [];
  copyInline: [];
  copyFull: [];
  copyJson: [];
  upsert: [];
  llm: [];
  ocr: [];
  history: [];
  pdf: [];
}>();
const i18n = useI18nStore();
const menuOpen = ref(false);
const titleClass=computed(()=>{
  const length=String(props.work||"").trim().length;
  if(length>105)return "record-title-xlong";
  if(length>76)return "record-title-long";
  if(length>48)return "record-title-medium";
  return "";
});
function act(fn:()=>void){ menuOpen.value=false; fn(); }
</script>

<template>
  <header class="record-workspace-header">
    <div class="record-workspace-nav" :aria-label="i18n.t('record.navigation','Record navigation')">
      <button type="button" class="record-icon-button" :disabled="!props.hasPrevious" :title="i18n.t('record.previous','Previous record')" @click="emit('previous')">
        <span aria-hidden="true">←</span><span class="sr-only">{{ i18n.t('record.previous','Previous record') }}</span>
      </button>
      <span class="record-position">{{ props.position }}</span>
      <button type="button" class="record-icon-button" :disabled="!props.hasNext" :title="i18n.t('record.next','Next record')" @click="emit('next')">
        <span aria-hidden="true">→</span><span class="sr-only">{{ i18n.t('record.next','Next record') }}</span>
      </button>
    </div>

    <div class="record-identity">
      <p class="record-kicker">{{ i18n.t('record.workspace_kicker','Corpus record') }}</p>
      <h1 :class="titleClass" :title="props.work || i18n.t('record.untitled','Untitled record')">{{ props.work || i18n.t('record.untitled','Untitled record') }}</h1>
      <div class="record-identity-meta">
        <span v-if="props.author">{{ props.author }}</span>
        <span v-if="props.year">{{ props.year }}</span>
        <span v-if="props.pages">{{ props.pages }}</span>
        <span v-if="props.recordId" class="record-id">{{ props.recordId }}</span>
      </div>
    </div>

    <div class="record-header-actions">
      <button v-if="props.canEvidence" type="button" class="record-primary-action" :class="{selected:props.evidenceSelected}" @click="emit('evidence')">
        <AppIcon :name="props.evidenceSelected?'record':'plus'" />
        {{ props.evidenceSelected ? i18n.t('record.evidence_selected','Evidence selected') : i18n.t('record.add_evidence','Add evidence') }}
      </button>
      <button v-if="props.canEdit" type="button" class="record-primary-action" @click="emit('edit')"><AppIcon name="edit" />{{ i18n.t('record.edit','Edit record') }}</button>
      <details class="record-more-menu" :open="menuOpen" @toggle="menuOpen=($event.currentTarget as HTMLDetailsElement).open">
        <summary :aria-label="i18n.t('record.more_actions','More record actions')">•••</summary>
        <div class="record-more-popover">
          <button type="button" @click="act(()=>emit('copyInline'))"><AppIcon name="copy" />{{ i18n.t('record.copy_inline','Copy inline citation') }}</button>
          <button type="button" @click="act(()=>emit('copyFull'))"><AppIcon name="copy" />{{ i18n.t('record.copy_full','Copy full citation') }}</button>
          <button type="button" @click="act(()=>emit('copyJson'))"><AppIcon name="copy" />{{ i18n.t('record.copy_json','Copy record JSON') }}</button>
          <button v-if="props.canReview" type="button" @click="act(()=>emit('review'))"><AppIcon name="plus" />{{ props.reviewSelected?i18n.t('record.remove_selection','Remove from selection'):i18n.t('record.add_selection','Add to selection') }}</button>
          <button v-if="props.canLlm" type="button" @click="act(()=>emit('llm'))"><AppIcon name="spark" />{{ i18n.t('record.review_llm','Review with LLM') }}</button>
          <button v-if="props.canUpsert" type="button" @click="act(()=>emit('upsert'))"><AppIcon name="database" />{{ i18n.t('record.upsert','Upsert record') }}</button>
          <button v-if="props.canEdit" type="button" @click="act(()=>emit('ocr'))"><AppIcon name="broom" />{{ i18n.t('record.clean_ocr','Clean OCR artifacts') }}</button>
          <button v-if="props.canHistory&&props.hasHistory" type="button" @click="act(()=>emit('history'))"><AppIcon name="history" />{{ i18n.t('record.history_undo','History & undo') }}</button>
          <button v-if="props.canPdf" type="button" @click="act(()=>emit('pdf'))"><AppIcon name="pdf" />{{ i18n.t('record.pdf_explorer','Open PDF Explorer') }}</button>
        </div>
      </details>
    </div>
  </header>
</template>

<style scoped>
.record-workspace-header{position:sticky;top:0;z-index:20;display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:18px;align-items:center;padding:14px 18px;border:1px solid var(--line,#dfe6ed);border-radius:16px;background:color-mix(in srgb,#fff 94%,var(--ui-accent-soft,#eef7f1));box-shadow:0 8px 28px rgba(15,23,42,.07);backdrop-filter:blur(14px)}
.record-workspace-nav{display:flex;align-items:center;gap:6px}.record-icon-button{width:38px;height:38px;border:1px solid var(--line,#dfe6ed);border-radius:10px;background:#fff;color:#334155;font-size:17px;cursor:pointer}.record-icon-button:disabled{opacity:.4;cursor:not-allowed}.record-position{min-width:62px;text-align:center;font-size:12px;color:#64748b;font-variant-numeric:tabular-nums}.record-identity{min-width:0}.record-kicker{margin:0 0 2px;color:var(--ui-accent-dark,#286442);font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.record-identity h1{margin:0;max-width:100%;font:600 clamp(22px,2.05vw,31px)/1.12 Georgia,"Times New Roman",serif;letter-spacing:-.018em;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;overflow-wrap:anywhere}.record-identity h1.record-title-medium{font-size:clamp(20px,1.75vw,27px)}.record-identity h1.record-title-long{font-size:clamp(18px,1.55vw,23px);line-height:1.16}.record-identity h1.record-title-xlong{font-size:clamp(17px,1.35vw,21px);line-height:1.18}.record-identity-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:5px;color:#64748b;font-size:12.5px}.record-identity-meta>span+span:before{content:"·";margin-right:8px;color:#a0aab6}.record-id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#7b8797}.record-header-actions{display:flex;align-items:center;gap:8px}.record-primary-action{min-height:38px;display:inline-flex;align-items:center;gap:7px;border:1px solid #ccd8d1;border-radius:10px;background:#fff;padding:0 12px;color:#244335;font-weight:700;cursor:pointer}.record-primary-action.selected{background:var(--ui-accent-soft,#edf7f0);border-color:color-mix(in srgb,var(--ui-accent,#3c8d62) 42%,#ccd8d1)}.record-primary-action :deep(svg){width:16px;height:16px}.record-more-menu{position:relative}.record-more-menu summary{list-style:none;width:38px;height:38px;display:grid;place-items:center;border:1px solid var(--line,#dfe6ed);border-radius:10px;background:#fff;cursor:pointer;font-weight:900;letter-spacing:2px}.record-more-menu summary::-webkit-details-marker{display:none}.record-more-popover{position:absolute;right:0;top:46px;z-index:40;width:250px;padding:7px;border:1px solid var(--line,#dfe6ed);border-radius:12px;background:#fff;box-shadow:0 18px 50px rgba(15,23,42,.16)}.record-more-popover button{width:100%;min-height:38px;display:flex;align-items:center;gap:9px;border:0;border-radius:8px;background:transparent;padding:8px 10px;text-align:left;color:#334155;cursor:pointer}.record-more-popover button:hover,.record-more-popover button:focus-visible{background:#f3f6f5}.record-more-popover :deep(svg){width:16px;height:16px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
button:focus-visible,summary:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 45%,#fff);outline-offset:2px}
@media(max-width:900px){.record-workspace-header{grid-template-columns:1fr auto}.record-workspace-nav{grid-column:1/-1;justify-content:flex-start}.record-identity{min-width:0}.record-primary-action{font-size:0;padding:0;width:40px;justify-content:center}.record-primary-action :deep(svg){width:18px;height:18px}}
</style>
