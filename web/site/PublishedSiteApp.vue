<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import UiSelect from "../src/components/ui/UiSelect.vue";
import PublishedNotesView from "./PublishedNotesView.vue";
import PublishedProvidersView from "./PublishedProvidersView.vue";
import PublishedRecordDialog from "./PublishedRecordDialog.vue";
import PublishedResearchView from "./PublishedResearchView.vue";
import PublishedSearchView from "./PublishedSearchView.vue";
import PublishedTutorial from "./PublishedTutorial.vue";
import PublishedWorksView from "./PublishedWorksView.vue";
import {
  createPublishedSiteContext,
  providePublishedSiteContext,
  type PublishedSiteView,
} from "./siteContext";

const site = createPublishedSiteContext();
providePublishedSiteContext(site);

const ready = ref(false);
const error = ref("");
const tutorialOpen = ref(false);

const publicationSummary = computed(() =>
  site.t("site.runtime.publication_summary", {
    works: (site.publication.works || []).length,
    records: site.recordCount.value,
    date: site.formatDate(site.publication.created_at),
  }),
);

async function initialize() {
  try {
    await site.initialize();
    ready.value = true;
    await nextTick();
    if (!site.tutorialSeen.value) tutorialOpen.value = true;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : String(caught);
  }
}

function setView(view: PublishedSiteView) {
  site.view.value = view;
}

function focusMain() {
  window.setTimeout(() => document.getElementById("site-main")?.focus(), 0);
}

async function changeLocale(event: Event) {
  await site.setLocaleAndRebuild((event.target as HTMLSelectElement).value);
}

onMounted(initialize);
</script>

<template>
  <div v-if="error" class="main">
    <div class="panel status error" role="alert">{{ error }}</div>
  </div>

  <div v-else-if="!ready" class="main" role="status" aria-live="polite">
    {{ site.t("site.runtime.loading_site") }}
  </div>

  <div v-else class="shell">
    <a class="skip-link" href="#site-main" @click="focusMain">
      {{ site.t("site.runtime.skip_to_content") }}
    </a>

    <header class="top">
      <div class="top-inner">
        <div class="brand">
          <strong>{{ site.publication.title || site.t("site.runtime.site_title") }}</strong>
          <small>{{ site.t("site.runtime.powered_by") }}</small>
        </div>

        <nav data-tour="nav" :aria-label="site.t('site.runtime.navigation')">
          <button
            type="button"
            :aria-current="site.view.value === 'search' ? 'page' : undefined"
            @click="setView('search')"
          >
            {{ site.t("site.runtime.search") }}
          </button>
          <button
            type="button"
            :aria-current="site.view.value === 'works' ? 'page' : undefined"
            @click="setView('works')"
          >
            {{ site.t("site.runtime.works") }}
          </button>
          <button
            type="button"
            :aria-current="site.view.value === 'research' ? 'page' : undefined"
            @click="setView('research')"
          >
            {{ site.t("site.runtime.research") }}
          </button>
          <button
            type="button"
            :aria-current="site.view.value === 'providers' ? 'page' : undefined"
            @click="setView('providers')"
          >
            {{ site.t("site.runtime.providers") }}
          </button>
          <button
            type="button"
            :aria-current="site.view.value === 'notes' ? 'page' : undefined"
            @click="setView('notes')"
          >
            {{ site.t("site.runtime.annotations") }}
          </button>
        </nav>

        <div
          class="header-controls"
          data-tour="controls"
          role="group"
          :aria-label="site.t('site.runtime.display_controls')"
        >
          <label class="compact-field">
            <span>{{ site.t("site.runtime.language") }}</span>
            <UiSelect
              :model-value="site.locale.value"
              class="control"
              :aria-label="site.t('site.runtime.language')"
              @change="changeLocale"
            >
              <option v-for="code in site.availableLocales" :key="code" :value="code">
                {{ site.languageLabel(code) }}
              </option>
            </UiSelect>
          </label>

          <label class="compact-field">
            <span>{{ site.t("site.runtime.theme") }}</span>
            <UiSelect
              :model-value="site.theme.value"
              class="control"
              :aria-label="site.t('site.runtime.theme')"
              @change="site.setTheme(($event.target as HTMLSelectElement).value)"
            >
              <option value="light">{{ site.t("site.runtime.theme_light") }}</option>
              <option value="dark">{{ site.t("site.runtime.theme_dark") }}</option>
            </UiSelect>
          </label>

          <label class="toggle">
            <input
              type="checkbox"
              :checked="site.highContrast.value"
              @change="site.setHighContrast(($event.target as HTMLInputElement).checked)"
            />
            <span>{{ site.t("site.runtime.high_contrast") }}</span>
          </label>

          <button
            type="button"
            data-tour="tutorial"
            @click="tutorialOpen = true"
          >
            {{ site.t("site.runtime.tutorial") }}
          </button>
        </div>
      </div>
    </header>

    <main id="site-main" class="main" tabindex="-1">
      <section class="hero" aria-labelledby="site-title">
        <h1 id="site-title">{{ site.publication.title || site.t("site.runtime.site_title") }}</h1>
        <p v-if="site.publication.description">{{ site.publication.description }}</p>
      </section>

      <PublishedSearchView v-if="site.view.value === 'search'" />
      <PublishedWorksView v-else-if="site.view.value === 'works'" />
      <PublishedResearchView v-else-if="site.view.value === 'research'" />
      <PublishedProvidersView v-else-if="site.view.value === 'providers'" />
      <PublishedNotesView v-else-if="site.view.value === 'notes'" />

      <footer class="footer">{{ publicationSummary }}</footer>
    </main>

    <PublishedRecordDialog />
    <PublishedTutorial :open="tutorialOpen" @close="tutorialOpen = false" />
  </div>
</template>
