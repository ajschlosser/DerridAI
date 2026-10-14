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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
import HelpContentsNav from "../components/help/HelpContentsNav.vue";
import HelpQuickStart from "../components/help/HelpQuickStart.vue";
import HelpSearchHero from "../components/help/HelpSearchHero.vue";
import HelpHighlight from "../components/HelpHighlight.vue";
import {
  type HelpGlossaryCategory,
  type HelpPageGroup,
  visibleGlossary,
  visibleHelp,
  visiblePageGuides,
  visibleStarters,
} from "../domain/helpTopics";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";

type SectionId = "help-pages" | "help-glossary" | "help-questions";

interface HelpContentsLink {
  id: string;
  icon: string;
  label: string;
  count: number;
}

const i18n = useI18nStore();
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const query = ref(String(route.query.q || ""));
const glossaryCategoryValues: HelpGlossaryCategory[] = [
  "all",
  "core",
  "ai",
  "retrieval",
  "provenance",
  "storage",
  "operations",
];
const initialCategory = String(route.query.topic || "all") as HelpGlossaryCategory;
const glossaryCategory = ref<HelpGlossaryCategory>(
  glossaryCategoryValues.includes(initialCategory) ? initialCategory : "all",
);
const searchHero = ref<{ focusSearch: () => void } | null>(null);
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

const glossaryCategories = glossaryCategoryValues;

const starters = computed(() =>
  visibleStarters(
    auth.isAdmin,
    (capability) => auth.can(capability),
    (key, fallback) => i18n.t(key, fallback),
  ),
);

const allPageGuides = computed(() =>
  visiblePageGuides(
    auth.isAdmin,
    (capability) => auth.can(capability),
    "",
    (key, fallback) => i18n.t(key, fallback),
  ),
);
const allGlossary = computed(() =>
  visibleGlossary("", "all", (key, fallback) => i18n.t(key, fallback)),
);
const allQuestionCount = computed(() =>
  visibleHelp(auth.isAdmin, "", (key, fallback) => i18n.t(key, fallback)).reduce(
    (total, section) => total + section.entries.length,
    0,
  ),
);

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
const conceptGlossary = computed(() =>
  visibleGlossary(query.value, glossaryCategory.value, (key, fallback) =>
    i18n.t(key, fallback),
  ).filter((entry) => entry.category !== "parameters"),
);
const parameterGlossary = computed(() =>
  visibleGlossary(query.value, "parameters", (key, fallback) => i18n.t(key, fallback)),
);
const glossary = computed(() => [...conceptGlossary.value, ...parameterGlossary.value]);
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
const questionKeys = computed(() =>
  sections.value.flatMap((section) => section.entries.map((entry) => `q:${entry.id}`)),
);

const railLinks = computed<HelpContentsLink[]>(() => {
  const links: HelpContentsLink[] = [];
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
  void nextTick(() => searchHero.value?.focusSearch());
}

function activateSection(id: string) {
  activeSection.value = id as SectionId;
}

function syncRouteState() {
  if (applyingRouteState) return;
  const trimmed = query.value.trim();
  void router.replace({
    name: "help",
    query: {
      ...route.query,
      q: trimmed || undefined,
      topic: !trimmed && glossaryCategory.value !== "all" ? glossaryCategory.value : undefined,
    },
    hash: route.hash,
  });
}

watch(query, (value) => {
  if (value.trim() && glossaryCategory.value !== "all") glossaryCategory.value = "all";
  syncRouteState();
});

watch(glossaryCategory, () => syncRouteState());

watch(
  () => [route.query.q, route.query.topic] as const,
  ([routeQuery, routeTopic]) => {
    const nextQuery = String(routeQuery || "");
    const candidate = String(routeTopic || "all") as HelpGlossaryCategory;
    const nextCategory = glossaryCategoryValues.includes(candidate) ? candidate : "all";
    if (nextQuery === query.value && nextCategory === glossaryCategory.value) return;
    applyingRouteState = true;
    query.value = nextQuery;
    glossaryCategory.value = nextQuery ? "all" : nextCategory;
    applyingRouteState = false;
  },
);

// While searching, matches open so the reader sees why they matched; clearing the search resets.
watch(
  [searching, guideKeys, questionKeys],
  ([active], [wasActive]) => {
    if (active) {
      openKeys.value = new Set([...guideKeys.value, ...questionKeys.value]);
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
  searchHero.value?.focusSearch();
}

function openFromHash() {
  const id = decodeURIComponent(route.hash.replace(/^#/, ""));
  if (!id) return;
  const prefixes: [string, string][] = [
    ["help-page-", "page:"],
    ["help-question-", "q:"],
  ];
  for (const [prefix, key] of prefixes) {
    if (id.startsWith(prefix)) {
      openKeys.value = new Set(openKeys.value).add(key + id.slice(prefix.length));
    }
  }
  if (id.startsWith("help-term-") && glossaryCategory.value !== "all") {
    glossaryCategory.value = "all";
  }
  void nextTick(() => {
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView?.({ block: "start" });
      return;
    }
    // A shareable anchor must remain useful even when an old search query hides it.
    if (query.value) {
      query.value = "";
      void nextTick(() => document.getElementById(id)?.scrollIntoView?.({ block: "start" }));
    }
  });
}

watch(
  () => route.hash,
  () => openFromHash(),
);

onMounted(() => {
  document.addEventListener("keydown", onGlobalKeydown);
  observeSections();
  if (searching.value) {
    openKeys.value = new Set([...guideKeys.value, ...questionKeys.value]);
  }
  openFromHash();
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onGlobalKeydown);
  observer?.disconnect();
});
</script>

<template>
  <section class="help-center" aria-labelledby="help-center-title">
    <HelpSearchHero
      ref="searchHero"
      v-model="query"
      :searching="searching"
      :match-count="matchCount"
      :page-count="allPageGuides.length"
      :term-count="allGlossary.length"
      :question-count="allQuestionCount"
      :is-admin="auth.isAdmin"
    />

    <HelpQuickStart v-if="!searching" :items="starters" />

    <div class="help-layout">
      <HelpContentsNav
        v-if="hasResults"
        :links="railLinks"
        :active-section="activeSection"
        @activate="activateSection"
      />

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
                    <div v-if="guide.impact">
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
          </header>

          <section v-if="conceptGlossary.length || !searching" class="help-glossary-subsection">
            <header class="help-subsection-heading">
              <div>
                <h3>{{ i18n.t("help.glossary_concepts") }}</h3>
                <p>{{ i18n.t("help.glossary_concepts_help") }}</p>
              </div>
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

            <p v-if="!conceptGlossary.length" class="help-filter-empty">
              {{ i18n.t("help.glossary_no_results") }}
            </p>

            <div class="help-glossary-grid">
              <article
                v-for="entry in conceptGlossary"
                :id="`help-term-${entry.id}`"
                :key="entry.id"
                class="help-glossary-entry"
              >
                <header class="help-glossary-term">
                  <span :class="{ 'help-code-term': entry.code }">
                    <HelpHighlight :text="entry.term" :query="query" />
                  </span>
                  <span class="help-category-badge">
                    {{ i18n.t(`help.glossary.category.${entry.category}`) }}
                  </span>
                </header>
                <p class="help-glossary-definition">
                  <HelpHighlight :text="entry.definition" :query="query" />
                </p>
                <p class="help-practical-inline">
                  <strong>{{ i18n.t("help.in_practice") }}</strong>
                  <span><HelpHighlight :text="entry.practical" :query="query" /></span>
                </p>
              </article>
            </div>
          </section>

          <section v-if="parameterGlossary.length" class="help-glossary-subsection">
            <header class="help-subsection-heading">
              <div>
                <h3>{{ i18n.t("help.parameter_reference") }}</h3>
                <p>{{ i18n.t("help.parameter_reference_help") }}</p>
              </div>
              <span class="help-subsection-count">{{ parameterGlossary.length }}</span>
            </header>

            <div class="help-parameter-list">
              <article
                v-for="entry in parameterGlossary"
                :id="`help-term-${entry.id}`"
                :key="entry.id"
                class="help-parameter-entry"
              >
                <div class="help-parameter-name">
                  <code v-if="entry.code"><HelpHighlight :text="entry.term" :query="query" /></code>
                  <strong v-else><HelpHighlight :text="entry.term" :query="query" /></strong>
                </div>
                <dl>
                  <div>
                    <dt>{{ i18n.t("help.parameter_controls") }}</dt>
                    <dd><HelpHighlight :text="entry.definition" :query="query" /></dd>
                  </div>
                  <div>
                    <dt>{{ i18n.t("help.parameter_effect") }}</dt>
                    <dd><HelpHighlight :text="entry.practical" :query="query" /></dd>
                  </div>
                </dl>
              </article>
            </div>
          </section>

          <p v-if="!glossary.length" class="help-filter-empty">
            {{ i18n.t("help.glossary_no_results") }}
          </p>
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
              :id="`help-question-${entry.id}`"
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
                <div v-if="entry.impact" class="help-impact">
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

.help-text-button:focus-visible,
.help-toggle-all:focus-visible,
.help-filter:focus-visible,
.help-open-page:focus-visible,
.help-guide-card summary:focus-visible,
.help-entry summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
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

.help-glossary-subsection {
  display: grid;
  gap: var(--space-3);
}

.help-subsection-heading {
  display: flex;
  gap: var(--space-3);
  align-items: end;
  justify-content: space-between;
}

.help-subsection-heading > div {
  display: grid;
  gap: 3px;
}

.help-subsection-heading h3,
.help-subsection-heading p {
  margin: 0;
}

.help-subsection-heading h3 {
  color: var(--text-primary);
  font-size: 1rem;
}

.help-subsection-heading p {
  max-inline-size: var(--measure);
  color: var(--text-tertiary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-subsection-count {
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
}

.help-guide-card,
.help-glossary-entry,
.help-parameter-entry,
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
.help-parameter-entry:hover,
.help-entry:hover {
  border-color: var(--border-strong);
}

.help-guide-card summary,
.help-entry summary {
  list-style: none;
  cursor: pointer;
}

.help-guide-card summary::-webkit-details-marker,
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
.help-entry summary :deep(svg) {
  inline-size: 16px;
  block-size: 16px;
  margin-block-start: 3px;
  color: var(--text-tertiary);
  transition: transform var(--motion-fast) var(--ease-standard);
}

.help-guide-card details[open] summary :deep(svg),
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

.help-glossary-entry,
.help-parameter-entry {
  scroll-margin-block-start: 5rem;
}

.help-glossary-entry {
  display: grid;
  gap: 8px;
  padding: 13px 14px 14px;
}

.help-glossary-term {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  color: var(--text-primary);
  font-weight: var(--fw-bold);
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

.help-code-term,
.help-parameter-name code {
  font-family: var(--font-mono);
}

.help-glossary-definition,
.help-practical-inline {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-practical-inline {
  display: grid;
  gap: 2px;
  padding-block-start: 8px;
  border-block-start: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
}

.help-practical-inline strong {
  color: var(--text-secondary);
  font-size: 0.75rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.help-parameter-list {
  display: grid;
  gap: var(--space-2);
}

.help-parameter-entry {
  display: grid;
  grid-template-columns: minmax(8rem, 0.35fr) minmax(0, 1fr);
  gap: var(--space-3);
  padding: 13px 14px;
}

.help-parameter-name {
  color: var(--text-primary);
}

.help-parameter-name code {
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
}

.help-parameter-entry dl,
.help-parameter-entry dl > div {
  display: grid;
  gap: 3px;
  margin: 0;
}

.help-parameter-entry dl {
  gap: 10px;
}

.help-parameter-entry dt {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.help-parameter-entry dd {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-entry-body {
  display: grid;
  gap: var(--space-2);
  padding: 13px 14px 15px;
  border-block-start: 1px solid var(--border-subtle);
}

.help-entry-body > p {
  margin: 0;
  max-inline-size: var(--measure);
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

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

.help-impact strong {
  color: var(--text-primary);
}

.help-question-section {
  gap: 8px;
}

.help-entry {
  scroll-margin-block-start: 5rem;
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
}

@media (max-width: 680px) {
  .help-guide-grid,
  .help-glossary-grid {
    grid-template-columns: 1fr;
  }

  .help-parameter-entry {
    grid-template-columns: 1fr;
    gap: var(--space-2);
  }

  .help-section-heading {
    align-items: start;
    flex-wrap: wrap;
  }

  .help-category-badge {
    display: none;
  }
}

@media (forced-colors: active) {
  .help-guide-card,
  .help-glossary-entry,
  .help-parameter-entry,
  .help-entry,
  .help-empty {
    border-color: CanvasText;
  }

  .help-filter.active {
    border-color: Highlight;
  }
}

@media (prefers-reduced-motion: reduce) {
  .help-guide-card summary :deep(svg),
  .help-entry summary :deep(svg) {
    transition: none;
  }
}
</style>
