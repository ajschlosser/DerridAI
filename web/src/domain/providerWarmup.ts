/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

// Warming an LLM provider profile (loads the model on the provider and records progress in `state.providerWarmups`).
// Moved verbatim from `appLifecycle.ts` so provider-profile code can use it without the legacy runtime.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  state: Loose;
  api: Fn;
  providerDisplayName: Fn;
  providerProfile: Fn;
  providerRequestConfig: Fn;
}

export function createProviderWarmup(deps: Deps) {
  const { state, api, providerDisplayName, providerProfile, providerRequestConfig } = deps;
  async function warmupProviderProfile(profileId: string | null = null) {
    const profile = providerProfile(profileId || state.appConfig.default_provider_profile);
    if (!profile) return;
    const current = state.providerWarmups?.[profile.id] || {};
    if (current.status === "running") return;
    const cfg = providerRequestConfig(profile, { textReview: false });
    const started = performance.now();
    const startedAt = new Date().toISOString();
    const running = {
      status: "running",
      message: `Warming ${cfg.model}…`,
      profile_id: profile.id,
      provider: profile.type,
      model: cfg.model,
      base_url: cfg.base_url,
      started_at: startedAt,
      completed_at: null,
      elapsed_seconds: null,
      error: null,
    };
    state.providerWarmups[profile.id] = running;
    if (profile.id === state.appConfig.default_provider_profile) state.warmup = running;
    if (state.view === "home") window.dispatchEvent(new CustomEvent("derridai:dashboard-refresh"));
    try {
      const result = await api("/api/llm/warmup", {
        method: "POST",
        body: JSON.stringify({
          provider: profile.type,
          model: cfg.model,
          base_url: cfg.base_url,
          api_key: cfg.api_key,
          // Load with the context real calls use, so the model is not loaded twice.
          num_ctx: Number(cfg.ollama?.num_ctx) > 0 ? Number(cfg.ollama.num_ctx) : undefined,
        }),
      });
      const ready = {
        status: "ready",
        message: `${providerDisplayName(profile)} · ${result.model || cfg.model} warmed`,
        profile_id: profile.id,
        provider: profile.type,
        model: result.model || cfg.model,
        base_url: result.base_url || cfg.base_url,
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        elapsed_seconds: (performance.now() - started) / 1000,
        error: null,
      };
      state.providerWarmups[profile.id] = ready;
      if (profile.id === state.appConfig.default_provider_profile) state.warmup = ready;
    } catch (caught) {
      const error = caught as Loose;
      const failed = {
        status: "failed",
        message: error.message,
        profile_id: profile.id,
        provider: profile.type,
        model: cfg.model,
        base_url: cfg.base_url,
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        elapsed_seconds: (performance.now() - started) / 1000,
        error: error.message,
      };
      state.providerWarmups[profile.id] = failed;
      if (profile.id === state.appConfig.default_provider_profile) state.warmup = failed;
    }
    if (state.view === "home") window.dispatchEvent(new CustomEvent("derridai:dashboard-refresh"));
  }
  return { warmupProviderProfile };
}
