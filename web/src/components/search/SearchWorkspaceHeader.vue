<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { SearchScope } from "../../types/search";

const props=withDefaults(defineProps<{
  scope:SearchScope;
  researcher?:boolean;
  totalLoaded?:number;
  databaseCount?:number;
  selectedEvidence?:number;
  canUseLoaded?:boolean;
}>(),{researcher:false,totalLoaded:0,databaseCount:0,selectedEvidence:0,canUseLoaded:true});
const emit=defineEmits<{
  "update:scope":[scope:SearchScope];
  save:[];
  share:[];
  views:[];
}>();
const i18n=useI18nStore();
const loadedDisabled=computed(()=>props.researcher||!props.canUseLoaded);
</script>

<template>
  <header class="search-workspace-header" aria-labelledby="search-page-title">
    <div class="search-workspace-heading">
      <span class="section-label">{{i18n.t('search.kicker','Corpus exploration')}}</span>
      <h1 id="search-page-title">{{i18n.t('search.title','Search')}}</h1>
      <p>{{i18n.t('search.subtitle','Explore loaded records or search the corpus database without losing the context of your query, filters, and evidence.')}}</p>
    </div>
    <div class="search-workspace-actions" :aria-label="i18n.t('search.view_actions','Search view actions')">
      <button type="button" class="btn" @click="emit('views')"><AppIcon name="history"/>{{i18n.t('search.saved_views','Saved views')}}</button>
      <button type="button" class="btn" @click="emit('save')"><AppIcon name="plus"/>{{i18n.t('search.save_view','Save view')}}</button>
      <button type="button" class="btn soft" @click="emit('share')"><AppIcon name="copy"/>{{i18n.t('search.copy_link','Copy link')}}</button>
    </div>
    <div class="search-scope-row">
      <div class="search-scope-switch" role="group" :aria-label="i18n.t('search.scope','Search scope')">
        <button
          type="button"
          :class="{active:scope==='loaded'}"
          :aria-pressed="scope==='loaded'"
          :disabled="loadedDisabled"
          :title="loadedDisabled?i18n.t('search.loaded_scope_unavailable','Loaded-record search is available to administrators with local JSONL records.') : ''"
          @click="emit('update:scope','loaded')"
        >
          <AppIcon name="list"/>
          <span>{{i18n.t('search.loaded_records','Loaded records')}}</span>
          <small>{{Number(totalLoaded||0).toLocaleString(i18n.locale)}}</small>
        </button>
        <button type="button" :class="{active:scope==='database'}" :aria-pressed="scope==='database'" @click="emit('update:scope','database')">
          <AppIcon name="database"/>
          <span>{{i18n.t('search.corpus_database','Corpus database')}}</span>
          <small>{{Number(databaseCount||0).toLocaleString(i18n.locale)}}</small>
        </button>
      </div>
      <div class="search-workspace-stats" aria-live="polite">
        <span><AppIcon name="spark"/>{{Number(selectedEvidence||0).toLocaleString(i18n.locale)}} {{i18n.t('dynamic.selected_evidence','selected evidence')}}</span>
      </div>
    </div>
  </header>
</template>
