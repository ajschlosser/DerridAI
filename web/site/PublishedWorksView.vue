<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import UiButton from "../src/components/ui/UiButton.vue";
import { usePublishedSite } from "./siteContext";

const site = usePublishedSite();

function openWork(work: string) {
  site.searchWork.value = work;
  site.view.value = "search";
}
</script>

<template>
  <section class="grid" data-tour="works" :aria-label="site.t('site.runtime.works')">
    <UiButton
      v-for="item in site.publication.works || []"
      :key="item.work"
      button-class="work-button card"
      @click="openWork(item.work)"
    >
      <span class="work-card-copy">
        <span class="work-title">{{ item.work }}</span>
        <span class="meta">{{ (item.authors || []).join(", ") }}</span>
        <span class="count">{{
          Number(item.record_count || 0).toLocaleString(site.locale.value)
        }}</span>
        <span class="muted">{{ site.t("site.runtime.records") }}</span>
      </span>
    </UiButton>
  </section>
</template>

<style scoped>
.work-card-copy {
  display: grid;
  gap: 0.15rem;
}
</style>
