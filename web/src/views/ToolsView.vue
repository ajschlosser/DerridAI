<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import RuntimeSurface from "../components/RuntimeSurface.vue";
import PdfWorkspaceView from "./PdfWorkspaceView.vue";
import VectorStoresView from "./VectorStoresView.vue";
const route=useRoute();
const isPdf=computed(()=>String(route.meta.view||"")==="pdf");
const isVector=computed(()=>String(route.meta.view||"")==="vector");
</script>

<template>
  <PdfWorkspaceView v-if="isPdf"/>
  <VectorStoresView v-else-if="isVector"/>
  <RuntimeSurface v-else/>
</template>
