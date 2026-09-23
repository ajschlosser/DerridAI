/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { ProviderProfile } from "../api/system";

export type ProviderKind = "ollama" | "openai";

export interface ProviderBulkField {
  key: string;
  types: ProviderKind[];
  input: "number" | "text" | "select";
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string; label: string }>;
}

export const PROVIDER_BULK_FIELDS: ProviderBulkField[] = [
  { key: "max_concurrent_requests", types: ["ollama", "openai"], input: "number", min: 1, max: 64 },
  { key: "num_ctx", types: ["ollama"], input: "number", min: 512 },
  { key: "num_predict", types: ["ollama", "openai"], input: "number", min: 16 },
  { key: "metadata_num_predict", types: ["ollama"], input: "number", min: 16 },
  { key: "temperature", types: ["ollama", "openai"], input: "number", min: 0, max: 2, step: 0.01 },
  { key: "top_p", types: ["ollama", "openai"], input: "number", min: 0, max: 1, step: 0.01 },
  { key: "top_k", types: ["ollama"], input: "number", min: 0 },
  { key: "min_p", types: ["ollama"], input: "number", min: 0, max: 1, step: 0.01 },
  { key: "repeat_penalty", types: ["ollama"], input: "number", min: 0, step: 0.01 },
  { key: "seed", types: ["ollama", "openai"], input: "number" },
  {
    key: "think",
    types: ["ollama"],
    input: "select",
    options: [
      { value: "false", label: "Off" },
      { value: "true", label: "On" },
      { value: "low", label: "Low" },
      { value: "medium", label: "Medium" },
      { value: "high", label: "High" },
    ],
  },
  { key: "keep_alive", types: ["ollama"], input: "text" },
  { key: "mirostat", types: ["ollama"], input: "number", min: 0 },
  { key: "mirostat_eta", types: ["ollama"], input: "number", min: 0, step: 0.01 },
  { key: "mirostat_tau", types: ["ollama"], input: "number", min: 0, step: 0.01 },
];

export function mergeSavedProfile(persisted: ProviderProfile[], draft: ProviderProfile): ProviderProfile[] {
  const copy = JSON.parse(JSON.stringify(draft)) as ProviderProfile;
  let found = false;
  const next = persisted.map((profile) => {
    if (profile.id !== draft.id) return profile;
    found = true;
    return copy;
  });
  if (!found) next.push(copy);
  return next;
}

export function applyProfileFieldValues(
  profiles: ProviderProfile[],
  ids: string[],
  values: Record<string, unknown>,
): ProviderProfile[] {
  const selected = new Set(ids);
  const keys = Object.keys(values);
  return profiles.map((profile) => {
    if (!selected.has(profile.id)) return profile;
    const next = { ...profile } as ProviderProfile;
    for (const key of keys) {
      const spec = PROVIDER_BULK_FIELDS.find((field) => field.key === key);
      if (!spec || !spec.types.includes(profile.type)) continue;
      next[key] = values[key];
    }
    return next;
  });
}
