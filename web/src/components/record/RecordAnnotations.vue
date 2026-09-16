<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import type { RecordAnnotationItem } from "../../types/record";
const props=withDefaults(defineProps<{annotations:RecordAnnotationItem[];canAdd?:boolean}>(),{canAdd:false});
const emit=defineEmits<{add:[];remove:[id:string]} >();
const i18n=useI18nStore();
function dateLabel(value?:string|null){if(!value)return '';const date=new Date(value);return Number.isNaN(date.getTime())?String(value):new Intl.DateTimeFormat(i18n.locale,{dateStyle:'medium',timeStyle:'short'}).format(date)}
</script>
<template>
  <section class="record-annotations-panel" aria-labelledby="recordAnnotationsHeading">
    <header><div><p>{{i18n.t('annotations.record_notes','Annotations')}}</p><h3 id="recordAnnotationsHeading">{{i18n.t('annotations.record_annotations','Record annotations')}}</h3></div><div class="annotation-header-actions"><span>{{props.annotations.length}}</span><button v-if="props.canAdd" type="button" @click="emit('add')">+ {{i18n.t('annotations.add_note','Add note')}}</button></div></header>
    <div v-if="props.annotations.length" class="annotation-list">
      <article v-for="annotation in props.annotations" :key="annotation.id" class="annotation-card">
        <div class="annotation-card-top"><span>{{annotation.field}}</span><time v-if="annotation.created_at">{{dateLabel(annotation.created_at)}}</time></div>
        <blockquote v-if="annotation.quote">{{annotation.quote}}</blockquote>
        <p v-if="annotation.note">{{annotation.note}}</p>
        <div v-if="annotation.tags.length" class="annotation-tags"><span v-for="tag in annotation.tags" :key="tag">{{tag}}</span></div>
        <footer><strong>{{annotation.author}}</strong><button v-if="annotation.removable" type="button" @click="emit('remove',annotation.id)">{{i18n.t('ui.remove','Remove')}}</button></footer>
      </article>
    </div>
    <div v-else class="annotation-empty"><strong>{{i18n.t('annotations.none_record','No annotations on this record yet')}}</strong><p>{{i18n.t('annotations.none_record_help','Select text in the reading pane to attach a note or tags.')}}</p></div>
  </section>
</template>
<style scoped>
.record-annotations-panel{display:grid;gap:14px}.record-annotations-panel>header{display:flex;justify-content:space-between;align-items:end;gap:12px}.record-annotations-panel>header p{margin:0;color:#64748b;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.record-annotations-panel h3{margin:2px 0 0;font-size:16px}.annotation-header-actions{display:flex;align-items:center;gap:7px}.annotation-header-actions>span{min-width:28px;height:28px;display:grid;place-items:center;border-radius:999px;background:#eef3f0;color:#596c60;font-size:11px;font-weight:800}.annotation-header-actions button{min-height:32px;border:1px solid #d7e0da;border-radius:8px;background:#fff;padding:0 9px;color:#365142;font-weight:800;cursor:pointer}.annotation-list{display:grid;gap:10px}.annotation-card{display:grid;gap:9px;border:1px solid #dfe6e2;border-radius:12px;background:#fff;padding:12px}.annotation-card-top{display:flex;justify-content:space-between;gap:10px;align-items:center}.annotation-card-top>span{padding:3px 7px;border-radius:999px;background:#edf6f0;color:#355843;font-size:10.5px;font-weight:800;text-transform:uppercase}.annotation-card time{color:#788496;font-size:11px}.annotation-card blockquote{margin:0;padding:9px 10px;border-left:3px solid var(--ui-accent,#3c8d62);border-radius:0 7px 7px 0;background:#f7f9f8;color:#39483f;font:13px/1.55 Georgia,"Times New Roman",serif}.annotation-card>p{margin:0;color:#34433a;font-size:13px;line-height:1.55}.annotation-tags{display:flex;gap:5px;flex-wrap:wrap}.annotation-tags span{padding:3px 7px;border-radius:999px;background:#eef2f0;color:#52645a;font-size:11px}.annotation-card footer{display:flex;justify-content:space-between;align-items:center;gap:8px;color:#68768a;font-size:11.5px}.annotation-card footer strong{font-weight:700}.annotation-card footer button{min-height:30px;border:0;border-radius:7px;background:#fff0f0;padding:0 8px;color:#9b3434;font-weight:700;cursor:pointer}.annotation-empty{padding:16px;border:1px dashed #d8e1dc;border-radius:12px;background:#fafcfb}.annotation-empty strong{font-size:13px}.annotation-empty p{margin:4px 0 0;color:#6b7889;font-size:12.5px;line-height:1.5}button:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 42%,#fff);outline-offset:2px}
</style>
