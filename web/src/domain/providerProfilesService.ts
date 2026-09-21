/* Copyright 2026 Aaron John Schlosser, PhD. */
import { cloneAuditValue } from "./recordValues";
import { providerRequestConfig } from "./providerRequest";

// LLM provider profiles: the configured list, defaults, status checks and the helpers the Settings and Providers
// views call. Moved verbatim from the legacy runtime; the runtime's state object and helpers are passed in.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  state: Loose;
  api: (path: string, options?: RequestInit) => Promise<any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  persistPrefs: () => void;
  uid: () => string;
  isResearcher: () => boolean;
  warmupProviderProfile: (profile: Loose, options?: Loose) => Promise<unknown>;
}

export function createProviderProfiles(deps: Deps) {
  const { state, api, persistPrefs, uid, isResearcher, warmupProviderProfile } = deps;
  function ensureProviderProfiles() {
    let profiles = Array.isArray(state.appConfig.provider_profiles)
      ? state.appConfig.provider_profiles
      : [];
    profiles = profiles.filter(
      (profile: Loose) => profile && profile.id && ["ollama", "openai"].includes(profile.type),
    );
    if (!profiles.length) {
      profiles = [
        {
          id: "ollama-default",
          name: "Local Ollama",
          type: "ollama",
          base_url: state.appConfig.ollama_base_url || "http://host.docker.internal:11434",
          model: state.appConfig.ollama_model || state.appConfig.chat_model || "gemma4:e2b",
          model_mode: "manual",
          model_kind: "any",
          api_key: "",
          num_ctx: state.llmConfig.num_ctx ?? 16384,
          num_predict: state.appConfig.text_num_predict ?? 4096,
          metadata_num_predict: state.appConfig.metadata_num_predict ?? 768,
          think: String(state.llmConfig.think ?? "false"),
          temperature: state.llmConfig.temperature ?? 0,
          top_k: state.llmConfig.top_k ?? 0,
          top_p: state.llmConfig.top_p ?? 1,
          min_p: state.llmConfig.min_p ?? "",
          repeat_penalty: state.llmConfig.repeat_penalty ?? 1.1,
          seed: state.llmConfig.seed ?? "",
          mirostat: state.llmConfig.mirostat ?? 0,
          mirostat_eta: state.llmConfig.mirostat_eta ?? "",
          mirostat_tau: state.llmConfig.mirostat_tau ?? "",
          keep_alive: state.llmConfig.keep_alive || "10m",
          extra_options: state.llmConfig.extra_options || "{}",
          max_concurrent_requests: 1,
        },
        {
          id: "openai-default",
          name: "FreeLLM / OpenAI-compatible",
          type: "openai",
          base_url: state.appConfig.openai_base_url || "http://host.docker.internal:3001/v1",
          model: state.appConfig.openai_model || "auto",
          model_mode: state.appConfig.openai_model_mode || "auto",
          model_kind: state.appConfig.openai_model_kind || "any",
          api_key: state.appConfig.openai_api_key || "",
          num_predict: state.appConfig.openai_num_predict ?? 4096,
          temperature: state.appConfig.openai_temperature ?? 0,
          top_p: state.appConfig.openai_top_p ?? 1,
          seed: state.appConfig.openai_seed ?? "",
          extra_options: state.appConfig.openai_extra_options || "{}",
          max_concurrent_requests: 32,
        },
      ];
    }
    profiles = profiles.map((profile: Loose) => ({
      ...profile,
      max_concurrent_requests: Math.max(
        1,
        Math.min(
          64,
          Number(profile.max_concurrent_requests ?? (profile.type === "ollama" ? 1 : 32)) || 1,
        ),
      ),
    }));
    // Ollama concurrency belongs to the endpoint, not the profile. Multiple
    // profiles can point at the same server/model host, so the safest configured
    // limit governs every profile sharing that endpoint. Normalize on read as
    // well as save so older browser preferences cannot bypass the shared cap.
    const ollamaEndpointLimits = new Map();
    for (const profile of profiles) {
      if (profile.type !== "ollama") continue;
      const endpoint = String(profile.base_url || "")
        .replace(/\/+$/g, "")
        .toLocaleLowerCase();
      const limit = Number(profile.max_concurrent_requests || 1);
      ollamaEndpointLimits.set(
        endpoint,
        Math.min(ollamaEndpointLimits.get(endpoint) ?? limit, limit),
      );
    }
    profiles = profiles.map((profile: Loose) =>
      profile.type === "ollama"
        ? {
            ...profile,
            max_concurrent_requests:
              ollamaEndpointLimits.get(
                String(profile.base_url || "")
                  .replace(/\/+$/g, "")
                  .toLocaleLowerCase(),
              ) ?? profile.max_concurrent_requests,
          }
        : profile,
    );
    state.appConfig.provider_profiles = profiles;
    if (
      !profiles.some((profile: Loose) => profile.id === state.appConfig.default_provider_profile)
    ) {
      const preferred =
        profiles.find(
          (profile: Loose) => profile.type === (state.appConfig.chat_provider || "ollama"),
        ) || profiles[0];
      state.appConfig.default_provider_profile = preferred?.id || "";
    }
    return profiles;
  }
  function providerProfiles() {
    if (isResearcher())
      return Array.isArray(state.researcherProviderProfiles)
        ? state.researcherProviderProfiles
        : [];
    return ensureProviderProfiles();
  }
  function providerProfile(id: string) {
    const profiles = providerProfiles();
    return profiles.find((profile: Loose) => profile.id === id) || profiles[0] || null;
  }
  function defaultProviderProfile() {
    return providerProfile(state.appConfig.default_provider_profile);
  }
  function providerDisplayName(profile: Loose) {
    if (!profile) return "LLM provider";
    return (
      profile.name ||
      `${profile.type === "ollama" ? "Ollama" : "OpenAI-compatible"} · ${profile.model || "model"}`
    );
  }
  async function refreshProviderStatuses() {
    const statuses: Loose = {};
    await Promise.all(
      providerProfiles().map(async (profile: Loose) => {
        try {
          statuses[profile.id] = await api("/api/llm/status", {
            method: "POST",
            body: JSON.stringify({
              provider: profile.type,
              base_url: profile.base_url || null,
              api_key: profile.type === "openai" ? profile.api_key || "" : null,
            }),
          });
        } catch (error) {
          statuses[profile.id] = {
            provider: profile.type,
            available: false,
            base_url: profile.base_url,
            configured_model: profile.model,
            models: [],
            error: (error as Error).message,
          };
        }
      }),
    );
    state.providerStatuses = statuses;
    const current = defaultProviderProfile();
    state.llmStatus = current ? statuses[current.id] || null : null;
    return statuses;
  }
  function getProviderProfilesForUi() {
    return cloneAuditValue(providerProfiles());
  }
  function getProviderRequestConfigForUi(profileId: string, { textReview = false } = {}) {
    const profile = providerProfile(profileId);
    return profile ? cloneAuditValue(providerRequestConfig(profile, { textReview })) : null;
  }
  function saveProviderProfilesForUi(profiles: Loose[] = []) {
    if (!Array.isArray(profiles) || !profiles.length)
      throw new Error("At least one provider profile is required.");
    state.appConfig.provider_profiles = cloneAuditValue(profiles);
    if (
      !state.appConfig.provider_profiles.some(
        (profile: Loose) => profile.id === state.appConfig.default_provider_profile,
      )
    )
      state.appConfig.default_provider_profile = state.appConfig.provider_profiles[0].id;
    const defaultProfile = defaultProviderProfile();
    if (defaultProfile) state.appConfig.chat_provider = defaultProfile.type;
    persistPrefs();
    return getProviderProfilesForUi();
  }
  function addProviderProfileForUi(type: string) {
    ensureProviderProfiles();
    const profile =
      type === "openai"
        ? {
            id: `openai-${uid()}`,
            name: "New OpenAI-compatible / FreeLLM",
            type: "openai",
            base_url: "http://host.docker.internal:3001/v1",
            model: "auto",
            model_mode: "auto",
            model_kind: "any",
            api_key: "",
            max_concurrent_requests: 32,
            num_predict: 4096,
            temperature: 0,
            top_p: 1,
            seed: "",
            extra_options: "{}",
          }
        : {
            id: `ollama-${uid()}`,
            name: "New Ollama",
            type: "ollama",
            base_url: "http://host.docker.internal:11434",
            model: "gemma4:e2b",
            model_mode: "manual",
            model_kind: "any",
            api_key: "",
            max_concurrent_requests: 1,
            num_ctx: 16384,
            metadata_num_predict: 768,
            num_predict: 4096,
            think: "false",
            temperature: 0,
            top_k: 0,
            top_p: 1,
            min_p: "",
            repeat_penalty: 1.1,
            seed: "",
            mirostat: 0,
            mirostat_eta: "",
            mirostat_tau: "",
            keep_alive: "10m",
            extra_options: "{}",
          };
    state.appConfig.provider_profiles = [...providerProfiles(), profile];
    persistPrefs();
    return cloneAuditValue(profile);
  }
  function removeProviderProfileForUi(profileId: string) {
    if (providerProfiles().length <= 1)
      throw new Error("At least one LLM provider profile is required.");
    state.appConfig.provider_profiles = providerProfiles().filter(
      (profile: Loose) => profile.id !== profileId,
    );
    if (state.appConfig.default_provider_profile === profileId)
      state.appConfig.default_provider_profile = state.appConfig.provider_profiles[0]?.id || "";
    persistPrefs();
    return getProviderProfilesForUi();
  }
  function setDefaultProviderProfileForUi(profileId: string) {
    if (!providerProfiles().some((profile: Loose) => profile.id === profileId))
      throw new Error("The selected provider profile is no longer available.");
    state.appConfig.default_provider_profile = profileId;
    const profile = providerProfile(profileId);
    if (profile) state.appConfig.chat_provider = profile.type;
    persistPrefs();
  }
  async function testProviderProfileForUi(profileId: string) {
    const profile = providerProfile(profileId);
    if (!profile) throw new Error("The selected provider profile is no longer available.");
    const result = await api("/api/llm/status", {
      method: "POST",
      body: JSON.stringify({
        provider: profile.type,
        base_url: profile.base_url,
        api_key: profile.type === "openai" ? profile.api_key : null,
      }),
    });
    state.providerStatuses[profile.id] = result;
    return cloneAuditValue(result);
  }
  async function warmProviderProfileForUi(profileId: string) {
    const profile = providerProfile(profileId);
    if (!profile) throw new Error("The selected provider profile is no longer available.");
    await warmupProviderProfile(profile.id);
    return cloneAuditValue(state.providerWarmups?.[profile.id] || {});
  }
  function getWarmOnStartForUi() {
    return state.appConfig.warm_default_provider_on_start === true;
  }
  function setWarmOnStartForUi(value: unknown) {
    state.appConfig.warm_default_provider_on_start = Boolean(value);
    persistPrefs();
    return getWarmOnStartForUi();
  }
  function getDefaultProviderProfileId() {
    return state.appConfig.default_provider_profile || defaultProviderProfile()?.id || "";
  }
  function getProviderStatusesForUi() {
    return cloneAuditValue(state.providerStatuses || {});
  }
  function getProviderWarmupsForUi() {
    return cloneAuditValue(state.providerWarmups || {});
  }
  return {
    ensureProviderProfiles,
    providerProfiles,
    providerProfile,
    defaultProviderProfile,
    providerDisplayName,
    refreshProviderStatuses,
    getProviderProfilesForUi,
    getProviderRequestConfigForUi,
    saveProviderProfilesForUi,
    addProviderProfileForUi,
    removeProviderProfileForUi,
    setDefaultProviderProfileForUi,
    testProviderProfileForUi,
    warmProviderProfileForUi,
    getWarmOnStartForUi,
    setWarmOnStartForUi,
    getDefaultProviderProfileId,
    getProviderStatusesForUi,
    getProviderWarmupsForUi,
  };
}
