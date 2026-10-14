/* Copyright © 2026 Aaron John Schlosser, PhD. AGPL-3.0-or-later. */
/** Infer the retrieval preset from the original run request, never the current composer. */
export function inferResearchPreset(cfg: Record<string, unknown>): string {
  if (cfg.skip_retrieval === true) return "evidence";
  const k = Number(cfg.k);
  const fetchK = Number(cfg.fetch_k);
  const top = Number(cfg.rerank_top_n);
  if (k === 40 && fetchK === 320 && top === 16) return "precision";
  if (k === 96 && fetchK === 1000 && top === 32) return "recall";
  if (k === 64 && fetchK === 500 && top === 24 && Math.abs(Number(cfg.lambda_mult) - 0.7) < 0.001)
    return "balanced";
  return "custom";
}
