/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref, type Ref } from "vue";
import type { CorpusBuild } from "../../../api/corpus";
import { systemApi, type ProviderProfile } from "../../../api/system";
import type { RecordSizingPolicy } from "../../../types/corpus";
import * as runtime from "../../../runtime/runtime.js";

const TEXT_CLEANUP_RULES = [
  "page_numbers",
  "repeated_short_lines",
  "line_hyphenation",
  "paragraph_lines",
  "empty_lines",
  "ocr_artifacts",
  "whitespace",
] as const;

export function useCorpusProviderConfiguration(currentBuild: Ref<CorpusBuild | null>) {
  const providerProfiles = ref<ProviderProfile[]>([]);
  const serverProviderIds = ref<Set<string>>(new Set());
  const selectedProviderId = ref("");
  const selectedReviewProviderId = ref("");
  const llmActionProviderId = ref("");
  const llmActionModel = ref("");

  const manualProvider = ref<"ollama" | "openai">("ollama");
  const manualModel = ref("");
  const manualBaseUrl = ref("");
  const manualApiKey = ref("");
  const useProfileDefaults = ref(true);
  const generationOverrides = ref<Record<string, unknown>>({});
  const maxConcurrentRequests = ref(1);
  const stageLimits = ref<Record<string, number>>({
    manifest_num_predict: 1800,
    segmentation_num_predict: 1200,
    reconciliation_num_predict: 1000,
    discourse_num_predict: 1600,
    quotation_num_predict: 1500,
    indexing_num_predict: 1200,
    segmentation_window_tokens: 5000,
  });
  const stageTimeouts = ref<Record<string, number>>({
    manifest: 300,
    segmentation: 300,
    reconciliation: 240,
    discourse: 240,
    quotation: 240,
    indexing: 180,
  });
  const recordSizing = ref<RecordSizingPolicy>({
    preferred_record_chars: 1750,
    record_length_tolerance: 200,
    long_record_chars: 3500,
    absolute_record_chars: 6000,
  });
  const enrichmentMode = ref<"fast" | "deep">("fast");
  const semanticIndexing = ref(true);
  const autoCleanText = ref(true);
  const llmTouchupDuringEnrichment = ref(false);
  const noiseUnusableThreshold = ref(45);
  const llmAssessTextNoise = ref(false);

  function directProfilePayload(profileId: string): Record<string, unknown> | null {
    const config = runtime.getProviderRequestConfigForUi?.(profileId, {
      textReview: false,
    }) as Record<string, unknown> | null;
    if (!config) return null;
    const ollama = config.ollama;
    return {
      provider_profile_id: profileId,
      provider: config.provider,
      model: config.model,
      base_url: config.base_url,
      api_key: config.api_key,
      max_concurrent_requests: Math.max(
        1,
        Math.min(16, Number(config.max_concurrent_requests || 1)),
      ),
      generation:
        config.provider === "ollama" && ollama && typeof ollama === "object" ? ollama : undefined,
    };
  }

  function directProfilePayloadWithModel(
    profileId: string,
    modelOverride = "",
  ): Record<string, unknown> | null {
    const payload = directProfilePayload(profileId);
    if (!payload) return null;
    return modelOverride ? { ...payload, model: modelOverride } : payload;
  }

  const selectedProfile = computed(
    () => providerProfiles.value.find((profile) => profile.id === selectedProviderId.value) || null,
  );
  const selectedProfileModel = computed(() => String(selectedProfile.value?.model || ""));
  const profileGeneration = computed<Record<string, unknown>>(() => {
    if (!selectedProviderId.value) return {};
    const payload = directProfilePayload(selectedProviderId.value);
    const generation = payload?.generation;
    return generation && typeof generation === "object"
      ? { ...(generation as Record<string, unknown>) }
      : {};
  });
  const effectiveGeneration = computed<Record<string, unknown>>(() =>
    useProfileDefaults.value
      ? profileGeneration.value
      : { ...profileGeneration.value, ...generationOverrides.value },
  );
  const effectiveNumCtx = computed(() => Number(effectiveGeneration.value.num_ctx || 0));
  const requiredContext = computed(
    () =>
      Number(stageLimits.value.segmentation_window_tokens || 5000) +
      Number(stageLimits.value.segmentation_num_predict || 1200) +
      1536,
  );
  const contextSafe = computed(
    () => !effectiveNumCtx.value || requiredContext.value <= effectiveNumCtx.value,
  );
  const selectedProviderLabel = computed(
    () =>
      selectedProfile.value?.name ||
      selectedProviderId.value ||
      (manualProvider.value === "openai" ? "OpenAI-compatible" : "Ollama"),
  );

  const providerPayload = computed<Record<string, unknown>>(() => {
    const buildGeneration = useProfileDefaults.value ? null : { ...effectiveGeneration.value };
    if (selectedProviderId.value) {
      const primary = directProfilePayload(selectedProviderId.value) || {
        provider_profile_id: selectedProviderId.value,
      };
      const payload: Record<string, unknown> = {
        ...primary,
        use_profile_defaults: useProfileDefaults.value,
      };
      if (!useProfileDefaults.value) payload.generation = buildGeneration;
      if (serverProviderIds.value.has(selectedProviderId.value)) {
        delete payload.provider;
        if (useProfileDefaults.value) delete payload.generation;
      }
      payload.max_concurrent_requests = maxConcurrentRequests.value;
      payload.stage_limits = { ...stageLimits.value };
      payload.stage_timeouts = { ...stageTimeouts.value };
      payload.record_sizing = { ...recordSizing.value };
      payload.enrichment_mode = enrichmentMode.value;
      payload.semantic_indexing = semanticIndexing.value;
      payload.auto_clean_text = autoCleanText.value;
      payload.llm_touchup_during_enrichment = llmTouchupDuringEnrichment.value;
      payload.noise_unusable_threshold = noiseUnusableThreshold.value;
      payload.llm_assess_text_noise = llmAssessTextNoise.value;
      payload.text_cleanup_rules = [...TEXT_CLEANUP_RULES];
      if (
        selectedReviewProviderId.value &&
        selectedReviewProviderId.value !== selectedProviderId.value
      ) {
        payload.review_provider_profile_id = selectedReviewProviderId.value;
        const review = directProfilePayload(selectedReviewProviderId.value);
        if (review) {
          const reviewConfig: Record<string, unknown> = {};
          if (review.base_url) reviewConfig.base_url = review.base_url;
          if (review.api_key) reviewConfig.api_key = review.api_key;
          if (!serverProviderIds.value.has(selectedReviewProviderId.value)) {
            for (const key of ["provider", "model", "generation"] as const) {
              if (review[key] !== undefined) reviewConfig[key] = review[key];
            }
          }
          if (Object.keys(reviewConfig).length) payload.review_provider = reviewConfig;
        }
      }
      return payload;
    }

    const payload: Record<string, unknown> = {
      provider: manualProvider.value,
      use_profile_defaults: false,
      max_concurrent_requests: maxConcurrentRequests.value,
      stage_limits: { ...stageLimits.value },
      stage_timeouts: { ...stageTimeouts.value },
      record_sizing: { ...recordSizing.value },
      enrichment_mode: enrichmentMode.value,
      semantic_indexing: semanticIndexing.value,
      auto_clean_text: autoCleanText.value,
      llm_touchup_during_enrichment: llmTouchupDuringEnrichment.value,
      noise_unusable_threshold: noiseUnusableThreshold.value,
      llm_assess_text_noise: llmAssessTextNoise.value,
      text_cleanup_rules: [...TEXT_CLEANUP_RULES],
    };
    if (manualModel.value.trim()) payload.model = manualModel.value.trim();
    if (manualBaseUrl.value.trim()) payload.base_url = manualBaseUrl.value.trim();
    if (manualApiKey.value) payload.api_key = manualApiKey.value;
    if (Object.keys(generationOverrides.value).length) {
      payload.generation = { ...generationOverrides.value };
    }
    return payload;
  });

  async function refreshProviders() {
    const runtimeProfiles = (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[];
    const defaultId = String(runtime.getDefaultProviderProfileId?.() || "");
    const publishProfiles = (profiles: ProviderProfile[]) => {
      providerProfiles.value = profiles;
      if (
        !selectedProviderId.value ||
        !profiles.some((profile) => profile.id === selectedProviderId.value)
      ) {
        selectedProviderId.value =
          profiles.find((profile) => profile.id === defaultId)?.id || profiles[0]?.id || "";
      }
      if (
        !llmActionProviderId.value ||
        !profiles.some((profile) => profile.id === llmActionProviderId.value)
      ) {
        llmActionProviderId.value = selectedProviderId.value;
      }
    };

    publishProfiles(runtimeProfiles);
    let serverProfiles: ProviderProfile[] = [];
    try {
      serverProfiles = (await systemApi.researcherProviders()).profiles || [];
    } catch {
      serverProfiles = [];
    }
    serverProviderIds.value = new Set(serverProfiles.map((profile) => profile.id));

    const merged = new Map<string, ProviderProfile>();
    for (const profile of serverProfiles) merged.set(profile.id, profile);
    for (const profile of runtimeProfiles) merged.set(profile.id, profile);
    const mergedProfiles = Array.from(merged.values());
    publishProfiles(mergedProfiles);

    providerProfiles.value = await Promise.all(
      mergedProfiles.map(async (profile) => {
        try {
          if (serverProviderIds.value.has(profile.id)) {
            const status = await systemApi.researcherProviderAvailability(profile.id);
            return {
              ...profile,
              available: Boolean(status.available && status.model_available),
              availability_error:
                status.error ||
                (!status.model_available
                  ? `Configured model "${status.configured_model || profile.model || "unknown"}" was not found.`
                  : ""),
            };
          }
          const config = directProfilePayload(profile.id);
          if (!config) {
            return {
              ...profile,
              available: false,
              availability_error: "Provider configuration is unavailable.",
            };
          }
          const status = await systemApi.llmStatus({
            provider: config.provider,
            base_url: config.base_url,
            api_key: config.api_key,
          });
          const names = new Set((status.models || []).map((model) => String(model.name || "")));
          const modelAvailable = Boolean(config.model && names.has(String(config.model)));
          return {
            ...profile,
            available: Boolean(status.available && modelAvailable),
            availability_error:
              status.error ||
              (!modelAvailable
                ? `Configured model "${String(config.model || "unknown")}" was not found.`
                : ""),
          };
        } catch (exc) {
          return {
            ...profile,
            available: false,
            availability_error: exc instanceof Error ? exc.message : String(exc),
          };
        }
      }),
    );

    const activeBuildProfile = String(
      (currentBuild.value?.request as Record<string, unknown> | undefined)?.provider_profile_id ||
        "",
    );
    if (
      activeBuildProfile &&
      providerProfiles.value.some((profile) => profile.id === activeBuildProfile)
    ) {
      selectedProviderId.value = activeBuildProfile;
    } else if (
      !currentBuild.value ||
      !selectedProviderId.value ||
      !providerProfiles.value.some((profile) => profile.id === selectedProviderId.value)
    ) {
      selectedProviderId.value =
        providerProfiles.value.find(
          (profile) => profile.id === defaultId && profile.available !== false,
        )?.id ||
        providerProfiles.value.find((profile) => profile.available !== false)?.id ||
        "";
    }
  }

  function applyBuildRequest(request: Record<string, unknown>) {
    if (
      typeof request.provider_profile_id === "string" &&
      providerProfiles.value.some((profile) => profile.id === request.provider_profile_id)
    ) {
      selectedProviderId.value = request.provider_profile_id;
    }
    if (
      typeof request.review_provider_profile_id === "string" &&
      providerProfiles.value.some((profile) => profile.id === request.review_provider_profile_id)
    ) {
      selectedReviewProviderId.value = request.review_provider_profile_id;
    }
    const requestGeneration = request.generation;
    if (requestGeneration && typeof requestGeneration === "object") {
      generationOverrides.value = { ...(requestGeneration as Record<string, unknown>) };
    }
    useProfileDefaults.value = request.use_profile_defaults !== false;
    if (request.stage_limits && typeof request.stage_limits === "object") {
      stageLimits.value = {
        ...stageLimits.value,
        ...(request.stage_limits as Record<string, number>),
      };
    }
    if (request.stage_timeouts && typeof request.stage_timeouts === "object") {
      stageTimeouts.value = {
        ...stageTimeouts.value,
        ...(request.stage_timeouts as Record<string, number>),
      };
    }
    if (request.record_sizing && typeof request.record_sizing === "object") {
      recordSizing.value = {
        ...recordSizing.value,
        ...(request.record_sizing as Partial<RecordSizingPolicy>),
      };
    }
    if (Number.isFinite(Number(request.max_concurrent_requests))) {
      maxConcurrentRequests.value = Math.max(
        1,
        Math.min(16, Number(request.max_concurrent_requests)),
      );
    }
  }

  return {
    providerProfiles,
    serverProviderIds,
    selectedProviderId,
    selectedReviewProviderId,
    llmActionProviderId,
    llmActionModel,
    manualProvider,
    manualModel,
    manualBaseUrl,
    manualApiKey,
    useProfileDefaults,
    generationOverrides,
    maxConcurrentRequests,
    stageLimits,
    stageTimeouts,
    recordSizing,
    enrichmentMode,
    semanticIndexing,
    autoCleanText,
    llmTouchupDuringEnrichment,
    noiseUnusableThreshold,
    llmAssessTextNoise,
    selectedProfile,
    selectedProfileModel,
    effectiveGeneration,
    effectiveNumCtx,
    requiredContext,
    contextSafe,
    selectedProviderLabel,
    providerPayload,
    directProfilePayload,
    directProfilePayloadWithModel,
    refreshProviders,
    applyBuildRequest,
  };
}
