<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { systemApi, type LanguageDictionary, type LanguageInfo, type ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";
import * as runtime from "../legacy/runtime.js";
import LanguageFlag from "../components/LanguageFlag.vue";
import ProviderProfileSelect from "../components/ProviderProfileSelect.vue";

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
const installTrigger = ref<HTMLButtonElement | null>(null);
const installCodeInput = ref<HTMLInputElement | null>(null);
const pendingDelete = ref<LanguageInfo | null>(null);
const install = ref({ code: "", name: "", flag: "🌐" });
const newKey = ref("");
const newValue = ref("");

const rows = computed(() => Object.entries(current.value?.dictionary || {}).sort(([a], [b]) => a.localeCompare(b)));
const selectedProvider = computed(() => providerProfiles.value.find(item => item.id === selectedProviderId.value) || providerProfiles.value[0] || null);

function flagFor(code: string, fallback = "🌐") {
  if (code === "en-US") return "🇺🇸";
  if (code === "fr-CA") return "🇨🇦";
  return fallback || "🌐";
}

function describeKey(key: string) {
  const [prefix] = key.split(".");
  const kind: Record<string, string> = {
    nav: i18n.t("language.description_nav", "Navigation label"),
    ui: i18n.t("language.description_ui", "Interface action, status, or helper text"),
    users: i18n.t("language.description_users", "User and role management text"),
    language: i18n.t("language.description_language", "Language-settings interface text"),
    research: i18n.t("language.description_research", "Research workspace text"),
    rag: i18n.t("language.description_rag", "Research and RAG workflow text"),
    section: i18n.t("language.description_section", "Section heading"),
    role: i18n.t("language.description_role", "Role label"),
    app: i18n.t("language.description_app", "Application identity text"),
  };
  return kind[prefix] || i18n.t("language.description_generic", "Interface text");
}

function sourceValue(key: string) {
  return referenceDictionary.value[key] || "";
}

function refreshProviderProfiles() {
  providerProfiles.value = (runtime.getProviderProfilesForUi?.() || []) as ProviderProfile[];
  const preferred = runtime.getDefaultProviderProfileId?.() || "";
  if (!providerProfiles.value.some(item => item.id === selectedProviderId.value)) {
    selectedProviderId.value = providerProfiles.value.some(item => item.id === preferred) ? preferred : (providerProfiles.value[0]?.id || "");
  }
}

async function refreshLanguages() {
  const data = await systemApi.languages();
  languages.value = data.languages.map(item => ({...item, flag: flagFor(item.code, item.flag)}));
  if (!languages.value.some(item => item.code === selectedCode.value)) selectedCode.value = languages.value[0]?.code || "en-US";
}

async function load(code = selectedCode.value) {
  loading.value = true;
  error.value = "";
  try {
    selectedCode.value = code;
    const value = await systemApi.language(code);
    current.value = {...value, flag: flagFor(value.code, value.flag)};
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally { loading.value = false; }
}

function updateValue(key: string, value: string) {
  if (!current.value) return;
  current.value = { ...current.value, dictionary: { ...current.value.dictionary, [key]: value } };
}
function addDictionaryEntry() {
  if (!current.value) return;
  const key = newKey.value.trim();
  if (!key) return;
  current.value = { ...current.value, dictionary: { ...current.value.dictionary, [key]: newValue.value } };
  newKey.value = "";
  newValue.value = "";
}
function removeDictionaryEntry(key: string) {
  if (!current.value) return;
  const next = {...current.value.dictionary};
  delete next[key];
  current.value = {...current.value, dictionary: next};
}

async function save() {
  if (!current.value) return;
  saving.value = true;
  error.value = "";
  try {
    current.value = await systemApi.updateLanguage(current.value.code, {
      name: current.value.name,
      flag: flagFor(current.value.code, current.value.flag),
      dictionary: current.value.dictionary,
    });
    await refreshLanguages();
    if (i18n.locale === current.value.code) await i18n.setLocale(current.value.code);
    runtime.notifyToast?.(i18n.t("language.saved", "Language dictionary saved."), {tone: "success"});
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
  finally { saving.value = false; }
}

function providerGeneration(profile: ProviderProfile) {
  const value = (key: string) => profile[key] as any;
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

async function installLanguage() {
  const profile = selectedProvider.value;
  if (!profile) {
    error.value = i18n.t("language.provider_profile_required", "Configure an LLM provider profile before installing a dictionary.");
    return;
  }
  installing.value = true;
  error.value = "";
  try {
    const model = String(profile.model || "").trim();
    if (!model) throw new Error(i18n.t("language.provider_model_required", "The selected provider profile does not have a model configured."));
    const created = await systemApi.installLanguage({
      code: install.value.code.trim(),
      name: install.value.name.trim() || install.value.code.trim(),
      flag: install.value.flag.trim() || "🌐",
      provider: profile.type,
      model,
      base_url: profile.base_url || undefined,
      api_key: profile.api_key || undefined,
      generation: providerGeneration(profile),
      provider_profile_id: profile.id,
      max_concurrent_requests: profile.max_concurrent_requests || 1,
    });
    installOpen.value = false;
    install.value = { code: "", name: "", flag: "🌐" };
    runtime.registerExternalJob?.(created);
    runtime.notifyToast?.(i18n.t("language.translation_started", "Translation started in the background. Track progress in Operations; the new language will appear when the job finishes."), {tone: "success"});
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
  finally { installing.value = false; }
}

async function removeLanguage(item: LanguageInfo) {
  if (["en-US", "fr-CA"].includes(item.code)) return;
  pendingDelete.value = item;
}
async function confirmRemoveLanguage() {
  const item = pendingDelete.value;
  if (!item) return;
  try {
    await systemApi.deleteLanguage(item.code);
    pendingDelete.value = null;
    await refreshLanguages();
    await load(languages.value[0]?.code || "en-US");
    await i18n.loadLanguages();
    runtime.notifyToast?.(i18n.t("language.removed", "Language removed."), {tone: "success"});
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
}

watch(installOpen, async open => {
  if (open) {
    refreshProviderProfiles();
    await nextTick();
    installCodeInput.value?.focus();
  } else installTrigger.value?.focus();
});

onMounted(async () => {
  try {
    refreshProviderProfiles();
    const base = await systemApi.language("en-US");
    referenceDictionary.value = base.dictionary || {};
    await refreshLanguages();
    await load(selectedCode.value);
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); loading.value = false; }
});
</script>

<template>
  <main class="vue-native-page languages-page">
    <section class="page-heading">
      <div><p>{{ i18n.t("section.system", "System") }}</p><h1>{{ i18n.t("language.page_title", "Languages & internationalization") }}</h1><span>{{ i18n.t("language.page_description", "Built-in locales are U.S. English and Canadian French (Québec). Install additional locale dictionaries with a configured LLM provider profile, then review every translated UI string directly.") }}</span></div>
      <button ref="installTrigger" class="btn primary" @click="installOpen = true">{{ i18n.t("language.install", "Install language") }}</button>
    </section>
    <div v-if="error" class="info error">{{ error }}</div>

    <Teleport to="body">
      <div v-if="installOpen" class="workflow-overlay" role="presentation" @mousedown.self="installOpen=false" @keydown.esc.stop.prevent="installOpen=false">
        <section class="workflow-dialog language-install-dialog" role="dialog" aria-modal="true" aria-labelledby="language-install-title">
          <header class="workflow-dialog-header">
            <div class="workflow-heading"><span class="workflow-icon" aria-hidden="true">🌐</span><div><p>{{ i18n.t("language.install_kicker", "New interface language") }}</p><h2 id="language-install-title">{{ i18n.t("language.install_dictionary", "Install translated dictionary") }}</h2><span>{{ i18n.t("language.install_help", "Translate the canonical English interface dictionary with one of the same provider profiles used elsewhere in DerridAI. Dictionary keys remain unchanged.") }}</span></div></div>
            <button class="icon-btn workflow-close" type="button" :title="i18n.t('ui.close','Close')" :aria-label="i18n.t('ui.close','Close')" @click="installOpen=false">×</button>
          </header>

          <ol class="workflow-steps" :aria-label="i18n.t('language.install_steps','Installation steps')"><li class="active"><span>1</span><b>{{ i18n.t("language.step_identity","Language") }}</b></li><li class="active"><span>2</span><b>{{ i18n.t("language.step_provider","Provider profile") }}</b></li><li><span>3</span><b>{{ i18n.t("language.step_review","Install") }}</b></li></ol>

          <form class="workflow-form" @submit.prevent="installLanguage">
            <section class="workflow-section">
              <div class="workflow-section-copy"><b>{{ i18n.t("language.identity_section","Language identity") }}</b><span>{{ i18n.t("language.identity_section_help","Choose the locale code and the label people will see in the language picker.") }}</span></div>
              <div class="workflow-fields workflow-identity-fields">
                <label class="workflow-field"><span>{{ i18n.t("language.locale_code","Locale code") }}</span><input ref="installCodeInput" v-model="install.code" class="control" required autocomplete="off" spellcheck="false" placeholder="de-DE"><small>{{ i18n.t("language.locale_code_help","BCP 47 locale identifier, for example de-DE or es-MX.") }}</small></label>
                <label class="workflow-field"><span>{{ i18n.t("language.name","Display name") }}</span><input v-model="install.name" class="control" autocomplete="off" placeholder="Deutsch (Deutschland)"><small>{{ i18n.t("language.name_help","Human-readable language name shown in the picker.") }}</small></label>
                <label class="workflow-field"><span>{{ i18n.t("language.flag","Flag / symbol") }}</span><div class="language-symbol-control"><span class="language-symbol-preview">{{ install.flag || '🌐' }}</span><input v-model="install.flag" class="control" maxlength="32"></div><small>{{ i18n.t("language.flag_help","Unicode emoji or symbol shown beside the locale name.") }}</small></label>
              </div>
            </section>

            <section class="workflow-section">
              <div class="workflow-section-copy"><b>{{ i18n.t("language.translation_section","Translation provider") }}</b><span>{{ i18n.t("language.translation_section_help","Use an existing LLM provider profile so model, endpoint, credentials, and generation defaults stay consistent with the rest of DerridAI.") }}</span></div>
              <div class="workflow-provider-area">
                <ProviderProfileSelect v-model="selectedProviderId" :profiles="providerProfiles" :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''" :label="i18n.t('language.provider_profile','Provider profile')" :help="i18n.t('language.provider_profile_help','Uses the same provider profiles and model defaults as Research, PDF tools, and LLM review.')" :empty-title="i18n.t('language.no_provider_profiles','No LLM provider profiles are configured')" :empty-help="i18n.t('language.no_provider_profiles_help','Create a provider profile first, then return here to translate a dictionary.')" :manage-label="i18n.t('language.manage_providers','Manage provider profiles')" :model-not-set-label="i18n.t('language.model_not_set','model not set')" :default-label="i18n.t('ui.default','Default')" :concurrent-label="i18n.t('language.concurrent_requests','max concurrent request(s)')" @manage="runtime.navigateView('providers'); installOpen=false" />
              </div>
            </section>

            <section class="workflow-next-steps" :aria-label="i18n.t('language.what_happens_next','What happens next')">
              <div class="workflow-next-step"><span class="workflow-step-icon">1</span><div><b>{{ i18n.t("language.background_translation","Runs in the background") }}</b><small>{{ i18n.t("language.background_translation_help","You can close this window immediately and continue working.") }}</small></div></div>
              <div class="workflow-next-step"><span class="workflow-step-icon">2</span><div><b>{{ i18n.t("language.track_operations","Track it in Operations") }}</b><small>{{ i18n.t("language.track_operations_help","Progress and failures appear with other background jobs.") }}</small></div></div>
              <div class="workflow-next-step"><span class="workflow-step-icon">3</span><div><b>{{ i18n.t("language.review_after","Review after completion") }}</b><small>{{ i18n.t("language.review_after_help","The installed dictionary will appear here when translation finishes; review and edit any field normally.") }}</small></div></div>
            </section>

            <footer class="workflow-actions"><button type="button" class="btn" @click="installOpen=false">{{ i18n.t("ui.cancel","Cancel") }}</button><button class="btn primary" :disabled="installing || !install.code.trim() || !selectedProvider">{{ installing ? i18n.t("language.starting","Starting…") : i18n.t("language.start_translation","Start translation") }}</button></footer>
          </form>
        </section>
      </div>
    </Teleport>

    <section class="language-layout">
      <aside class="card language-list-card">
        <div class="cardhead"><div><b>{{ i18n.t("language.installed", "Installed locales") }}</b><div class="note">{{ languages.length }} {{ i18n.t("language.locale_count", languages.length === 1 ? "language" : "languages") }}</div></div></div>
        <div v-for="item in languages" :key="item.code" class="language-row" :class="{active: item.code === selectedCode}" role="button" tabindex="0" @click="load(item.code)" @keydown.enter="load(item.code)">
          <LanguageFlag :code="item.code" :symbol="flagFor(item.code,item.flag)" :label="item.name" /><span><b>{{ item.name }}</b><small>{{ item.code }}</small></span>
          <button v-if="!['en-US','fr-CA'].includes(item.code)" class="btn tiny danger" type="button" @click.stop="removeLanguage(item)">{{ i18n.t("ui.remove", "Remove") }}</button>
        </div>
      </aside>

      <section class="card language-editor-card">
        <div v-if="loading" class="loading-state"><span class="spinner"></span>{{ i18n.t("ui.loading_dictionary", "Loading dictionary…") }}</div>
        <template v-else-if="current">
          <div class="cardhead"><div><b class="language-editor-title"><LanguageFlag :code="current.code" :symbol="flagFor(current.code,current.flag)" :label="current.name" /> {{ current.name }}</b><div class="note">{{ current.code }} · {{ rows.length }} {{ i18n.t("language.translated_keys", "translated keys") }}</div></div><button class="btn primary" :disabled="saving" @click="save">{{ saving ? i18n.t("ui.saving", "Saving…") : i18n.t("language.save_dictionary", "Save dictionary") }}</button></div>
          <div class="language-meta-grid aligned-field-grid"><label class="workflow-field"><span>{{ i18n.t("language.name", "Name") }}</span><input v-model="current.name" class="control"><small>{{ i18n.t("language.name_help","Human-readable language name shown in the picker.") }}</small></label><label class="workflow-field"><span>{{ i18n.t("language.flag", "Flag / symbol") }}</span><input v-model="current.flag" class="control"><small>{{ i18n.t("language.flag_help","Unicode emoji or symbol shown beside the locale name.") }}</small></label></div>
          <form class="language-dictionary-add" @submit.prevent="addDictionaryEntry">
            <input v-model="newKey" class="control" placeholder="ui.new_key" :aria-label="i18n.t('language.dictionary_key','Dictionary key')">
            <input v-model="newValue" class="control" :placeholder="i18n.t('language.translation','Translation')" :aria-label="i18n.t('language.dictionary_value','Dictionary value')">
            <button class="btn small" :disabled="!newKey.trim()">{{ i18n.t("language.add_key", "Add key") }}</button>
          </form>
          <div class="language-dictionary-table">
            <div class="language-dictionary-head"><span>{{ i18n.t("language.key", "Key") }}</span><span>{{ i18n.t("language.field_description", "Description") }}</span><span>{{ i18n.t("language.translation", "Translation") }}</span><span></span></div>
            <div v-for="([key, value]) in rows" :key="key" class="language-dictionary-row">
              <code :title="sourceValue(key)">{{ key }}</code>
              <small class="language-field-description" :title="sourceValue(key)">{{ describeKey(key) }}</small>
              <textarea class="control language-translation-field" rows="1" :value="value" :aria-label="`${i18n.t('language.translation','Translation')}: ${key}`" @input="updateValue(key, ($event.target as HTMLTextAreaElement).value)"></textarea>
              <button class="btn tiny danger" type="button" :title="i18n.t('language.remove_key', 'Remove dictionary key')" @click="removeDictionaryEntry(key)">×</button>
            </div>
          </div>
        </template>
      </section>
    </section>

    <div v-if="pendingDelete" class="native-confirm-backdrop" role="presentation" @click.self="pendingDelete = null"><section class="card native-confirm-card" role="dialog" aria-modal="true"><div class="cardhead"><div><b>{{ i18n.t("language.remove_confirm","Remove language?") }}</b><div class="note">{{ pendingDelete.name }} · {{ pendingDelete.code }}</div></div></div><p>{{ i18n.t("language.remove_help","The installed dictionary will be deleted from this DerridAI instance.") }}</p><div class="actions"><button class="btn" @click="pendingDelete=null">{{ i18n.t("ui.cancel","Cancel") }}</button><button class="btn danger" @click="confirmRemoveLanguage">{{ i18n.t("language.remove_language","Remove language") }}</button></div></section></div>
  </main>
</template>
