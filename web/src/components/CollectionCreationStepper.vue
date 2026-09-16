<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
const props=withDefaults(defineProps<{ steps:string[]; activeStep:number }>(),{activeStep:0});
const i18n=useI18nStore();
</script>
<template><ol class="storybook-collection-stepper" :aria-label="i18n.t('vector.collection_creation_steps','Collection creation steps')"><li v-for="(step,index) in props.steps" :key="step" :class="{active:index===props.activeStep,done:index<props.activeStep}"><span>{{ index+1 }}</span><b>{{ step }}</b></li></ol></template>
