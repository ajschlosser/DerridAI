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
import { nextTick, onBeforeUnmount, onMounted } from "vue";
import { refreshJobs } from "../domain/jobsActions";
import { mountOperationsPanelHost } from "../domain/operationsPanelHooks";
import { unmountOperationsPanel } from "../domain/operationsPanelHost";

onMounted(async () => {
  await refreshJobs({ rerender: true });
  await nextTick();
  mountOperationsPanelHost();
});

onBeforeUnmount(() => unmountOperationsPanel());
</script>

<template>
  <main class="vue-native-page operations-page" aria-labelledby="ops-heading">
    <div id="operationsPanelHost"></div>
  </main>
</template>

<style scoped>
.operations-page {
  min-width: 0;
}
</style>
