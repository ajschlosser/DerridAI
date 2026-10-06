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
import { onBeforeUnmount, onMounted, shallowRef, type Component } from "vue";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiLoadingState from "../ui/UiLoadingState.vue";

defineOptions({ inheritAttrs: false });

type RouteViewModule = { default: Component } | Component;

const props = defineProps<{
  loader: () => Promise<RouteViewModule>;
}>();

const i18n = useI18nStore();
const resolvedComponent = shallowRef<Component | null>(null);
const loadError = shallowRef<Error | null>(null);
let requestVersion = 0;
let revealReady = false;
let pendingComponent: Component | null = null;
let pendingError: Error | null = null;
let firstFrame = 0;
let secondFrame = 0;
let fallbackTimer = 0;

function revealPending() {
  if (!revealReady) return;
  if (pendingComponent) {
    resolvedComponent.value = pendingComponent;
    loadError.value = null;
    return;
  }
  if (pendingError) loadError.value = pendingError;
}

/**
 * Always give the committed destination shell one browser paint before mounting
 * the real page. Even a cached module can have expensive synchronous setup; if
 * it mounts in the same frame as navigation, that setup can make the old page
 * appear to linger despite the route already being committed.
 */
function allowRevealAfterFirstPaint() {
  const reveal = () => {
    revealReady = true;
    revealPending();
  };
  if (typeof window.requestAnimationFrame !== "function") {
    fallbackTimer = window.setTimeout(reveal, 0);
    return;
  }
  firstFrame = window.requestAnimationFrame(() => {
    secondFrame = window.requestAnimationFrame(reveal);
  });
}

async function load() {
  const version = ++requestVersion;
  pendingComponent = null;
  pendingError = null;
  loadError.value = null;
  try {
    const module = await props.loader();
    if (version !== requestVersion) return;
    pendingComponent =
      typeof module === "object" && module !== null && "default" in module
        ? module.default
        : (module as Component);
    revealPending();
  } catch (error) {
    if (version !== requestVersion) return;
    pendingError = error instanceof Error ? error : new Error(String(error));
    revealPending();
  }
}

function reloadPage() {
  window.location.reload();
}

onMounted(allowRevealAfterFirstPaint);
onBeforeUnmount(() => {
  ++requestVersion;
  if (firstFrame) window.cancelAnimationFrame(firstFrame);
  if (secondFrame) window.cancelAnimationFrame(secondFrame);
  if (fallbackTimer) window.clearTimeout(fallbackTimer);
});

void load();
</script>

<template>
  <component v-if="resolvedComponent" :is="resolvedComponent" v-bind="$attrs" />
  <section v-else-if="loadError" class="progressive-route-error" role="alert">
    <div>
      <strong>{{ i18n.t("loading.page_content_failed") }}</strong>
      <p>{{ i18n.t("loading.page_content_failed_help") }}</p>
    </div>
    <div class="progressive-route-actions">
      <UiButton :label="i18n.t('ui.retry')" size="small" @click="load" />
      <UiButton :label="i18n.t('loading.reload_page')" size="small" @click="reloadPage" />
    </div>
  </section>
  <UiLoadingState
    v-else
    class="progressive-route-loading"
    variant="skeleton"
    :skeleton-count="3"
    :label="i18n.t('loading.page_content')"
    :detail="i18n.t('loading.page_content_help')"
  />
</template>

<style scoped>
.progressive-route-loading,
.progressive-route-error {
  min-block-size: min(28rem, 55vh);
  padding: var(--space-5, 24px);
}

.progressive-route-error {
  display: grid;
  place-content: center;
  gap: var(--space-4, 16px);
  color: var(--text-primary);
  text-align: center;
}

.progressive-route-error p {
  max-inline-size: 48rem;
  margin: var(--space-2, 8px) 0 0;
  color: var(--text-secondary);
}

.progressive-route-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}
</style>
