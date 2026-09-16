import { ref } from "vue";
import { defineStore } from "pinia";
import { systemApi, type LanguageInfo } from "../api/system";
import * as runtime from "../legacy/runtime.js";

export const useI18nStore = defineStore("i18n", () => {
  const locale = ref(localStorage.getItem("derridai-locale") || "en-US");
  const languages = ref<LanguageInfo[]>([]);
  const dictionary = ref<Record<string, string>>({});
  const baseDictionary = ref<Record<string, string>>({});
  const loading = ref(false);

  function t(key: string, fallback?: string) {
    return dictionary.value[key] || fallback || key;
  }

  function tf(key: string, fallback: string, values: Record<string, string | number> = {}) {
    let text = String(t(key, fallback));
    for (const [name, value] of Object.entries(values)) text = text.replaceAll(`{${name}}`, String(value));
    return text;
  }

  async function loadLanguages() {
    try { languages.value = (await systemApi.languages()).languages; }
    catch { languages.value = [{code: "en-US", name: "U.S. English", flag: "🇺🇸"}, {code: "fr-CA", name: "Français (Québec)", flag: "🇨🇦"}]; }
  }

  async function setLocale(code: string) {
    loading.value = true;
    try {
      const [data, base] = await Promise.all([
        systemApi.language(code),
        code === "en-US" ? systemApi.language(code) : systemApi.language("en-US"),
      ]);
      locale.value = data.code;
      dictionary.value = data.dictionary || {};
      baseDictionary.value = base.dictionary || {};
      localStorage.setItem("derridai-locale", data.code);
      document.documentElement.lang = data.code;
      runtime.setTranslationDictionary(data.code, dictionary.value, baseDictionary.value);
      if (document.querySelector("#main")) runtime.renderView();
    } finally { loading.value = false; }
  }

  async function initialize() {
    await loadLanguages();
    const available = languages.value.some(item => item.code === locale.value) ? locale.value : "en-US";
    try {
      await setLocale(available);
    } catch (exc) {
      // Localization must never prevent the sign-in/application shell from
      // loading. Vue labels already provide English fallbacks.
      console.warn("Could not load interface dictionary", exc);
      locale.value = available;
      dictionary.value = {};
      baseDictionary.value = {};
      document.documentElement.lang = available;
      runtime.setTranslationDictionary(available, {}, {});
    }
  }

  return { locale, languages, dictionary, baseDictionary, loading, t, tf, loadLanguages, setLocale, initialize };
});
