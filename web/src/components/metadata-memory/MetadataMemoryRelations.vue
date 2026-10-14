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
import { RouterLink } from "vue-router";
import { useI18nStore } from "../../stores/i18n";

// Explains how the three System Data surfaces over the same memory differ, so an
// administrator knows which one to open for auditing, index debugging, or backlog checks.
const i18n = useI18nStore();
const examplesTo = { name: "system-data-metadata" };
const outboxTo = {
  name: "system-data-databases",
  query: { table: "semantic_memory_outbox" },
};
</script>

<template>
  <details class="memory-relations">
    <summary>{{ i18n.t("metadata_memory.relation_title") }}</summary>
    <ol>
      <li aria-current="page">
        <strong>{{ i18n.t("metadata_memory.relation_memory_title") }}</strong>
        <p>{{ i18n.t("metadata_memory.relation_memory_body") }}</p>
      </li>
      <li>
        <strong>{{ i18n.t("metadata_memory.relation_examples_title") }}</strong>
        <p>{{ i18n.t("metadata_memory.relation_examples_body") }}</p>
        <RouterLink :to="examplesTo">{{ i18n.t("metadata_memory.open_examples") }}</RouterLink>
      </li>
      <li>
        <strong class="mono">{{ i18n.t("metadata_memory.relation_outbox_title") }}</strong>
        <p>{{ i18n.t("metadata_memory.relation_outbox_body") }}</p>
        <RouterLink :to="outboxTo">{{ i18n.t("metadata_memory.open_outbox") }}</RouterLink>
      </li>
    </ol>
  </details>
</template>

<style scoped>
.memory-relations {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card, 10px);
  background: var(--surface-inset);
}
.memory-relations summary {
  padding: 10px 14px;
  font-weight: var(--fw-semibold, 650);
  cursor: pointer;
}
.memory-relations summary:focus-visible {
  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);
  outline-offset: 2px;
}
.memory-relations ol {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
  padding: 0 14px 14px;
  list-style: none;
}
.memory-relations li {
  display: grid;
  align-content: start;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface-card);
}
.memory-relations li[aria-current="page"] {
  border-color: var(--accent);
}
.memory-relations p {
  margin: 0;
  color: var(--text-secondary, var(--muted));
  font-size: 0.8125rem;
  line-height: 1.5;
}
.memory-relations a {
  font-size: 0.8125rem;
  font-weight: var(--fw-semibold, 650);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (max-width: 900px) {
  .memory-relations ol {
    grid-template-columns: 1fr;
  }
}
</style>
