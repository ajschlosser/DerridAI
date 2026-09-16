<script setup lang="ts">
const props=withDefaults(defineProps<{modelValue?:"compact"|"roomy"|"cards";label?:string}>(),{modelValue:"compact",label:"Result layout"});
const emit=defineEmits<{"update:modelValue":[value:"compact"|"roomy"|"cards"]}>();
const options:["compact"|"roomy"|"cards",string][]=[["compact","Compact table"],["roomy","Comfortable table"],["cards","Cards"]];
</script>
<template><div class="search-layout-switcher" role="group" :aria-label="props.label"><button v-for="[value,text] in options" :key="value" type="button" class="btn tiny" :class="{active:props.modelValue===value}" :aria-pressed="props.modelValue===value" @click="emit('update:modelValue',value)">{{text}}</button></div></template>
