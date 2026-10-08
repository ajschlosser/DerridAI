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
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import SidebarNavButton from "./SidebarNavButton.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import type { SidebarNavEntry, SidebarNavGroup } from "./sidebarNav";
import { runAfterNextPaint } from "../../domain/interactionTiming";

const props = defineProps<{
  groups: SidebarNavGroup[];
  collapsed: boolean;
  pendingId?: string;
  storageScope?: string;
}>();
const emit = defineEmits<{ navigate: [string] }>();
const i18n = useI18nStore();

const FAVORITES_KEY = "derridai.ui.navigationFavorites";
const RECENTS_KEY = "derridai.ui.navigationRecents";
const COLLAPSED_GROUPS_KEY = "derridai.ui.navigationCollapsedGroups";
const DEFAULT_COLLAPSED_GROUPS = ["Corpus Management", "AI & Automation", "System"];
const query = ref("");
const scopedStorageKey = (key: string) =>
  props.storageScope ? `${key}.${props.storageScope}` : key;

const favorites = ref<string[]>(loadIds(FAVORITES_KEY));
const recents = ref<string[]>(loadIds(RECENTS_KEY));
const collapsedGroups = ref<string[]>(loadIds(COLLAPSED_GROUPS_KEY, DEFAULT_COLLAPSED_GROUPS));

function loadIds(key: string, fallback: string[] = []): string[] {
  try {
    const raw = localStorage.getItem(scopedStorageKey(key));
    if (raw === null) return [...fallback];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String).slice(0, 12) : [...fallback];
  } catch {
    return [...fallback];
  }
}

function saveIds(key: string, values: string[]) {
  try {
    localStorage.setItem(scopedStorageKey(key), JSON.stringify(values));
  } catch {
    /* Navigation personalization is optional. */
  }
}

watch(
  () => props.storageScope,
  () => {
    favorites.value = loadIds(FAVORITES_KEY);
    recents.value = loadIds(RECENTS_KEY);
    collapsedGroups.value = loadIds(COLLAPSED_GROUPS_KEY, DEFAULT_COLLAPSED_GROUPS);
  },
);

function groupKey(group: SidebarNavGroup) {
  return group.id || group.section;
}

function isOverview(group: SidebarNavGroup) {
  return group.items.some((item) => item.id === "home");
}

function isGroupOpen(group: SidebarNavGroup) {
  if (props.collapsed || isOverview(group) || query.value.trim()) return true;
  if (group.items.some((item) => item.active)) return true;
  return !collapsedGroups.value.includes(groupKey(group));
}

function toggleGroup(group: SidebarNavGroup) {
  const key = groupKey(group);
  collapsedGroups.value = collapsedGroups.value.includes(key)
    ? collapsedGroups.value.filter((item) => item !== key)
    : [...collapsedGroups.value, key];
  saveIds(COLLAPSED_GROUPS_KEY, collapsedGroups.value);
}

const allItems = computed(() => props.groups.flatMap((group) => group.items));
const itemById = computed(() => new Map(allItems.value.map((item) => [item.id, item])));
const favoriteItems = computed(() =>
  favorites.value
    .map((id) => itemById.value.get(id))
    .filter((item): item is SidebarNavEntry => item !== undefined && item.id !== "home"),
);
const recentItems = computed(() =>
  recents.value
    .map((id) => itemById.value.get(id))
    .filter(
      (item): item is SidebarNavEntry =>
        item !== undefined && item.id !== "home" && !favorites.value.includes(item.id),
    )
    .slice(0, 3),
);
const filteredGroups = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  if (!needle) return props.groups;
  return props.groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${group.section} ${item.label}`.toLocaleLowerCase().includes(needle),
      ),
    }))
    .filter((group) => group.items.length);
});
const hasMatches = computed(() => filteredGroups.value.some((group) => group.items.length));

function navigate(id: string) {
  // Publish the user's primary navigation intent before optional personalization
  // storage. The application shell can render pending feedback immediately even
  // if browser storage is slow.
  emit("navigate", id);
  recents.value = [id, ...recents.value.filter((item) => item !== id)].slice(0, 8);
  const nextRecents = [...recents.value];
  runAfterNextPaint(() => saveIds(RECENTS_KEY, nextRecents));
}

function toggleFavorite(id: string) {
  favorites.value = favorites.value.includes(id)
    ? favorites.value.filter((item) => item !== id)
    : [...favorites.value, id].slice(0, 12);
  saveIds(FAVORITES_KEY, favorites.value);
}

function isFavorite(id: string) {
  return favorites.value.includes(id);
}
</script>

<template>
  <nav
    class="shell-navigation"
    :class="{ collapsed }"
    :aria-label="i18n.t('ui.primary_navigation')"
  >
    <label v-if="!collapsed" class="shell-nav-search">
      <AppIcon name="search" aria-hidden="true" />
      <span class="sr-only">{{ i18n.t("nav.filter_navigation") }}</span>
      <input
        v-model="query"
        type="search"
        autocomplete="off"
        :placeholder="i18n.t('nav.filter_navigation')"
        @keydown.esc="query = ''"
      />
      <button
        v-if="query"
        type="button"
        class="shell-nav-search-clear"
        :aria-label="i18n.t('common.clear')"
        @click="query = ''"
      >
        <AppIcon name="close" aria-hidden="true" />
      </button>
    </label>

    <div
      v-if="!collapsed && !query && (favoriteItems.length || recentItems.length)"
      class="shell-nav-shortcuts"
    >
      <section v-if="favoriteItems.length" class="shell-nav-section quick">
        <h2>{{ i18n.t("nav.favorites") }}</h2>
        <div class="shell-nav-list">
          <SidebarNavButton
            v-for="item in favoriteItems"
            :key="`favorite-${item.id}`"
            :id="item.id"
            :label="item.label"
            :icon="item.icon"
            :collapsed="collapsed"
            :active="item.active"
            :pending="item.id === pendingId"
            :disabled-reason="item.disabledReason"
            @navigate="navigate"
          />
        </div>
      </section>

      <section v-if="recentItems.length" class="shell-nav-section quick">
        <h2>{{ i18n.t("nav.recent") }}</h2>
        <div class="shell-nav-list">
          <SidebarNavButton
            v-for="item in recentItems"
            :key="`recent-${item.id}`"
            :id="item.id"
            :label="item.label"
            :icon="item.icon"
            :collapsed="collapsed"
            :active="item.active"
            :pending="item.id === pendingId"
            :disabled-reason="item.disabledReason"
            @navigate="navigate"
          />
        </div>
      </section>
    </div>

    <section
      v-for="group in filteredGroups"
      :key="groupKey(group)"
      class="shell-nav-section"
      :class="{ overview: isOverview(group) }"
    >
      <h2 v-if="!collapsed && !isOverview(group)" class="shell-nav-group-heading">
        <button
          type="button"
          class="shell-nav-group-toggle"
          :aria-expanded="isGroupOpen(group)"
          @click="toggleGroup(group)"
        >
          <span>{{ group.section }}</span>
          <AppIcon name="chevron-down" aria-hidden="true" />
        </button>
      </h2>
      <div v-show="isGroupOpen(group)" class="shell-nav-list">
        <div v-for="item in group.items" :key="item.id" class="shell-nav-row">
          <SidebarNavButton
            :id="item.id"
            :label="item.label"
            :icon="item.icon"
            :collapsed="collapsed"
            :active="item.active"
            :pending="item.id === pendingId"
            :disabled-reason="item.disabledReason"
            @navigate="navigate"
          />
          <UiTooltip
            v-if="!collapsed && !isOverview(group)"
            :text="
              i18n.tf(isFavorite(item.id) ? 'nav.unpin' : 'nav.pin', {
                label: item.label,
              })
            "
            trigger-mode="content"
            :content-focusable="false"
            placement="bottom"
          >
            <button
              type="button"
              class="shell-nav-favorite"
              :class="{ active: isFavorite(item.id) }"
              :aria-label="
                i18n.tf(isFavorite(item.id) ? 'nav.unpin' : 'nav.pin', {
                  label: item.label,
                })
              "
              @click="toggleFavorite(item.id)"
            >
              <AppIcon name="star" aria-hidden="true" />
            </button>
          </UiTooltip>
        </div>
      </div>
    </section>

    <p v-if="!collapsed && query && !hasMatches" class="shell-nav-empty" role="status">
      {{ i18n.t("nav.no_navigation_matches") }}
    </p>
  </nav>
</template>

<style scoped>
.shell-navigation {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
  gap: 14px;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 2px 3px 12px;
  font-family: var(--font-ui);
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--muted) 45%, transparent) transparent;
}

.shell-nav-search {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) 24px;
  align-items: center;
  gap: 9px;
  min-height: 38px;
  margin: 1px 2px 0;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-inset);
  color: var(--muted);
  transition:
    border-color var(--motion-fast, 120ms) var(--ease-standard, ease),
    box-shadow var(--motion-fast, 120ms) var(--ease-standard, ease),
    background-color var(--motion-fast, 120ms) var(--ease-standard, ease);
}

.shell-nav-search:focus-within {
  border-color: color-mix(in srgb, var(--ui-accent) 48%, var(--line));
  background: var(--card);
  box-shadow: 0 0 0 3px var(--ui-accent-focus);
}

.shell-nav-search :deep(svg) {
  width: 16px;
  height: 16px;
}

.shell-nav-search input {
  min-width: 0;
  min-height: 0;
  height: 36px;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 0.8125rem;
}

.shell-nav-search input::placeholder {
  color: var(--muted);
  opacity: 0.9;
}

.shell-nav-search-clear {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
}

.shell-nav-search-clear:hover,
.shell-nav-search-clear:focus-visible {
  background: var(--surface-hover);
  color: var(--text);
}

.shell-nav-search-clear :deep(svg) {
  width: 14px;
  height: 14px;
}

.shell-nav-shortcuts {
  display: grid;
  gap: 11px;
  padding: 0 2px 2px;
}

.shell-nav-section {
  display: grid;
  gap: 4px;
}

.shell-nav-section:not(.overview):not(.quick) {
  padding-top: 6px;
}

.shell-nav-section.overview {
  padding-bottom: 1px;
}

.shell-nav-section.quick {
  gap: 3px;
}

.shell-nav-section.quick h2 {
  margin: 0;
  padding: 0 9px;
  color: var(--text-tertiary);
  font-family: var(--font-ui);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold, 650);
  letter-spacing: 0.075em;
  line-height: 1.5;
  text-transform: uppercase;
}

.shell-nav-section.quick :deep(.nav-tooltip-wrap > button) {
  min-height: 34px;
  padding-block: 6px;
  font-size: 0.78125rem;
}

.shell-nav-section.quick :deep(.nav-tooltip-wrap > button svg) {
  width: 16px;
  height: 16px;
}

.shell-nav-group-heading {
  margin: 0;
}

.shell-nav-group-toggle {
  display: flex;
  min-height: 28px;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 3px 7px 3px 9px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  box-shadow: none;
  color: var(--muted);
  font-family: var(--font-ui);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold, 650);
  letter-spacing: 0.075em;
  line-height: 1.25;
  text-align: left;
  text-transform: uppercase;
  cursor: pointer;
}

.shell-nav-group-toggle:hover,
.shell-nav-group-toggle:focus-visible {
  background: var(--surface-hover);
  color: var(--text-2);
}

.shell-nav-group-toggle:focus-visible {
  outline-offset: 1px;
}

.shell-nav-group-toggle > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-nav-group-toggle :deep(svg) {
  width: 13px;
  height: 13px;
  flex: 0 0 auto;
  transition: transform var(--motion-fast, 120ms) var(--ease-standard, ease);
}

.shell-nav-group-toggle[aria-expanded="false"] :deep(svg) {
  transform: rotate(-90deg);
}

.shell-nav-list {
  display: grid;
  gap: 1px;
}

.shell-nav-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 24px;
  align-items: center;
  min-width: 0;
}

.shell-nav-row :deep(.nav-tooltip-wrap) {
  min-width: 0;
}

.shell-nav-favorite {
  display: grid;
  width: 24px;
  height: 30px;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: transparent;
  box-shadow: none;
  color: var(--muted);
  opacity: 0;
  cursor: pointer;
  transition:
    opacity var(--motion-fast, 120ms) var(--ease-standard, ease),
    background-color var(--motion-fast, 120ms) var(--ease-standard, ease),
    color var(--motion-fast, 120ms) var(--ease-standard, ease);
}

.shell-nav-row:hover .shell-nav-favorite,
.shell-nav-favorite:focus-visible,
.shell-nav-favorite.active {
  opacity: 0.72;
}

.shell-nav-favorite:hover,
.shell-nav-favorite:focus-visible {
  background: var(--surface-hover);
  color: var(--text);
  opacity: 1;
}

.shell-nav-favorite.active {
  color: var(--accent-fg);
  opacity: 1;
}

.shell-nav-favorite :deep(svg) {
  width: 13px;
  height: 13px;
}

.shell-nav-empty {
  margin: 4px 9px;
  color: var(--muted);
  font-size: 0.8125rem;
}

.shell-navigation.collapsed {
  gap: 6px;
  overflow-y: auto;
  overflow-x: visible;
  padding-inline: 0;
}

.shell-navigation.collapsed .shell-nav-section {
  gap: 2px;
}

.shell-navigation.collapsed .shell-nav-row {
  display: block;
}

.shell-navigation.collapsed :deep(.nav-tooltip-wrap > button) {
  justify-content: center;
  min-height: 40px;
  padding-inline: 8px;
  box-shadow: none;
}

.shell-navigation.collapsed :deep(.nav-tooltip-wrap > button.active) {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ui-accent) 44%, transparent);
}

.shell-navigation.collapsed :deep(.nav-tooltip-wrap > button span) {
  display: none;
}

.shell-navigation.collapsed :deep(.nav-tooltip-wrap > button svg) {
  width: 18px;
  height: 18px;
}

@media (hover: none) {
  .shell-nav-favorite {
    opacity: 0.5;
  }
}

@media (prefers-reduced-motion: reduce) {
  .shell-nav-search,
  .shell-nav-group-toggle :deep(svg),
  .shell-nav-favorite {
    transition: none;
  }
}

@media (forced-colors: active) {
  .shell-nav-search {
    border-color: CanvasText;
  }

  .shell-nav-favorite.active {
    outline: 1px solid CanvasText;
  }
}
</style>
