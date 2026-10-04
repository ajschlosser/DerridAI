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

import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { systemApi, type LanguageInfo } from "../api/system";
import { englishDefault, COMMON_KEY_ALIASES } from "../i18n/englishDefault";
import { setTranslationDictionary } from "../domain/sharedTranslate";
import { renderView } from "../domain/sharedNavigation";
import {
  AUTO_TIME_ZONE,
  LOCALE_STORAGE_KEY,
  TIME_ZONE_STORAGE_KEY,
  browserLocaleCodes,
  detectBrowserTimeZone,
  detectInstalledBrowserLocale,
  resolveTimeZone,
  supportedTimeZones,
} from "../domain/localePreferences";

let languageEventBridgeInstalled = false;

export const useI18nStore = defineStore("i18n", () => {
  const locale = ref("en-US");
  const browserLocale = ref("");
  const missingBrowserLocale = ref("");
  const browserTimeZone = ref(detectBrowserTimeZone());
  const timeZonePreference = ref(localStorage.getItem(TIME_ZONE_STORAGE_KEY) || AUTO_TIME_ZONE);
  const timeZone = computed(() => resolveTimeZone(timeZonePreference.value, browserTimeZone.value));
  const timeZones = computed(() => supportedTimeZones(browserTimeZone.value));
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

  async function setLocale(code: string, options: { persist?: boolean } = {}) {
    loading.value = true;
    try {
      const [data, base] = await Promise.all([
        systemApi.language(code),
        code === "en-US" ? systemApi.language(code) : systemApi.language("en-US"),
      ]);
      locale.value = data.code;
      dictionary.value = data.dictionary || {};
      baseDictionary.value = base.dictionary || {};
      if (options.persist !== false) {
        localStorage.setItem(LOCALE_STORAGE_KEY, data.code);
        missingBrowserLocale.value = "";
      }
      document.documentElement.lang = data.code;
      document.documentElement.dir = directionForLocale(data.code);
      setTranslationDictionary(data.code, dictionary.value, baseDictionary.value, {
        name: data.name,
        flag: data.flag,
      });
      if (document.querySelector("#main")) renderView();
    } finally {
      loading.value = false;
    }
  }

  function browserMatch() {
    const detected = detectInstalledBrowserLocale(languages.value, browserLocaleCodes());
    browserLocale.value = detected.requested;
    return detected;
  }

  function setTimeZone(value: string) {
    const requested = value || AUTO_TIME_ZONE;
    timeZonePreference.value =
      requested === AUTO_TIME_ZONE || supportedTimeZones(browserTimeZone.value).includes(requested)
        ? requested
        : AUTO_TIME_ZONE;
    localStorage.setItem(TIME_ZONE_STORAGE_KEY, timeZonePreference.value);
    document.documentElement.dataset.timeZone = timeZone.value;
  }

  async function refreshLanguagesFromEvent() {
    await loadLanguages();
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY) || "";
    const savedLanguage = languages.value.find(
      (item) => item.code.toLowerCase() === saved.toLowerCase(),
    );
    if (savedLanguage) {
      missingBrowserLocale.value = "";
      await setLocale(savedLanguage.code, { persist: false });
      return;
    }
    const detected = browserMatch();
    missingBrowserLocale.value = detected.requested && !detected.match ? detected.requested : "";
    await setLocale(detected.match || "en-US", { persist: Boolean(detected.match) });
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
    browserTimeZone.value = detectBrowserTimeZone();
    document.documentElement.dataset.timeZone = timeZone.value;
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY) || "";
    const savedLanguage = languages.value.find(
      (item) => item.code.toLowerCase() === saved.toLowerCase(),
    );
    const detected = browserMatch();
    const available = savedLanguage?.code || detected.match || "en-US";
    missingBrowserLocale.value =
      !savedLanguage && detected.requested && !detected.match ? detected.requested : "";
    try {
      await setLocale(available, { persist: Boolean(savedLanguage || detected.match) });
    } catch (exc) {
      // Localization must never prevent the sign-in/application shell from
      // loading. Vue labels already provide English fallbacks.
      console.warn("Could not load interface dictionary", exc);
      locale.value = available;
      dictionary.value = {};
      baseDictionary.value = {};
      document.documentElement.lang = available;
      document.documentElement.dir = directionForLocale(available);
      setTranslationDictionary(available, {}, {});
    }
  }

  return {
    locale,
    browserLocale,
    missingBrowserLocale,
    browserTimeZone,
    timeZonePreference,
    timeZone,
    timeZones,
    languages,
    dictionary,
    baseDictionary,
    loading,
    t,
    tf,
    directionForLocale,
    loadLanguages,
    setLocale,
    setTimeZone,
    initialize,
  };
});
