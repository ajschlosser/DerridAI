<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import {
  APP_CODENAME,
  APP_GIT_COMMIT,
  APP_VERSION,
  COPYRIGHT_YEAR,
  appVersionLabel,
} from "../buildInfo";

const props = withDefaults(
  defineProps<{
    showCopyright?: boolean;
    showCommit?: boolean;
    compact?: boolean;
    landmark?: boolean;
  }>(),
  {
    showCopyright: true,
    showCommit: false,
    compact: false,
    landmark: false,
  },
);

const i18n = useI18nStore();
const holder = computed(() => i18n.t("about.copyright_holder"));
const copyright = computed(() =>
  i18n.tf("about.copyright", { year: COPYRIGHT_YEAR, holder: holder.value }),
);
const product = computed(() =>
  i18n.tf("about.product_version", {
    version: appVersionLabel(APP_VERSION, "", APP_CODENAME),
  }),
);
const commitLabel = computed(() => {
  const commit = String(APP_GIT_COMMIT || "").trim();
  return commit ? i18n.tf("about.build_commit", { commit }) : "";
});
</script>

<template>
  <div
    class="app-build-info"
    :class="{ compact: props.compact }"
    :role="props.landmark ? 'contentinfo' : undefined"
    :aria-label="i18n.t('about.title')"
  >
    <p v-if="props.showCopyright">{{ copyright }}</p>
    <p>{{ product }}</p>
    <p v-if="props.showCommit && commitLabel">{{ commitLabel }}</p>
  </div>
</template>

<style scoped>
.app-build-info {
  display: grid;
  gap: 2px;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.app-build-info p {
  margin: 0;
}
.app-build-info.compact {
  gap: 1px;
}
</style>
