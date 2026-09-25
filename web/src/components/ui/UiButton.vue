<script setup lang="ts">
import AppIcon from "../AppIcon.vue";

const props = withDefaults(
  defineProps<{
    label?: string;
    icon?: string;
    variant?: "default" | "primary" | "soft" | "danger" | "ghost";
    size?: "default" | "small";
    disabled?: boolean;
    disabledReason?: string;
    count?: number;
    type?: "button" | "submit" | "reset";
    iconOnly?: boolean;
    pressed?: boolean;
  }>(),
  {
    label: "",
    icon: "",
    variant: "default",
    size: "default",
    disabled: false,
    disabledReason: "",
    count: 0,
    type: "button",
    iconOnly: false,
    pressed: undefined,
  },
);

const emit = defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <span class="ui-button-wrap" :data-tooltip="props.disabled ? props.disabledReason : ''">
    <button
      class="ui-button"
      :class="[`variant-${props.variant}`, `size-${props.size}`, { 'icon-only': props.iconOnly }]"
      :type="props.type"
      :disabled="props.disabled"
      :aria-disabled="props.disabled || undefined"
      :aria-pressed="props.pressed"
      :aria-label="props.iconOnly ? props.label : undefined"
      :title="props.disabled ? props.disabledReason : props.iconOnly ? props.label : undefined"
      @click="emit('click', $event)"
    >
      <AppIcon v-if="props.icon" :name="props.icon" aria-hidden="true" />
      <span v-if="!props.iconOnly"
        ><slot>{{ props.label }}</slot></span
      >
      <slot v-else name="icon-label" />
      <span v-if="props.count" class="ui-button-count" aria-hidden="true">{{ props.count }}</span>
      <span v-if="props.count" class="sr-only">{{ props.count }}</span>
    </button>
  </span>
</template>

<style scoped>
.ui-button-wrap {
  display: inline-flex;
  position: relative;
}
.ui-button {
  min-height: var(--control-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  padding: 8px 13px;
  background: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 700;
  line-height: 1.2;
  box-shadow: var(--shadow-card);
  transition:
    background var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}
.ui-button:hover:not(:disabled) {
  background: var(--surface-hover);
  border-color: var(--border-interactive);
  box-shadow: var(--elev-2);
  transform: translateY(-1px);
}
.ui-button:active:not(:disabled) {
  transform: none;
}
.ui-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.ui-button:disabled {
  background: var(--surface-disabled);
  opacity: 0.72;
  cursor: not-allowed;
  box-shadow: none;
}
.ui-button.variant-primary {
  background: var(--accent);
  color: var(--accent-on);
  border-color: var(--accent);
}
.ui-button.variant-primary:hover:not(:disabled) {
  background: var(--accent-2);
  border-color: var(--accent-2);
}
.ui-button.variant-soft {
  background: var(--surface-selected);
  color: var(--accent-fg);
  border-color: var(--border-interactive);
}
.ui-button.variant-danger {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  border-color: var(--tone-danger-border);
}
.ui-button.variant-ghost {
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}
.ui-button.variant-ghost:hover:not(:disabled) {
  background: var(--surface-hover);
  border-color: var(--border-subtle);
}
.ui-button.size-small {
  min-height: var(--control-height-small);
  padding: 6px 10px;
  font-size: 0.8125rem;
}
.ui-button.icon-only {
  width: var(--control-height);
  padding: 0;
}
.ui-button.size-small.icon-only {
  width: var(--control-height-small);
}
.ui-button :deep(svg) {
  width: 16px;
  height: 16px;
}
.ui-button-count {
  min-width: 1.55em;
  padding: 1px 5px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  font-size: 0.75rem;
  text-align: center;
}
@media (prefers-reduced-motion: reduce) {
  .ui-button {
    transition: none;
  }
  .ui-button:hover:not(:disabled) {
    transform: none;
  }
}
</style>
