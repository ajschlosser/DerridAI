<script setup lang="ts">
import { computed, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { SearchFacet } from "../../types/search";

const props=withDefaults(defineProps<{facets:SearchFacet[];compact?:boolean}>(),{compact:false});
const emit=defineEmits<{toggle:[field:string,value:string];clear:[]}>();
const i18n=useI18nStore();
const filter=ref("");
const visibleFacets=computed(()=>{
  const q=filter.value.trim().toLocaleLowerCase();
  if(!q)return props.facets;
  return props.facets.map(facet=>({...facet,values:facet.values.filter(item=>item.label.toLocaleLowerCase().includes(q))})).filter(facet=>facet.values.length||facet.label.toLocaleLowerCase().includes(q));
});
const activeCount=computed(()=>props.facets.reduce((sum,facet)=>sum+facet.values.filter(item=>item.selected).length,0));
</script>

<template>
  <aside class="search-facets" :class="{compact}" :aria-label="i18n.t('search.filters','Filters')">
    <div class="search-facets-head">
      <div><span class="section-label">{{i18n.t('search.refine','Refine')}}</span><h2>{{i18n.t('search.filters','Filters')}}</h2></div>
      <button v-if="activeCount" type="button" class="text-button" @click="emit('clear')">{{i18n.t('search.clear_all','Clear all')}} ({{activeCount}})</button>
    </div>
    <label class="search-facet-find">
      <span class="sr-only">{{i18n.t('search.filter_facets','Filter facet values')}}</span>
      <AppIcon name="search"/>
      <input v-model="filter" type="search" :placeholder="i18n.t('search.filter_values','Filter values…')" />
    </label>
    <div v-if="visibleFacets.length" class="search-facet-groups">
      <details v-for="(facet,index) in visibleFacets" :key="facet.field" class="search-facet-group" :open="index<4||facet.values.some(item=>item.selected)">
        <summary><span>{{facet.label}}</span><span class="search-facet-active-count" v-if="facet.values.some(item=>item.selected)">{{facet.values.filter(item=>item.selected).length}}</span></summary>
        <div class="search-facet-values">
          <label v-for="item in facet.values" :key="`${facet.field}:${item.value}`" class="search-facet-option" :class="{selected:item.selected}">
            <input type="checkbox" :checked="item.selected" @change="emit('toggle',facet.field,item.value)" />
            <span class="search-facet-label" :title="item.label">{{item.label}}</span>
            <span class="search-facet-count">{{item.count.toLocaleString(i18n.locale)}}</span>
          </label>
        </div>
      </details>
    </div>
    <p v-else class="search-facet-empty">{{i18n.t('search.no_facet_values','No facet values match this filter.')}}</p>
  </aside>
</template>

<style scoped>
.search-facet-empty {
  margin: 12px 0;
  color: var(--muted);
  font-size: .8125rem;
  line-height: 1.45;
}
</style>
