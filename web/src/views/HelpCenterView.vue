<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
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

const i18n = useI18nStore();
const auth = useAuthStore();
const query = ref("");
const glossaryCategory = ref<HelpGlossaryCategory>("all");

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
  visiblePageGuides(auth.isAdmin, (capability) => auth.can(capability), query.value, (key, fallback) =>
    i18n.t(key, fallback),
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
const matchCount = computed(() => pageGuides.value.length + glossary.value.length + questionCount.value);
const hasResults = computed(() => matchCount.value > 0);
</script>

<template>
  <section class="help-center">
    <UiPageHeader :title="i18n.t('help.title')" :description="i18n.t('help.intro')" />

    <section class="help-hero" :aria-labelledby="'help-search-heading'">
      <div class="help-search-copy">
        <h2 id="help-search-heading">{{ i18n.t("help.find_answer") }}</h2>
        <p>{{ i18n.t("help.find_answer_help") }}</p>
      </div>
      <label class="help-search" for="help-search-input">
        <span>{{ i18n.t("help.search") }}</span>
        <span class="help-search-control">
          <AppIcon name="search" aria-hidden="true" />
          <input
            id="help-search-input"
            v-model="query"
            class="control"
            type="search"
            :placeholder="i18n.t('help.search_placeholder')"
            autocomplete="off"
          />
        </span>
      </label>
      <p class="help-search-hint">{{ i18n.t("help.search_hint") }}</p>
      <div class="help-summary" aria-label="Help Center contents">
        <span>
          <strong>{{ pageGuides.length }}</strong>
          {{ i18n.t("help.pages_count_label") }}
        </span>
        <span>
          <strong>{{ glossary.length }}</strong>
          {{ i18n.t("help.terms_count_label") }}
        </span>
        <span>
          <strong>{{ questionCount }}</strong>
          {{ i18n.t("help.questions_count_label") }}
        </span>
      </div>
    </section>

    <p class="sr-only" role="status" aria-live="polite">
      {{ query ? i18n.tf("help.result_count", { count: matchCount }) : "" }}
    </p>

    <div class="help-layout">
      <aside class="help-toc">
        <nav :aria-label="i18n.t('help.contents')">
          <p class="help-toc-title">{{ i18n.t("help.contents") }}</p>
          <a href="#help-pages">
            <AppIcon name="list" aria-hidden="true" />
            <span>{{ i18n.t("help.page_guides") }}</span>
          </a>
          <a href="#help-glossary">
            <AppIcon name="books" aria-hidden="true" />
            <span>{{ i18n.t("help.glossary_title") }}</span>
          </a>
          <a href="#help-questions">
            <AppIcon name="help" aria-hidden="true" />
            <span>{{ i18n.t("help.common_questions") }}</span>
          </a>
        </nav>
      </aside>

      <main class="help-content">
        <section v-if="!hasResults" class="help-empty" role="status">
          <AppIcon name="search" aria-hidden="true" />
          <div>
            <h2>{{ i18n.t("help.no_results_title") }}</h2>
            <p>{{ i18n.tf("help.no_results", { query }) }}</p>
            <button type="button" class="help-text-button" @click="query = ''">
              {{ i18n.t("help.clear_search") }}
            </button>
          </div>
        </section>

        <section
          v-if="pageGroups.length"
          id="help-pages"
          class="help-major-section"
          aria-labelledby="help-pages-heading"
        >
          <header class="help-section-heading">
            <div>
              <p class="help-eyebrow">{{ i18n.t("help.browse_by_page") }}</p>
              <h2 id="help-pages-heading">{{ i18n.t("help.page_guides") }}</h2>
              <p>{{ i18n.t("help.page_guides_help") }}</p>
            </div>
            <span class="help-count">{{ pageGuides.length }}</span>
          </header>

          <section
            v-for="group in pageGroups"
            :key="group.group"
            class="help-page-group"
            :aria-labelledby="`help-group-${group.group}`"
          >
            <h3 :id="`help-group-${group.group}`">{{ group.title }}</h3>
            <div class="help-guide-grid">
              <details
                v-for="guide in group.guides"
                :id="`help-page-${guide.id}`"
                :key="guide.id"
                class="help-guide-card"
                :open="Boolean(query)"
              >
                <summary>
                  <span class="help-guide-summary">
                    <span class="help-guide-title">{{ guide.title }}</span>
                    <span class="help-guide-description">{{ guide.summary }}</span>
                  </span>
                  <AppIcon name="chevron-down" aria-hidden="true" />
                </summary>
                <div class="help-guide-body">
                  <div>
                    <h4>{{ i18n.t("help.use_page_to") }}</h4>
                    <p>{{ guide.tasks }}</p>
                  </div>
                  <div>
                    <h4>{{ i18n.t("help.impact_heading") }}</h4>
                    <p>{{ guide.impact }}</p>
                  </div>
                  <RouterLink v-if="guide.path !== '/help'" class="help-open-page" :to="guide.path">
                    {{ i18n.t("help.open_page") }}
                    <AppIcon name="chevron-right" aria-hidden="true" />
                  </RouterLink>
                </div>
              </details>
            </div>
          </section>
        </section>

        <section
          v-if="glossary.length || !query"
          id="help-glossary"
          class="help-major-section"
          aria-labelledby="help-glossary-heading"
        >
          <header class="help-section-heading">
            <div>
              <p class="help-eyebrow">{{ i18n.t("help.plain_language") }}</p>
              <h2 id="help-glossary-heading">{{ i18n.t("help.glossary_title") }}</h2>
              <p>{{ i18n.t("help.glossary_intro") }}</p>
            </div>
            <span class="help-count">{{ glossary.length }}</span>
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
              :open="Boolean(query)"
            >
              <summary>
                <span :class="{ 'help-code-term': entry.code }">{{ entry.term }}</span>
                <span class="help-category-badge">
                  {{ i18n.t(`help.glossary.category.${entry.category}`) }}
                </span>
                <AppIcon name="chevron-down" aria-hidden="true" />
              </summary>
              <div class="help-glossary-body">
                <p>{{ entry.definition }}</p>
                <div class="help-practical">
                  <strong>{{ i18n.t("help.in_practice") }}</strong>
                  <span>{{ entry.practical }}</span>
                </div>
              </div>
            </details>
          </div>
        </section>

        <section
          v-if="sections.length"
          id="help-questions"
          class="help-major-section"
          aria-labelledby="help-questions-heading"
        >
          <header class="help-section-heading">
            <div>
              <p class="help-eyebrow">{{ i18n.t("help.decision_help") }}</p>
              <h2 id="help-questions-heading">{{ i18n.t("help.common_questions") }}</h2>
              <p>{{ i18n.t("help.common_questions_help") }}</p>
            </div>
            <span class="help-count">{{ questionCount }}</span>
          </header>

          <section
            v-for="section in sections"
            :key="section.id"
            class="help-question-section"
            :aria-labelledby="`help-${section.id}`"
          >
            <h3 :id="`help-${section.id}`">{{ section.title }}</h3>
            <details
              v-for="entry in section.entries"
              :key="entry.id"
              class="help-entry"
              :open="Boolean(query)"
            >
              <summary>
                <span>{{ entry.question }}</span>
                <AppIcon name="chevron-down" aria-hidden="true" />
              </summary>
              <div class="help-entry-body">
                <p>{{ entry.answer }}</p>
                <div class="help-impact">
                  <strong>{{ i18n.t("help.impact_heading") }}</strong>
                  <span>{{ entry.impact }}</span>
                </div>
              </div>
            </details>
          </section>
        </section>
      </main>
    </div>
  </section>
</template>

<style scoped>
.help-center {
  display: grid;
  gap: var(--space-5);
  max-inline-size: 80rem;
  margin-inline: auto;
  padding-block-end: var(--space-7);
}

.help-hero {
  display: grid;
  gap: var(--space-3);
  padding: clamp(20px, 3vw, 32px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
}

.help-search-copy {
  display: grid;
  gap: var(--space-1);
}

.help-search-copy h2,
.help-search-copy p,
.help-section-heading h2,
.help-section-heading p,
.help-page-group h3,
.help-question-section h3,
.help-empty h2,
.help-empty p {
  margin: 0;
}

.help-search-copy h2 {
  color: var(--text-primary);
  font-size: clamp(1.15rem, 2vw, 1.4rem);
}

.help-search-copy p,
.help-section-heading p {
  max-inline-size: var(--measure);
  color: var(--text-tertiary);
  line-height: var(--lh-normal);
}

.help-search {
  display: grid;
  gap: var(--space-1);
  max-inline-size: 46rem;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}

.help-search-control {
  position: relative;
  display: block;
}

.help-search-control :deep(svg) {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-start: 13px;
  inline-size: 18px;
  block-size: 18px;
  color: var(--text-tertiary);
  pointer-events: none;
  transform: translateY(-50%);
}

.help-search-control input {
  inline-size: 100%;
  min-block-size: 46px;
  padding-inline-start: 42px;
  font-size: 1rem;
}

.help-search-hint {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}

.help-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-block-start: var(--space-1);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}

.help-summary span {
  display: inline-flex;
  gap: 5px;
  align-items: baseline;
  padding: 5px 9px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
}

.help-summary strong {
  color: var(--text-primary);
}

.help-layout {
  display: grid;
  grid-template-columns: minmax(10rem, 13rem) minmax(0, 1fr);
  gap: clamp(20px, 3vw, 36px);
  align-items: start;
}

.help-toc {
  position: sticky;
  inset-block-start: var(--space-4);
}

.help-toc nav {
  display: grid;
  gap: 4px;
  padding: var(--space-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}

.help-toc-title {
  margin: 0;
  padding: 7px 10px 5px;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.help-toc a {
  display: flex;
  gap: 8px;
  align-items: center;
  min-block-size: 38px;
  padding: 8px 10px;
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

.help-toc a:focus-visible,
.help-text-button:focus-visible,
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
  scroll-margin-top: var(--space-5);
}

.help-section-heading {
  display: flex;
  gap: var(--space-3);
  align-items: start;
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

.help-count {
  min-inline-size: 2rem;
  padding: 4px 8px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
  text-align: center;
}

.help-page-group,
.help-question-section {
  display: grid;
  gap: var(--space-2);
}

.help-page-group h3,
.help-question-section h3 {
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
}

.help-guide-card,
.help-glossary-entry,
.help-entry {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
  overflow: clip;
}

.help-guide-card {
  scroll-margin-top: var(--space-5);
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
  min-block-size: 100%;
  padding: 15px 16px;
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
  color: var(--text-tertiary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-guide-card summary :deep(svg),
.help-glossary-entry summary :deep(svg),
.help-entry summary :deep(svg) {
  inline-size: 16px;
  block-size: 16px;
  color: var(--text-tertiary);
  transition: transform var(--motion-fast) var(--ease-standard);
}

.help-guide-card[open] summary :deep(svg),
.help-glossary-entry[open] summary :deep(svg),
.help-entry[open] summary :deep(svg) {
  transform: rotate(180deg);
}

.help-guide-body {
  display: grid;
  gap: var(--space-3);
  padding: 0 16px 16px;
  border-block-start: 1px solid var(--border-subtle);
}

.help-guide-body > div {
  display: grid;
  gap: 4px;
  padding-block-start: var(--space-3);
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
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-open-page {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  justify-self: start;
  min-block-size: 34px;
  padding: 6px 9px;
  border-radius: var(--radius-control);
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
  text-decoration: none;
}

.help-open-page:hover {
  background: var(--surface-hover);
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
  min-block-size: 34px;
  padding: 6px 11px;
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
  scroll-margin-top: var(--space-5);
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

.help-category-badge {
  padding: 3px 7px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-tertiary);
  font-size: 0.6875rem;
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
  padding: 12px 14px;
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

.help-text-button {
  justify-self: start;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-size: 0.875rem;
  font-weight: var(--fw-bold);
  cursor: pointer;
}

@media (max-width: 900px) {
  .help-layout {
    grid-template-columns: 1fr;
  }

  .help-toc {
    position: static;
  }

  .help-toc nav {
    display: flex;
    flex-wrap: wrap;
  }

  .help-toc-title {
    flex-basis: 100%;
  }
}

@media (max-width: 680px) {
  .help-guide-grid,
  .help-glossary-grid {
    grid-template-columns: 1fr;
  }

  .help-hero {
    padding: var(--space-4);
  }

  .help-section-heading {
    align-items: center;
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
