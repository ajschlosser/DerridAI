<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, useId } from "vue";

const props = withDefaults(defineProps<{
  label: string;
  hint?: string;
  error?: string;
  wide?: boolean;
  required?: boolean;
  persistence?: string;
}>(), {hint: "", error: "", wide: false, required: false, persistence: ""});

const generatedId = useId();
const hintId = computed(() => `${generatedId}-hint`);
const errorId = computed(() => `${generatedId}-error`);
const describedby = computed(() => [props.hint ? hintId.value : "", props.error ? errorId.value : ""].filter(Boolean).join(" ") || undefined);
</script>
<template>
  <label class="ui-field" :class="{wide, invalid: Boolean(error)}">
    <span class="ui-field-label">
      {{ label }}
      <span v-if="required" class="ui-field-required" aria-hidden="true"> *</span>
      <span v-if="persistence" class="ui-field-persist">{{ persistence }}</span>
    </span>
    <slot :describedby="describedby" :invalid="Boolean(error)" />
    <span v-if="hint" :id="hintId" class="ui-field-hint">{{ hint }}</span>
    <span v-if="error" :id="errorId" class="ui-field-error" role="alert">{{ error }}</span>
  </label>
</template>
<style scoped>
.ui-field{display:grid;gap:6px;min-width:0}
.ui-field.wide{grid-column:1/-1}
.ui-field-label{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;font-size:.8125rem;font-weight:700;color:var(--text)}
.ui-field-required{color:var(--danger)}
.ui-field-persist{margin-left:auto;font-weight:650;color:var(--muted);font-size:.8125rem;letter-spacing:.02em;text-transform:uppercase}
.ui-field-hint{font-size:.8125rem;line-height:1.45;color:var(--muted)}
.ui-field-error{font-size:.8125rem;line-height:1.45;color:var(--danger);font-weight:700}
.ui-field.invalid :deep(input),.ui-field.invalid :deep(select),.ui-field.invalid :deep(textarea){border-color:var(--danger)}
</style>
