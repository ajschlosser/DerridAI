<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { usePublishedSite } from "./siteContext";

defineProps<{
  text: boolean;
  vector: boolean;
  llm: boolean;
}>();

const site = usePublishedSite();
</script>

<template>
  <div
    class="method-strip"
    data-tour="methods"
    role="group"
    :aria-label="site.t('site.runtime.method_disclosure')"
  >
    <span class="method-badge" :data-active="text ? 'true' : 'false'">
      <span>{{ site.t("site.runtime.method_text") }}</span>
      <span class="state">{{
        site.t(text ? "site.runtime.method_on" : "site.runtime.method_off")
      }}</span>
    </span>
    <span class="method-badge" :data-active="vector ? 'true' : 'false'">
      <span>{{ site.t("site.runtime.method_vector") }}</span>
      <span class="state">{{
        site.t(vector ? "site.runtime.method_on" : "site.runtime.method_off")
      }}</span>
    </span>
    <span class="method-badge" :data-active="llm ? 'true' : 'false'">
      <span>{{ site.t("site.runtime.method_llm") }}</span>
      <span class="state">{{
        site.t(llm ? "site.runtime.method_on" : "site.runtime.method_off")
      }}</span>
    </span>
  </div>
</template>
