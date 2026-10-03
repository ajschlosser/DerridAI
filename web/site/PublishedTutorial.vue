<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import { type PublishedSiteView, usePublishedSite } from "./siteContext";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();
const site = usePublishedSite();

const steps: Array<{
  id: string;
  target?: string;
  view?: PublishedSiteView;
}> = [
  { id: "welcome" },
  { id: "nav", target: "nav" },
  { id: "works", view: "works", target: "works" },
  { id: "search", view: "search", target: "search" },
  { id: "filters", view: "search", target: "filters" },
  { id: "methods", view: "search", target: "methods" },
  { id: "research", view: "research", target: "research" },
  { id: "provider", view: "providers", target: "provider" },
  { id: "evidence", view: "research", target: "evidence" },
  { id: "notes", view: "notes", target: "notes" },
  { id: "controls", target: "controls" },
  { id: "restart", target: "tutorial" },
];

const dialog = ref<HTMLDialogElement | null>(null);
const spot = ref<HTMLElement | null>(null);
const card = ref<HTMLElement | null>(null);
const index = ref(0);
const centered = ref(true);
const dockClass = ref("");
const currentTarget = ref<HTMLElement | null>(null);
const busy = ref(false);
let startView: PublishedSiteView = "search";
let priorActive: HTMLElement | null = null;
let outcome: "done" | "skipped" = "skipped";
let queued = 0;

const step = computed(() => steps[index.value]);
const title = computed(() => site.t(`site.runtime.tutorial_${step.value.id}_title`));
const body = computed(() => site.t(`site.runtime.tutorial_${step.value.id}_body`));
const progress = computed(() =>
  site.t("site.runtime.tutorial_progress", {
    current: index.value + 1,
    total: steps.length,
  }),
);
const fillWidth = computed(() => `${((index.value + 1) / steps.length) * 100}%`);
const nextLabel = computed(() =>
  index.value === steps.length - 1
    ? site.t("site.runtime.finish")
    : site.t("site.runtime.next"),
);

function resetCardPosition() {
  if (!card.value) return;
  card.value.style.top = "";
  card.value.style.left = "";
}

function place() {
  const target = currentTarget.value;
  const targetRect = target?.getBoundingClientRect() || null;
  const shouldCenter = !targetRect || (targetRect.width === 0 && targetRect.height === 0);
  centered.value = shouldCenter;
  dockClass.value = "";
  resetCardPosition();
  if (shouldCenter || !spot.value || !card.value || !targetRect) return;

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const pad = 6;
  const edge = 8;
  const gap = 14;
  const box = {
    left: Math.max(targetRect.left - pad, 4),
    top: Math.max(targetRect.top - pad, 4),
    right: Math.min(targetRect.right + pad, viewportWidth - 4),
    bottom: Math.min(targetRect.bottom + pad, viewportHeight - 4),
  };

  Object.assign(spot.value.style, {
    left: `${box.left}px`,
    top: `${box.top}px`,
    width: `${Math.max(box.right - box.left, 0)}px`,
    height: `${Math.max(box.bottom - box.top, 0)}px`,
  });

  const width = card.value.offsetWidth;
  const height = card.value.offsetHeight;
  const clampLeft = (value: number) =>
    Math.min(Math.max(value, edge), Math.max(viewportWidth - width - edge, edge));
  const clampTop = (value: number) =>
    Math.min(Math.max(value, edge), Math.max(viewportHeight - height - edge, edge));
  const put = (left: number, top: number) => {
    if (!card.value) return;
    card.value.style.left = `${clampLeft(left)}px`;
    card.value.style.top = `${clampTop(top)}px`;
  };
  const dock = () => {
    dockClass.value =
      box.bottom + edge + height > viewportHeight && box.top - edge >= height
        ? "tour-dock-top"
        : "tour-dock";
  };

  if (viewportWidth <= 760) dock();
  else if (viewportHeight - box.bottom - gap - edge >= height) put(box.left, box.bottom + gap);
  else if (box.top - gap - edge >= height) put(box.left, box.top - gap - height);
  else if (viewportWidth - box.right - gap - edge >= width) put(box.right + gap, box.top);
  else if (box.left - gap - edge >= width) put(box.left - gap - width, box.top);
  else dock();
}

function reveal() {
  const target = currentTarget.value;
  if (!target || target.closest("header.top") || !card.value) return;
  const rect = target.getBoundingClientRect();
  const usable =
    window.innerHeight - (window.innerWidth <= 760 ? card.value.offsetHeight + 24 : 0);
  if (rect.top < 72 || rect.bottom > usable) {
    if (window.innerWidth <= 760) window.scrollBy(0, rect.top - 16);
    else {
      target.scrollIntoView({
        block: rect.height > usable ? "start" : "center",
        inline: "nearest",
      });
    }
  }
}

function reposition() {
  if (queued) return;
  queued = window.requestAnimationFrame(() => {
    queued = 0;
    place();
  });
}

async function show(nextIndex: number) {
  if (busy.value || nextIndex < 0 || nextIndex >= steps.length) return;
  busy.value = true;
  try {
    index.value = nextIndex;
    const nextStep = steps[nextIndex];
    if (nextStep.view && nextStep.view !== site.view.value) {
      site.view.value = nextStep.view;
      await nextTick();
    }
    await nextTick();
    currentTarget.value = nextStep.target
      ? document.querySelector<HTMLElement>(`[data-tour="${nextStep.target}"]`)
      : null;
    place();
    reveal();
    place();
    await nextTick();
    card.value?.querySelector<HTMLButtonElement>("button.ui-button.variant-primary")?.focus();
  } finally {
    busy.value = false;
  }
}

function move(delta: number) {
  if (busy.value) return;
  if (delta > 0 && index.value === steps.length - 1) {
    outcome = "done";
    dialog.value?.close();
    return;
  }
  void show(index.value + delta);
}

function skip() {
  outcome = "skipped";
  dialog.value?.close();
}

function onKeydown(event: KeyboardEvent) {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  const rtl = document.documentElement.dir === "rtl";
  if (event.key === (rtl ? "ArrowLeft" : "ArrowRight")) {
    event.preventDefault();
    move(1);
  } else if (event.key === (rtl ? "ArrowRight" : "ArrowLeft")) {
    event.preventDefault();
    move(-1);
  }
}

function onCancel() {
  outcome = "skipped";
}

async function onClose() {
  window.removeEventListener("resize", reposition);
  window.removeEventListener("scroll", reposition, true);
  site.markTutorial(outcome);
  if (site.view.value !== startView) {
    site.view.value = startView;
    await nextTick();
  }
  emit("close");
  if (priorActive?.dataset?.tour === "tutorial") {
    document.querySelector<HTMLElement>('[data-tour="tutorial"]')?.focus();
  }
}

async function openDialog() {
  if (!dialog.value || dialog.value.open) return;
  startView = site.view.value;
  priorActive = document.activeElement as HTMLElement | null;
  outcome = "skipped";
  index.value = 0;
  dialog.value.showModal();
  window.addEventListener("resize", reposition);
  window.addEventListener("scroll", reposition, true);
  await show(0);
}

watch(
  () => props.open,
  async (open) => {
    await nextTick();
    if (open) await openDialog();
    else if (dialog.value?.open) dialog.value.close();
  },
);

onMounted(() => {
  if (props.open) void openDialog();
});

onBeforeUnmount(() => {
  if (queued) cancelAnimationFrame(queued);
  window.removeEventListener("resize", reposition);
  window.removeEventListener("scroll", reposition, true);
});
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="tour"
      :class="[centered ? 'tour-centered' : '', dockClass]"
      aria-labelledby="tutorial-title"
      aria-describedby="tutorial-body"
      @keydown="onKeydown"
      @cancel="onCancel"
      @close="onClose"
    >
      <div ref="spot" class="tour-spot" aria-hidden="true"></div>
      <div ref="card" class="tour-card">
        <div class="tour-bar" aria-hidden="true"><span :style="{ width: fillWidth }"></span></div>
        <div aria-live="polite" aria-atomic="true">
          <div class="dialog-head">
            <h2 id="tutorial-title">{{ title }}</h2>
            <div class="tutorial-progress">{{ progress }}</div>
          </div>
          <div class="dialog-body">
            <p id="tutorial-body" class="tutorial-copy">{{ body }}</p>
          </div>
        </div>
        <div class="dialog-body muted tour-hint">{{ site.t("site.runtime.tutorial_hint") }}</div>
        <div class="dialog-actions">
          <UiButton :label="site.t('site.runtime.skip_tutorial')" @click="skip" />
          <UiButton
            :label="site.t('site.runtime.previous')"
            :disabled="index === 0"
            @click="move(-1)"
          />
          <UiButton variant="primary" :label="nextLabel" @click="move(1)" />
        </div>
      </div>
    </dialog>
  </Teleport>
</template>
