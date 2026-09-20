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
.record-annotations-panel{display:grid;gap:14px}.record-annotations-panel>header{display:flex;justify-content:space-between;align-items:end;gap:12px}.record-annotations-panel>header p{margin:0;color:var(--muted);font-size:.8125rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.record-annotations-panel h3{margin:2px 0 0;font-size:1rem}.annotation-header-actions{display:flex;align-items:center;gap:7px}.annotation-header-actions>span{min-width:28px;height:28px;display:grid;place-items:center;border-radius:999px;background:var(--soft);color:var(--text-2);font-size:.8125rem;font-weight:800}.annotation-header-actions button{min-height:32px;border:1px solid var(--line);border-radius:8px;background:var(--card);padding:0 9px;color:var(--text-2);font-weight:800;cursor:pointer}.annotation-list{display:grid;gap:10px}.annotation-card{display:grid;gap:9px;border:1px solid var(--line);border-radius:12px;background:var(--card);padding:12px}.annotation-card-top{display:flex;justify-content:space-between;gap:10px;align-items:center}.annotation-card-top>span{padding:3px 7px;border-radius:999px;background:var(--tone-ok-bg);color:var(--text-2);font-size:.8125rem;font-weight:800;text-transform:uppercase}.annotation-card time{color:var(--muted);font-size:.8125rem}.annotation-card blockquote{margin:0;padding:9px 10px;border-left:3px solid var(--ui-accent,#3c8d62);border-radius:0 7px 7px 0;background:var(--card);color:var(--text-2);font:13px/1.55 Georgia,"Times New Roman",serif}.annotation-card>p{margin:0;color:var(--text-2);font-size:0.8125rem;line-height:1.55}.annotation-tags{display:flex;gap:5px;flex-wrap:wrap}.annotation-tags span{padding:3px 7px;border-radius:999px;background:var(--soft);color:var(--text-2);font-size:.8125rem}.annotation-card footer{display:flex;justify-content:space-between;align-items:center;gap:8px;color:var(--muted);font-size:.8125rem}.annotation-card footer strong{font-weight:700}.annotation-card footer button{min-height:30px;border:0;border-radius:7px;background:var(--tone-danger-bg);padding:0 8px;color:var(--tone-danger-fg);font-weight:700;cursor:pointer}.annotation-empty{padding:16px;border:1px dashed var(--line);border-radius:12px;background:var(--card)}.annotation-empty strong{font-size:0.8125rem}.annotation-empty p{margin:4px 0 0;color:var(--muted);font-size:0.78125rem;line-height:1.5}button:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 42%,var(--card));outline-offset:2px}
</style>
