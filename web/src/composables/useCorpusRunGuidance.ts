// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref, type ComputedRef, type Ref, watch } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import type { MetadataSchema } from "../api/metadataSchemas";
import type { RunGuidanceEntry, RunGuidanceField } from "../components/CorpusRunGuidance.vue";

type Translate = (key: string, fallback: string) => string;

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

  watch(schema, (next, previous) => {
    if (next?.id !== previous?.id) guidance.value = {};
  });

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
    for (const [field, value] of Object.entries(guidance.value)) {
      const entry = {
        instructions: value.instructions.trim(),
        look_for: value.look_for.map((term) => term.trim()).filter(Boolean).slice(0, 40),
      };
      if (entry.instructions || entry.look_for.length) result[field] = entry;
    }
    return result;
  }

  return { guidance, fields, active, payload };
}
