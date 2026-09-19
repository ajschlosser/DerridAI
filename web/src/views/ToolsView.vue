<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import RuntimeSurface from "../components/RuntimeSurface.vue";
import PdfWorkspaceView from "./PdfWorkspaceView.vue";
const route=useRoute();
const isPdf=computed(()=>String(route.meta.view||"")==="pdf");
</script>

<template><PdfWorkspaceView v-if="isPdf"/><RuntimeSurface v-else/></template>
