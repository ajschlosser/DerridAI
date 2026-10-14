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
import { computed, ref, watch } from "vue";
import PdfEvidenceViewer from "./PdfEvidenceViewer.vue";
import PdfPageLabelEditor from "./PdfPageLabelEditor.vue";
import DocumentLayoutRegionLayer from "./DocumentLayoutRegionLayer.vue";
import { corpusBuilderApi } from "../api/corpus";
import { useI18nStore } from "../stores/i18n";
import type { DocumentLayoutPlan, PdfAsset, SourceBlock } from "../api/pdfCorpus";
import {
  MAX_LAYOUT_REGIONS,
  canonicalRegion,
  defaultFlow,
  detectRecipe,
  fullPageMain,
  marginSide,
  matchRegion,
  placeMargin,
  presetRegions,
  regionApplies,
  regionFromRect,
  type LayoutRecipe,
  type LayoutRegion,
  type LayoutRole,
  type LayoutScope,
  type LayoutThread,
} from "../domain/documentLayoutRegions";

const props = withDefaults(
  defineProps<{
    asset: PdfAsset;
    pdfUrl: string;
    blocks?: SourceBlock[];
    disabled?: boolean;
    saving?: boolean;
  }>(),
  { blocks: () => [], disabled: false, saving: false },
);
const emit = defineEmits<{
  save: [plan: DocumentLayoutPlan];
  savePageLabels: [labels: Record<number, string | null>];
  pageChange: [page: number];
}>();
const i18n = useI18nStore();
const current = ref(1);
const drawing = ref(false);
const selectedRegionId = ref("");
const marginPreference = ref<"left" | "right">("left");
const pageBlocks = ref<SourceBlock[]>([]);
const draft = ref<DocumentLayoutPlan>({
  page_layout: "single",
  reading_order: "left_to_right",
  thread_mode: "continuous",
  unit_policy: { mode: "default" },
  layout_regions: [],
});
const recipes: LayoutRecipe[] = ["single", "two_up", "margin", "infobox", "quote", "custom"];

function normalized(plan?: DocumentLayoutPlan | null) {
  return {
    page_layout: plan?.page_layout ?? "single",
    reading_order: plan?.reading_order ?? "left_to_right",
    thread_mode: plan?.thread_mode ?? "continuous",
    main_text_pdf_start: plan?.main_text_pdf_start ?? null,
    main_text_printed_start: plan?.main_text_printed_start ?? null,
    main_text_slot: plan?.main_text_slot ?? null,
    bibliography_pdf_start: plan?.bibliography_pdf_start ?? null,
    thread_a_language: plan?.thread_a_language ?? "",
    thread_b_language: plan?.thread_b_language ?? "",
    unit_policy: plan?.unit_policy ?? { mode: "default" },
    layout_regions: (plan?.layout_regions || []).map((region) => canonicalRegion(region)),
  };
}
type StartInference = {
  page: number | null;
  confidence: number;
  clues: { kind: string; detail: string }[];
  offered: boolean;
};
const inference = computed(() => {
  const value = (props.asset as { main_text_start_inference?: StartInference })
    .main_text_start_inference;
  return value && value.offered && typeof value.page === "number" && value.clues?.length
    ? value
    : null;
});
watch(
  () => props.asset.document_layout,
  (plan) => {
    draft.value = { ...normalized(plan) } as DocumentLayoutPlan;
    if (!plan?.main_text_pdf_start && inference.value)
      draft.value.main_text_pdf_start = inference.value.page;
    const margin = draft.value.layout_regions?.find((region) => region.role.startsWith("margin"));
    if (margin) marginPreference.value = marginSide(margin);
    drawing.value = false;
  },
  { immediate: true, deep: true },
);
const showClues = computed(
  () => inference.value && draft.value.main_text_pdf_start === inference.value.page,
);
const dirty = computed(
  () =>
    JSON.stringify(normalized(draft.value)) !==
    JSON.stringify(normalized(props.asset.document_layout)),
);
const pageInfo = computed(() => props.asset.pages?.find((p) => p.pdf_page === current.value));
type LogicalPagePreview = { slot: string; printed_page_label?: string | null };
const logicalPreview = computed<LogicalPagePreview[]>(() => pageInfo.value?.logical_pages || []);
const regions = computed(() => draft.value.layout_regions || []);
const activeRecipe = computed(() => detectRecipe(draft.value.page_layout, regions.value));
const marginRegion = computed(() =>
  regions.value.find((region) => region.role.startsWith("margin")),
);
const hasSeparateRegion = computed(() =>
  regions.value.some((region) => region.flow === "separate"),
);
const atRegionLimit = computed(() => regions.value.length >= MAX_LAYOUT_REGIONS);
const mappedCount = computed(
  () =>
    props.asset.pages?.filter(
      (page) =>
        Boolean(String(page.printed_page_label ?? "").trim()) ||
        (page.logical_pages || []).some((item) =>
          Boolean(String(item.printed_page_label ?? "").trim()),
        ),
    ).length || 0,
);
const exceptionCount = computed(
  () =>
    props.asset.pages?.filter((page) =>
      String(page.printed_page_label_source || "").includes("override"),
    ).length || 0,
);
const extractionSummary = computed(() => {
  const pages = props.asset.pages || [];
  const methods = new Set(pages.map((page) => page.extraction_method).filter(Boolean));
  const regionTypes = new Set(pages.map((page) => page.deterministic_region_type).filter(Boolean));
  const threads = new Set(pages.flatMap((page) => page.thread_ids || []));
  return { methods: [...methods], regions: [...regionTypes], threads: threads.size };
});
const regionLabels = computed(() => {
  const labels: Record<string, string> = {};
  for (const region of regions.value) labels[region.id] = roleLabel(region.role);
  return labels;
});
const blockCounts = computed(() => {
  const counts = new Map<string, number>();
  const width = pageInfo.value?.width || 0;
  const height = pageInfo.value?.height || 0;
  for (const block of pageBlocks.value) {
    const region = matchRegion(regions.value, current.value, block.bbox, width, height);
    if (!region) continue;
    counts.set(region.id, (counts.get(region.id) || 0) + 1);
  }
  return counts;
});

watch(
  [() => props.asset.asset_id, current],
  async ([assetId, page]) => {
    if (!assetId) {
      pageBlocks.value = [];
      return;
    }
    try {
      const result = await corpusBuilderApi.blocks(assetId, 0, 1000, [], page);
      if (props.asset.asset_id === assetId && current.value === page)
        pageBlocks.value = result.items || [];
    } catch {
      if (props.asset.asset_id === assetId && current.value === page)
        pageBlocks.value = props.blocks.filter((block) => Number(block.page) === Number(page));
    }
  },
  { immediate: true },
);

function roleLabel(role: LayoutRole) {
  switch (role) {
    case "main":
      return i18n.t("pdf_corpus.role_main");
    case "margin_parallel":
      return i18n.t("pdf_corpus.role_margin_parallel");
    case "margin_apparatus":
      return i18n.t("pdf_corpus.role_margin_apparatus");
    case "infobox":
      return i18n.t("pdf_corpus.role_infobox");
    case "block_quote":
      return i18n.t("pdf_corpus.role_block_quote");
    case "running_matter":
      return i18n.t("pdf_corpus.role_running_matter");
  }
}
function scopeLabel(scope: LayoutScope) {
  switch (scope) {
    case "all":
      return i18n.t("pdf_corpus.applies_all");
    case "odd":
      return i18n.t("pdf_corpus.applies_odd");
    case "even":
      return i18n.t("pdf_corpus.applies_even");
    case "range":
      return i18n.t("pdf_corpus.applies_range");
    case "page":
      return i18n.t("pdf_corpus.applies_page");
  }
}
function recipeLabel(recipe: LayoutRecipe) {
  switch (recipe) {
    case "single":
      return i18n.t("pdf_corpus.recipe_single");
    case "two_up":
      return i18n.t("pdf_corpus.recipe_two_up");
    case "margin":
      return i18n.t("pdf_corpus.recipe_margin");
    case "infobox":
      return i18n.t("pdf_corpus.recipe_infobox");
    case "quote":
      return i18n.t("pdf_corpus.recipe_quote");
    case "custom":
      return i18n.t("pdf_corpus.recipe_custom");
  }
}
function recipeHint(recipe: LayoutRecipe) {
  switch (recipe) {
    case "single":
      return i18n.t("pdf_corpus.recipe_single_hint");
    case "two_up":
      return i18n.t("pdf_corpus.recipe_two_up_hint");
    case "margin":
      return i18n.t("pdf_corpus.recipe_margin_hint");
    case "infobox":
      return i18n.t("pdf_corpus.recipe_infobox_hint");
    case "quote":
      return i18n.t("pdf_corpus.recipe_quote_hint");
    case "custom":
      return i18n.t("pdf_corpus.recipe_custom_hint");
  }
}
function replaceRegions(next: LayoutRegion[]) {
  draft.value.layout_regions = next.map((region) => canonicalRegion(region));
  const extra = next.find((region) => region.role !== "main");
  selectedRegionId.value = extra?.id || next[0]?.id || "";
}
function selectRecipe(recipe: LayoutRecipe) {
  if (props.disabled) return;
  if (recipe === "custom") {
    drawing.value = true;
    return;
  }
  if (recipe === activeRecipe.value) return;
  drawing.value = false;
  if (recipe === "single") {
    draft.value.page_layout = "single";
    if (draft.value.thread_mode === "left_right" || draft.value.thread_mode === "right_left")
      draft.value.thread_mode = "continuous";
    replaceRegions([]);
    return;
  }
  if (recipe === "two_up") {
    draft.value.page_layout = "two_up";
    if (draft.value.thread_mode === "continuous") draft.value.thread_mode = "left_right";
    replaceRegions([]);
    return;
  }
  draft.value.page_layout = "single";
  draft.value.thread_mode = "continuous";
  replaceRegions(presetRegions(recipe, marginPreference.value));
}
function resetPattern() {
  const recipe = activeRecipe.value;
  if (recipe === "single" || recipe === "two_up" || recipe === "custom") {
    replaceRegions([]);
    return;
  }
  replaceRegions(presetRegions(recipe, marginPreference.value));
}
function setMargin(side: "left" | "right") {
  marginPreference.value = side;
  draft.value.layout_regions = regions.value.map((region) =>
    region.role.startsWith("margin") ? placeMargin(region, side) : region,
  );
}
function patchRegion(id: string, patch: Partial<LayoutRegion>) {
  draft.value.layout_regions = regions.value.map((region) =>
    region.id === id ? canonicalRegion({ ...region, ...patch }) : region,
  );
}
function setRole(region: LayoutRegion, role: LayoutRole) {
  patchRegion(region.id, { role, flow: defaultFlow(role) });
}
function setScope(region: LayoutRegion, scope: LayoutScope) {
  patchRegion(region.id, {
    applies_to: scope,
    page: scope === "page" ? region.page || current.value : null,
    page_start: scope === "range" ? region.page_start || current.value : null,
    page_end: scope === "range" ? region.page_end || props.asset.page_count : null,
  });
}
function onGeometry(next: LayoutRegion) {
  patchRegion(next.id, next);
}
function onDraw(rect: { x0: number; y0: number; x1: number; y1: number }) {
  if (atRegionLimit.value) return;
  const created = regionFromRect(rect, current.value, regions.value);
  const next = [...regions.value];
  if (!next.some((region) => region.role === "main")) next.unshift(fullPageMain());
  next.push(created);
  replaceRegions(next);
  selectedRegionId.value = created.id;
  drawing.value = false;
}
function removeRegion(id: string) {
  let next = regions.value.filter((region) => region.id !== id);
  if (next.length === 1 && next[0].role === "main") next = [];
  replaceRegions(next);
}
function setPage(value: number) {
  current.value = Math.max(1, Math.min(props.asset.page_count || 1, value));
  emit("pageChange", current.value);
}
function save() {
  if (!dirty.value || props.saving) return;
  emit("save", {
    ...draft.value,
    layout_regions: regions.value.map((region) => canonicalRegion(region)),
  });
}
function visibleOnPage(region: LayoutRegion) {
  return regionApplies(region, current.value);
}
</script>
<template>
  <section class="structure-config" aria-labelledby="document-structure-title">
    <header>
      <div>
        <span class="eyebrow">{{ i18n.t("pdf_corpus.document_structure") }}</span>
        <h3 id="document-structure-title">{{ asset.filename }}</h3>
        <p>{{ i18n.t("pdf_corpus.document_structure_help") }}</p>
      </div>
    </header>
    <div class="structure-grid">
      <section class="browser">
        <div class="page-nav">
          <button
            class="btn small"
            type="button"
            :disabled="current <= 1"
            @click="setPage(current - 1)"
          >
            ← {{ i18n.t("ui.previous") }}
          </button>
          <label>
            <span class="sr-only">{{ i18n.t("pdf_corpus.physical_pdf_page") }}</span>
            <input
              class="control compact"
              type="number"
              min="1"
              :max="asset.page_count"
              :value="current"
              @change="setPage(Number(($event.target as HTMLInputElement).value))"
            />
          </label>
          <span>/ {{ asset.page_count }}</span>
          <button
            class="btn small"
            type="button"
            :disabled="current >= asset.page_count"
            @click="setPage(current + 1)"
          >
            {{ i18n.t("ui.next") }} →
          </button>
        </div>
        <p v-if="drawing" class="draw-hint" role="status">
          {{ i18n.t("pdf_corpus.draw_region_hint") }}
        </p>
        <PdfEvidenceViewer
          :pdf-url="pdfUrl"
          :page="current"
          :page-width="pageInfo?.width || 0"
          :page-height="pageInfo?.height || 0"
          :blocks="pageBlocks"
          :show-source-boxes="regions.length === 0"
          :max-width="760"
        >
          <template #overlay>
            <DocumentLayoutRegionLayer
              :regions="regions"
              :page="current"
              :labels="regionLabels"
              :drawing="drawing"
              :selected-id="selectedRegionId"
              :blocks="pageBlocks"
              :page-width="pageInfo?.width || 0"
              :page-height="pageInfo?.height || 0"
              :disabled="disabled"
              @select="selectedRegionId = $event"
              @update="onGeometry"
              @draw="onDraw"
              @remove="removeRegion"
            />
          </template>
        </PdfEvidenceViewer>
        <div
          v-if="draft.page_layout === 'two_up'"
          class="two-up-preview"
          :aria-label="i18n.t('pdf_corpus.two_up_logical_preview')"
        >
          <span
            v-for="item in logicalPreview.length
              ? logicalPreview
              : [
                  { slot: 'left', printed_page_label: null },
                  { slot: 'right', printed_page_label: null },
                ]"
            :key="item.slot"
          >
            <b>{{ i18n.t(`pdf_corpus.${item.slot}_page`, item.slot) }}</b>
            <small>{{
              item.printed_page_label
                ? i18n.tf("pdf_corpus.printed_page_value", { page: item.printed_page_label })
                : i18n.t("pdf_corpus.not_mapped_yet")
            }}</small>
          </span>
        </div>
        <div
          class="current-page-actions"
          role="group"
          :aria-label="i18n.t('pdf_corpus.page_mapping')"
        >
          <button
            class="btn"
            type="button"
            :disabled="disabled"
            @click="draft.main_text_pdf_start = current"
          >
            {{ i18n.t("pdf_corpus.set_current_main_start") }}
          </button>
          <button
            class="btn"
            type="button"
            :disabled="disabled"
            @click="draft.bibliography_pdf_start = current"
          >
            {{ i18n.t("pdf_corpus.set_current_bibliography") }}
          </button>
        </div>
      </section>
      <section class="rules">
        <fieldset class="compact-fieldset">
          <legend>{{ i18n.t("pdf_corpus.layout_recipe") }}</legend>
          <p class="field-help">{{ i18n.t("pdf_corpus.layout_recipe_help") }}</p>
          <div class="recipes" role="radiogroup" :aria-label="i18n.t('pdf_corpus.layout_recipe')">
            <label v-for="recipe in recipes" :key="recipe" class="recipe">
              <input
                type="radio"
                name="layout-recipe"
                :value="recipe"
                :checked="activeRecipe === recipe"
                :disabled="disabled"
                @change="selectRecipe(recipe)"
              />
              <span class="figure" :data-recipe="recipe" aria-hidden="true"
                ><span></span><span></span><span></span
              ></span>
              <span class="recipe-copy">
                <b>{{ recipeLabel(recipe) }}</b>
                <small>{{ recipeHint(recipe) }}</small>
              </span>
            </label>
          </div>
          <label v-if="draft.page_layout === 'two_up'">
            <span>{{ i18n.t("pdf_corpus.reading_order") }}</span>
            <select v-model="draft.reading_order" class="control" :disabled="disabled">
              <option value="left_to_right">{{ i18n.t("pdf_corpus.left_to_right") }}</option>
              <option value="right_to_left">{{ i18n.t("pdf_corpus.right_to_left") }}</option>
            </select>
          </label>
        </fieldset>

        <fieldset class="compact-fieldset">
          <legend>{{ i18n.t("pdf_corpus.regions_title") }}</legend>
          <p class="field-help">{{ i18n.t("pdf_corpus.regions_help") }}</p>
          <p class="field-help">{{ i18n.t("pdf_corpus.regions_scale_note") }}</p>
          <div
            v-if="marginRegion"
            class="segmented"
            role="group"
            :aria-label="i18n.t('pdf_corpus.margin_side')"
          >
            <button
              class="btn small"
              type="button"
              :aria-pressed="marginSide(marginRegion) === 'left'"
              :disabled="disabled"
              @click="setMargin('left')"
            >
              {{ i18n.t("pdf_corpus.margin_left") }}
            </button>
            <button
              class="btn small"
              type="button"
              :aria-pressed="marginSide(marginRegion) === 'right'"
              :disabled="disabled"
              @click="setMargin('right')"
            >
              {{ i18n.t("pdf_corpus.margin_right") }}
            </button>
          </div>
          <p v-if="!regions.length" class="field-help">{{ i18n.t("pdf_corpus.regions_empty") }}</p>
          <ul v-else class="region-list">
            <li
              v-for="region in regions"
              :key="region.id"
              :data-off-page="visibleOnPage(region) ? 'false' : 'true'"
            >
              <button
                class="region-summary"
                type="button"
                :aria-expanded="selectedRegionId === region.id"
                @click="selectedRegionId = region.id"
              >
                <span class="swatch" :data-role="region.role" aria-hidden="true"></span>
                <span>
                  <b>{{ roleLabel(region.role) }}</b>
                  <small>
                    {{ scopeLabel(region.applies_to) }}
                    <template v-if="blockCounts.get(region.id)">
                      ·
                      {{
                        i18n.tf("pdf_corpus.region_block_count", {
                          count: blockCounts.get(region.id) || 0,
                        })
                      }}
                    </template>
                  </small>
                </span>
              </button>
              <div v-if="selectedRegionId === region.id" class="region-editor">
                <label>
                  <span>{{ i18n.t("pdf_corpus.region_role") }}</span>
                  <select
                    class="control"
                    :value="region.role"
                    :disabled="disabled"
                    @change="
                      setRole(region, ($event.target as HTMLSelectElement).value as LayoutRole)
                    "
                  >
                    <option value="main">{{ i18n.t("pdf_corpus.role_main") }}</option>
                    <option value="margin_parallel">
                      {{ i18n.t("pdf_corpus.role_margin_parallel") }}
                    </option>
                    <option value="margin_apparatus">
                      {{ i18n.t("pdf_corpus.role_margin_apparatus") }}
                    </option>
                    <option value="infobox">{{ i18n.t("pdf_corpus.role_infobox") }}</option>
                    <option value="block_quote">{{ i18n.t("pdf_corpus.role_block_quote") }}</option>
                    <option value="running_matter">
                      {{ i18n.t("pdf_corpus.role_running_matter") }}
                    </option>
                  </select>
                </label>
                <label v-if="region.role !== 'main'">
                  <span>{{ i18n.t("pdf_corpus.region_thread") }}</span>
                  <select
                    class="control"
                    :value="region.thread"
                    :disabled="disabled"
                    @change="
                      patchRegion(region.id, {
                        thread: ($event.target as HTMLSelectElement).value as LayoutThread,
                      })
                    "
                  >
                    <option value="thread_a">{{ i18n.t("pdf_corpus.thread_name_a") }}</option>
                    <option value="thread_b">{{ i18n.t("pdf_corpus.thread_name_b") }}</option>
                    <option value="thread_c">{{ i18n.t("pdf_corpus.thread_name_c") }}</option>
                    <option value="thread_d">{{ i18n.t("pdf_corpus.thread_name_d") }}</option>
                  </select>
                </label>
                <label>
                  <span>{{ i18n.t("pdf_corpus.region_applies") }}</span>
                  <select
                    class="control"
                    :value="region.applies_to"
                    :disabled="disabled"
                    @change="
                      setScope(region, ($event.target as HTMLSelectElement).value as LayoutScope)
                    "
                  >
                    <option value="all">{{ i18n.t("pdf_corpus.applies_all") }}</option>
                    <option value="odd">{{ i18n.t("pdf_corpus.applies_odd") }}</option>
                    <option value="even">{{ i18n.t("pdf_corpus.applies_even") }}</option>
                    <option value="range">{{ i18n.t("pdf_corpus.applies_range") }}</option>
                    <option value="page">{{ i18n.t("pdf_corpus.applies_page") }}</option>
                  </select>
                </label>
                <div v-if="region.applies_to === 'range'" class="range-pair">
                  <label>
                    <span>{{ i18n.t("pdf_corpus.region_range_start") }}</span>
                    <input
                      class="control"
                      type="number"
                      min="1"
                      :max="asset.page_count"
                      :value="region.page_start || ''"
                      :disabled="disabled"
                      @change="
                        patchRegion(region.id, {
                          page_start: Number(($event.target as HTMLInputElement).value),
                        })
                      "
                    />
                  </label>
                  <label>
                    <span>{{ i18n.t("pdf_corpus.region_range_end") }}</span>
                    <input
                      class="control"
                      type="number"
                      min="1"
                      :max="asset.page_count"
                      :value="region.page_end || ''"
                      :disabled="disabled"
                      @change="
                        patchRegion(region.id, {
                          page_end: Number(($event.target as HTMLInputElement).value),
                        })
                      "
                    />
                  </label>
                </div>
                <label v-if="region.applies_to === 'page'">
                  <span>{{ i18n.t("pdf_corpus.physical_pdf_page") }}</span>
                  <input
                    class="control"
                    type="number"
                    min="1"
                    :max="asset.page_count"
                    :value="region.page || current"
                    :disabled="disabled"
                    @change="
                      patchRegion(region.id, {
                        page: Number(($event.target as HTMLInputElement).value),
                      })
                    "
                  />
                </label>
                <label v-if="region.role !== 'main'">
                  <span>{{ i18n.t("pdf_corpus.region_flow") }}</span>
                  <select
                    class="control"
                    :value="region.flow"
                    :disabled="disabled"
                    @change="
                      patchRegion(region.id, {
                        flow: ($event.target as HTMLSelectElement).value as LayoutRegion['flow'],
                      })
                    "
                  >
                    <option value="with_main">{{ i18n.t("pdf_corpus.flow_with_main") }}</option>
                    <option value="separate">{{ i18n.t("pdf_corpus.flow_separate") }}</option>
                  </select>
                </label>
                <label v-if="region.flow === 'separate'">
                  <span>{{ i18n.t("pdf_corpus.region_language") }}</span>
                  <input
                    class="control"
                    :value="region.language || ''"
                    placeholder="en_us"
                    :disabled="disabled"
                    @change="
                      patchRegion(region.id, {
                        language: ($event.target as HTMLInputElement).value,
                      })
                    "
                  />
                </label>
                <button
                  class="btn small"
                  type="button"
                  :disabled="disabled"
                  @click="removeRegion(region.id)"
                >
                  {{ i18n.t("pdf_corpus.remove_region") }}
                </button>
              </div>
            </li>
          </ul>
          <p v-if="hasSeparateRegion" class="field-help">
            {{ i18n.t("pdf_corpus.flow_separate_help") }}
          </p>
          <p class="field-help">{{ i18n.t("pdf_corpus.region_keyboard") }}</p>
          <p v-if="atRegionLimit" class="field-help">
            {{ i18n.tf("pdf_corpus.region_limit", { max: MAX_LAYOUT_REGIONS }) }}
          </p>
          <div class="region-actions">
            <button
              class="btn"
              type="button"
              :disabled="disabled || atRegionLimit"
              :aria-pressed="drawing"
              @click="drawing = !drawing"
            >
              {{
                drawing ? i18n.t("pdf_corpus.draw_region_stop") : i18n.t("pdf_corpus.draw_region")
              }}
            </button>
            <button
              v-if="regions.length"
              class="btn"
              type="button"
              :disabled="disabled"
              @click="resetPattern"
            >
              {{ i18n.t("pdf_corpus.reset_pattern") }}
            </button>
          </div>
        </fieldset>

        <fieldset class="compact-fieldset">
          <legend>{{ i18n.t("pdf_corpus.structural_anchors") }}</legend>
          <label>
            <span>{{ i18n.t("pdf_corpus.main_text_starts_pdf") }}</span>
            <div class="anchor">
              <input
                v-model.number="draft.main_text_pdf_start"
                class="control"
                type="number"
                min="1"
                :max="asset.page_count"
                :disabled="disabled"
              />
              <button
                class="btn small"
                type="button"
                :disabled="disabled"
                @click="draft.main_text_pdf_start = current"
              >
                {{ i18n.t("pdf_corpus.use_current_page") }}
              </button>
            </div>
          </label>
          <div v-if="showClues && inference" class="start-clues" role="note">
            <b>{{
              i18n.tf("pdf_corpus.manifest_start_inferred", {
                percent: Math.round(inference.confidence * 100),
              })
            }}</b>
            <ul>
              <li v-for="clue in inference.clues" :key="clue.kind">{{ clue.detail }}</li>
            </ul>
          </div>
          <label>
            <span>{{ i18n.t("pdf_corpus.first_printed_page_number") }}</span>
            <input
              v-model.number="draft.main_text_printed_start"
              class="control"
              type="number"
              min="1"
              :disabled="disabled"
            />
          </label>
          <label v-if="draft.page_layout === 'two_up'">
            <span>{{ i18n.t("pdf_corpus.main_text_slot") }}</span>
            <select v-model="draft.main_text_slot" class="control" :disabled="disabled">
              <option value="left">{{ i18n.t("pdf_corpus.left_page") }}</option>
              <option value="right">{{ i18n.t("pdf_corpus.right_page") }}</option>
            </select>
          </label>
          <label>
            <span>{{ i18n.t("pdf_corpus.bibliography_starts_pdf") }}</span>
            <div class="anchor">
              <input
                v-model.number="draft.bibliography_pdf_start"
                class="control"
                type="number"
                min="1"
                :max="asset.page_count"
                :disabled="disabled"
              />
              <button
                class="btn small"
                type="button"
                :disabled="disabled"
                @click="draft.bibliography_pdf_start = current"
              >
                {{ i18n.t("pdf_corpus.use_current_page") }}
              </button>
            </div>
          </label>
        </fieldset>

        <fieldset class="compact-fieldset">
          <legend>{{ i18n.t("pdf_corpus.page_threads") }}</legend>
          <p v-if="hasSeparateRegion" class="field-help">
            {{ i18n.t("pdf_corpus.thread_pattern_with_regions") }}
          </p>
          <label>
            <span>{{ i18n.t("pdf_corpus.thread_pattern") }}</span>
            <select v-model="draft.thread_mode" class="control" :disabled="disabled">
              <option value="continuous">{{ i18n.t("pdf_corpus.thread_continuous") }}</option>
              <option value="odd_even">{{ i18n.t("pdf_corpus.thread_odd_even") }}</option>
              <option value="even_odd">{{ i18n.t("pdf_corpus.thread_even_odd") }}</option>
              <option value="left_right" :disabled="draft.page_layout !== 'two_up'">
                {{ i18n.t("pdf_corpus.thread_left_right") }}
              </option>
              <option value="right_left" :disabled="draft.page_layout !== 'two_up'">
                {{ i18n.t("pdf_corpus.thread_right_left") }}
              </option>
            </select>
          </label>
          <div v-if="draft.thread_mode !== 'continuous'" class="thread-languages">
            <label>
              <span>{{ i18n.t("pdf_corpus.thread_a_language") }}</span>
              <input
                v-model="draft.thread_a_language"
                class="control"
                placeholder="en_us"
                :disabled="disabled"
              />
            </label>
            <label>
              <span>{{ i18n.t("pdf_corpus.thread_b_language") }}</span>
              <input
                v-model="draft.thread_b_language"
                class="control"
                placeholder="fr_fr"
                :disabled="disabled"
              />
            </label>
          </div>
        </fieldset>

        <fieldset class="compact-fieldset">
          <legend>{{ i18n.t("pdf_corpus.evidence_structure", "Evidence source units") }}</legend>
          <p class="field-help">
            {{
              i18n.t(
                "pdf_corpus.evidence_structure_help",
                "Choose the smallest source span reviewers can cite as evidence.",
              )
            }}
          </p>
          <label>
            <span>{{ i18n.t("pdf_corpus.source_unit_mode", "Source-unit rule") }}</span>
            <select v-model="draft.unit_policy!.mode" class="control" :disabled="disabled">
              <option value="default">
                {{ i18n.t("pdf_corpus.source_unit_default", "Default extracted units") }}
              </option>
              <option value="sentence">
                {{ i18n.t("pdf_corpus.source_unit_sentence", "Every sentence") }}
              </option>
              <option value="line">
                {{ i18n.t("pdf_corpus.source_unit_line", "Every line") }}
              </option>
              <option value="paragraph">
                {{ i18n.t("pdf_corpus.source_unit_paragraph", "Every paragraph") }}
              </option>
              <option value="chars">
                {{ i18n.t("pdf_corpus.source_unit_chars", "Every N characters") }}
              </option>
            </select>
          </label>
          <label v-if="draft.unit_policy?.mode === 'chars'">
            <span>{{
              i18n.t("pdf_corpus.source_unit_chars_count", "Characters per source unit")
            }}</span>
            <input
              v-model.number="draft.unit_policy.chars"
              class="control"
              type="number"
              min="60"
              max="20000"
              step="10"
              :disabled="disabled"
            />
          </label>
        </fieldset>
      </section>
    </div>
    <section class="mapping-summary">
      <div aria-live="polite">
        <b>{{ i18n.t("pdf_corpus.generated_mapping") }}</b>
        <span>{{
          i18n.tf("pdf_corpus.mapping_summary", {
            mapped: mappedCount,
            total: asset.page_count,
            exceptions: exceptionCount,
          })
        }}</span>
        <small>{{
          i18n.tf("pdf_corpus.deterministic_structure_summary", {
            methods: extractionSummary.methods.length,
            regions: extractionSummary.regions.length,
            threads: extractionSummary.threads,
          })
        }}</small>
      </div>
      <details class="exceptions">
        <summary class="btn">{{ i18n.t("pdf_corpus.review_mapping") }}</summary>
        <p>{{ i18n.t("pdf_corpus.mapping_exceptions_help") }}</p>
        <PdfPageLabelEditor
          :pages="asset.pages || []"
          :disabled="disabled"
          @save="(labels) => emit('savePageLabels', labels)"
        />
      </details>
    </section>
    <footer class="structure-save">
      <div class="save-state">
        <span
          :data-state="saving ? 'saving' : dirty ? 'dirty' : 'saved'"
          role="status"
          aria-live="polite"
          >{{
            saving
              ? i18n.t("ui.saving")
              : dirty
                ? i18n.t("pdf_corpus.unsaved_structure")
                : i18n.t("pdf_corpus.structure_saved_state")
          }}</span
        >
        <button
          class="btn primary"
          type="button"
          :disabled="disabled || saving || !dirty"
          @click="save"
        >
          {{ saving ? i18n.t("ui.saving") : i18n.t("pdf_corpus.save_document_structure") }}
        </button>
      </div>
    </footer>
  </section>
</template>
<style scoped>
.start-clues {
  margin: 0.5rem 0 0;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--tone-info-border);
  border-radius: 8px;
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.start-clues ul {
  margin: 0.25rem 0 0;
  padding-inline-start: 1.125rem;
}
.structure-save {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.structure-config {
  container-type: inline-size;
  display: grid;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.structure-config > header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}
.structure-config h3 {
  margin: 2px 0;
  font-size: 1rem;
}
.structure-config header p,
.field-help {
  margin: 4px 0 0;
  max-width: 78ch;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.eyebrow {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  font-weight: 800;
}
.save-state {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.save-state span {
  font-size: 0.8125rem;
  font-weight: 750;
  color: var(--muted);
}
.save-state span[data-state="dirty"] {
  color: var(--warning, var(--tone-warn-fg));
}
.save-state span[data-state="saved"] {
  color: var(--success, var(--tone-ok-fg));
}
.structure-grid {
  display: grid;
  grid-template-columns: minmax(520px, 1.25fr) minmax(340px, 0.85fr);
  gap: 18px;
  align-items: start;
}
.browser,
.rules fieldset {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.compact-fieldset {
  gap: 7px !important;
  padding: 10px !important;
}
.browser {
  overflow: hidden;
  position: sticky;
  top: 78px;
  align-self: start;
}
.page-nav,
.region-actions,
.segmented {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
}
.page-nav {
  padding: 9px;
  border-bottom: 1px solid var(--line);
  background: var(--card);
}
.page-nav input {
  width: 76px;
}
.draw-hint {
  margin: 0;
  padding: 8px 10px;
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  border-bottom: 1px solid var(--tone-info-border);
  font-size: 0.8125rem;
}
.rules {
  display: grid;
  gap: 12px;
  align-content: start;
}
.rules fieldset {
  display: grid;
  gap: 9px;
  margin: 0;
  padding: 12px;
}
.rules legend {
  padding: 0 4px;
  font-size: 0.875rem;
  font-weight: 800;
}
.rules label {
  display: grid;
  gap: 5px;
  font-size: 0.8125rem;
  line-height: 1.4;
}
.recipes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
  gap: 8px;
}
.recipe {
  position: relative;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-height: 64px;
  margin: 0;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  cursor: pointer;
}
.recipe input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}
.recipe:has(input:checked) {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
}
.recipe:focus-within {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.recipe-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.recipe-copy b,
.region-summary b {
  font-size: 0.8125rem;
}
.recipe-copy small,
.region-summary small {
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.35;
}
.figure {
  display: grid;
  width: 42px;
  height: 52px;
  padding: 4px;
  border: 1px solid var(--line-strong, var(--line));
  border-radius: 4px;
  background: var(--surface-overlay);
  gap: 3px;
}
.figure span {
  display: block;
  border-radius: 2px;
  background: color-mix(in srgb, var(--accent-fg) 55%, var(--card));
}
.figure[data-recipe="single"] {
  grid-template-rows: 1fr;
}
.figure[data-recipe="single"] span:not(:first-child) {
  display: none;
}
.figure[data-recipe="two_up"] {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr;
}
.figure[data-recipe="two_up"] span:last-child {
  display: none;
}
.figure[data-recipe="margin"] {
  grid-template-columns: 0.35fr 1fr;
  grid-template-rows: 1fr;
}
.figure[data-recipe="margin"] span:first-child {
  background: color-mix(in srgb, var(--tone-warn-border) 70%, var(--card));
}
.figure[data-recipe="margin"] span:last-child {
  display: none;
}
.figure[data-recipe="infobox"] {
  grid-template-rows: 0.7fr 1fr;
}
.figure[data-recipe="infobox"] span:first-child {
  justify-self: end;
  width: 46%;
  background: color-mix(in srgb, var(--tone-ok-border) 70%, var(--card));
}
.figure[data-recipe="infobox"] span:last-child {
  display: none;
}
.figure[data-recipe="quote"] {
  grid-template-rows: 0.6fr 1fr 0.8fr;
}
.figure[data-recipe="quote"] span:nth-child(2) {
  width: 78%;
  justify-self: center;
  background: color-mix(in srgb, var(--tone-info-border) 70%, var(--card));
}
.figure[data-recipe="custom"] span {
  background: var(--line);
}
.anchor,
.range-pair {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 7px;
}
.range-pair {
  grid-template-columns: 1fr 1fr;
}
.thread-languages,
.region-list {
  display: grid;
  gap: 8px;
}
.region-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.region-list li {
  display: grid;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
}
.region-list li[data-off-page="true"] {
  opacity: 0.72;
}
.region-summary {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: start;
  cursor: pointer;
}
.region-summary span:last-child {
  display: grid;
}
.swatch {
  width: 12px;
  height: 28px;
  flex: none;
  border-radius: 99px;
  background: var(--accent-fg);
}
.swatch[data-role="margin_parallel"],
.swatch[data-role="margin_apparatus"] {
  background: var(--tone-warn-border);
}
.swatch[data-role="infobox"] {
  background: var(--tone-ok-border);
}
.swatch[data-role="block_quote"] {
  background: var(--tone-info-border);
}
.swatch[data-role="running_matter"] {
  background: var(--muted);
}
.region-editor {
  display: grid;
  gap: 8px;
}
.two-up-preview {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-top: 1px solid var(--line);
  background: var(--card);
}
.two-up-preview span {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border-inline-end: 1px solid var(--line);
}
.two-up-preview small {
  color: var(--muted);
}
.current-page-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px;
  background: var(--card);
  border-top: 1px solid var(--line);
}
.mapping-summary {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.mapping-summary > div {
  display: grid;
  gap: 3px;
}
.mapping-summary span,
.exceptions > p {
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.exceptions {
  min-width: min(460px, 100%);
}
.exceptions summary {
  list-style: none;
  cursor: pointer;
  width: max-content;
}
.exceptions summary::-webkit-details-marker {
  display: none;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.structure-config :is(input, select, button, summary):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.recipe:focus-within {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@container (max-width: 900px) {
  .structure-grid {
    grid-template-columns: 1fr;
  }
  .browser {
    position: static;
  }
  .mapping-summary {
    flex-direction: column;
  }
  .exceptions {
    min-width: 0;
    width: 100%;
  }
}
@media (max-width: 1120px) {
  .structure-grid {
    grid-template-columns: 1fr;
  }
  .browser {
    position: static;
  }
  .mapping-summary {
    flex-direction: column;
  }
  .exceptions {
    min-width: 0;
    width: 100%;
  }
}
@media (max-width: 720px) {
  .structure-config > header,
  .save-state {
    align-items: stretch;
    flex-direction: column;
  }
  .anchor,
  .range-pair {
    grid-template-columns: 1fr;
  }
  .current-page-actions .btn {
    flex: 1 1 100%;
  }
}
</style>
