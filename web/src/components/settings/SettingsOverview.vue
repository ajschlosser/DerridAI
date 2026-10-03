<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
-->

<script setup lang="ts">
import type { SettingsSectionId } from "../../domain/settings";

defineProps<{
  title: string;
  description: string;
  navLabel: string;
  items: Array<{
    id: SettingsSectionId;
    label: string;
    description: string;
    path: string;
    detail?: string;
    attention?: boolean;
  }>;
}>();
</script>

<template>
  <section class="settings-overview" aria-labelledby="settings-overview-title">
    <header class="settings-overview-head">
      <div>
        <h2 id="settings-overview-title">{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
    </header>

    <nav :aria-label="navLabel">
      <ul class="settings-overview-grid">
        <li v-for="item in items" :key="item.id">
          <RouterLink class="settings-overview-link" :to="item.path">
            <span class="settings-overview-copy">
              <strong>{{ item.label }}</strong>
              <small>{{ item.description }}</small>
            </span>
            <span
              v-if="item.detail"
              class="settings-overview-detail"
              :class="{ attention: item.attention }"
            >
              {{ item.detail }}
            </span>
            <span class="settings-overview-arrow" aria-hidden="true">→</span>
          </RouterLink>
        </li>
      </ul>
    </nav>

    <footer v-if="$slots.footer" class="settings-overview-footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.settings-overview {
  display: grid;
  gap: 24px;
  min-width: 0;
}
.settings-overview-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.settings-overview-head h2 {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.5rem;
  line-height: 1.2;
}
.settings-overview-head p {
  margin: 8px 0 0;
  max-width: 68ch;
  color: var(--muted);
  line-height: 1.55;
}
.settings-overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.settings-overview-link {
  min-height: 108px;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "copy arrow"
    "detail arrow";
  gap: 10px 16px;
  align-items: center;
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  color: var(--text);
  text-decoration: none;
}
.settings-overview-link:hover {
  border-color: var(--line-strong);
  background: var(--panel-2);
}
.settings-overview-link:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.settings-overview-copy {
  grid-area: copy;
  min-width: 0;
}
.settings-overview-copy strong,
.settings-overview-copy small {
  display: block;
}
.settings-overview-copy strong {
  font-size: 0.95rem;
}
.settings-overview-copy small {
  margin-top: 5px;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.settings-overview-detail {
  grid-area: detail;
  width: fit-content;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 650;
}
.settings-overview-detail.attention {
  color: var(--tone-warn-fg, var(--text));
}
.settings-overview-arrow {
  grid-area: arrow;
  color: var(--muted);
  font-size: 1.125rem;
}
.settings-overview-footer {
  padding-top: 18px;
  border-top: 1px solid var(--line);
}
@media (max-width: 760px) {
  .settings-overview-grid {
    grid-template-columns: 1fr;
  }
}
@media (forced-colors: active) {
  .settings-overview-link {
    border-color: CanvasText;
  }
}
</style>
