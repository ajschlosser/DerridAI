<script setup lang="ts">
import { useId } from "vue";

// One titled group of fields on a metadata form. Edit document metadata and Bulk edit share this so the two
// forms look and read the same: a heading with a line of help, then a two-column grid that collapses on a phone.
defineProps<{ title: string; description?: string }>();
const id = useId();
</script>

<template>
  <section class="metadata-form-section" :aria-labelledby="id">
    <header>
      <h3 :id="id">{{ title }}</h3>
      <p v-if="description">{{ description }}</p>
    </header>
    <div class="metadata-form-grid"><slot /></div>
  </section>
</template>

<style scoped>
.metadata-form-section { display: grid; gap: 12px; }
.metadata-form-section > header { display: grid; gap: 4px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
h3 { margin: 0; font-size: 1rem; }
p { margin: 0; color: var(--muted); font-size: 0.875rem; line-height: 1.5; }
.metadata-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 16px; }
.metadata-form-grid :deep(.wide) { grid-column: 1 / -1; }
@media (max-width: 720px) { .metadata-form-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
