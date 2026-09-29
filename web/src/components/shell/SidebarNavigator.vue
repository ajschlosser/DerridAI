<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import SidebarNavButton from "./SidebarNavButton.vue";
import type { SidebarNavEntry, SidebarNavGroup } from "./sidebarNav";

const props = defineProps<{ groups: SidebarNavGroup[]; collapsed: boolean }>();
const emit = defineEmits<{ navigate: [string] }>();
const i18n = useI18nStore();

const FAVORITES_KEY = "derridai.ui.navigationFavorites";
const RECENTS_KEY = "derridai.ui.navigationRecents";
const query = ref("");
const favorites = ref<string[]>(loadIds(FAVORITES_KEY));
const recents = ref<string[]>(loadIds(RECENTS_KEY));

function loadIds(key: string): string[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(parsed) ? parsed.map(String).slice(0, 12) : [];
  } catch {
    return [];
  }
}

function saveIds(key: string, values: string[]) {
  try {
    localStorage.setItem(key, JSON.stringify(values));
  } catch {
    /* Navigation personalization is optional. */
  }
}

const allItems = computed(() => props.groups.flatMap((group) => group.items));
const itemById = computed(() => new Map(allItems.value.map((item) => [item.id, item])));
const favoriteItems = computed(() =>
  favorites.value.map((id) => itemById.value.get(id)).filter((item): item is SidebarNavEntry => Boolean(item)),
);
const recentItems = computed(() =>
  recents.value
    .map((id) => itemById.value.get(id))
    .filter((item): item is SidebarNavEntry => Boolean(item))
    .slice(0, 4),
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
  recents.value = [id, ...recents.value.filter((item) => item !== id)].slice(0, 8);
  saveIds(RECENTS_KEY, recents.value);
  emit("navigate", id);
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
  <nav class="shell-navigation" :aria-label="i18n.t('ui.primary_navigation')">
    <label v-if="!collapsed" class="shell-nav-search">
      <AppIcon name="search" aria-hidden="true" />
      <span class="sr-only">{{ i18n.t("nav.filter_navigation") }}</span>
      <input
        v-model="query"
        type="search"
        autocomplete="off"
        :placeholder="i18n.t('nav.filter_navigation')"
      />
    </label>

    <section v-if="!collapsed && !query && favoriteItems.length" class="shell-nav-section quick">
      <h2>{{ i18n.t("nav.favorites") }}</h2>
      <div class="shell-nav-list">
        <SidebarNavButton
          v-for="item in favoriteItems"
          :key="`favorite-${item.id}`"
          :id="item.id"
          :label="item.label"
          :icon="item.icon"
          :active="item.active"
          :disabled-reason="item.disabledReason"
          @navigate="navigate"
        />
      </div>
    </section>

    <section v-if="!collapsed && !query && recentItems.length" class="shell-nav-section quick">
      <h2>{{ i18n.t("nav.recent") }}</h2>
      <div class="shell-nav-list">
        <SidebarNavButton
          v-for="item in recentItems"
          :key="`recent-${item.id}`"
          :id="item.id"
          :label="item.label"
          :icon="item.icon"
          :active="item.active"
          :disabled-reason="item.disabledReason"
          @navigate="navigate"
        />
      </div>
    </section>

    <section
      v-for="group in filteredGroups"
      :key="group.section"
      class="shell-nav-section"
      :class="{ overview: group.items.some((item) => item.id === 'home') }"
    >
      <h2 v-if="!collapsed && !group.items.some((item) => item.id === 'home')">{{ group.section }}</h2>
      <div class="shell-nav-list">
        <div v-for="item in group.items" :key="item.id" class="shell-nav-row">
          <SidebarNavButton
            :id="item.id"
            :label="item.label"
            :icon="item.icon"
            :active="item.active"
            :disabled-reason="item.disabledReason"
            @navigate="navigate"
          />
          <button
            v-if="!collapsed && !group.items.some((item) => item.id === 'home')"
            type="button"
            class="shell-nav-favorite"
            :class="{ active: isFavorite(item.id) }"
            :aria-label="
              i18n.tf(isFavorite(item.id) ? 'nav.unpin' : 'nav.pin', {
                label: item.label,
              })
            "
            :title="
              i18n.tf(isFavorite(item.id) ? 'nav.unpin' : 'nav.pin', {
                label: item.label,
              })
            "
            @click="toggleFavorite(item.id)"
          >
            <AppIcon name="star" aria-hidden="true" />
          </button>
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
  display: grid;
  gap: 10px;
  min-height: 0;
  overflow: auto;
  padding: 0 2px 10px;
}
.shell-nav-search {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  margin: 2px 4px 4px;
  padding: 7px 9px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  color: var(--muted);
}
.shell-nav-search :deep(svg) {
  width: 16px;
  height: 16px;
}
.shell-nav-search input {
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 0.8125rem;
}
.shell-nav-section {
  display: grid;
  gap: 4px;
}
.shell-nav-section + .shell-nav-section:not(.quick) {
  padding-top: 7px;
  border-top: 1px solid var(--line);
}
.shell-nav-section h2 {
  margin: 0;
  padding: 0 10px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}
.shell-nav-section.quick h2 {
  color: var(--text-tertiary);
}
.shell-nav-list {
  display: grid;
  gap: 1px;
}
.shell-nav-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px;
  align-items: center;
}
.shell-nav-row :deep(.nav-tooltip-wrap) {
  min-width: 0;
}
.shell-nav-row :deep(.nav-tooltip-wrap > button) {
  width: 100%;
}
.shell-nav-favorite {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  opacity: 0.35;
  cursor: pointer;
}
.shell-nav-row:hover .shell-nav-favorite,
.shell-nav-favorite:focus-visible,
.shell-nav-favorite.active {
  opacity: 1;
}
.shell-nav-favorite.active {
  color: var(--accent-fg);
}
.shell-nav-favorite :deep(svg) {
  width: 14px;
  height: 14px;
}
.shell-nav-empty {
  margin: 6px 10px;
  color: var(--muted);
  font-size: 0.8125rem;
}
:global(.sidebar-collapsed) .shell-navigation {
  overflow: visible;
  padding-inline: 0;
}
:global(.sidebar-collapsed) .shell-nav-row {
  display: block;
}
</style>
