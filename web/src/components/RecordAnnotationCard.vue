<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import { useI18nStore } from "../stores/i18n";
const props = withDefaults(defineProps<{ field:string; quote?:string; note?:string; tags?:string[]; author?:string; timestamp?:string; removable?:boolean }>(), {quote:"",note:"",tags:()=>[],author:"",timestamp:"",removable:false});
const emit = defineEmits<{ remove:[] }>();
const i18n = useI18nStore();
</script>
<template>
  <article class="record-annotation-component">
    <section class="context"><span class="field-label">{{ props.field }}</span><blockquote v-if="props.quote">{{ props.quote }}</blockquote></section>
    <section class="body"><p v-if="props.note">{{ props.note }}</p><div v-if="props.tags.length" class="tags"><span v-for="tag in props.tags" :key="tag">{{ tag }}</span></div><footer><span>{{ props.author }}</span><time>{{ props.timestamp }}</time></footer></section>
    <button v-if="props.removable" type="button" class="btn tiny danger" @click="emit('remove')"><AppIcon name="close" />{{ i18n.t("ui.remove", "Remove") }}</button>
  </article>
</template>
