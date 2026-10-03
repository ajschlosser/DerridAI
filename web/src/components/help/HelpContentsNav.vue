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
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";

export interface HelpContentsLink {
  id: string;
  icon: string;
  label: string;
  count: number;
}

defineProps<{
  links: HelpContentsLink[];
  activeSection: string;
}>();

const emit = defineEmits<{ activate: [id: string] }>();
const i18n = useI18nStore();
</script>

<template>
  <aside class="help-toc">
    <nav :aria-label="i18n.t('help.contents')">
      <p class="help-toc-title">{{ i18n.t("help.contents") }}</p>
      <a
        v-for="link in links"
        :key="link.id"
        :href="`#${link.id}`"
        :aria-current="activeSection === link.id ? 'location' : undefined"
        :class="{ active: activeSection === link.id }"
        @click="emit('activate', link.id)"
      >
        <AppIcon :name="link.icon" aria-hidden="true" />
        <span class="help-toc-label">{{ link.label }}</span>
        <span class="help-toc-count">{{ link.count }}</span>
      </a>
    </nav>
  </aside>
</template>

<style scoped>
.help-toc {
  position: sticky;
  inset-block-start: 5rem;
}

.help-toc nav {
  display: grid;
  gap: 2px;
}

.help-toc-title {
  margin: 0;
  padding: 0 10px 6px;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.help-toc a {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-block-size: 42px;
  padding: 8px 10px;
  border-inline-start: 3px solid transparent;
  border-radius: var(--radius-control);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 650;
  text-decoration: none;
}

.help-toc a:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.help-toc a.active {
  border-inline-start-color: var(--accent-fg);
  background: var(--surface-selected);
  color: var(--text-primary);
}

.help-toc a:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.help-toc :deep(svg) {
  inline-size: 16px;
  block-size: 16px;
}

.help-toc-count {
  min-inline-size: 1.75rem;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  text-align: center;
}

@media (max-width: 900px) {
  .help-toc {
    position: static;
  }

  .help-toc nav {
    display: flex;
    gap: 6px;
    padding-block: 3px 6px;
    overflow-x: auto;
    scrollbar-width: thin;
  }

  .help-toc-title {
    display: none;
  }

  .help-toc a {
    flex: 0 0 auto;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-pill);
    background: var(--surface-page);
  }

  .help-toc a.active {
    border-color: var(--border-interactive);
  }

  .help-toc-label {
    white-space: nowrap;
  }
}

@media (forced-colors: active) {
  .help-toc a,
  .help-toc a.active {
    border-color: LinkText;
  }
}
</style>
