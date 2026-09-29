<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
import HelpHighlight from "../components/HelpHighlight.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import {
  type HelpGlossaryCategory,
  type HelpPageGroup,
  visibleGlossary,
  visibleHelp,
  visiblePageGuides,
} from "../domain/helpTopics";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";

type SectionId = "help-pages" | "help-glossary" | "help-questions";

const i18n = useI18nStore();
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const query = ref(String(route.query.q || ""));
const glossaryCategory = ref<HelpGlossaryCategory>("all");
const searchInput = ref<HTMLInputElement | null>(null);
const contentRoot = ref<HTMLElement | null>(null);
const activeSection = ref<SectionId>("help-pages");
const openKeys = ref(new Set<string>());
let applyingRouteState = false;
let observer: IntersectionObserver | null = null;

const groupOrder: HelpPageGroup[] = [
  "overview",
  "research",
  "corpora",
  "corpus_management",
  "ai_automation",
  "system",
  "support",
];

const glossaryCategories: HelpGlossaryCategory[] = [
  "all",
  "ai",
  "retrieval",
  "parameters",
  "provenance",
  "storage",
];

const pageGuides = computed(() =>
  visiblePageGuides(
    auth.isAdmin,
    (capability) => auth.can(capability),
    query.value,
    (key, fallback) => i18n.t(key, fallback),
  ),
);
const pageGroups = computed(() =>
  groupOrder
    .map((group) => ({
      group,
      title: i18n.t(`help.group.${group}`),
      guides: pageGuides.value.filter((guide) => guide.group === group),
    }))
    .filter((group) => group.guides.length),
);
const glossary = computed(() =>
  visibleGlossary(query.value, glossaryCategory.value, (key, fallback) => i18n.t(key, fallback)),
);
const sections = computed(() =>
  visibleHelp(auth.isAdmin, query.value, (key, fallback) => i18n.t(key, fallback)),
);
const questionCount = computed(() =>
  sections.value.reduce((total, section) => total + section.entries.length, 0),
);
const matchCount = computed(
  () => pageGuides.value.length + glossary.value.length + questionCount.value,
);
const hasResults = computed(() => matchCount.value > 0);
const searching = computed(() => Boolean(query.value.trim()));

const guideKeys = computed(() => pageGuides.value.map((guide) => `page:${guide.id}`));
const termKeys = computed(() => glossary.value.map((entry) => `term:${entry.id}`));
const questionKeys = computed(() =>
  sections.value.flatMap((section) => section.entries.map((entry) => `q:${entry.id}`)),
);

const railLinks = computed(() => {
  const links: { id: SectionId; icon: string; label: string; count: number }[] = [];
  if (pageGroups.value.length) {
    links.push({
      id: "help-pages",
      icon: "list",
      label: i18n.t("help.page_guides"),
      count: pageGuides.value.length,
    });
  }
  links.push({
    id: "help-glossary",
    icon: "books",
    label: i18n.t("help.glossary_title"),
    count: glossary.value.length,
  });
  if (sections.value.length) {
    links.push({
      id: "help-questions",
      icon: "help",
      label: i18n.t("help.common_questions"),
      count: questionCount.value,
    });
  }
  return links;
});

function isOpen(key: string): boolean {
  return openKeys.value.has(key);
}

function onToggle(key: string, event: Event) {
  const next = new Set(openKeys.value);
  if ((event.target as HTMLDetailsElement).open) next.add(key);
  else next.delete(key);
  openKeys.value = next;
}

function allOpen(keys: string[]): boolean {
  return keys.length > 0 && keys.every((key) => openKeys.value.has(key));
}

function toggleAll(keys: string[]) {
  const next = new Set(openKeys.value);
  const open = !allOpen(keys);
  for (const key of keys) {
    if (open) next.add(key);
    else next.delete(key);
  }
  openKeys.value = next;
}

function clearSearch() {
  query.value = "";
  searchInput.value?.focus();
}

watch(query, (value) => {
  if (applyingRouteState) return;
  void router.replace({
    name: "help",
    query: { ...route.query, q: value.trim() || undefined },
  });
});

watch(
  () => route.query.q,
  (value) => {
    const next = String(value || "");
    if (next === query.value) return;
    applyingRouteState = true;
    query.value = next;
    applyingRouteState = false;
  },
);

// While searching, matches open so the reader sees why they matched; clearing the search resets.
watch(
  [searching, guideKeys, termKeys, questionKeys],
  ([active], [wasActive]) => {
    if (active) {
      openKeys.value = new Set([...guideKeys.value, ...termKeys.value, ...questionKeys.value]);
    } else if (wasActive) {
      openKeys.value = new Set();
    }
  },
  { flush: "sync" },
);

function observeSections() {
  observer?.disconnect();
  if (typeof IntersectionObserver === "undefined" || !contentRoot.value) return;
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (visible) activeSection.value = visible.target.id as SectionId;
    },
    { rootMargin: "-15% 0px -70% 0px" },
  );
  contentRoot.value.querySelectorAll("[data-help-section]").forEach((el) => observer?.observe(el));
}

watch(
  () => railLinks.value.map((link) => link.id).join(","),
  () => void nextTick(observeSections),
);

function onGlobalKeydown(event: KeyboardEvent) {
  if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
  const target = event.target as HTMLElement | null;
  if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
  event.preventDefault();
  searchInput.value?.focus();
}

function openFromHash() {
  const id = decodeURIComponent(route.hash.replace(/^#/, ""));
  if (!id) return;
  const prefixes: [string, string][] = [
    ["help-page-", "page:"],
    ["help-term-", "term:"],
  ];
  for (const [prefix, key] of prefixes) {
    if (id.startsWith(prefix))
      openKeys.value = new Set(openKeys.value).add(key + id.slice(prefix.length));
  }
  void nextTick(() => document.getElementById(id)?.scrollIntoView?.({ block: "start" }));
}

onMounted(() => {
  document.addEventListener("keydown", onGlobalKeydown);
  observeSections();
  if (searching.value) {
    openKeys.value = new Set([...guideKeys.value, ...termKeys.value, ...questionKeys.value]);
  }
  openFromHash();
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onGlobalKeydown);
  observer?.disconnect();
});
</script>

<template>
  <section class="help-center">
    <UiPageHeader :title="i18n.t('help.title')" :description="i18n.t('help.intro')" />

    <div class="help-search-bar" role="search">
      <label class="help-search" for="help-search-input">
        <span class="sr-only">{{ i18n.t("help.search") }}</span>
        <span class="help-search-control">
          <AppIcon name="search" aria-hidden="true" />
          <input
            id="help-search-input"
            ref="searchInput"
            v-model="query"
            class="control"
            type="search"
            :placeholder="i18n.t('help.search_placeholder')"
            autocomplete="off"
            aria-describedby="help-search-status"
            @keydown.esc="query = ''"
          />
          <button
            v-if="query"
            type="button"
            class="help-search-clear"
            :aria-label="i18n.t('help.clear_search')"
            @click="clearSearch"
          >
            <AppIcon name="close" aria-hidden="true" />
          </button>
          <kbd v-else class="help-kbd" :title="i18n.t('help.search_shortcut')" aria-hidden="true">
            /
          </kbd>
        </span>
      </label>
      <p id="help-search-status" class="help-search-status" role="status" aria-live="polite">
        {{
          searching
            ? i18n.tf("help.results_found", { count: matchCount })
            : i18n.t("help.search_hint")
        }}
      </p>
    </div>

    <div class="help-layout">
      <aside class="help-toc">
        <nav :aria-label="i18n.t('help.contents')">
          <p class="help-toc-title">{{ i18n.t("help.contents") }}</p>
          <a
            v-for="link in railLinks"
            :key="link.id"
            :href="`#${link.id}`"
            :aria-current="activeSection === link.id ? 'location' : undefined"
            :class="{ active: activeSection === link.id }"
            @click="activeSection = link.id"
          >
            <AppIcon :name="link.icon" aria-hidden="true" />
            <span class="help-toc-label">{{ link.label }}</span>
            <span class="help-toc-count">{{ link.count }}</span>
          </a>
        </nav>
      </aside>

      <div ref="contentRoot" class="help-content">
        <section v-if="!hasResults" class="help-empty">
          <AppIcon name="search" aria-hidden="true" />
          <div>
            <h2>{{ i18n.t("help.no_results_title") }}</h2>
            <p>{{ i18n.tf("help.no_results", { query }) }}</p>
            <button type="button" class="help-text-button" @click="clearSearch">
              {{ i18n.t("help.clear_search") }}
            </button>
          </div>
        </section>

        <section
          v-if="pageGroups.length"
          id="help-pages"
          data-help-section
          class="help-major-section"
          aria-labelledby="help-pages-heading"
        >
          <header class="help-section-heading">
            <div>
              <p class="help-eyebrow">{{ i18n.t("help.browse_by_page") }}</p>
              <h2 id="help-pages-heading">{{ i18n.t("help.page_guides") }}</h2>
              <p>{{ i18n.t("help.page_guides_help") }}</p>
            </div>
            <button type="button" class="help-toggle-all" @click="toggleAll(guideKeys)">
              {{ i18n.t(allOpen(guideKeys) ? "help.collapse_all" : "help.expand_all") }}
            </button>
          </header>

          <section
            v-for="group in pageGroups"
            :key="group.group"
            class="help-page-group"
            :aria-labelledby="`help-group-${group.group}`"
          >
            <h3 :id="`help-group-${group.group}`">
              {{ group.title }}
              <span class="help-group-count">{{ group.guides.length }}</span>
            </h3>
            <div class="help-guide-grid">
              <article
                v-for="guide in group.guides"
                :id="`help-page-${guide.id}`"
                :key="guide.id"
                class="help-guide-card"
              >
                <details
                  :open="isOpen(`page:${guide.id}`)"
                  @toggle="onToggle(`page:${guide.id}`, $event)"
                >
                  <summary>
                    <span class="help-guide-summary">
                      <span class="help-guide-title">
                        <HelpHighlight :text="guide.title" :query="query" />
                      </span>
                      <span class="help-guide-description">
                        <HelpHighlight :text="guide.summary" :query="query" />
                      </span>
                    </span>
                    <AppIcon name="chevron-down" aria-hidden="true" />
                  </summary>
                  <div class="help-guide-body">
                    <div>
                      <h4>{{ i18n.t("help.use_page_to") }}</h4>
                      <p><HelpHighlight :text="guide.tasks" :query="query" /></p>
                    </div>
                    <div>
                      <h4>{{ i18n.t("help.impact_heading") }}</h4>
                      <p><HelpHighlight :text="guide.impact" :query="query" /></p>
                    </div>
                  </div>
                </details>
                <RouterLink v-if="guide.path !== '/help'" class="help-open-page" :to="guide.path">
                  {{ i18n.t("help.open_page") }}
                  <AppIcon name="chevron-right" aria-hidden="true" />
                </RouterLink>
              </article>
            </div>
          </section>
        </section>

        <section
          id="help-glossary"
          data-help-section
          class="help-major-section"
          aria-labelledby="help-glossary-heading"
        >
          <header class="help-section-heading">
            <div>
              <p class="help-eyebrow">{{ i18n.t("help.plain_language") }}</p>
              <h2 id="help-glossary-heading">{{ i18n.t("help.glossary_title") }}</h2>
              <p>{{ i18n.t("help.glossary_intro") }}</p>
            </div>
            <button
              v-if="glossary.length"
              type="button"
              class="help-toggle-all"
              @click="toggleAll(termKeys)"
            >
              {{ i18n.t(allOpen(termKeys) ? "help.collapse_all" : "help.expand_all") }}
            </button>
          </header>

          <div class="help-filter-row" role="group" :aria-label="i18n.t('help.glossary_filter')">
            <button
              v-for="category in glossaryCategories"
              :key="category"
              type="button"
              class="help-filter"
              :class="{ active: glossaryCategory === category }"
              :aria-pressed="glossaryCategory === category"
              @click="glossaryCategory = category"
            >
              {{ i18n.t(`help.glossary.category.${category}`) }}
            </button>
          </div>

          <p v-if="!glossary.length" class="help-filter-empty">
            {{ i18n.t("help.glossary_no_results") }}
          </p>

          <div class="help-glossary-grid">
            <details
              v-for="entry in glossary"
              :id="`help-term-${entry.id}`"
              :key="entry.id"
              class="help-glossary-entry"
              :open="isOpen(`term:${entry.id}`)"
              @toggle="onToggle(`term:${entry.id}`, $event)"
            >
              <summary>
                <span :class="{ 'help-code-term': entry.code }">
                  <HelpHighlight :text="entry.term" :query="query" />
                </span>
                <span class="help-category-badge">
                  {{ i18n.t(`help.glossary.category.${entry.category}`) }}
                </span>
                <AppIcon name="chevron-down" aria-hidden="true" />
              </summary>
              <div class="help-glossary-body">
                <p><HelpHighlight :text="entry.definition" :query="query" /></p>
                <div class="help-practical">
                  <strong>{{ i18n.t("help.in_practice") }}</strong>
                  <span><HelpHighlight :text="entry.practical" :query="query" /></span>
                </div>
              </div>
            </details>
          </div>
        </section>

        <section
          v-if="sections.length"
          id="help-questions"
          data-help-section
          class="help-major-section"
          aria-labelledby="help-questions-heading"
        >
          <header class="help-section-heading">
            <div>
              <p class="help-eyebrow">{{ i18n.t("help.decision_help") }}</p>
              <h2 id="help-questions-heading">{{ i18n.t("help.common_questions") }}</h2>
              <p>{{ i18n.t("help.common_questions_help") }}</p>
            </div>
            <button type="button" class="help-toggle-all" @click="toggleAll(questionKeys)">
              {{ i18n.t(allOpen(questionKeys) ? "help.collapse_all" : "help.expand_all") }}
            </button>
          </header>

          <section
            v-for="section in sections"
            :key="section.id"
            class="help-question-section"
            :aria-labelledby="`help-${section.id}`"
          >
            <h3 :id="`help-${section.id}`">
              {{ section.title }}
              <span class="help-group-count">{{ section.entries.length }}</span>
            </h3>
            <details
              v-for="entry in section.entries"
              :key="entry.id"
              class="help-entry"
              :open="isOpen(`q:${entry.id}`)"
              @toggle="onToggle(`q:${entry.id}`, $event)"
            >
              <summary>
                <span><HelpHighlight :text="entry.question" :query="query" /></span>
                <AppIcon name="chevron-down" aria-hidden="true" />
              </summary>
              <div class="help-entry-body">
                <p><HelpHighlight :text="entry.answer" :query="query" /></p>
                <div class="help-impact">
                  <strong>{{ i18n.t("help.impact_heading") }}</strong>
                  <span><HelpHighlight :text="entry.impact" :query="query" /></span>
                </div>
              </div>
            </details>
          </section>
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped>
.help-center {
  display: grid;
  gap: var(--space-4);
  max-inline-size: 80rem;
  margin-inline: auto;
  padding-block-end: var(--space-7);
}

/* Search is the primary entry point, so it sits directly under the title and stays reachable. */
.help-search-bar {
  position: sticky;
  inset-block-start: 0;
  z-index: 5;
  display: grid;
  gap: 6px;
  padding-block: var(--space-2);
  background: var(--surface-page, var(--bg, #fff));
}

.help-search {
  display: block;
  max-inline-size: 46rem;
}

.help-search-control {
  position: relative;
  display: block;
}

.help-search-control > :deep(svg) {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-start: 14px;
  inline-size: 18px;
  block-size: 18px;
  color: var(--text-tertiary);
  pointer-events: none;
  transform: translateY(-50%);
}

.help-search-control input {
  inline-size: 100%;
  min-block-size: 48px;
  padding-inline: 44px 48px;
  border-radius: var(--radius-card);
  font-size: 1rem;
}

.help-search-control input::-webkit-search-cancel-button {
  display: none;
}

.help-kbd {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-end: 12px;
  min-inline-size: 24px;
  padding: 2px 7px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--surface-inset);
  color: var(--text-secondary);
  font: inherit;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  text-align: center;
  pointer-events: none;
  transform: translateY(-50%);
}

.help-search-clear {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-end: 6px;
  display: grid;
  place-items: center;
  inline-size: 36px;
  block-size: 36px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transform: translateY(-50%);
}

.help-search-clear:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.help-search-clear :deep(svg) {
  inline-size: 16px;
  block-size: 16px;
}

.help-search-status {
  margin: 0;
  min-block-size: 1.25rem;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}

.help-section-heading h2,
.help-section-heading p,
.help-page-group h3,
.help-question-section h3,
.help-empty h2,
.help-empty p {
  margin: 0;
}

.help-section-heading p {
  max-inline-size: var(--measure);
  color: var(--text-tertiary);
  line-height: var(--lh-normal);
}

.help-layout {
  display: grid;
  grid-template-columns: minmax(11rem, 14rem) minmax(0, 1fr);
  gap: clamp(20px, 3vw, 40px);
  align-items: start;
}

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
  min-block-size: 40px;
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

.help-toc-count,
.help-group-count {
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0;
}

.help-toc a:focus-visible,
.help-text-button:focus-visible,
.help-toggle-all:focus-visible,
.help-search-clear:focus-visible,
.help-filter:focus-visible,
.help-open-page:focus-visible,
.help-guide-card summary:focus-visible,
.help-glossary-entry summary:focus-visible,
.help-entry summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.help-toc :deep(svg) {
  inline-size: 16px;
  block-size: 16px;
}

.help-content {
  display: grid;
  gap: var(--space-7);
  min-inline-size: 0;
}

.help-major-section {
  display: grid;
  gap: var(--space-4);
  scroll-margin-block-start: 5rem;
}

.help-section-heading {
  display: flex;
  gap: var(--space-3);
  align-items: end;
  justify-content: space-between;
  padding-block-end: var(--space-2);
  border-block-end: 1px solid var(--border-subtle);
}

.help-section-heading > div {
  display: grid;
  gap: 4px;
}

.help-section-heading h2 {
  color: var(--text-primary);
  font-size: 1.35rem;
  letter-spacing: -0.015em;
}

.help-eyebrow {
  color: var(--accent-fg) !important;
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.help-toggle-all,
.help-text-button {
  padding: 6px 4px;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
  white-space: nowrap;
  cursor: pointer;
}

.help-toggle-all {
  min-block-size: 36px;
  padding-inline: 10px;
}

.help-toggle-all:hover {
  background: var(--surface-hover);
}

.help-page-group,
.help-question-section {
  display: grid;
  gap: var(--space-2);
}

.help-page-group h3,
.help-question-section h3 {
  display: flex;
  gap: 8px;
  align-items: center;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.help-guide-grid,
.help-glossary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  align-items: start;
}

.help-guide-card,
.help-glossary-entry,
.help-entry {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  overflow: clip;
}

.help-guide-card {
  box-shadow: var(--shadow-card);
  scroll-margin-block-start: 5rem;
}

.help-guide-card:hover,
.help-glossary-entry:hover,
.help-entry:hover {
  border-color: var(--border-strong);
}

.help-guide-card summary,
.help-glossary-entry summary,
.help-entry summary {
  list-style: none;
  cursor: pointer;
}

.help-guide-card summary::-webkit-details-marker,
.help-glossary-entry summary::-webkit-details-marker,
.help-entry summary::-webkit-details-marker {
  display: none;
}

.help-guide-card summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: start;
  padding: 14px 16px 8px;
}

.help-guide-card summary:hover,
.help-glossary-entry summary:hover,
.help-entry summary:hover {
  background: var(--surface-hover);
}

.help-guide-summary {
  display: grid;
  gap: 5px;
}

.help-guide-title {
  color: var(--text-primary);
  font-weight: var(--fw-bold);
}

.help-guide-description {
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-guide-card summary :deep(svg),
.help-glossary-entry summary :deep(svg),
.help-entry summary :deep(svg) {
  inline-size: 16px;
  block-size: 16px;
  margin-block-start: 3px;
  color: var(--text-tertiary);
  transition: transform var(--motion-fast) var(--ease-standard);
}

.help-guide-card details[open] summary :deep(svg),
.help-glossary-entry[open] summary :deep(svg),
.help-entry[open] summary :deep(svg) {
  transform: rotate(180deg);
}

.help-guide-body {
  display: grid;
  gap: var(--space-3);
  padding: 4px 16px 12px;
}

.help-guide-body > div {
  display: grid;
  gap: 4px;
}

.help-guide-body h4 {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.help-guide-body p {
  margin: 0;
  max-inline-size: var(--measure);
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

/* The primary action stays visible without expanding the card. */
.help-open-page {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  margin: 0 8px 8px;
  min-block-size: 36px;
  padding: 6px 8px;
  border-radius: var(--radius-control);
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
  text-decoration: none;
}

.help-open-page:hover {
  background: var(--surface-hover);
  text-decoration: underline;
}

.help-open-page :deep(svg) {
  inline-size: 14px;
  block-size: 14px;
}

.help-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.help-filter {
  min-block-size: 36px;
  padding: 6px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  background: var(--surface-card);
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 650;
  cursor: pointer;
}

.help-filter:hover {
  background: var(--surface-hover);
}

.help-filter.active {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
  color: var(--accent-fg);
}

.help-glossary-entry {
  scroll-margin-block-start: 5rem;
}

.help-glossary-entry summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 8px;
  align-items: center;
  padding: 12px 14px;
  color: var(--text-primary);
  font-weight: var(--fw-bold);
}

.help-glossary-entry summary :deep(svg),
.help-entry summary :deep(svg) {
  margin-block-start: 0;
}

.help-category-badge {
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.02em;
}

.help-code-term {
  font-family: var(--font-mono);
}

.help-glossary-body,
.help-entry-body {
  display: grid;
  gap: var(--space-2);
  padding: 13px 14px 15px;
  border-block-start: 1px solid var(--border-subtle);
}

.help-glossary-body > p,
.help-entry-body > p {
  margin: 0;
  max-inline-size: var(--measure);
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-practical,
.help-impact {
  display: grid;
  gap: 3px;
  padding: 9px 10px;
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}

.help-practical strong,
.help-impact strong {
  color: var(--text-primary);
}

.help-question-section {
  gap: 8px;
}

.help-entry summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
  padding: 13px 14px;
  color: var(--text-primary);
  font-weight: 650;
}

.help-empty {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-4);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-card);
  color: var(--text-secondary);
}

.help-empty :deep(svg) {
  inline-size: 22px;
  block-size: 22px;
  color: var(--text-tertiary);
}

.help-empty > div {
  display: grid;
  gap: 5px;
}

.help-empty h2 {
  color: var(--text-primary);
  font-size: 1rem;
}

.help-filter-empty {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

@media (max-width: 900px) {
  .help-layout {
    grid-template-columns: 1fr;
  }

  /* The contents rail becomes a compact, sticky jump bar beneath the search. */
  .help-toc {
    position: sticky;
    inset-block-start: 4.25rem;
    z-index: 4;
    padding-block: 4px;
    background: var(--surface-page, var(--bg, #fff));
  }

  .help-toc nav {
    display: flex;
    gap: 6px;
    overflow-x: auto;
  }

  .help-toc-title {
    display: none;
  }

  .help-toc a {
    flex: 0 0 auto;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-pill);
  }

  .help-toc a.active {
    border-color: var(--border-interactive);
  }

  .help-toc .help-toc-label {
    white-space: nowrap;
  }
}

@media (max-width: 680px) {
  .help-guide-grid,
  .help-glossary-grid {
    grid-template-columns: 1fr;
  }

  .help-section-heading {
    align-items: start;
    flex-wrap: wrap;
  }

  .help-glossary-entry summary {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .help-category-badge {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .help-guide-card summary :deep(svg),
  .help-glossary-entry summary :deep(svg),
  .help-entry summary :deep(svg) {
    transition: none;
  }
}
</style>
