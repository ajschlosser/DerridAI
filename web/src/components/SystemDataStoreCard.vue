<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "./AppIcon.vue";

defineProps<{
  icon: string;
  title: string;
  detail: string;
  technical?: string;
  status: string;
  count?: string;
  sensitive?: boolean;
  actionLabel: string;
}>();
defineEmits<{ open: [] }>();
</script>

<template>
  <article class="system-store-card" :class="{ sensitive }">
    <div class="store-icon" aria-hidden="true"><AppIcon :name="icon" /></div>
    <div class="store-copy">
      <div class="store-heading">
        <h3>{{ title }}</h3>
        <span class="store-status"><span class="status-dot" />{{ status }}</span>
      </div>
      <p>{{ detail }}</p>
      <small v-if="technical">{{ technical }}</small>
    </div>
    <div class="store-action">
      <strong v-if="count">{{ count }}</strong>
      <button class="btn tiny" type="button" @click="$emit('open')">
        {{ actionLabel }}
        <AppIcon name="chevron-right" />
      </button>
    </div>
  </article>
</template>

<style scoped>
.system-store-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: start;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.system-store-card.sensitive { border-style: dashed; }
.store-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: var(--soft);
}
.store-icon :deep(svg) { width: 21px; height: 21px; }
.store-copy { min-width: 0; }
.store-heading { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
h3 { margin: 0; font-size: .98rem; }
p { margin: 5px 0 0; color: var(--muted); line-height: 1.45; }
small { display: block; margin-top: 7px; color: var(--muted); overflow-wrap: anywhere; }
.store-status {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-size: .75rem;
  color: var(--muted);
}
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.store-action { display: grid; gap: 8px; justify-items: end; }
.store-action strong { font-size: 1.05rem; }
.store-action :deep(svg) { width: 14px; height: 14px; }
@media (max-width: 640px) {
  .system-store-card { grid-template-columns: 38px minmax(0,1fr); }
  .store-action { grid-column: 2; width: 100%; display: flex; justify-content: space-between; align-items: center; }
}
</style>
