<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import { useI18nStore } from "../stores/i18n";
const props = defineProps<{ title:string; count:number; coverUrl?:string; subtitle?:string; selected?:boolean }>();
const emit = defineEmits<{ open:[] }>();
const i18n=useI18nStore();
</script>
<template><button type="button" class="work-cover-component" :class="{selected:props.selected}" @click="emit('open')"><img v-if="props.coverUrl" :src="props.coverUrl" :alt="i18n.tf('works.cover_of','Cover of {title}',{title:props.title})" loading="lazy"><span v-else class="work-cover-component-placeholder"><AppIcon name="books" /></span><span class="work-cover-component-copy"><b>{{ props.title }}</b><small v-if="props.subtitle">{{ props.subtitle }}</small><small>{{ props.count.toLocaleString(i18n.locale) }} {{i18n.t('dynamic.records','records')}}</small></span><span aria-hidden="true">›</span></button></template>
