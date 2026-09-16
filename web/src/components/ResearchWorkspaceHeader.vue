<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";
const props=withDefaults(defineProps<{ title:string; description:string; evidenceCount?:number; databaseCount?:number }>(),{evidenceCount:0,databaseCount:0});
const i18n=useI18nStore();
</script>
<template><header class="research-workspace-header"><div><span class="section-label">{{ i18n.t("nav.rag", "Research") }}</span><h1>{{props.title}}</h1><p>{{props.description}}</p></div><div class="status"><span>{{ i18n.tf(props.evidenceCount===1 ? "research.selected_evidence_count_one" : "research.selected_evidence_count_many", props.evidenceCount===1 ? "{count} selected evidence" : "{count} selected evidence", {count:props.evidenceCount}) }}</span><span>{{ i18n.tf(props.databaseCount===1 ? "research.database_count_one" : "research.database_count_many", props.databaseCount===1 ? "{count} database" : "{count} databases", {count:props.databaseCount}) }}</span></div></header></template>
