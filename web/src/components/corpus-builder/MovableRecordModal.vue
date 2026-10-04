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
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{ text: string; recordId: string }>();
const emit = defineEmits<{ close: [] }>();
const i18n = useI18nStore();
const dialog = ref<HTMLElement | null>(null);
const position = ref({ x: 0, y: 0 });
const dragging = ref(false);
let pointerId: number | null = null;
let priorActive: HTMLElement | null = null;
let origin = { x: 0, y: 0, left: 0, top: 0 };

function focusables() {
  if (!dialog.value) return [] as HTMLElement[];
  return Array.from(
    dialog.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])',
    ),
  ).filter((node) => node.offsetParent !== null);
}

function beginDrag(event: PointerEvent) {
  if (event.button !== 0 || (event.target as HTMLElement | null)?.closest("button")) return;
  pointerId = event.pointerId;
  origin = {
    x: event.clientX,
    y: event.clientY,
    left: position.value.x,
    top: position.value.y,
  };
  dragging.value = true;
  const target = event.currentTarget as HTMLElement;
  target.setPointerCapture?.(event.pointerId);
}
function moveDrag(event: PointerEvent) {
  if (!dragging.value || event.pointerId !== pointerId) return;
  position.value = {
    x: origin.left + event.clientX - origin.x,
    y: origin.top + event.clientY - origin.y,
  };
}
function endDrag(event: PointerEvent) {
  if (event.pointerId !== pointerId) return;
  dragging.value = false;
  pointerId = null;
}
function moveFromKeyboard(event: KeyboardEvent) {
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
  event.preventDefault();
  const step = event.shiftKey ? 48 : 16;
  position.value = {
    x:
      position.value.x +
      (event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0),
    y:
      position.value.y +
      (event.key === "ArrowDown" ? step : event.key === "ArrowUp" ? -step : 0),
  };
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (event.key !== "Tab") return;
  const nodes = focusables();
  if (!nodes.length) {
    event.preventDefault();
    dialog.value?.focus();
    return;
  }
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  if (
    event.shiftKey &&
    (document.activeElement === first || document.activeElement === dialog.value)
  ) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

onMounted(() => {
  priorActive = document.activeElement as HTMLElement | null;
  void nextTick(() => dialog.value?.focus());
});
onBeforeUnmount(() => {
  dragging.value = false;
  pointerId = null;
  priorActive?.focus?.({ preventScroll: true });
});
</script>

<template>
  <div class="record-popout-backdrop" @click.self="emit('close')">
    <article
      ref="dialog"
      class="record-popout"
      role="dialog"
      aria-modal="true"
      :aria-label="`${i18n.t('pdf_corpus.reviewed_record_text')} ${props.recordId}`"
      tabindex="-1"
      :style="{ transform: `translate(${position.x}px, ${position.y}px)` }"
      @keydown="onKeydown"
    >
      <header
        class="record-popout-head"
        :class="{ dragging }"
        tabindex="0"
        :aria-label="`${i18n.t('pdf_corpus.reviewed_record_text')} ${props.recordId}`"
        aria-keyshortcuts="ArrowLeft ArrowRight ArrowUp ArrowDown"
        @keydown="moveFromKeyboard"
        @pointerdown="beginDrag"
        @pointermove="moveDrag"
        @pointerup="endDrag"
        @pointercancel="endDrag"
      >
        <b>{{ props.recordId }}</b>
        <button
          type="button"
          class="btn small"
          :aria-label="i18n.t('ui.close')"
          @click="emit('close')"
        >
          {{ i18n.t("ui.close") }}
        </button>
      </header>
      <div class="record-popout-body" tabindex="0" data-record-text>{{ props.text }}</div>
    </article>
  </div>
</template>

<style scoped>
.record-popout-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 4vh 4vw;
  background: color-mix(in srgb, var(--text) 48%, transparent);
}
.record-popout {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  inline-size: min(900px, 92vw);
  block-size: min(720px, 86vh);
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-panel);
  background: var(--surface-raised);
  box-shadow: var(--shadow-overlay);
}
.record-popout-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.7rem 1rem;
  border-block-end: 1px solid var(--line);
  background: var(--surface-overlay);
  cursor: move;
  touch-action: none;
}
.record-popout-head.dragging {
  cursor: grabbing;
}
.record-popout-body {
  overflow: auto;
  padding: 1.25rem 1.5rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 1rem;
  line-height: 1.7;
}
</style>
