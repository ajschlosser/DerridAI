<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
const props = withDefaults(defineProps<{ title:string; description:string; actionLabel?:string; icon?:string }>(), {actionLabel:"",icon:"record"});
const emit = defineEmits<{ action:[] }>();
</script>
<template><section class="accessible-empty-state" role="status"><span class="accessible-empty-icon"><AppIcon :name="props.icon" /></span><h2>{{ props.title }}</h2><p>{{ props.description }}</p><button v-if="props.actionLabel" type="button" class="btn primary" @click="emit('action')">{{ props.actionLabel }}</button></section></template>
