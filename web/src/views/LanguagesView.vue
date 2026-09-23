<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  systemApi,
  type LanguageContentPolicy,
  type LanguageDictionary,
  type LanguageInfo,
  type ProviderProfile,
} from "../api/system";
import { jobsApi, type JobSummary } from "../api/jobs";
import { useI18nStore } from "../stores/i18n";
import * as runtime from "../runtime/runtime.js";
import LanguageFlag from "../components/LanguageFlag.vue";
import ProviderProfileSelect from "../components/ProviderProfileSelect.vue";
import CountryFlagPicker from "../components/CountryFlagPicker.vue";
import LanguageWorkspaceHeader from "../components/LanguageWorkspaceHeader.vue";
import AppIcon from "../components/AppIcon.vue";

const i18n = useI18nStore();
const languages = ref<LanguageInfo[]>([]);
const selectedCode = ref("en-US");
const current = ref<LanguageDictionary | null>(null);
const referenceDictionary = ref<Record<string, string>>({});
const providerProfiles = ref<ProviderProfile[]>([]);
const selectedProviderId = ref("");
const loading = ref(true);
const saving = ref(false);
const installing = ref(false);
const error = ref("");
const installOpen = ref(false);
const installCloseConfirm = ref(false);
const manageProvidersConfirm = ref(false);
const headerRef = ref<InstanceType<typeof LanguageWorkspaceHeader> | null>(null);
const installCodeInput = ref<HTMLInputElement | null>(null);
const installDialog = ref<HTMLElement | null>(null);
const installCloseDialog = ref<HTMLElement | null>(null);
const manageProvidersDialog = ref<HTMLElement | null>(null);
const unsavedDialog = ref<HTMLElement | null>(null);
const deleteDialog = ref<HTMLElement | null>(null);
let confirmationReturnFocus: HTMLElement | null = null;
const pendingDelete = ref<LanguageInfo | null>(null);
const pendingLocaleCode = ref("");
const localeQuery = ref("");
const keyQuery = ref("");
const activeCategory = ref("all");
const importInput = ref<HTMLInputElement | null>(null);
const statusFilter = ref<"all" | "localized" | "english" | "missing" | "review">("all");
const install = ref({ code: "", name: "", flag: "🌐" });
const installAutoName = ref("");
const installFlagTouched = ref(false);
const newKey = ref("");
const newValue = ref("");
const baseline = ref("");
const installJob = ref<JobSummary | null>(null);
const policyJob = ref<JobSummary | null>(null);
const contentPolicy = ref<LanguageContentPolicy | null>(null);
const newPolicyTerm = ref("");
const savingPolicy = ref(false);
const resumeJobId = ref("");
const translationRiskAcknowledged = ref(false);
let installPollTimer = 0;
let policyPollTimer = 0;

const selectedProvider = computed(
  () =>
    providerProfiles.value.find((item) => item.id === selectedProviderId.value) ||
    providerProfiles.value[0] ||
    null,
);
const isCanonical = computed(() => current.value?.code === "en-US");
const allKeys = computed(() => {
  const keys = new Set<string>([
    ...Object.keys(referenceDictionary.value),
    ...Object.keys(current.value?.dictionary || {}),
  ]);
  return [...keys].sort((a, b) => a.localeCompare(b));
});
const categories = computed(() => {
  const counts = new Map<string, number>();
  for (const key of allKeys.value) {
    const category = key.includes(".") ? key.split(".")[0] : "other";
    counts.set(category, (counts.get(category) || 0) + 1);
  }
  return [
    { id: "all", count: allKeys.value.length },
    ...[...counts.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([id, count]) => ({ id, count })),
  ];
});
const rows = computed(() =>
  allKeys.value.map((key) => [key, current.value?.dictionary?.[key] || ""] as const),
);
const trackedFallbackKeys = computed(
  () => new Set((current.value?.translation_report?.failed_keys || []).map(String)),
);
const trackedFallbackCount = computed(() => trackedFallbackKeys.value.size);
const trackedFallbackFailures = computed(() =>
  (current.value?.translation_report?.failures || []).filter(
    (item) => item?.key && trackedFallbackKeys.value.has(String(item.key)),
  ),
);
const stats = computed(() => {
  const total = rows.value.length;
  let missing = 0;
  let matchesEnglish = 0;
  let localized = 0;
  for (const [key, value] of rows.value) {
    if (!value.trim()) missing += 1;
    else if (!isCanonical.value && value.trim() === sourceValue(key).trim()) matchesEnglish += 1;
    else localized += 1;
  }
  return {
    total,
    missing,
    matchesEnglish,
    localized,
    coverage: total ? Math.round(((total - missing) / total) * 100) : 0,
  };
});
const filteredRows = computed(() => {
  const needle = keyQuery.value.trim().toLocaleLowerCase(i18n.locale);
  return rows.value.filter(([key, value]) => {
    const category = key.includes(".") ? key.split(".")[0] : "other";
    if (activeCategory.value !== "all" && category !== activeCategory.value) return false;
    const source = sourceValue(key);
    const matchesSearch =
      !needle ||
      key.toLocaleLowerCase(i18n.locale).includes(needle) ||
      source.toLocaleLowerCase(i18n.locale).includes(needle) ||
      value.toLocaleLowerCase(i18n.locale).includes(needle);
    if (!matchesSearch) return false;
    if (statusFilter.value === "missing") return !value.trim();
    if (statusFilter.value === "review")
      return !isCanonical.value && trackedFallbackKeys.value.has(key);
    if (statusFilter.value === "english")
      return !isCanonical.value && Boolean(value.trim()) && value.trim() === source.trim();
    if (statusFilter.value === "localized")
      return isCanonical.value
        ? Boolean(value.trim())
        : Boolean(value.trim()) && value.trim() !== source.trim();
    return true;
  });
});
const filteredLanguages = computed(() => {
  const needle = localeQuery.value.trim().toLocaleLowerCase(i18n.locale);
  if (!needle) return languages.value;
  return languages.value.filter(
    (item) =>
      item.code.toLowerCase().includes(needle) ||
      item.name.toLocaleLowerCase(i18n.locale).includes(needle),
  );
});
const dirty = computed(() => Boolean(current.value) && snapshotCurrent() !== baseline.value);
const installProgress = computed(() => {
  const total = Number(installJob.value?.total || 0);
  const completed = Number(installJob.value?.completed || 0);
  return total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
});
const installCodeExists = computed(() => {
  const candidate = install.value.code.trim().replaceAll("_", "-").toLowerCase();
  return (
    Boolean(candidate) &&
    languages.value.some((item) => item.code.replaceAll("_", "-").toLowerCase() === candidate)
  );
});
const installDraftDirty = computed(() =>
  Boolean(
    install.value.code.trim() ||
      install.value.name.trim() ||
      (install.value.flag && install.value.flag !== "🌐"),
  ),
);
const modelTranslationRisk = computed(() =>
  translationRiskForModel(String(selectedProvider.value?.model || "")),
);
const modelTranslationRiskMessage = computed(() => {
  const risk = modelTranslationRisk.value;
  if (!risk) return "";
  if (risk.kind === "embedding")
    return i18n.tf("language.model_translation_risk_embedding", { model: risk.label });
  if (risk.kind === "code")
    return i18n.tf("language.model_translation_risk_code", { model: risk.label });
  if (risk.kind === "language")
    return i18n.tf("language.model_translation_risk_language", { model: risk.label });
  return i18n.tf("language.model_translation_risk_small", { model: risk.label });
});
const resumableInstallJob = computed(() => {
  const job = installJob.value;
  if (!job || !["failed", "cancelled"].includes(job.status)) return null;
  return job.result?.resumable ? job : null;
});
const installFailureCount = computed(() =>
  Number(installJob.value?.result?.failed_count || installJob.value?.result?.fallback_count || 0),
);
const installPartialCount = computed(() =>
  Number(
    installJob.value?.result?.partial_key_count ||
      installJob.value?.result?.translated_count ||
      installJob.value?.completed ||
      0,
  ),
);
const pendingPolicyCount = computed(
  () => languages.value.filter((item) => !item.content_policy_ready).length,
);
const policyReady = computed(
  () =>
    contentPolicy.value?.status === "ready" &&
    Boolean(
      contentPolicy.value.blocked_terms?.length || contentPolicy.value.contextual_terms?.length,
    ),
);
const policyBusy = computed(() =>
  Boolean(
    policyJob.value && !["completed", "failed", "cancelled"].includes(policyJob.value.status),
  ),
);

function translationRiskForModel(model: string) {
  const id = model.trim().toLowerCase();
  if (!id || id === "auto") return null;
  if (
    /(?:bge(?:-|_)|nomic[-_.]?embed|mxbai[-_.]?embed|all[-_.]?minilm|e5[-_.]|gte[-_.]|rerank|cross[-_.]?encoder)/i.test(
      id,
    )
  ) {
    return { kind: "embedding", label: model };
  }
  if (
    /(?:codegemma|codellama|starcoder|deepseek[^/:]*coder|qwen[^/:]*coder|granite[^/:]*code)/i.test(
      id,
    )
  ) {
    return { kind: "code", label: model };
  }
  if (/(?:phi[-_. ]?[34]?[-_. ]?mini|tinyllama|smollm|orca[-_. ]?mini|stablelm)/i.test(id)) {
    return { kind: "language", label: model };
  }
  const size = id.match(/(?:^|[^0-9])(\d+(?:\.\d+)?)b(?:[^a-z]|$)/i);
  if (size && Number(size[1]) <= 4.5) return { kind: "small", label: model };
  return null;
}

// A language's flag is plain stored data; nothing here depends on which language it is.
function flagFor(_code: string, stored = "🌐") {
  return stored || "🌐";
}
function snapshotCurrent() {
  if (!current.value) return "";
  return JSON.stringify({
    name: current.value.name,
    flag: current.value.flag,
    dictionary: current.value.dictionary,
  });
}
function describeKey(key: string) {
  const [prefix] = key.split(".");
  const kind: Record<string, string> = {
    nav: i18n.t("language.description_nav"),
    ui: i18n.t("language.description_ui"),
    users: i18n.t("language.description_users"),
    language: i18n.t("language.description_language"),
    research: i18n.t("language.description_research"),
    rag: i18n.t("language.description_rag"),
    record: i18n.t("language.description_record"),
    section: i18n.t("language.description_section"),
    role: i18n.t("language.description_role"),
    app: i18n.t("language.description_app"),
  };
  return kind[prefix] || i18n.t("language.description_generic");
}
function sourceValue(key: string) {
  return isCanonical.value
    ? current.value?.dictionary?.[key] || referenceDictionary.value[key] || ""
    : referenceDictionary.value[key] || "";
}
function localeDisplayName(code: string) {
  try {
    return new Intl.DisplayNames([i18n.locale], { type: "language" }).of(code) || code;
  } catch {
    return code;
  }
}
function regionFlagForLocale(code: string) {
  try {
    const region = new Intl.Locale(code.replaceAll("_", "-")).region;
    if (!region || !/^[A-Z]{2}$/i.test(region)) return "🌐";
    return region
      .toUpperCase()
      .replace(/[A-Z]/g, (char) => String.fromCodePoint(127397 + char.charCodeAt(0)));
  } catch {
    return "🌐";
  }
}
function setInstallFlag(value: string) {
  install.value.flag = value;
  installFlagTouched.value = true;
}
function refreshProviderProfiles() {
  providerProfiles.value = (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[];
  const preferred = runtime.getDefaultProviderProfileId?.() || "";
  if (!providerProfiles.value.some((item) => item.id === selectedProviderId.value)) {
    selectedProviderId.value = providerProfiles.value.some((item) => item.id === preferred)
      ? preferred
      : providerProfiles.value[0]?.id || "";
  }
}
async function refreshLanguages() {
  const data = await systemApi.languages();
  languages.value = data.languages.map((item) => ({
    ...item,
    flag: flagFor(item.code, item.flag),
  }));
  if (!languages.value.some((item) => item.code === selectedCode.value))
    selectedCode.value = languages.value[0]?.code || "en-US";
}
async function load(code = selectedCode.value) {
  loading.value = true;
  error.value = "";
  try {
    selectedCode.value = code;
    const value = await systemApi.language(code);
    current.value = { ...value, flag: flagFor(value.code, value.flag) };
    baseline.value = snapshotCurrent();
    keyQuery.value = "";
    activeCategory.value = categories.value[1]?.id || "all";
    statusFilter.value = "all";
    await loadContentPolicy(code);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}
async function loadContentPolicy(code = selectedCode.value) {
  try {
    contentPolicy.value = await systemApi.languageContentPolicy(code);
  } catch {
    contentPolicy.value = { code, status: "missing", blocked_terms: [], contextual_terms: [] };
  }
}
async function monitorPolicy(jobId: string) {
  window.clearTimeout(policyPollTimer);
  try {
    const job = await jobsApi.get(jobId);
    policyJob.value = job;
    if (["completed", "failed", "cancelled"].includes(job.status)) {
      if (job.status === "completed") {
        await refreshLanguages();
        await loadContentPolicy(String(job.result?.code || selectedCode.value));
        runtime.notifyToast?.(
          i18n.t("language.content_policy_generated"),
          { tone: "success" },
        );
      } else if (job.status === "failed") {
        error.value =
          job.stage_detail ||
          i18n.t("language.content_policy_missing_help");
      }
      return;
    }
    policyPollTimer = window.setTimeout(() => void monitorPolicy(jobId), 1200);
  } catch {
    policyPollTimer = window.setTimeout(() => void monitorPolicy(jobId), 2000);
  }
}
async function generateContentPolicy() {
  const profile = selectedProvider.value;
  const code = current.value?.code;
  if (!profile || !code) {
    error.value = i18n.t("language.provider_profile_required");
    return;
  }
  const model = String(profile.model || "").trim();
  if (!model) {
    error.value = i18n.t("language.provider_model_required");
    return;
  }
  error.value = "";
  try {
    const created = await systemApi.generateLanguageContentPolicy({
      code,
      provider: profile.type,
      model,
      base_url: profile.base_url || undefined,
      // The OpenAI key lives on the browser profile. Record review sends it with
      // the request; leaving it off makes this call go out with no credential.
      api_key: profile.api_key || undefined,
      generation: providerGeneration(profile),
      provider_profile_id: profile.id,
      max_concurrent_requests: profile.max_concurrent_requests || 1,
    });
    policyJob.value = created;
    runtime.registerExternalJob?.(created);
    runtime.notifyToast?.(
      i18n.t("language.content_policy_generating"),
      { tone: "info" },
    );
    void monitorPolicy(created.id);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
function addPolicyTerm() {
  const term = newPolicyTerm.value.trim();
  if (!term || !contentPolicy.value) return;
  const blocked = [...(contentPolicy.value.blocked_terms || [])];
  if (!blocked.includes(term)) blocked.push(term);
  contentPolicy.value = { ...contentPolicy.value, blocked_terms: blocked };
  newPolicyTerm.value = "";
}
function removePolicyTerm(term: string) {
  if (!contentPolicy.value) return;
  contentPolicy.value = {
    ...contentPolicy.value,
    blocked_terms: (contentPolicy.value.blocked_terms || []).filter((item) => item !== term),
  };
}
async function saveContentPolicy() {
  if (!current.value || !contentPolicy.value) return;
  savingPolicy.value = true;
  error.value = "";
  try {
    contentPolicy.value = await systemApi.updateLanguageContentPolicy(current.value.code, {
      blocked_terms: contentPolicy.value.blocked_terms || [],
      contextual_terms: contentPolicy.value.contextual_terms || [],
    });
    await refreshLanguages();
    runtime.notifyToast?.(
      i18n.t("language.content_policy_saved"),
      { tone: "success" },
    );
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    savingPolicy.value = false;
  }
}
function rememberConfirmationFocus() {
  confirmationReturnFocus =
    document.activeElement instanceof HTMLElement ? document.activeElement : null;
}
function restoreConfirmationFocus() {
  const target = confirmationReturnFocus;
  confirmationReturnFocus = null;
  if (target?.isConnected) target.focus();
}
async function focusDialog(root: HTMLElement | null) {
  await nextTick();
  root
    ?.querySelector<HTMLElement>(
      'button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[href],[tabindex]:not([tabindex="-1"])',
    )
    ?.focus();
}
function requestLoad(code: string) {
  if (code === selectedCode.value) return;
  if (dirty.value) {
    rememberConfirmationFocus();
    pendingLocaleCode.value = code;
    return;
  }
  void load(code);
}
function discardAndSwitch() {
  const code = pendingLocaleCode.value;
  pendingLocaleCode.value = "";
  if (code) void load(code);
}
function updateValue(key: string, value: string) {
  if (!current.value) return;
  current.value = { ...current.value, dictionary: { ...current.value.dictionary, [key]: value } };
}
function exportDictionary() {
  if (!current.value) return;
  const keys =
    activeCategory.value === "all"
      ? allKeys.value
      : allKeys.value.filter(
          (key) => (key.includes(".") ? key.split(".")[0] : "other") === activeCategory.value,
        );
  const dictionary = Object.fromEntries(
    keys.map((key) => [key, current.value?.dictionary?.[key] || ""]),
  );
  const payload = {
    format: "derridai-language-dictionary-v1",
    code: current.value.code,
    name: current.value.name,
    flag: current.value.flag,
    scope: activeCategory.value === "all" ? "full" : "category",
    category: activeCategory.value === "all" ? undefined : activeCategory.value,
    dictionary,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${current.value.code}${activeCategory.value === "all" ? "" : `-${activeCategory.value}`}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
function openImport() {
  importInput.value?.click();
}
async function importDictionary(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || !current.value) return;
  try {
    const parsed = JSON.parse(await file.text()) as { code?: string; dictionary?: unknown };
    if (parsed.code && parsed.code !== current.value.code)
      throw new Error(
        i18n.t("language.import_locale_mismatch"),
      );
    if (
      !parsed.dictionary ||
      typeof parsed.dictionary !== "object" ||
      Array.isArray(parsed.dictionary)
    )
      throw new Error(i18n.t("language.import_invalid"));
    const entries = Object.entries(parsed.dictionary as Record<string, unknown>).filter(
      (entry): entry is [string, string] =>
        Boolean(entry[0].trim()) && typeof entry[1] === "string",
    );
    if (!entries.length)
      throw new Error(
        i18n.t("language.import_empty"),
      );
    current.value = {
      ...current.value,
      dictionary: { ...current.value.dictionary, ...Object.fromEntries(entries) },
    };
    runtime.notifyToast?.(
      i18n.tf("language.imported", { count: entries.length }),
      { tone: "success" },
    );
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
function addDictionaryEntry() {
  if (!current.value || !isCanonical.value) return;
  const key = newKey.value.trim();
  if (!key) return;
  current.value = {
    ...current.value,
    dictionary: { ...current.value.dictionary, [key]: newValue.value },
  };
  newKey.value = "";
  newValue.value = "";
}
function removeDictionaryEntry(key: string) {
  if (!current.value || !isCanonical.value) return;
  const next = { ...current.value.dictionary };
  delete next[key];
  current.value = { ...current.value, dictionary: next };
}
async function save() {
  if (!current.value) return false;
  saving.value = true;
  error.value = "";
  try {
    current.value = await systemApi.updateLanguage(current.value.code, {
      name: current.value.name,
      flag: flagFor(current.value.code, current.value.flag),
      dictionary: current.value.dictionary,
    });
    if (current.value.code === "en-US") referenceDictionary.value = { ...current.value.dictionary };
    baseline.value = snapshotCurrent();
    await refreshLanguages();
    window.dispatchEvent(
      new CustomEvent("derridai:languages-changed", {
        detail: { source: "language-save", code: current.value.code },
      }),
    );
    runtime.notifyToast?.(i18n.t("language.saved"), {
      tone: "success",
    });
    return true;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
    return false;
  } finally {
    saving.value = false;
  }
}
async function saveAndSwitch() {
  const code = pendingLocaleCode.value;
  if (await save()) {
    pendingLocaleCode.value = "";
    if (code) await load(code);
  }
}
function providerGeneration(profile: ProviderProfile) {
  const value = (key: string) => profile[key];
  return {
    num_ctx: value("num_ctx") || undefined,
    num_predict: value("metadata_num_predict") || value("num_predict") || undefined,
    think: value("think") ?? undefined,
    temperature: value("temperature") ?? 0,
    top_k: value("top_k") ?? 0,
    top_p: value("top_p") ?? 1,
    min_p: value("min_p") || undefined,
    repeat_penalty: value("repeat_penalty") || undefined,
    seed: value("seed") || undefined,
    mirostat: value("mirostat") ?? 0,
    mirostat_eta: value("mirostat_eta") || undefined,
    mirostat_tau: value("mirostat_tau") || undefined,
    keep_alive: value("keep_alive") || undefined,
  };
}
async function monitorInstall(jobId: string) {
  window.clearTimeout(installPollTimer);
  try {
    const job = await jobsApi.get(jobId);
    installJob.value = job;
    if (["completed", "failed", "cancelled"].includes(job.status)) {
      if (job.status === "completed") {
        await refreshLanguages();
        window.dispatchEvent(
          new CustomEvent("derridai:languages-changed", {
            detail: { source: "language-install", jobId },
          }),
        );
        const code = String(job.result?.code || job.request?.code || "");
        if (code) await load(code);
        const fallbackCount = Number(job.result?.fallback_count || job.result?.failed_count || 0);
        if (fallbackCount > 0) {
          statusFilter.value = "review";
          runtime.notifyToast?.(
            i18n.tf("language.installed_with_fallbacks", { count: fallbackCount.toLocaleString(i18n.locale) }),
            { tone: "warning" },
          );
        } else {
          runtime.notifyToast?.(
            i18n.t("language.translation_complete"),
            { tone: "success" },
          );
        }
        resumeJobId.value = "";
      } else if (job.status === "failed") {
        error.value = i18n.tf("language.translation_failed_detail", {
            message:
              job.stage_detail || i18n.t("language.translation_failed"),
          });
      } else if (job.result?.resumable) {
        runtime.notifyToast?.(
          i18n.t("language.partial_translation_restored"),
          { tone: "info" },
        );
      }
      return;
    }
    installPollTimer = window.setTimeout(() => void monitorInstall(jobId), 1200);
  } catch {
    installPollTimer = window.setTimeout(() => void monitorInstall(jobId), 2000);
  }
}

function openInstallDialog() {
  resumeJobId.value = "";
  install.value = { code: "", name: "", flag: "🌐" };
  installAutoName.value = "";
  installFlagTouched.value = false;
  translationRiskAcknowledged.value = false;
  installOpen.value = true;
}

function requestCloseInstall() {
  if (installing.value) return;
  if (installDraftDirty.value) {
    rememberConfirmationFocus();
    installCloseConfirm.value = true;
    return;
  }
  installOpen.value = false;
}

function discardInstallDraft() {
  installCloseConfirm.value = false;
  installOpen.value = false;
}

function openResumeDialog() {
  const job = resumableInstallJob.value;
  if (!job) return;
  const result = (job.result || {}) as Record<string, unknown>;
  const request = (job.request || {}) as Record<string, unknown>;
  const code = String(result.code || request.code || "");
  if (
    !code ||
    languages.value.some(
      (item) =>
        item.code.replaceAll("_", "-").toLowerCase() === code.replaceAll("_", "-").toLowerCase(),
    )
  ) {
    error.value = i18n.t("language.resume_no_longer_needed");
    return;
  }
  install.value = {
    code,
    name: String(result.name || request.name || localeDisplayName(code)),
    flag: String(result.flag || request.flag || regionFlagForLocale(code) || "🌐"),
  };
  installAutoName.value = install.value.name;
  installFlagTouched.value = true;
  resumeJobId.value = job.id;
  const priorProfileId = String(job.provider_profile_id || "");
  if (priorProfileId && providerProfiles.value.some((item) => item.id === priorProfileId))
    selectedProviderId.value = priorProfileId;
  translationRiskAcknowledged.value = false;
  error.value = "";
  installOpen.value = true;
}

async function restoreLanguageTranslationJob() {
  try {
    const data = await jobsApi.list();
    const summary = data.jobs.find(
      (job) =>
        job.mode === "language_dictionary" &&
        ["queued", "running", "cancelling", "failed", "cancelled"].includes(job.status),
    );
    const policySummary = data.jobs.find(
      (job) =>
        job.mode === "language_content_policy" &&
        ["queued", "running", "cancelling"].includes(job.status),
    );
    if (policySummary) {
      const job = await jobsApi.get(policySummary.id);
      policyJob.value = job;
      if (!["failed", "cancelled", "completed"].includes(job.status)) void monitorPolicy(job.id);
    }
    if (!summary) return;
    const job = await jobsApi.get(summary.id);
    const code = String(job.result?.code || job.request?.code || "");
    if (
      code &&
      languages.value.some(
        (item) =>
          item.code.replaceAll("_", "-").toLowerCase() === code.replaceAll("_", "-").toLowerCase(),
      ) &&
      ["failed", "cancelled"].includes(job.status)
    )
      return;
    installJob.value = job;
    if (!["failed", "cancelled", "completed"].includes(job.status)) void monitorInstall(job.id);
  } catch {
    // Job recovery is a convenience; a transient Operations failure must not block the page.
  }
}

async function installLanguage() {
  const profile = selectedProvider.value;
  if (!profile) {
    error.value = i18n.t("language.provider_profile_required");
    return;
  }
  if (installCodeExists.value) {
    error.value = i18n.t("language.locale_already_installed");
    return;
  }
  if (modelTranslationRisk.value && !translationRiskAcknowledged.value) {
    error.value = i18n.t("language.model_translation_risk_ack_required");
    return;
  }
  installing.value = true;
  error.value = "";
  try {
    const model = String(profile.model || "").trim();
    if (!model)
      throw new Error(
        i18n.t("language.provider_model_required"),
      );
    const status = await systemApi.researcherProviderStatus({
      id: profile.id,
      type: profile.type,
      base_url: profile.base_url || undefined,
      api_key: profile.api_key || undefined,
    });
    if (!status.available)
      throw new Error(
        i18n.tf("language.provider_unavailable", {
            message:
              status.error || i18n.t("language.provider_unavailable_short", "provider unavailable"),
          }),
      );
    const created = await systemApi.installLanguage({
      code: install.value.code.trim(),
      name: install.value.name.trim() || localeDisplayName(install.value.code.trim()),
      flag: install.value.flag.trim() || regionFlagForLocale(install.value.code) || "🌐",
      resume_job_id: resumeJobId.value || undefined,
      provider: profile.type,
      model,
      base_url: profile.base_url || undefined,
      api_key: profile.api_key || undefined,
      generation: providerGeneration(profile),
      provider_profile_id: profile.id,
      max_concurrent_requests: profile.max_concurrent_requests || 1,
    });
    const wasResume = Boolean(resumeJobId.value);
    installOpen.value = false;
    installJob.value = created;
    runtime.registerExternalJob?.(created);
    runtime.notifyToast?.(
      i18n.t(
        wasResume ? "language.translation_resumed" : "language.translation_started_modern",
        wasResume
          ? "Translation resumed from the retained partial dictionary."
          : "Translation started. DerridAI is translating the English interface set before installing the locale.",
      ),
      { tone: "success" },
    );
    resumeJobId.value = "";
    void monitorInstall(created.id);
    install.value = { code: "", name: "", flag: "🌐" };
    installAutoName.value = "";
    installFlagTouched.value = false;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    installing.value = false;
  }
}

function requestManageProviders() {
  rememberConfirmationFocus();
  manageProvidersConfirm.value = true;
}
function confirmManageProviders() {
  confirmationReturnFocus = null;
  manageProvidersConfirm.value = false;
  installOpen.value = false;
  window.dispatchEvent(
    new CustomEvent("derridai:navigate-native", {
      detail: { path: "/providers", runtimeView: "providers" },
    }),
  );
}
function removeLanguage(item: LanguageInfo) {
  if (["en-US", "fr-CA"].includes(item.code)) return;
  rememberConfirmationFocus();
  pendingDelete.value = item;
}
async function confirmRemoveLanguage() {
  const item = pendingDelete.value;
  if (!item) return;
  try {
    await systemApi.deleteLanguage(item.code);
    pendingDelete.value = null;
    await refreshLanguages();
    window.dispatchEvent(
      new CustomEvent("derridai:languages-changed", {
        detail: { source: "language-delete", code: item.code },
      }),
    );
    await load(languages.value[0]?.code || "en-US");
    runtime.notifyToast?.(i18n.t("language.removed"), { tone: "success" });
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
function trapFocus(event: KeyboardEvent, root: HTMLElement | null) {
  if (event.key !== "Tab" || !root) return;
  const focusable = [
    ...root.querySelectorAll<HTMLElement>(
      'button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[href],[tabindex]:not([tabindex="-1"])',
    ),
  ].filter((el) => !el.hasAttribute("hidden"));
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

watch(selectedProviderId, () => {
  translationRiskAcknowledged.value = false;
});
watch(
  () => selectedProvider.value?.model,
  () => {
    translationRiskAcknowledged.value = false;
  },
);

watch(installOpen, async (open) => {
  if (open) {
    refreshProviderProfiles();
    await nextTick();
    installCodeInput.value?.focus();
  } else if (!manageProvidersConfirm.value) headerRef.value?.focusInstall?.();
});

watch(manageProvidersConfirm, async (open) => {
  if (open) await focusDialog(manageProvidersDialog.value);
  else if (installOpen.value) restoreConfirmationFocus();
});
watch(installCloseConfirm, async (open) => {
  if (open) await focusDialog(installCloseDialog.value);
  else if (installOpen.value) restoreConfirmationFocus();
});
watch(pendingLocaleCode, async (code) => {
  if (code) await focusDialog(unsavedDialog.value);
  else restoreConfirmationFocus();
});
watch(pendingDelete, async (item) => {
  if (item) await focusDialog(deleteDialog.value);
  else restoreConfirmationFocus();
});

watch(
  () => install.value.code,
  (code) => {
    const value = code.trim();
    if (!value) {
      if (install.value.name === installAutoName.value) install.value.name = "";
      installAutoName.value = "";
      if (!installFlagTouched.value) install.value.flag = "🌐";
      return;
    }
    const suggestedName = localeDisplayName(value);
    if (!install.value.name.trim() || install.value.name === installAutoName.value) {
      install.value.name = suggestedName;
      installAutoName.value = suggestedName;
    }
    if (!installFlagTouched.value) install.value.flag = regionFlagForLocale(value);
  },
);

onMounted(async () => {
  try {
    refreshProviderProfiles();
    const base = await systemApi.language("en-US");
    referenceDictionary.value = base.dictionary || {};
    await refreshLanguages();
    await load(selectedCode.value);
    await restoreLanguageTranslationJob();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
    loading.value = false;
  }
});
onUnmounted(() => {
  window.clearTimeout(installPollTimer);
  window.clearTimeout(policyPollTimer);
});
</script>

<template>
  <main class="vue-native-page languages-page language-studio">
    <LanguageWorkspaceHeader
      ref="headerRef"
      :language-count="languages.length"
      :key-count="Object.keys(referenceDictionary).length"
      :policy-pending-count="pendingPolicyCount"
      @install="openInstallDialog"
    />

    <div v-if="error" class="language-alert error" role="alert">
      <AppIcon name="warning" /><span>{{ error }}</span
      ><button type="button" :aria-label="i18n.t('ui.close')" @click="error = ''">
        ×
      </button>
    </div>
    <section v-if="pendingPolicyCount" class="language-policy-banner" role="status">
      <AppIcon name="warning" />
      <span>{{
        i18n.tf("language.content_policy_missing_banner", { count: pendingPolicyCount.toLocaleString(i18n.locale) })
      }}</span>
    </section>
    <section
      v-if="installJob && !['completed', 'failed', 'cancelled'].includes(installJob.status)"
      class="translation-progress-card"
      aria-live="polite"
    >
      <div class="translation-progress-icon"><span class="spinner"></span></div>
      <div>
        <b>{{ i18n.t("language.translating_install") }}</b
        ><span>{{
          installJob.stage_detail ||
          i18n.t("language.translation_in_progress")
        }}</span>
        <div class="translation-progress-track">
          <i :style="{ width: `${installProgress}%` }"></i>
        </div>
      </div>
      <div class="translation-progress-actions">
        <strong>{{ installProgress }}%</strong
        ><button type="button" class="btn tiny" @click="runtime.triggerOperations?.()">
          {{ i18n.t("language.track_operations") }}
        </button>
      </div>
    </section>
    <section v-if="resumableInstallJob" class="translation-recovery-card" aria-live="polite">
      <div class="translation-recovery-icon" aria-hidden="true"><AppIcon name="history" /></div>
      <div class="translation-recovery-copy">
        <b>{{ i18n.t("language.translation_incomplete_title") }}</b>
        <span>{{
          i18n.tf("language.translation_incomplete_help", {
              done: installPartialCount.toLocaleString(i18n.locale),
              failed: installFailureCount.toLocaleString(i18n.locale),
            })
        }}</span>
      </div>
      <div class="translation-recovery-actions">
        <button type="button" class="btn primary" @click="openResumeDialog">
          {{ i18n.t("language.resume_translation") }}
        </button>
        <button type="button" class="btn tiny" @click="runtime.triggerOperations?.()">
          {{ i18n.t("language.track_operations") }}
        </button>
      </div>
    </section>

    <section class="language-studio-grid">
      <aside
        class="language-locale-rail"
        :aria-label="i18n.t('language.installed')"
      >
        <div class="language-rail-head">
          <div>
            <p>{{ i18n.t("language.locale_library") }}</p>
            <h2>{{ i18n.t("language.installed") }}</h2>
          </div>
          <span>{{ languages.length }}</span>
        </div>
        <label class="language-search-field"
          ><span class="sr-only">{{ i18n.t("language.search_locales") }}</span
          ><AppIcon name="search" /><input
            v-model="localeQuery"
            type="search"
            :placeholder="i18n.t('language.search_locales')"
        /></label>
        <div class="language-locale-list">
          <button
            v-for="item in filteredLanguages"
            :key="item.code"
            type="button"
            class="language-locale-card"
            :class="{ active: item.code === selectedCode }"
            :aria-current="item.code === selectedCode ? 'page' : undefined"
            @click="requestLoad(item.code)"
          >
            <LanguageFlag
              :code="item.code"
              :symbol="flagFor(item.code, item.flag)"
              :label="item.name"
              size="large"
            />
            <span class="language-locale-copy"
              ><b>{{ item.name }}</b
              ><small>{{ item.code }}</small></span
            >
            <span v-if="!item.content_policy_ready" class="locale-kind policy-needed">{{
              i18n.t("language.content_policy_needed")
            }}</span>
            <span v-else-if="['en-US', 'fr-CA'].includes(item.code)" class="locale-kind">{{
              i18n.t("language.built_in")
            }}</span>
            <span v-else class="locale-kind custom">{{ i18n.t("language.custom") }}</span>
          </button>
          <p v-if="!filteredLanguages.length" class="language-empty-list">
            {{ i18n.t("language.no_locale_matches") }}
          </p>
        </div>
      </aside>

      <section class="language-editor-workspace" aria-live="polite">
        <div v-if="loading" class="language-loading">
          <span class="spinner"></span>{{ i18n.t("ui.loading_dictionary") }}
        </div>
        <template v-else-if="current">
          <header class="language-editor-hero">
            <div class="language-editor-identity">
              <LanguageFlag
                :code="current.code"
                :symbol="flagFor(current.code, current.flag)"
                :label="current.name"
                size="large"
              />
              <div>
                <p>
                  {{
                    isCanonical
                      ? i18n.t("language.canonical_source")
                      : i18n.t("language.translation_target")
                  }}
                </p>
                <h2>{{ current.name }}</h2>
                <span
                  >{{ current.code }} · {{ stats.total.toLocaleString(i18n.locale) }}
                  {{ i18n.t("language.interface_strings") }}</span
                >
              </div>
            </div>
            <div class="language-editor-metrics">
              <span
                ><b>{{ stats.coverage }}%</b>{{ i18n.t("language.coverage") }}</span
              >
              <span v-if="!isCanonical"
                ><b>{{ stats.matchesEnglish.toLocaleString(i18n.locale) }}</b
                >{{ i18n.t("language.matches_english") }}</span
              >
              <span
                ><b>{{ stats.missing.toLocaleString(i18n.locale) }}</b
                >{{ i18n.t("language.missing") }}</span
              >
            </div>
            <div class="language-editor-save">
              <span v-if="dirty" class="unsaved-dot">{{
                i18n.t("language.unsaved_changes")
              }}</span
              ><button class="btn primary" type="button" :disabled="saving || !dirty" @click="save">
                {{
                  saving
                    ? i18n.t("ui.saving")
                    : i18n.t("language.save_dictionary")
                }}
              </button>
            </div>
          </header>

          <section
            class="language-identity-card"
            :aria-label="i18n.t('language.locale_identity')"
          >
            <label class="language-meta-field"
              ><span>{{ i18n.t("language.name") }}</span
              ><input v-model="current.name" class="control" /><small>{{
                i18n.t("language.name_help")
              }}</small></label
            >
            <CountryFlagPicker
              v-model="current.flag"
              :locale-code="current.code"
              :label="i18n.t('language.locale_icon')"
              :help="
                i18n.t('language.flag_library_help')
              "
            />
            <div class="language-source-card">
              <span>{{ i18n.t("language.source_language") }}</span
              ><b>🇺🇸 {{ i18n.t("language.english_us") }}</b
              ><small>{{
                i18n.t("language.source_language_help")
              }}</small>
            </div>
            <button
              v-if="!['en-US', 'fr-CA'].includes(current.code)"
              type="button"
              class="language-remove-action"
              @click="removeLanguage(current)"
            >
              <AppIcon name="trash" />{{ i18n.t("language.remove_language") }}
            </button>
          </section>

          <section
            class="language-policy-card"
            :aria-label="i18n.t('language.content_policy_title')"
          >
            <div class="language-policy-copy">
              <p>{{ i18n.t("language.content_policy") }}</p>
              <b>{{
                policyReady
                  ? i18n.t("language.content_policy_ready")
                  : i18n.t("language.content_policy_missing")
              }}</b>
              <span>{{
                policyReady
                  ? i18n.tf("language.content_policy_count", {
                      count: (contentPolicy?.blocked_terms?.length || 0).toLocaleString(
                        i18n.locale,
                      ),
                    })
                  : i18n.t("language.content_policy_missing_help")
              }}</span>
              <span
                v-if="policyReady && contentPolicy?.generation_report"
                class="language-policy-report"
                >{{
                  i18n.tf("language.content_policy_report", {
                      attempts: contentPolicy.generation_report.attempts,
                      removed: contentPolicy.generation_report.removed_as_wrong_language,
                    })
                }}</span
              >
              <span
                v-if="policyReady && contentPolicy?.generation_report?.short_categories?.length"
                class="language-policy-gap"
                role="status"
                >{{
                  i18n.tf("language.content_policy_short", {
                      categories: contentPolicy.generation_report.short_categories
                        .map((id) =>
                          i18n.t(`language.policy_category.${id}`, id.replaceAll("_", " ")),
                        )
                        .join(", "),
                    })
                }}</span
              >
              <small>{{
                i18n.t("language.content_policy_help")
              }}</small>
              <details v-if="policyReady" class="language-policy-terms">
                <summary>
                  {{ i18n.t("language.content_policy_show_terms") }}
                </summary>
                <span>{{ i18n.t("language.content_policy_blocked") }}</span>
                <ul
                  tabindex="0"
                  :aria-label="i18n.t('language.content_policy_blocked')"
                >
                  <li v-for="term in contentPolicy?.blocked_terms || []" :key="term">
                    <code>{{ term }}</code>
                    <button
                      type="button"
                      class="language-row-remove"
                      :aria-label="`${i18n.t('language.content_policy_remove')}: ${term}`"
                      @click="removePolicyTerm(term)"
                    >
                      ×
                    </button>
                  </li>
                </ul>
                <form class="language-policy-add" @submit.prevent="addPolicyTerm">
                  <label
                    ><span class="sr-only">{{
                      i18n.t("language.content_policy_term")
                    }}</span
                    ><input
                      v-model="newPolicyTerm"
                      class="control"
                      :placeholder="
                        i18n.t('language.content_policy_add_placeholder')
                      "
                  /></label>
                  <button class="btn small" type="submit" :disabled="!newPolicyTerm.trim()">
                    {{ i18n.t("language.content_policy_add") }}
                  </button>
                  <button
                    class="btn small"
                    type="button"
                    :disabled="savingPolicy"
                    @click="saveContentPolicy"
                  >
                    {{
                      savingPolicy
                        ? i18n.t("ui.saving")
                        : i18n.t("language.content_policy_save")
                    }}
                  </button>
                </form>
                <small
                  v-if="contentPolicy?.contextual_terms?.length"
                  class="language-policy-contextual"
                  >{{ i18n.t("language.content_policy_contextual") }} ·
                  {{
                    i18n.t("language.content_policy_contextual_help")
                  }}</small
                >
              </details>
            </div>
            <div class="language-policy-actions">
              <ProviderProfileSelect
                v-model="selectedProviderId"
                :profiles="providerProfiles"
                :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''"
                :label="i18n.t('language.provider_profile')"
                :help="
                  i18n.t('language.content_policy_generate_help')
                "
                :empty-title="
                  i18n.t('language.no_provider_profiles')
                "
                :empty-help="
                  i18n.t('language.no_provider_profiles_help')
                "
                :manage-label="i18n.t('language.manage_providers')"
                :model-not-set-label="i18n.t('language.model_not_set')"
                :default-label="i18n.t('ui.default')"
                :concurrent-label="
                  i18n.t('language.concurrent_requests')
                "
                :context-label="i18n.t('providers.context_tokens')"
                @manage="requestManageProviders"
              />
              <button
                type="button"
                class="btn primary"
                :disabled="policyBusy || !selectedProvider"
                @click="generateContentPolicy"
              >
                {{
                  policyBusy
                    ? i18n.t("language.content_policy_generating")
                    : policyReady
                      ? i18n.t("language.content_policy_regenerate")
                      : i18n.t("language.content_policy_generate")
                }}
              </button>
            </div>
          </section>

          <section
            v-if="!isCanonical && trackedFallbackCount"
            class="language-fallback-report"
            role="status"
          >
            <div class="language-fallback-report-main">
              <AppIcon name="warning" />
              <div>
                <b>{{
                  i18n.tf("language.tracked_fallbacks_title", { count: trackedFallbackCount.toLocaleString(i18n.locale) })
                }}</b
                ><span>{{
                  i18n.t("language.tracked_fallbacks_help")
                }}</span>
              </div>
            </div>
            <div class="language-fallback-report-actions">
              <button
                type="button"
                class="btn small"
                @click="
                  keyQuery = '';
                  statusFilter = 'review';
                "
              >
                {{ i18n.t("language.review_fallbacks") }}
              </button>
              <details v-if="trackedFallbackFailures.length">
                <summary>{{ i18n.t("language.failure_details") }}</summary>
                <ul>
                  <li v-for="item in trackedFallbackFailures" :key="String(item.key)">
                    <code>{{ item.key }}</code
                    ><span>{{ item.reason }}</span>
                  </li>
                </ul>
              </details>
            </div>
          </section>

          <section class="language-translation-toolbar">
            <label class="language-key-search"
              ><span class="sr-only">{{
                i18n.t("language.search_strings")
              }}</span
              ><AppIcon name="search" /><input
                v-model="keyQuery"
                type="search"
                :placeholder="
                  i18n.t('language.search_strings')
                "
            /></label>
            <label class="language-category-select"
              ><span class="sr-only">{{ i18n.t("language.category") }}</span
              ><select v-model="activeCategory" class="control">
                <option v-for="category in categories" :key="category.id" :value="category.id">
                  {{
                    category.id === "all"
                      ? i18n.t("language.all_categories")
                      : category.id
                  }}
                  · {{ category.count }}
                </option>
              </select></label
            >
            <div class="language-transfer-actions">
              <button type="button" class="btn small" @click="exportDictionary">
                {{ i18n.t("language.export_dictionary") }}
              </button>
              <button type="button" class="btn small" @click="openImport">
                {{ i18n.t("language.import_dictionary") }}
              </button>
              <label class="sr-only" for="language-dictionary-import">
                {{ i18n.t("language.import_dictionary") }}
              </label>
              <input
                id="language-dictionary-import"
                ref="importInput"
                class="sr-only"
                type="file"
                accept="application/json,.json"
                @change="importDictionary"
              />
            </div>
            <div
              class="language-filter-tabs"
              :aria-label="i18n.t('language.translation_filters')"
            >
              <button
                type="button"
                :aria-pressed="statusFilter === 'all'"
                @click="statusFilter = 'all'"
              >
                {{ i18n.t("ui.all") }} <span>{{ rows.length }}</span>
              </button>
              <button
                type="button"
                :aria-pressed="statusFilter === 'localized'"
                @click="statusFilter = 'localized'"
              >
                {{
                  isCanonical
                    ? i18n.t("language.filled")
                    : i18n.t("language.localized")
                }}
                <span>{{ stats.localized }}</span>
              </button>
              <button
                v-if="!isCanonical && trackedFallbackCount"
                type="button"
                :aria-pressed="statusFilter === 'review'"
                @click="statusFilter = 'review'"
              >
                {{ i18n.t("language.needs_review") }}
                <span>{{ trackedFallbackCount }}</span>
              </button>
              <button
                v-if="!isCanonical"
                type="button"
                :aria-pressed="statusFilter === 'english'"
                @click="statusFilter = 'english'"
              >
                {{ i18n.t("language.matches_english") }}
                <span>{{ stats.matchesEnglish }}</span>
              </button>
              <button
                type="button"
                :aria-pressed="statusFilter === 'missing'"
                @click="statusFilter = 'missing'"
              >
                {{ i18n.t("language.missing") }} <span>{{ stats.missing }}</span>
              </button>
            </div>
          </section>

          <section
            class="language-string-editor"
            :aria-label="i18n.t('language.translation_editor')"
          >
            <div class="language-string-head" :class="{ canonical: isCanonical }">
              <span>{{ i18n.t("language.key_context") }}</span
              ><span v-if="!isCanonical">{{
                i18n.t("language.english_source")
              }}</span
              ><span>{{
                isCanonical
                  ? i18n.t("language.english_value")
                  : i18n.t("language.translation")
              }}</span>
            </div>
            <article
              v-for="[key, value] in filteredRows"
              :key="key"
              class="language-string-row"
              :class="{
                canonical: isCanonical,
                fallback:
                  !isCanonical && value.trim() === sourceValue(key).trim() && Boolean(value.trim()),
                missing: !value.trim(),
              }"
            >
              <div class="language-key-cell">
                <code>{{ key }}</code
                ><small>{{ describeKey(key) }}</small>
              </div>
              <div v-if="!isCanonical" class="language-source-cell" :lang="'en-US'">
                <span class="mobile-column-label">{{
                  i18n.t("language.english_source")
                }}</span
                >{{ sourceValue(key) }}
              </div>
              <label class="language-target-cell"
                ><span class="sr-only">{{
                  `${i18n.t("language.translation")}: ${key}`
                }}</span
                ><textarea
                  class="control"
                  rows="2"
                  :lang="current.code"
                  :dir="i18n.directionForLocale(current.code)"
                  :value="value"
                  @input="updateValue(key, ($event.target as HTMLTextAreaElement).value)"
                ></textarea
                ><small
                  v-if="
                    !isCanonical &&
                    value.trim() === sourceValue(key).trim() &&
                    Boolean(value.trim())
                  "
                  >{{
                    i18n.t("language.english_fallback_note")
                  }}</small
                ></label
              >
              <button
                v-if="isCanonical"
                class="language-row-remove"
                type="button"
                :title="i18n.t('language.remove_key')"
                :aria-label="`${i18n.t('language.remove_key')}: ${key}`"
                @click="removeDictionaryEntry(key)"
              >
                ×
              </button>
            </article>
            <div v-if="!filteredRows.length" class="language-no-results">
              <AppIcon name="search" /><b>{{
                i18n.t("language.no_string_matches")
              }}</b
              ><button
                type="button"
                class="btn small"
                @click="
                  keyQuery = '';
                  statusFilter = 'all';
                "
              >
                {{ i18n.t("research.clear_filters") }}
              </button>
            </div>
          </section>

          <details v-if="isCanonical" class="language-advanced-key">
            <summary>{{ i18n.t("language.add_source_key") }}</summary>
            <form @submit.prevent="addDictionaryEntry">
              <label
                ><span>{{ i18n.t("language.dictionary_key") }}</span
                ><input v-model="newKey" class="control" placeholder="ui.new_key" /></label
              ><label
                ><span>{{ i18n.t("language.english_value") }}</span
                ><input v-model="newValue" class="control" /></label
              ><button class="btn" :disabled="!newKey.trim()">
                {{ i18n.t("language.add_key") }}
              </button>
            </form>
            <p>
              {{
                i18n.t("language.add_source_key_help")
              }}
            </p>
          </details>
        </template>
      </section>
    </section>

    <Teleport to="body">
      <div
        v-if="installOpen"
        class="workflow-overlay language-modal-overlay"
        role="presentation"
        @mousedown.self="requestCloseInstall"
        @keydown.esc.stop.prevent="requestCloseInstall"
        @keydown="trapFocus($event, installDialog)"
      >
        <section
          ref="installDialog"
          class="workflow-dialog language-install-dialog modern-language-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="language-install-title"
          aria-describedby="language-install-description"
        >
          <header class="workflow-dialog-header">
            <div class="workflow-heading">
              <span class="workflow-icon" aria-hidden="true">🌐</span>
              <div>
                <p>{{ i18n.t("language.install_kicker") }}</p>
                <h2 id="language-install-title">
                  {{ i18n.t("language.install_dictionary_modern") }}
                </h2>
                <span id="language-install-description">{{
                  i18n.t("language.install_help_modern")
                }}</span>
              </div>
            </div>
            <button
              class="icon-btn workflow-close"
              type="button"
              :title="i18n.t('ui.close')"
              :aria-label="i18n.t('ui.close')"
              @click="requestCloseInstall"
            >
              ×
            </button>
          </header>
          <form class="workflow-form language-install-form" @submit.prevent="installLanguage">
            <section class="language-install-source">
              <span class="language-install-source-icon">🇺🇸</span>
              <div>
                <b>{{ i18n.t("language.english_source_set") }}</b
                ><small>{{
                  i18n.tf("language.source_key_count", { count: Object.keys(referenceDictionary).length.toLocaleString(i18n.locale) })
                }}</small>
              </div>
              <span class="source-lock"
                ><AppIcon name="lock" />{{ i18n.t("language.canonical") }}</span
              >
            </section>
            <section class="workflow-section">
              <div class="workflow-section-copy">
                <b>{{ i18n.t("language.identity_section") }}</b
                ><span>{{
                  i18n.t("language.identity_section_help_modern")
                }}</span>
              </div>
              <div class="workflow-fields workflow-identity-fields">
                <label class="workflow-field"
                  ><span>{{ i18n.t("language.locale_code") }}</span
                  ><input
                    ref="installCodeInput"
                    v-model="install.code"
                    class="control"
                    required
                    autocomplete="off"
                    spellcheck="false"
                    placeholder="de-DE"
                    aria-describedby="locale-code-help"
                    :disabled="Boolean(resumeJobId)"
                  /><small id="locale-code-help">{{
                    i18n.t("language.locale_code_help_modern")
                  }}</small></label
                ><label class="workflow-field"
                  ><span>{{ i18n.t("language.name") }}</span
                  ><input
                    v-model="install.name"
                    class="control"
                    autocomplete="off"
                    placeholder="Deutsch (Deutschland)"
                  /><small>{{
                    i18n.t("language.name_help")
                  }}</small></label
                ><CountryFlagPicker
                  :model-value="install.flag"
                  :locale-code="install.code"
                  :label="i18n.t('language.locale_icon')"
                  :help="
                    i18n.t('language.flag_library_help')
                  "
                  @update:model-value="setInstallFlag"
                />
              </div>
            </section>
            <section v-if="resumeJobId" class="language-resume-notice" role="status">
              <AppIcon name="history" /><span
                ><b>{{ i18n.t("language.resuming_partial") }}</b
                ><small>{{
                  i18n.tf("language.resuming_partial_help", { count: installPartialCount.toLocaleString(i18n.locale) })
                }}</small></span
              >
            </section>
            <section class="workflow-section">
              <div class="workflow-section-copy">
                <b>{{ i18n.t("language.translation_section") }}</b
                ><span>{{
                  i18n.t("language.translation_section_help_modern")
                }}</span>
              </div>
              <div class="workflow-provider-area">
                <ProviderProfileSelect
                  v-model="selectedProviderId"
                  :profiles="providerProfiles"
                  :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''"
                  :label="i18n.t('language.provider_profile')"
                  :help="
                    i18n.t('language.provider_profile_help')
                  "
                  :empty-title="
                    i18n.t('language.no_provider_profiles')
                  "
                  :empty-help="
                    i18n.t('language.no_provider_profiles_help')
                  "
                  :manage-label="i18n.t('language.manage_providers')"
                  :model-not-set-label="i18n.t('language.model_not_set')"
                  :default-label="i18n.t('ui.default')"
                  :concurrent-label="
                    i18n.t('language.concurrent_requests')
                  "
                  :context-label="i18n.t('providers.context_tokens')"
                  @manage="requestManageProviders"
                />
                <aside
                  v-if="modelTranslationRisk"
                  class="language-model-warning"
                  role="note"
                  aria-live="polite"
                >
                  <AppIcon name="warning" />
                  <div>
                    <b>{{
                      i18n.t("language.model_translation_risk_title")
                    }}</b>
                    <p>{{ modelTranslationRiskMessage }}</p>
                    <label
                      ><input v-model="translationRiskAcknowledged" type="checkbox" /><span>{{
                        i18n.t("language.model_translation_risk_ack")
                      }}</span></label
                    >
                  </div>
                </aside>
              </div>
            </section>
            <section class="language-install-assurance">
              <div>
                <AppIcon name="check" /><span
                  ><b>{{ i18n.t("language.atomic_install") }}</b
                  ><small>{{
                    i18n.t("language.atomic_install_help")
                  }}</small></span
                >
              </div>
              <div>
                <AppIcon name="history" /><span
                  ><b>{{ i18n.t("language.background_translation") }}</b
                  ><small>{{
                    i18n.t("language.background_translation_help_modern")
                  }}</small></span
                >
              </div>
            </section>
            <footer class="workflow-actions">
              <button type="button" class="btn" @click="requestCloseInstall">
                {{ i18n.t("ui.cancel") }}</button
              ><button
                class="btn primary"
                :disabled="
                  installing ||
                  !install.code.trim() ||
                  !selectedProvider ||
                  installCodeExists ||
                  Boolean(modelTranslationRisk && !translationRiskAcknowledged)
                "
              >
                {{
                  installing
                    ? i18n.t("language.checking_provider")
                    : resumeJobId
                      ? i18n.t("language.resume_translation")
                      : i18n.t("language.translate_install")
                }}
              </button>
            </footer>
          </form>
        </section>
      </div>

      <div
        v-if="installCloseConfirm"
        class="native-confirm-backdrop"
        role="presentation"
        @click.self="installCloseConfirm = false"
        @keydown.esc.stop.prevent="installCloseConfirm = false"
        @keydown="trapFocus($event, installCloseDialog)"
      >
        <section
          ref="installCloseDialog"
          class="card native-confirm-card language-confirm-card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="discard-install-title"
        >
          <div class="cardhead">
            <div>
              <b id="discard-install-title">{{
                i18n.t("language.discard_install_title")
              }}</b>
              <div class="note">
                {{
                  i18n.t("language.discard_install_help")
                }}
              </div>
            </div>
          </div>
          <div class="actions">
            <button class="btn" type="button" @click="installCloseConfirm = false">
              {{ i18n.t("language.keep_editing") }}</button
            ><button class="btn danger" type="button" @click="discardInstallDraft">
              {{ i18n.t("language.discard_install") }}
            </button>
          </div>
        </section>
      </div>

      <div
        v-if="manageProvidersConfirm"
        class="native-confirm-backdrop"
        role="presentation"
        @click.self="manageProvidersConfirm = false"
        @keydown.esc.stop.prevent="manageProvidersConfirm = false"
        @keydown="trapFocus($event, manageProvidersDialog)"
      >
        <section
          ref="manageProvidersDialog"
          class="card native-confirm-card language-confirm-card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="manage-provider-warning"
        >
          <div class="cardhead">
            <div>
              <b id="manage-provider-warning">{{
                i18n.t("language.leave_install_title")
              }}</b>
              <div class="note">
                {{
                  i18n.t("language.leave_install_help")
                }}
              </div>
            </div>
          </div>
          <div class="actions">
            <button class="btn" type="button" @click="manageProvidersConfirm = false">
              {{ i18n.t("ui.stay") }}</button
            ><button class="btn primary" type="button" @click="confirmManageProviders">
              {{ i18n.t("language.leave_manage_providers") }}
            </button>
          </div>
        </section>
      </div>

      <div
        v-if="pendingLocaleCode"
        class="native-confirm-backdrop"
        role="presentation"
        @click.self="pendingLocaleCode = ''"
        @keydown.esc.stop.prevent="pendingLocaleCode = ''"
        @keydown="trapFocus($event, unsavedDialog)"
      >
        <section
          ref="unsavedDialog"
          class="card native-confirm-card language-confirm-card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="unsaved-language-title"
        >
          <div class="cardhead">
            <div>
              <b id="unsaved-language-title">{{
                i18n.t("language.unsaved_title")
              }}</b>
              <div class="note">
                {{
                  i18n.t("language.unsaved_help")
                }}
              </div>
            </div>
          </div>
          <div class="actions">
            <button class="btn" type="button" @click="pendingLocaleCode = ''">
              {{ i18n.t("ui.cancel") }}</button
            ><button class="btn" type="button" @click="discardAndSwitch">
              {{ i18n.t("language.discard_switch") }}</button
            ><button class="btn primary" type="button" @click="saveAndSwitch">
              {{ i18n.t("language.save_switch") }}
            </button>
          </div>
        </section>
      </div>

      <div
        v-if="pendingDelete"
        class="native-confirm-backdrop"
        role="presentation"
        @click.self="pendingDelete = null"
        @keydown.esc.stop.prevent="pendingDelete = null"
        @keydown="trapFocus($event, deleteDialog)"
      >
        <section
          ref="deleteDialog"
          class="card native-confirm-card language-confirm-card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="remove-language-title"
        >
          <div class="cardhead">
            <div>
              <b id="remove-language-title">{{
                i18n.t("language.remove_confirm")
              }}</b>
              <div class="note">{{ pendingDelete.name }} · {{ pendingDelete.code }}</div>
            </div>
          </div>
          <p>
            {{
              i18n.t("language.remove_help")
            }}
          </p>
          <div class="actions">
            <button class="btn" type="button" @click="pendingDelete = null">
              {{ i18n.t("ui.cancel") }}</button
            ><button class="btn danger" type="button" @click="confirmRemoveLanguage">
              {{ i18n.t("language.remove_language") }}
            </button>
          </div>
        </section>
      </div>
    </Teleport>
  </main>
</template>

<style scoped>
.language-policy-banner {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 11px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.language-policy-banner :deep(svg) {
  width: 18px;
  height: 18px;
  color: var(--tone-warn-fg);
}
.language-policy-card {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 14px;
  align-items: start;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.language-policy-copy {
  display: grid;
  gap: 4px;
}
.language-policy-copy p {
  margin: 0;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.language-policy-copy b {
  font-size: 0.9375rem;
  color: var(--text);
}
.language-policy-copy span,
.language-policy-copy small {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--muted);
}
.language-policy-actions {
  display: grid;
  gap: 10px;
}
.language-policy-terms {
  display: grid;
  gap: 8px;
  margin-top: 6px;
}
.language-policy-terms > span {
  font-size: 0.8125rem;
  font-weight: 750;
  color: var(--text-2);
}
.language-policy-terms ul {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 11rem;
  overflow: auto;
}
.language-policy-terms li {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
}
.language-policy-terms code {
  font-size: 0.8125rem;
  color: var(--text-2);
}
.language-policy-add {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.language-policy-add label {
  flex: 1;
  min-width: 180px;
}
.language-policy-gap {
  color: var(--tone-warn-fg) !important;
  font-weight: 650;
}
.language-policy-contextual {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--tone-warn-fg);
}
.language-studio {
  display: grid;
  gap: var(--page-gap);
}
.language-alert {
  min-height: 46px;
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) 34px;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid var(--tone-danger-edge);
  border-radius: 11px;
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: 0.78125rem;
}
.language-alert :deep(svg) {
  width: 18px;
  height: 18px;
}
.language-alert button {
  min-width: 34px;
  min-height: 34px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  font-size: 1.25rem;
  cursor: pointer;
}
.translation-progress-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.translation-progress-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--card);
}
.translation-progress-card > div:nth-child(2) {
  display: grid;
  gap: 3px;
}
.translation-progress-card b {
  font-size: 0.78125rem;
  color: var(--text);
}
.translation-progress-card span {
  font-size: 0.8125rem;
  color: var(--muted);
}
.translation-progress-actions {
  display: grid;
  justify-items: end;
  gap: 5px;
}
.translation-progress-actions > strong {
  font-size: 0.8125rem;
  color: var(--accent-fg);
  font-variant-numeric: tabular-nums;
}
.translation-progress-track {
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--soft);
  margin-top: 3px;
}
.translation-progress-track i {
  display: block;
  height: 100%;
  background: var(--ui-accent, #3c8d62);
  transition: width 0.25s ease;
}
.translation-recovery-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 12px;
  background: var(--tone-warn-bg);
}
.translation-recovery-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--card);
  color: var(--tone-warn-fg);
}
.translation-recovery-icon :deep(svg) {
  width: 18px;
  height: 18px;
}
.translation-recovery-copy {
  display: grid;
  gap: 3px;
}
.translation-recovery-copy b {
  font-size: 0.78125rem;
  color: var(--tone-warn-fg);
}
.translation-recovery-copy span {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--tone-warn-fg);
}
.translation-recovery-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
  flex-wrap: wrap;
}
.language-resume-notice {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 9px;
  align-items: start;
  margin: 14px 20px 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
  color: var(--text-2);
}
.language-resume-notice :deep(svg) {
  width: 17px;
  height: 17px;
  margin-top: 1px;
}
.language-resume-notice span {
  display: grid;
  gap: 2px;
}
.language-resume-notice b {
  font-size: 0.8125rem;
}
.language-resume-notice small {
  font-size: 0.8125rem;
  line-height: 1.4;
  color: var(--text-2);
}
.language-model-warning {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 9px;
  align-items: start;
  margin-top: 10px;
  padding: 11px 12px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 10px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.language-model-warning > :deep(svg) {
  width: 17px;
  height: 17px;
  margin-top: 2px;
}
.language-model-warning > div {
  display: grid;
  gap: 5px;
}
.language-model-warning b {
  font-size: 0.8125rem;
}
.language-model-warning p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--tone-warn-fg);
}
.language-model-warning label {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 0.8125rem;
  font-weight: 700;
  line-height: 1.35;
  cursor: pointer;
}
.language-model-warning input {
  width: 16px;
  height: 16px;
  margin: 0;
  flex: 0 0 auto;
}
.language-studio-grid {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}
.language-locale-rail {
  position: sticky;
  top: 116px;
  max-height: calc(100vh - 140px);
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
  box-shadow: 0 6px 22px rgba(15, 23, 42, 0.04);
}
.language-rail-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}
.language-rail-head p {
  margin: 0;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.language-rail-head h2 {
  margin: 2px 0 0;
  font-size: 1rem;
  color: var(--text);
}
.language-rail-head > span {
  min-width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: var(--soft);
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
}
.language-search-field,
.language-key-search {
  min-height: 40px;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  padding: 0 10px;
}
.language-search-field :deep(svg),
.language-key-search :deep(svg) {
  width: 15px;
  height: 15px;
  color: var(--muted);
}
.language-search-field input,
.language-key-search input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-2);
  font: inherit;
  font-size: 0.8125rem;
}
.language-locale-list {
  min-height: 0;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 5px;
  padding-inline-end: 2px;
}
.language-locale-card {
  width: 100%;
  min-height: 59px;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  border: 1px solid transparent;
  border-radius: 11px;
  background: transparent;
  padding: 7px;
  text-align: start;
  color: var(--text-2);
  cursor: pointer;
}
.language-locale-card:hover {
  background: var(--card);
}
.language-locale-card.active {
  border-color: var(--line);
  background: var(--ui-accent-soft, #eef7f1);
  box-shadow: inset 3px 0 0 var(--ui-accent, #3c8d62);
}
.language-locale-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.language-locale-copy b {
  font-size: 0.8125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.language-locale-copy small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.locale-kind {
  padding: 4px 6px;
  border-radius: 999px;
  background: var(--soft);
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.locale-kind.custom {
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.locale-kind.policy-needed {
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.language-empty-list {
  padding: 24px 10px;
  text-align: center;
  color: var(--muted);
  font-size: 0.8125rem;
}
.language-editor-workspace {
  min-width: 0;
  display: grid;
  gap: 12px;
}
.language-loading {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
  color: var(--muted);
  font-size: 0.8125rem;
}
.language-editor-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 18px;
  align-items: center;
  padding: 15px 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.language-editor-identity {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}
.language-editor-identity > div {
  min-width: 0;
}
.language-editor-identity p {
  margin: 0;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.language-editor-identity h2 {
  margin: 1px 0;
  font:
    600 22px/1.15 Georgia,
    "Times New Roman",
    serif;
  color: var(--text);
}
.language-editor-identity span {
  font-size: 0.8125rem;
  color: var(--muted);
}
.language-editor-metrics {
  display: flex;
  gap: 7px;
}
.language-editor-metrics span {
  min-width: 84px;
  display: grid;
  gap: 1px;
  padding: 7px 9px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  color: var(--muted);
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.language-editor-metrics b {
  font-size: 0.875rem;
  color: var(--text-2);
  letter-spacing: 0;
}
.language-editor-save {
  display: grid;
  justify-items: end;
  gap: 5px;
}
.unsaved-dot {
  font-size: 0.8125rem;
  color: var(--tone-warn-fg);
}
.language-identity-card {
  display: grid;
  grid-template-columns: minmax(180px, 0.9fr) minmax(250px, 1.1fr) minmax(220px, 0.85fr) auto;
  gap: 12px;
  align-items: start;
  padding: 13px 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.language-meta-field {
  display: grid;
  gap: 7px;
}
.language-meta-field > span,
.language-source-card > span {
  font-size: 0.8125rem;
  font-weight: 750;
  color: var(--text-2);
}
.language-meta-field small,
.language-source-card small {
  font-size: 0.8125rem;
  line-height: 1.35;
  color: var(--muted);
}
.language-source-card {
  min-height: 73px;
  display: grid;
  align-content: start;
  gap: 5px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.language-source-card b {
  font-size: 0.8125rem;
  color: var(--text-2);
}
.language-remove-action {
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  padding: 0 10px;
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
}
.language-remove-action :deep(svg) {
  width: 14px;
  height: 14px;
}
.language-fallback-report {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  padding: 12px 14px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 12px;
  background: var(--tone-warn-bg);
}
.language-fallback-report-main {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}
.language-fallback-report-main :deep(svg) {
  width: 17px;
  height: 17px;
  margin-top: 1px;
  color: var(--tone-warn-fg);
}
.language-fallback-report-main > div {
  display: grid;
  gap: 3px;
}
.language-fallback-report-main b {
  font-size: 0.8125rem;
  color: var(--tone-warn-fg);
}
.language-fallback-report-main span {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--tone-warn-fg);
}
.language-fallback-report-actions {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.language-fallback-report details {
  min-width: 180px;
}
.language-fallback-report summary {
  min-height: 34px;
  display: flex;
  align-items: center;
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
  font-weight: 750;
  cursor: pointer;
}
.language-fallback-report ul {
  max-height: 220px;
  margin: 4px 0 0;
  padding: 7px 9px;
  overflow: auto;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 8px;
  background: var(--card);
  list-style: none;
}
.language-fallback-report li {
  display: grid;
  gap: 2px;
  padding: 5px 0;
  border-top: 1px solid var(--line);
}
.language-fallback-report li:first-child {
  border-top: 0;
}
.language-fallback-report code {
  font-size: 0.8125rem;
  color: var(--text-2);
  overflow-wrap: anywhere;
}
.language-fallback-report li span {
  font-size: 0.8125rem;
  color: var(--tone-warn-fg);
}
.language-translation-toolbar {
  position: sticky;
  top: 115px;
  z-index: 12;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 11px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: color-mix(in srgb, var(--card) 96%, transparent);
  backdrop-filter: blur(12px);
  box-shadow: 0 5px 18px rgba(15, 23, 42, 0.05);
}
.language-key-search {
  flex: 1;
  max-width: 520px;
}
.language-filter-tabs {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}
.language-filter-tabs button {
  min-height: 34px;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  padding: 0 9px;
  color: var(--text-2);
  font-size: 0.8125rem;
  cursor: pointer;
}
.language-filter-tabs button[aria-pressed="true"] {
  border-color: var(--line);
  background: var(--ui-accent-soft, #eef7f1);
  color: var(--tone-ok-fg);
}
.language-filter-tabs button span {
  padding: 2px 5px;
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.8125rem;
}
.language-string-editor {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.language-string-head,
.language-string-row {
  display: grid;
  grid-template-columns: minmax(160px, 0.72fr) minmax(220px, 1fr) minmax(280px, 1.3fr);
  gap: 0;
}
.language-string-head.canonical,
.language-string-row.canonical {
  grid-template-columns: minmax(190px, 0.7fr) minmax(320px, 1.5fr) 40px;
}
.language-string-head {
  position: static;
  z-index: auto;
  border-bottom: 1px solid var(--line);
  background: var(--card);
}
.language-string-head span {
  padding: 9px 11px;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.language-string-row {
  border-bottom: 1px solid var(--line);
}
.language-string-row:last-of-type {
  border-bottom: 0;
}
.language-string-row.fallback {
  background: var(--card);
}
.language-string-row.missing {
  background: var(--card);
}
.language-key-cell,
.language-source-cell,
.language-target-cell {
  min-width: 0;
  padding: 10px 11px;
  border-inline-end: 1px solid var(--line);
}
.language-key-cell {
  display: grid;
  align-content: start;
  gap: 5px;
}
.language-key-cell code {
  font-size: 0.8125rem;
  color: var(--text-2);
  overflow-wrap: anywhere;
}
.language-key-cell small {
  font-size: 0.8125rem;
  line-height: 1.35;
  color: var(--muted);
}
.language-source-cell {
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--text-2);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.mobile-column-label {
  display: none;
}
.language-target-cell {
  display: grid;
  gap: 4px;
}
.language-target-cell textarea {
  width: 100%;
  min-height: 48px;
  resize: vertical;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.language-target-cell small {
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.language-row-remove {
  align-self: start;
  justify-self: center;
  min-width: 28px;
  min-height: 28px;
  margin-top: 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  color: var(--tone-danger-fg);
  font-size: 1.0625rem;
  cursor: pointer;
}
.language-no-results {
  display: grid;
  justify-items: center;
  gap: 7px;
  padding: 38px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.language-no-results :deep(svg) {
  width: 22px;
  height: 22px;
}
.language-advanced-key {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
}
.language-advanced-key summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 750;
  color: var(--text-2);
}
.language-advanced-key form {
  display: grid;
  grid-template-columns: minmax(170px, 0.7fr) minmax(240px, 1.3fr) auto;
  gap: 9px;
  align-items: end;
  margin-top: 11px;
}
.language-advanced-key label {
  display: grid;
  gap: 5px;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--text-2);
}
.language-advanced-key p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.modern-language-dialog {
  width: min(980px, calc(100vw - 32px));
}
.language-install-form {
  display: grid;
}
.language-install-source {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  margin: 16px 20px 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--card);
}
.language-install-source-icon {
  font-size: 1.5625rem;
}
.language-install-source > div {
  display: grid;
  gap: 2px;
}
.language-install-source b {
  font-size: 0.8125rem;
  color: var(--text-2);
}
.language-install-source small {
  font-size: 0.8125rem;
  color: var(--muted);
}
.source-lock {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 750;
}
.source-lock :deep(svg) {
  width: 13px;
  height: 13px;
}
.language-install-assurance {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 14px 20px;
}
.language-install-assurance > div {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
}
.language-install-assurance :deep(svg) {
  width: 17px;
  height: 17px;
  color: var(--accent-fg);
}
.language-install-assurance span {
  display: grid;
  gap: 2px;
}
.language-install-assurance b {
  font-size: 0.8125rem;
  color: var(--text-2);
}
.language-install-assurance small {
  font-size: 0.8125rem;
  line-height: 1.4;
  color: var(--muted);
}
.language-confirm-card {
  max-width: 520px;
}
.language-confirm-card .actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}
.language-category-select {
  min-width: 170px;
}
.language-category-select select {
  width: 100%;
  min-height: 40px;
}
.language-transfer-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.language-policy-terms > summary {
  cursor: pointer;
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 750;
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
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
summary:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 48%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 1200px) {
  .language-studio-grid {
    grid-template-columns: 235px minmax(0, 1fr);
  }
  .language-policy-card {
    grid-template-columns: 1fr;
  }
  .language-identity-card {
    grid-template-columns: 1fr 1fr;
  }
  .language-source-card {
    grid-column: 1/-1;
  }
  .language-editor-hero {
    grid-template-columns: 1fr auto;
  }
  .language-editor-metrics {
    grid-row: 2;
    grid-column: 1/-1;
  }
  .language-editor-save {
    grid-column: 2;
    grid-row: 1;
  }
  .language-string-head,
  .language-string-row {
    grid-template-columns: minmax(145px, 0.6fr) minmax(190px, 0.9fr) minmax(250px, 1.2fr);
  }
}
@media (max-width: 900px) {
  .language-fallback-report {
    grid-template-columns: 1fr;
  }
  .language-fallback-report-actions {
    justify-content: flex-start;
  }
  .translation-recovery-card {
    grid-template-columns: 38px minmax(0, 1fr);
  }
  .translation-recovery-actions {
    grid-column: 1/-1;
    justify-content: flex-start;
  }
  .language-studio-grid {
    grid-template-columns: 1fr;
  }
  .language-locale-rail {
    position: static;
    max-height: none;
  }
  .language-locale-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    max-height: 260px;
  }
  .language-translation-toolbar {
    top: 112px;
    align-items: stretch;
    flex-direction: column;
  }
  .language-key-search {
    max-width: none;
  }
  .language-string-head {
    display: none;
  }
  .language-string-row,
  .language-string-row.canonical {
    grid-template-columns: 1fr;
  }
  .language-key-cell,
  .language-source-cell,
  .language-target-cell {
    border-inline-end: 0;
    border-bottom: 1px solid var(--line);
  }
  .mobile-column-label {
    display: block !important;
    margin-bottom: 5px;
    color: var(--muted);
    font-size: 0.8125rem;
    font-weight: 800;
    text-transform: uppercase;
  }
  .language-row-remove {
    justify-self: end;
    margin: 0 10px 9px;
  }
  .language-advanced-key form {
    grid-template-columns: 1fr;
  }
  .language-install-assurance {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 560px) {
  .language-locale-list {
    grid-template-columns: 1fr;
  }
  .language-editor-hero {
    grid-template-columns: 1fr;
  }
  .language-editor-save {
    grid-column: 1;
    grid-row: auto;
    justify-items: stretch;
  }
  .language-editor-metrics {
    grid-column: 1;
    grid-row: auto;
    overflow: auto;
  }
  .language-identity-card {
    grid-template-columns: 1fr;
  }
  .language-filter-tabs {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .language-filter-tabs button {
    justify-content: center;
  }
  .language-install-source {
    grid-template-columns: 34px 1fr;
  }
  .source-lock {
    grid-column: 1/-1;
  }
  .language-install-assurance {
    padding-inline: 14px;
  }
}
.native-confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10020;
  background: rgba(12, 18, 14, 0.42);
  display: grid;
  place-items: center;
  padding: 20px;
}
.workflow-overlay {
  position: fixed;
  inset: 0;
  z-index: 480;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.46);
  backdrop-filter: blur(4px);
}
@media (max-width: 780px) {
  .workflow-overlay {
    padding: 10px;
  }
}
</style>
