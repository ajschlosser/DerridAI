<script setup lang="ts">
import AppIcon from "../AppIcon.vue";

const props = withDefaults(defineProps<{
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
}>(), {
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
});

const emit = defineEmits<{ click:[event:MouseEvent] }>();
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
      :title="props.disabled ? props.disabledReason : (props.iconOnly ? props.label : undefined)"
      @click="emit('click',$event)"
    >
      <AppIcon v-if="props.icon" :name="props.icon" aria-hidden="true" />
      <span v-if="!props.iconOnly"><slot>{{ props.label }}</slot></span>
      <slot v-else name="icon-label" />
      <span v-if="props.count" class="ui-button-count" aria-hidden="true">{{ props.count }}</span>
      <span v-if="props.count" class="sr-only">{{ props.count }}</span>
    </button>
  </span>
</template>

<style scoped>
.ui-button-wrap{display:inline-flex;position:relative}.ui-button{min-height:40px;display:inline-flex;align-items:center;justify-content:center;gap:7px;border:1px solid var(--line-strong);border-radius:var(--radius-sm);padding:8px 12px;background:var(--panel);color:var(--text);font-size:.875rem;font-weight:700;line-height:1.2;box-shadow:0 1px 1px rgba(23,29,26,.025);transition:background .12s ease,border-color .12s ease,box-shadow .12s ease,transform .12s ease}.ui-button:hover:not(:disabled){background:var(--panel-2);border-color:#aeb7af;box-shadow:0 3px 10px rgba(30,40,34,.06);transform:translateY(-1px)}.ui-button:active:not(:disabled){transform:none}.ui-button:focus-visible{outline:3px solid var(--focus-ring);outline-offset:2px}.ui-button:disabled{opacity:.55;cursor:not-allowed;box-shadow:none}.ui-button.variant-primary{background:var(--accent);color:#fff;border-color:var(--accent)}.ui-button.variant-primary:hover:not(:disabled){background:var(--accent-2);border-color:var(--accent-2)}.ui-button.variant-soft{background:var(--accent-soft);color:var(--accent-2);border-color:#c2d6cc}.ui-button.variant-danger{background:var(--danger-bg);color:var(--danger);border-color:#dfbcbc}.ui-button.variant-ghost{background:transparent;border-color:transparent;box-shadow:none}.ui-button.variant-ghost:hover:not(:disabled){background:var(--panel-2);border-color:var(--line)}.ui-button.size-small{min-height:36px;padding:6px 10px;font-size:.8125rem}.ui-button.icon-only{width:40px;padding:0}.ui-button.size-small.icon-only{width:36px}.ui-button :deep(svg){width:16px;height:16px}.ui-button-count{min-width:1.55em;padding:1px 5px;border-radius:999px;background:rgba(0,0,0,.08);font-size:.75rem;text-align:center}@media (prefers-reduced-motion:reduce){.ui-button{transition:none}.ui-button:hover:not(:disabled){transform:none}}
</style>
