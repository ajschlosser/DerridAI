/* Copyright 2026 Aaron John Schlosser, PhD. */
// Retrieval presets are named bundles of retrieval parameters. A config or a
// run's request matches a preset only when its parameters are exactly those.
export type ResearchPresetSource = {
  skip_retrieval?: boolean | null;
  k?: number | string | null;
  fetch_k?: number | string | null;
  rerank_top_n?: number | string | null;
  lambda_mult?: number | string | null;
};

export function inferResearchPreset(cfg: ResearchPresetSource): string {
  if (cfg.skip_retrieval) return "evidence";
  const k = Number(cfg.k),
    fetchK = Number(cfg.fetch_k),
    top = Number(cfg.rerank_top_n);
  if (k === 40 && fetchK === 320 && top === 16) return "precision";
  if (k === 96 && fetchK === 1000 && top === 32) return "recall";
  if (k === 64 && fetchK === 500 && top === 24 && Math.abs(Number(cfg.lambda_mult) - 0.7) < 0.001)
    return "balanced";
  return "custom";
}

export function researchPresetLabel(
  preset: string,
  t: (key: string, fallback: string) => string,
): string {
  const labels: Record<string, [string, string]> = {
    balanced: ["research.preset_balanced", "Balanced"],
    precision: ["research.preset_precision", "High precision"],
    recall: ["research.preset_recall", "High recall"],
    evidence: ["research.preset_evidence", "Selected evidence only"],
    custom: ["research.preset_custom", "Custom"],
  };
  const match = labels[preset];
  return match ? t(match[0], match[1]) : preset;
}
