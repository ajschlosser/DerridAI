<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
const props=withDefaults(defineProps<{done?:number;total:number;status?:string}>(),{done:0,status:""});
const emit=defineEmits<{cancel:[]}>();
const i18n=useI18nStore();
const statusText=computed(()=>props.status||i18n.t("operations.syncing_records","Syncing records…"));
</script>
<template><section class="blocking-upsert-progress" aria-live="polite"><progress :max="props.total" :value="props.done"></progress><div><b>{{props.done.toLocaleString(i18n.locale)}} / {{props.total.toLocaleString(i18n.locale)}}</b><span>{{statusText}}</span></div><button type="button" class="btn danger" @click="emit('cancel')">{{i18n.t('ui.cancel','Cancel')}}</button></section></template>
