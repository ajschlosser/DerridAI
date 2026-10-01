// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref, type ComputedRef, type Ref, watch } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import type { MetadataSchema } from "../api/metadataSchemas";
import type { RunGuidanceEntry, RunGuidanceField } from "../components/CorpusRunGuidance.vue";

type Translate = (key: string, fallback: string) => string;

// Guidance is remembered per schema so imported or hand-written guidance
// survives reloads and switching schemas. It is a browser-local convenience;
// a build's own request keeps the authoritative copy of what a run used.
export const RUN_GUIDANCE_STORAGE_KEY = "derridai.run-guidance.v1";

function readStore(): Record<string, Record<string, RunGuidanceEntry>> {
  try {
    const parsed = JSON.parse(localStorage.getItem(RUN_GUIDANCE_STORAGE_KEY) || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function saveGuidance(schemaId: string, value: Record<string, RunGuidanceEntry>) {
  try {
    const store = readStore();
    if (Object.keys(value).length) store[schemaId] = value;
    else delete store[schemaId];
    localStorage.setItem(RUN_GUIDANCE_STORAGE_KEY, JSON.stringify(store));
  } catch {
    /* storage unavailable: guidance still works for this session */
  }
}

function loadGuidance(schemaId: string): Record<string, RunGuidanceEntry> {
  const stored = readStore()[schemaId];
  if (!stored || typeof stored !== "object") return {};
  const result: Record<string, RunGuidanceEntry> = {};
  for (const [field, raw] of Object.entries(stored)) {
    if (!raw || typeof raw !== "object") continue;
    result[field] = {
      instructions: typeof raw.instructions === "string" ? raw.instructions : "",
      look_for: Array.isArray(raw.look_for)
        ? raw.look_for.filter((term): term is string => typeof term === "string")
        : [],
      required: raw.required === true,
    };
  }
  return result;
}

export function useCorpusRunGuidance(
  schema: Ref<MetadataSchema | null>,
  build: Ref<CorpusBuild | null>,
  translate: Translate,
) {
  const guidance = ref<Record<string, RunGuidanceEntry>>({});
  const fields: ComputedRef<RunGuidanceField[]> = computed(() => {
    const core = ["region_type", "primary_text", "discourse_role"].map((name) => ({
      name,
      label: translate(`record.${name}`, name.replaceAll("_", " ")),
      group: "discourse",
    }));
    const custom = (schema.value?.fields || []).map((field) => ({
      name: field.name,
      label: field.label,
      group: schema.value?.groups.find((item) => item.key === field.group)?.label || field.group,
    }));
    return [...core, ...custom];
  });

  watch(
    schema,
    (next, previous) => {
      if (next?.id !== previous?.id) guidance.value = next ? loadGuidance(next.id) : {};
    },
    { immediate: true },
  );
  watch(
    guidance,
    (value) => {
      if (schema.value) saveGuidance(schema.value.id, value);
    },
    { deep: true },
  );

  const active = computed(() => {
    const request = build.value?.request;
    const stored = request?.run_guidance;
    if (!stored || typeof stored !== "object" || Array.isArray(stored)) return [];
    const labels = new Map(
      (build.value?.schema?.fields || []).map((field) => [field.name, field.label]),
    );
    return Object.entries(stored as Record<string, RunGuidanceEntry>)
      .filter(([, value]) => value && (value.instructions || value.look_for?.length))
      .map(([field, value]) => ({
        field,
        label: labels.get(field) || translate(`record.${field}`, field.replaceAll("_", " ")),
        instructions: value.instructions || "",
        lookFor: value.look_for || [],
      }));
  });

  function payload(): Record<string, RunGuidanceEntry> {
    const result: Record<string, RunGuidanceEntry> = {};
    const known = new Set(fields.value.map((field) => field.name));
    for (const [field, value] of Object.entries(guidance.value)) {
      if (!known.has(field)) continue;
      const required = value.required === true;
      const entry: RunGuidanceEntry = {
        instructions: value.instructions.trim(),
        look_for: value.look_for
          .map((term) => term.trim())
          .filter(Boolean)
          .slice(0, 40),
        required,
      };
      if (entry.instructions || entry.look_for.length || required) result[field] = entry;
    }
    return result;
  }

  return { guidance, fields, active, payload };
}
