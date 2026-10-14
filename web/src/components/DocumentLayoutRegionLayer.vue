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
import { computed, ref } from "vue";
import type { SourceBlock } from "../api/pdfCorpus";
import {
  edgeAt,
  matchRegion,
  moveRegion,
  regionApplies,
  resizeRegion,
  type LayoutRegion,
  type RegionEdge,
} from "../domain/documentLayoutRegions";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(
  defineProps<{
    regions: LayoutRegion[];
    page: number;
    labels: Record<string, string>;
    drawing?: boolean;
    selectedId?: string;
    blocks?: SourceBlock[];
    pageWidth?: number;
    pageHeight?: number;
    disabled?: boolean;
  }>(),
  {
    drawing: false,
    selectedId: "",
    blocks: () => [],
    pageWidth: 0,
    pageHeight: 0,
    disabled: false,
  },
);
const emit = defineEmits<{
  select: [id: string];
  update: [region: LayoutRegion];
  draw: [rect: { x0: number; y0: number; x1: number; y1: number }];
  remove: [id: string];
}>();
const i18n = useI18nStore();
const layer = ref<HTMLElement | null>(null);
const draftRect = ref<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
type Drag =
  | { kind: "move"; id: string; originX: number; originY: number; start: LayoutRegion }
  | { kind: "resize"; id: string; edge: RegionEdge; start: LayoutRegion }
  | { kind: "draw"; x0: number; y0: number };

let drag: Drag | null = null;

const visible = computed(() =>
  props.regions.filter((region) => {
    if (!regionApplies(region, props.page)) return false;
    // The full-page main region is the fallback, not a band the reader should see.
    const span = (region.x1 - region.x0) * (region.y1 - region.y0);
    return !(region.role === "main" && span > 0.9);
  }),
);
const captures = computed(() =>
  props.blocks
    .filter((block) => Number(block.page) === Number(props.page))
    .map((block) => {
      const region = matchRegion(
        props.regions,
        props.page,
        block.bbox,
        props.pageWidth,
        props.pageHeight,
      );
      return { block, role: region?.role || "main" };
    }),
);

function bandStyle(region: { x0: number; y0: number; x1: number; y1: number }) {
  const x0 = Math.min(region.x0, region.x1);
  const y0 = Math.min(region.y0, region.y1);
  const x1 = Math.max(region.x0, region.x1);
  const y1 = Math.max(region.y0, region.y1);
  return {
    insetInlineStart: `${x0 * 100}%`,
    top: `${y0 * 100}%`,
    width: `${(x1 - x0) * 100}%`,
    height: `${(y1 - y0) * 100}%`,
  };
}
function boxStyle(block: SourceBlock) {
  const [x0 = 0, y0 = 0, x1 = 0, y1 = 0] = block.bbox || [];
  const width = Number(props.pageWidth || 0);
  const height = Number(props.pageHeight || 0);
  if (!width || !height) return { display: "none" };
  const left = Math.max(0, Math.min(width, Math.min(Number(x0), Number(x1))));
  const right = Math.max(left, Math.min(width, Math.max(Number(x0), Number(x1))));
  const top = Math.max(0, Math.min(height, Math.min(Number(y0), Number(y1))));
  const bottom = Math.max(top, Math.min(height, Math.max(Number(y0), Number(y1))));
  return {
    insetInlineStart: `${(left / width) * 100}%`,
    top: `${(top / height) * 100}%`,
    width: `${((right - left) / width) * 100}%`,
    height: `${((bottom - top) / height) * 100}%`,
  };
}
function point(event: PointerEvent) {
  const bounds = layer.value?.getBoundingClientRect();
  if (!bounds || bounds.width < 1 || bounds.height < 1) return null;
  return {
    x: Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width)),
    y: Math.min(1, Math.max(0, (event.clientY - bounds.top) / bounds.height)),
  };
}
function onLayerDown(event: PointerEvent) {
  if (props.disabled || !props.drawing || event.button !== 0) return;
  const pt = point(event);
  if (!pt) return;
  drag = { kind: "draw", x0: pt.x, y0: pt.y };
  draftRect.value = { x0: pt.x, y0: pt.y, x1: pt.x, y1: pt.y };
  layer.value?.setPointerCapture?.(event.pointerId);
}
function onBandDown(region: LayoutRegion, event: PointerEvent) {
  if (props.disabled || props.drawing || event.button !== 0) return;
  event.stopPropagation();
  emit("select", region.id);
  const pt = point(event);
  if (!pt) return;
  const target = event.currentTarget as HTMLElement;
  const bounds = target.getBoundingClientRect();
  const edge = edgeAt(
    event.clientX - bounds.left,
    event.clientY - bounds.top,
    bounds.width,
    bounds.height,
  );
  drag = edge
    ? { kind: "resize", id: region.id, edge, start: { ...region } }
    : { kind: "move", id: region.id, originX: pt.x, originY: pt.y, start: { ...region } };
  layer.value?.setPointerCapture?.(event.pointerId);
}
function onMove(event: PointerEvent) {
  if (!drag) return;
  const pt = point(event);
  if (!pt) return;
  if (drag.kind === "move") {
    emit("update", moveRegion(drag.start, pt.x - drag.originX, pt.y - drag.originY));
    return;
  }
  if (drag.kind === "resize") {
    emit("update", resizeRegion(drag.start, drag.edge, pt.x, pt.y));
    return;
  }
  draftRect.value = { x0: drag.x0, y0: drag.y0, x1: pt.x, y1: pt.y };
}
function onUp() {
  if (drag?.kind === "draw" && draftRect.value) {
    const width = Math.abs(draftRect.value.x1 - draftRect.value.x0);
    const height = Math.abs(draftRect.value.y1 - draftRect.value.y0);
    if (width >= 0.03 && height >= 0.03) emit("draw", { ...draftRect.value });
  }
  drag = null;
  draftRect.value = null;
}
function onKey(region: LayoutRegion, event: KeyboardEvent) {
  if (props.disabled) return;
  const step = event.shiftKey ? 0 : 0.01;
  const grow = event.shiftKey ? 0.01 : 0;
  let next = region;
  if (event.key === "ArrowLeft")
    next = grow
      ? resizeRegion(region, "e", region.x1 - grow, region.y1)
      : moveRegion(region, -step, 0);
  else if (event.key === "ArrowRight")
    next = grow
      ? resizeRegion(region, "e", region.x1 + grow, region.y1)
      : moveRegion(region, step, 0);
  else if (event.key === "ArrowUp")
    next = grow
      ? resizeRegion(region, "s", region.x1, region.y1 - grow)
      : moveRegion(region, 0, -step);
  else if (event.key === "ArrowDown")
    next = grow
      ? resizeRegion(region, "s", region.x1, region.y1 + grow)
      : moveRegion(region, 0, step);
  else if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    emit("remove", region.id);
    return;
  } else return;
  event.preventDefault();
  emit("update", next);
}
</script>

<template>
  <div
    ref="layer"
    class="region-layer"
    :class="{ drawing, disabled }"
    role="group"
    :aria-label="i18n.t('pdf_corpus.region_overlay')"
    @pointerdown="onLayerDown"
    @pointermove="onMove"
    @pointerup="onUp"
    @pointercancel="onUp"
  >
    <span
      v-for="item in captures"
      :key="item.block.block_id"
      class="capture"
      :data-role="item.role"
      :style="boxStyle(item.block)"
    ></span>
    <div
      v-for="region in visible"
      :key="region.id"
      class="band"
      :data-role="region.role"
      :data-selected="region.id === selectedId ? 'true' : 'false'"
      :style="bandStyle(region)"
      role="button"
      tabindex="0"
      :aria-label="labels[region.id] || region.role"
      :aria-pressed="region.id === selectedId"
      @pointerdown="onBandDown(region, $event)"
      @keydown="onKey(region, $event)"
      @click.stop="emit('select', region.id)"
    >
      <span class="chip">{{ labels[region.id] || region.role }}</span>
    </div>
    <div v-if="draftRect" class="band draft" :style="bandStyle(draftRect)"></div>
  </div>
</template>

<style scoped>
.region-layer {
  position: absolute;
  inset: 0;
  z-index: 2;
  touch-action: none;
  line-height: 1.3;
}
.region-layer.drawing {
  cursor: crosshair;
}
.region-layer.disabled {
  pointer-events: none;
}
.capture {
  position: absolute;
  pointer-events: none;
  border: 1px solid color-mix(in srgb, var(--accent-fg) 35%, transparent);
  background: color-mix(in srgb, var(--accent-fg) 8%, transparent);
}
.capture[data-role="margin_parallel"],
.capture[data-role="margin_apparatus"] {
  border-color: color-mix(in srgb, var(--tone-warn-border) 70%, transparent);
  background: color-mix(in srgb, var(--tone-warn-bg) 55%, transparent);
}
.capture[data-role="infobox"] {
  border-color: color-mix(in srgb, var(--tone-ok-border) 70%, transparent);
  background: color-mix(in srgb, var(--tone-ok-bg) 55%, transparent);
}
.capture[data-role="block_quote"] {
  border-color: color-mix(in srgb, var(--tone-info-border) 70%, transparent);
  background: color-mix(in srgb, var(--tone-info-bg) 55%, transparent);
}
.capture[data-role="running_matter"] {
  border-color: color-mix(in srgb, var(--muted) 55%, transparent);
  background: color-mix(in srgb, var(--muted) 16%, transparent);
}
.band {
  position: absolute;
  box-sizing: border-box;
  border: 2px solid var(--accent-fg);
  background: color-mix(in srgb, var(--accent-fg) 12%, transparent);
  cursor: grab;
}
.region-layer.drawing .band {
  pointer-events: none;
}
.band[data-role="margin_parallel"],
.band[data-role="margin_apparatus"] {
  border-color: var(--tone-warn-border);
  background: color-mix(in srgb, var(--tone-warn-border) 18%, transparent);
}
.band[data-role="infobox"] {
  border-color: var(--tone-ok-border);
  background: color-mix(in srgb, var(--tone-ok-border) 16%, transparent);
}
.band[data-role="block_quote"] {
  border-color: var(--tone-info-border);
  background: color-mix(in srgb, var(--tone-info-border) 16%, transparent);
}
.band[data-role="running_matter"] {
  border-color: var(--muted);
  background: color-mix(in srgb, var(--muted) 18%, transparent);
}
.band[data-selected="true"] {
  box-shadow: inset 0 0 0 1px var(--surface-overlay);
}
.band.draft {
  border-style: dashed;
  pointer-events: none;
}
.band:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.chip {
  position: absolute;
  inset-inline-start: 4px;
  top: 4px;
  max-width: calc(100% - 8px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 6px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-overlay);
  color: var(--text-primary);
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1.3;
  pointer-events: none;
}
</style>
