/* Copyright 2026 Aaron John Schlosser, PhD. */
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Builds the LLM request configuration for a provider profile, moved verbatim from the legacy runtime.

export function providerRequestConfig(
  profile: Loose | null | undefined,
  { textReview = false }: { textReview?: boolean } = {},
) {
  if (!profile) return null;
  let extra = {};
  try {
    extra = JSON.parse(profile.extra_options || "{}");
  } catch {
    // Best effort: fall through to the default.
  }
  if (!extra || Array.isArray(extra) || typeof extra !== "object") extra = {};
  let think = null;
  if (profile.type === "ollama") {
    const raw = String(profile.think ?? "false");
    think = raw === "true" ? true : ["low", "medium", "high"].includes(raw) ? raw : false;
  }
  return {
    provider_profile_id: profile.id,
    max_concurrent_requests: Math.max(
      1,
      Math.min(
        64,
        Number(profile.max_concurrent_requests ?? (profile.type === "ollama" ? 1 : 32)) || 1,
      ),
    ),
    provider: profile.type,
    model:
      profile.type === "openai" && profile.model_mode === "auto" ? "auto" : profile.model || "",
    base_url: profile.base_url || null,
    api_key: profile.type === "openai" ? profile.api_key || "" : null,
    ollama: {
      num_ctx:
        profile.type === "ollama" &&
        Number(profile.num_ctx) >= 512 &&
        Number(profile.num_ctx) <= 262144
          ? Number(profile.num_ctx)
          : null,
      num_predict: Number(
        textReview
          ? (profile.num_predict ?? 4096)
          : (profile.metadata_num_predict ?? profile.num_predict ?? 768),
      ),
      think,
      temperature: profile.temperature === "" ? null : Number(profile.temperature ?? 0),
      top_k: profile.type === "ollama" && profile.top_k !== "" ? Number(profile.top_k) : null,
      top_p: profile.top_p === "" ? null : Number(profile.top_p ?? 1),
      min_p: profile.type === "ollama" && profile.min_p !== "" ? Number(profile.min_p) : null,
      repeat_penalty:
        profile.type === "ollama" && profile.repeat_penalty !== ""
          ? Number(profile.repeat_penalty)
          : null,
      seed: profile.seed === "" ? null : Number(profile.seed),
      mirostat:
        profile.type === "ollama" && profile.mirostat !== "" ? Number(profile.mirostat) : null,
      mirostat_eta:
        profile.type === "ollama" && profile.mirostat_eta !== ""
          ? Number(profile.mirostat_eta)
          : null,
      mirostat_tau:
        profile.type === "ollama" && profile.mirostat_tau !== ""
          ? Number(profile.mirostat_tau)
          : null,
      keep_alive: profile.type === "ollama" ? profile.keep_alive || null : null,
      extra_options: extra,
    },
  };
}
