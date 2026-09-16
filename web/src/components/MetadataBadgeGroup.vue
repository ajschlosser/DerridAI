<script setup lang="ts">
const props = defineProps<{ title:string; values:string[]; emptyLabel?:string }>();
const emit = defineEmits<{ search:[value:string] }>();
</script>
<template><section class="metadata-badge-group"><header><h3>{{ props.title }}</h3><span>{{ props.values.length }}</span></header><div class="metadata-badge-list"><button v-for="value in props.values" :key="value" type="button" @click="emit('search',value)">{{ value }}</button><small v-if="!props.values.length">{{ props.emptyLabel || 'None' }}</small></div></section></template>
