<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import { useI18nStore } from "../../stores/i18n";
const i18n = useI18nStore();
const emit = defineEmits<{ search: []; works: [] }>();
</script>
<template>
  <section class="hero card" aria-labelledby="home-page-title">
    <img src="/brand/derridai-mark.png" class="hero-mark" alt="" />
    <div>
      <p class="section-label">{{ i18n.t("nav.home", "Home") }}</p>
      <h1 id="home-page-title">{{ i18n.t("dashboard.welcome", "Welcome to DerridAI") }}</h1>
      <p>{{ i18n.t("dashboard.tagline", "Search. Compare. Annotate. Always already.") }}</p>
      <blockquote>{{ i18n.t("dashboard.quote", "“Il n’y a pas de hors-texte.”") }}</blockquote>
      <small>{{ i18n.t("dashboard.quote_attribution", "— Jacques Derrida") }}</small>
      <div class="actions">
        <UiButton
          variant="primary"
          icon="search"
          :label="i18n.t('dashboard.start_searching', 'Start searching')"
          @click="emit('search')"
        /><UiButton
          icon="books"
          :label="i18n.t('dashboard.browse_works', 'Browse works')"
          @click="emit('works')"
        />
      </div>
    </div>
  </section>
</template>
<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(140px, 0.45fr) 1fr;
  gap: var(--space-5);
  align-items: center;
  padding: var(--space-6);
}
.hero-mark {
  max-width: 100%;
  height: 180px;
  object-fit: contain;
}
.hero h1 {
  margin: 0;
  color: var(--text);
  font-size: var(--fs-2xl);
  line-height: var(--lh-tight);
}
.hero p,
.hero blockquote {
  color: var(--text-2);
}
.hero blockquote {
  margin: var(--space-4) 0 var(--space-1);
  font-family: var(--font-reading);
  font-style: italic;
}
.hero small {
  color: var(--muted);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-5);
}
@media (max-width: 620px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero-mark {
    height: 120px;
    margin: auto;
  }
}
</style>
