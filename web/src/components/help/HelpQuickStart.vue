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
import type { HelpStarter } from "../../domain/helpTopics";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";

defineProps<{ items: HelpStarter[] }>();

const i18n = useI18nStore();
</script>

<template>
  <section class="help-start" aria-labelledby="help-start-heading">
    <header>
      <div>
        <p class="help-start-eyebrow">{{ i18n.t("help.start_here") }}</p>
        <h2 id="help-start-heading">{{ i18n.t("help.start_here") }}</h2>
        <p>{{ i18n.t("help.start_here_help") }}</p>
      </div>
    </header>

    <div class="help-start-grid">
      <RouterLink v-for="item in items" :key="item.id" class="help-start-card" :to="item.path">
        <span class="help-start-icon"><AppIcon :name="item.icon" aria-hidden="true" /></span>
        <span class="help-start-copy">
          <strong>{{ item.title }}</strong>
          <span>{{ item.description }}</span>
        </span>
        <AppIcon class="help-start-arrow" name="chevron-right" aria-hidden="true" />
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.help-start {
  display: grid;
  gap: var(--space-2);
}

.help-start header > div {
  display: grid;
  gap: 3px;
}

.help-start h2,
.help-start p {
  margin: 0;
}

.help-start h2 {
  color: var(--text-primary);
  font-size: 1.05rem;
}

.help-start header p:last-child {
  color: var(--text-tertiary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-start-eyebrow {
  color: var(--accent-fg) !important;
  font-size: 0.75rem !important;
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.help-start-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
}

.help-start-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
  min-block-size: 88px;
  padding: 13px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  color: inherit;
  text-decoration: none;
  box-shadow: var(--shadow-card);
}

.help-start-card:hover {
  border-color: var(--border-strong);
  background: var(--surface-hover);
}

.help-start-card:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.help-start-icon {
  display: grid;
  place-items: center;
  inline-size: 34px;
  block-size: 34px;
  border-radius: var(--radius-control);
  background: var(--surface-selected);
  color: var(--accent-fg);
}

.help-start-icon :deep(svg) {
  inline-size: 17px;
  block-size: 17px;
}

.help-start-copy {
  display: grid;
  gap: 4px;
  min-inline-size: 0;
}

.help-start-copy strong {
  color: var(--text-primary);
  font-size: 0.875rem;
}

.help-start-copy > span {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}

.help-start-arrow {
  inline-size: 15px;
  block-size: 15px;
  margin-block-start: 3px;
  color: var(--text-tertiary);
}

@media (max-width: 900px) {
  .help-start-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 580px) {
  .help-start-grid {
    grid-template-columns: 1fr;
  }
}

@media (forced-colors: active) {
  .help-start-card {
    border-color: ButtonText;
  }

  .help-start-icon {
    border: 1px solid ButtonText;
  }
}
</style>
