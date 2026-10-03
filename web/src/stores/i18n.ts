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

import { ref } from "vue";
import { defineStore } from "pinia";
import { systemApi, type LanguageInfo } from "../api/system";
import { englishDefault, COMMON_KEY_ALIASES } from "../i18n/englishDefault";
import * as runtime from "../runtime/runtimeBridge";
import { renderView } from "../domain/sharedNavigation";

let languageEventBridgeInstalled = false;

export const useI18nStore = defineStore("i18n", () => {
  const locale = ref(localStorage.getItem("derridai-locale") || "en-US");
  const languages = ref<LanguageInfo[]>([]);
  const dictionary = ref<Record<string, string>>({});
  const baseDictionary = ref<Record<string, string>>({});
  const loading = ref(false);

  function t(key: string, fallback?: string) {
    const commonKey = COMMON_KEY_ALIASES[key];
    return (
      dictionary.value[key] ||
      (commonKey ? dictionary.value[commonKey] : undefined) ||
      baseDictionary.value[key] ||
      (commonKey ? baseDictionary.value[commonKey] : undefined) ||
      fallback ||
      englishDefault(key) ||
      (commonKey ? englishDefault(commonKey) : "") ||
      key
    );
  }

  function tf(
    key: string,
    fallbackOrValues?: string | Record<string, string | number>,
    values?: Record<string, string | number>,
  ) {
    let fallback: string | undefined;
    let vars = values || {};
    if (fallbackOrValues && typeof fallbackOrValues === "object") vars = fallbackOrValues;
    else if (typeof fallbackOrValues === "string") fallback = fallbackOrValues;
    let text = String(t(key, fallback));
    for (const [name, value] of Object.entries(vars))
      text = text.replaceAll(`{${name}}`, String(value));
    return text;
  }

  function directionForLocale(code: string) {
    try {
      const script = new Intl.Locale(code).maximize().script || "";
      return new Set(["Arab", "Hebr", "Syrc", "Thaa", "Nkoo", "Adlm", "Rohg", "Mand"]).has(script)
        ? "rtl"
        : "ltr";
    } catch {
      return "ltr";
    }
  }

  async function loadLanguages() {
    try {
      languages.value = (await systemApi.languages()).languages;
    } catch {
      languages.value = [
        { code: "en-US", name: "English", flag: "🇺🇸" },
        { code: "fr-CA", name: "Français", flag: "🇨🇦" },
      ];
    }
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
      document.documentElement.dir = directionForLocale(data.code);
      runtime.setTranslationDictionary(data.code, dictionary.value, baseDictionary.value, {
        name: data.name,
        flag: data.flag,
      });
      if (document.querySelector("#main")) renderView();
    } finally {
      loading.value = false;
    }
  }

  async function refreshLanguagesFromEvent() {
    const requested = locale.value;
    await loadLanguages();
    const available = languages.value.some((item) => item.code === requested);
    await setLocale(available ? requested : "en-US");
  }

  if (typeof window !== "undefined" && !languageEventBridgeInstalled) {
    languageEventBridgeInstalled = true;
    window.addEventListener("derridai:languages-changed", () => {
      void refreshLanguagesFromEvent().catch((exc) =>
        console.warn("Could not refresh installed languages", exc),
      );
    });
  }

  async function initialize() {
    await loadLanguages();
    const available = languages.value.some((item) => item.code === locale.value)
      ? locale.value
      : "en-US";
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
      document.documentElement.dir = directionForLocale(available);
      runtime.setTranslationDictionary(available, {}, {});
    }
  }

  return {
    locale,
    languages,
    dictionary,
    baseDictionary,
    loading,
    t,
    tf,
    directionForLocale,
    loadLanguages,
    setLocale,
    initialize,
  };
});
