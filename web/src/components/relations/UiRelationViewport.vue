<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, useId, watch } from "vue";
import { useRelationResize } from "../../composables/relations/useRelationResize";
import { useRelationViewport } from "../../composables/relations/useRelationViewport";
import type {
  RelationBounds,
  RelationPoint,
  RelationSize,
  RelationViewportState,
} from "../../domain/relations/types";
import UiRelationResizeHandle from "./UiRelationResizeHandle.vue";

const props = withDefaults(
  defineProps<{
    accessibleLabel: string;
    helpText?: string;
    resizeLabel: string;
    minZoom?: number;
    maxZoom?: number;
    initialZoom?: number;
    initialCenter?: RelationPoint | null;
    contentBounds?: RelationBounds | null;
    fitPadding?: number;
    contentWidth?: number;
    contentHeight?: number;
    resizable?: boolean;
    resizeAxis?: "horizontal" | "vertical" | "both";
    minWidth?: number;
    maxWidth?: number;
    minHeight?: number;
    maxHeight?: number;
    layerMarker?: string;
  }>(),
  {
    helpText: "",
    minZoom: 0.45,
    maxZoom: 6,
    initialZoom: 1,
    initialCenter: null,
    contentBounds: null,
    fitPadding: 32,
    contentWidth: 0,
    contentHeight: 0,
    resizable: true,
    resizeAxis: "both",
    minWidth: 280,
    maxWidth: Number.POSITIVE_INFINITY,
    minHeight: 220,
    maxHeight: 900,
    layerMarker: "",
  },
);

const emit = defineEmits<{
  viewportChange: [state: RelationViewportState];
  resize: [size: RelationSize | null];
}>();

const helpId = useId();
const surface = ref<HTMLElement | null>(null);

const viewport = useRelationViewport({
  minZoom: props.minZoom,
  maxZoom: props.maxZoom,
  initialZoom: props.initialZoom,
});
const resize = useRelationResize({
  minWidth: props.minWidth,
  maxWidth: props.maxWidth,
  minHeight: props.minHeight,
  maxHeight: props.maxHeight,
});

const viewportStyle = computed<Record<string, string>>(() => {
  if (!resize.size.value) return {};
  const style: Record<string, string> = {};
  if (props.resizeAxis !== "vertical") {
    style.width = `${resize.size.value.width}px`;
    style.maxWidth = "100%";
  }
  if (props.resizeAxis !== "horizontal") style.height = `${resize.size.value.height}px`;
  return style;
});

const layerStyle = computed(() => ({
  transform: `translate(${viewport.pan.value.x}px, ${viewport.pan.value.y}px) scale(${viewport.zoom.value})`,
  width: props.contentWidth > 0 ? `${props.contentWidth}px` : undefined,
  height: props.contentHeight > 0 ? `${props.contentHeight}px` : undefined,
}));

const layerAttributes = computed<Record<string, string>>(() =>
  props.layerMarker ? { [props.layerMarker]: "" } : {},
);

watch(
  () => viewport.state.value,
  (state) => emit("viewportChange", state),
  { deep: true },
);
watch(
  () => resize.size.value,
  (size) => emit("resize", size),
  { deep: true },
);

function viewportSize(): RelationSize {
  const box = surface.value?.getBoundingClientRect();
  return {
    width: box?.width || 640,
    height: box?.height || 420,
  };
}

function localPoint(event: WheelEvent | MouseEvent): RelationPoint {
  const box = surface.value?.getBoundingClientRect();
  return {
    x: event.clientX - (box?.left || 0),
    y: event.clientY - (box?.top || 0),
  };
}

function centerOnPoint(point: RelationPoint, nextZoom = viewport.zoom.value) {
  viewport.centerOn(point, viewportSize(), nextZoom);
}

function centerInitial(nextZoom = props.initialZoom) {
  if (props.initialCenter) {
    centerOnPoint(props.initialCenter, nextZoom);
    return;
  }
  viewport.setState({ pan: { x: 0, y: 0 }, zoom: nextZoom });
}

function resetView() {
  centerInitial(props.initialZoom);
}

function fitView(bounds: RelationBounds | null = props.contentBounds) {
  if (!bounds) {
    centerInitial(viewport.zoom.value);
    return;
  }
  viewport.fit(bounds, viewportSize(), props.fitPadding);
}

function zoomBy(factor: number, anchor?: RelationPoint) {
  const target = anchor ?? {
    x: viewportSize().width / 2,
    y: viewportSize().height / 2,
  };
  viewport.zoomBy(factor, target);
}

function onWheel(event: WheelEvent) {
  const factor = event.deltaY < 0 ? 1.15 : 1 / 1.15;
  zoomBy(factor, localPoint(event));
}

function onPointerDown(event: PointerEvent) {
  const target = event.target as Element | null;
  if (
    target?.closest?.(
      "[data-relation-node],[data-relation-resize-handle],[data-relation-ignore-pan]",
    )
  ) {
    return;
  }
  viewport.beginPan(event);
}

function onKeydown(event: KeyboardEvent) {
  if (event.target !== event.currentTarget) return;
  if (event.key === "0") {
    resetView();
    event.preventDefault();
    return;
  }
  viewport.handleViewportKeydown(event);
}

function currentSize(): RelationSize {
  const box = surface.value?.getBoundingClientRect();
  return {
    width: box?.width || props.minWidth,
    height: box?.height || props.minHeight,
  };
}

function onResizeStart(event: PointerEvent) {
  resize.begin(event, currentSize(), props.resizeAxis);
}

function onResizeKeydown(event: KeyboardEvent) {
  resize.keyboardResize(event, resize.size.value ?? currentSize(), props.resizeAxis);
}

onMounted(() => centerInitial());

defineExpose({
  pan: viewport.pan,
  zoom: viewport.zoom,
  zoomBy,
  fitView,
  resetView,
  centerOn: centerOnPoint,
  setViewport: viewport.setState,
  resetSize: resize.resetSize,
});
</script>

<template>
  <div
    ref="surface"
    class="ui-relation-viewport"
    :class="{ panning: viewport.panning.value, resizing: resize.resizing.value }"
    :style="viewportStyle"
    role="region"
    tabindex="0"
    :aria-label="accessibleLabel"
    :aria-describedby="helpText ? helpId : undefined"
    @pointerdown="onPointerDown"
    @pointermove="viewport.updatePan"
    @pointerup="viewport.endPan"
    @pointercancel="viewport.endPan"
    @wheel.prevent="onWheel"
    @keydown="onKeydown"
  >
    <p v-if="helpText" :id="helpId" class="sr-only">{{ helpText }}</p>
    <div
      class="ui-relation-viewport-layer"
      data-relation-viewport-layer
      v-bind="layerAttributes"
      :style="layerStyle"
    >
      <slot :pan="viewport.pan.value" :zoom="viewport.zoom.value" />
    </div>
    <UiRelationResizeHandle
      v-if="resizable"
      :label="resizeLabel"
      :axis="resizeAxis"
      @pointerdown="onResizeStart"
      @pointermove="resize.update"
      @pointerup="resize.end"
      @pointercancel="resize.end"
      @keydown="onResizeKeydown"
    />
  </div>
</template>

<style scoped>
.ui-relation-viewport {
  position: relative;
  min-width: 0;
  height: var(--relation-viewport-height, auto);
  min-height: 220px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.ui-relation-viewport.panning {
  cursor: grabbing;
}
.ui-relation-viewport:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.ui-relation-viewport-layer {
  position: absolute;
  inset: 0 auto auto 0;
  transform-origin: 0 0;
  will-change: transform;
}
@media (prefers-reduced-motion: reduce) {
  .ui-relation-viewport-layer {
    will-change: auto;
  }
}
</style>
