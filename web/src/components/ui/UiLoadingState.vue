<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string;
    detail?: string;
    variant?: "status" | "skeleton" | "inline";
    skeletonCount?: number;
  }>(),
  { detail: "", variant: "status", skeletonCount: 3 },
);
</script>

<template>
  <section
    class="ui-loading-state"
    :class="`is-${variant}`"
    role="status"
    aria-live="polite"
    aria-atomic="true"
  >
    <div class="ui-loading-copy">
      <span class="ui-loading-indicator" aria-hidden="true"></span>
      <div>
        <strong>{{ label }}</strong>
        <p v-if="detail">{{ detail }}</p>
      </div>
    </div>
    <div v-if="variant === 'skeleton'" class="ui-loading-skeletons" aria-hidden="true">
      <div v-for="index in skeletonCount" :key="index" class="ui-loading-skeleton">
        <span></span><span></span><span></span>
      </div>
    </div>
    <slot />
  </section>
</template>

<style scoped>
.ui-loading-state {
  display: grid;
  gap: var(--space-4, 16px);
  color: var(--text-primary);
}

.ui-loading-state.is-inline {
  display: flex;
  padding-block: var(--space-2, 8px);
}

.ui-loading-state.is-status {
  min-block-size: 96px;
  place-content: center;
  padding: var(--space-5, 24px);
  text-align: center;
}

.ui-loading-copy {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: var(--space-3, 12px);
  text-align: start;
}

.ui-loading-copy strong {
  display: block;
  font-size: var(--fs-base, 0.875rem);
  line-height: var(--lh-tight, 1.25);
}

.ui-loading-copy p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm, 0.8125rem);
  line-height: var(--lh-normal, 1.5);
}

.ui-loading-indicator {
  flex: 0 0 auto;
  inline-size: 18px;
  block-size: 18px;
  margin-block-start: 1px;
  border: 2px solid var(--border-interactive);
  border-block-start-color: transparent;
  border-radius: 50%;
  animation:
    ui-loading-reveal 0s 180ms both,
    ui-loading-spin 800ms 180ms linear infinite;
}

.ui-loading-skeletons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3, 12px);
}

.ui-loading-skeleton {
  display: grid;
  gap: 10px;
  min-block-size: 104px;
  padding: var(--space-4, 16px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card, 12px);
  background: var(--surface-inset);
}

.ui-loading-skeleton span {
  display: block;
  block-size: 10px;
  border-radius: var(--radius-pill, 999px);
  background: var(--border-subtle);
}

.ui-loading-skeleton span:first-child {
  inline-size: 68%;
  block-size: 16px;
}

.ui-loading-skeleton span:last-child {
  inline-size: 54%;
}

@keyframes ui-loading-reveal {
  from {
    visibility: hidden;
  }
  to {
    visibility: visible;
  }
}

@keyframes ui-loading-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ui-loading-indicator {
    animation: none;
    border-block-start-color: var(--border-interactive);
  }
}

@media (forced-colors: active) {
  .ui-loading-indicator,
  .ui-loading-skeleton {
    border-color: CanvasText;
  }

  .ui-loading-indicator {
    border-block-start-color: transparent;
  }

  .ui-loading-skeleton span {
    background: CanvasText;
  }
}
</style>
