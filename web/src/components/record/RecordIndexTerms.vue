<script setup lang="ts">
import { ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
const props=withDefaults(defineProps<{title:string;field:string;values:string[];editable?:boolean}>(),{editable:false});
const emit=defineEmits<{search:[field:string,value:string];change:[field:string,values:string[]]} >();
const i18n=useI18nStore();
const draft=ref("");
function add(){const value=draft.value.trim();if(!value)return;const exists=props.values.some(item=>item.localeCompare(value,undefined,{sensitivity:'accent'})===0);if(exists){draft.value='';return}emit('change',props.field,[...props.values,value]);draft.value=''}
function remove(index:number){emit('change',props.field,props.values.filter((_,i)=>i!==index))}
</script>
<template>
  <section class="record-index-terms">
    <header><h3>{{props.title}}</h3><span>{{props.values.length}}</span></header>
    <div class="record-index-chip-list">
      <span v-for="(value,index) in props.values" :key="`${value}-${index}`" class="record-index-chip">
        <button type="button" class="record-index-search" @click="emit('search',props.field,value)">{{value}}</button>
        <button v-if="props.editable" type="button" class="record-index-remove" :aria-label="i18n.tf('record.remove_term','Remove {value}',{value})" @click="remove(index)">×</button>
      </span>
      <span v-if="!props.values.length" class="record-index-empty">{{i18n.t('ui.none','None')}}</span>
    </div>
    <div v-if="props.editable" class="record-index-add"><label><span class="sr-only">{{i18n.tf('record.add_term','Add {label}',{label:props.title})}}</span><input v-model="draft" :placeholder="i18n.tf('record.add_term','Add {label}',{label:props.title.toLocaleLowerCase()})" @keydown.enter.prevent="add"></label><button type="button" :disabled="!draft.trim()" @click="add">{{i18n.t('ui.add','Add')}}</button></div>
  </section>
</template>
<style scoped>
.record-index-terms{display:grid;gap:11px}.record-index-terms header{display:flex;justify-content:space-between;align-items:center}.record-index-terms h3{margin:0;font-size:13px}.record-index-terms header>span{min-width:26px;height:26px;display:grid;place-items:center;border-radius:999px;background:#eef3f0;color:#596d61;font-size:.8125rem;font-weight:800}.record-index-chip-list{display:flex;flex-wrap:wrap;gap:7px;align-items:flex-start}.record-index-chip{display:inline-flex;width:auto;max-width:100%;align-items:stretch;border:1px solid #d7e4dc;border-radius:999px;background:#f4f9f6;overflow:hidden}.record-index-search{display:inline-flex;width:auto;max-width:100%;min-height:32px;align-items:center;border:0;background:transparent;padding:5px 10px;color:#2e4a3b;font-size:12.5px;font-weight:700;white-space:normal;overflow-wrap:anywhere;text-align:left;cursor:pointer}.record-index-remove{width:31px;min-width:31px;min-height:31px;border:0;border-left:1px solid #d7e4dc;background:transparent;color:#67776d;cursor:pointer}.record-index-search:hover,.record-index-search:focus-visible,.record-index-remove:hover,.record-index-remove:focus-visible{background:#eaf4ee}.record-index-empty{color:#778497;font-size:12.5px}.record-index-add{display:flex;gap:7px}.record-index-add label{flex:1}.record-index-add input{width:100%;min-height:36px;border:1px solid #dce4df;border-radius:9px;padding:0 10px;font-size:13px}.record-index-add>button{min-height:36px;border:1px solid #d6e0da;border-radius:9px;background:#fff;padding:0 11px;color:#34503f;font-weight:800;cursor:pointer}.record-index-add>button:disabled{opacity:.45;cursor:not-allowed}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}button:focus-visible,input:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 42%,#fff);outline-offset:2px}
</style>
