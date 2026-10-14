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

import type { LanguageInfo } from "../api/system";

export const LOCALE_STORAGE_KEY = "derridai-locale";
export const TIME_ZONE_STORAGE_KEY = "derridai-time-zone";
export const AUTO_TIME_ZONE = "auto";

export interface BrowserLocaleMatch {
  requested: string;
  match: string | null;
}

export function normalizeLocale(code: string): string {
  const value = String(code || "")
    .trim()
    .replaceAll("_", "-");
  if (!value) return "";
  try {
    return new Intl.Locale(value).toString();
  } catch {
    return value;
  }
}

function languagePart(code: string): string {
  try {
    return new Intl.Locale(code).language.toLowerCase();
  } catch {
    return code.split("-", 1)[0].toLowerCase();
  }
}

export function browserLocaleCodes(): string[] {
  if (typeof navigator === "undefined") return [];
  const values = [
    ...(Array.isArray(navigator.languages) ? navigator.languages : []),
    navigator.language,
  ];
  return [...new Set(values.map(normalizeLocale).filter(Boolean))];
}

export function detectInstalledBrowserLocale(
  languages: readonly Pick<LanguageInfo, "code">[],
  requested = browserLocaleCodes(),
): BrowserLocaleMatch {
  const code = normalizeLocale(requested[0] || "");
  if (!code) return { requested: "", match: null };

  const installed = languages.map((item) => ({
    original: item.code,
    normalized: normalizeLocale(item.code).toLowerCase(),
    language: languagePart(item.code),
  }));

  const exact = installed.find((item) => item.normalized === code.toLowerCase());
  if (exact) return { requested: code, match: exact.original };

  const base = languagePart(code);
  const compatible = installed.find((item) => item.language === base);
  return { requested: code, match: compatible?.original || null };
}

export function detectBrowserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export function isSupportedTimeZone(zone: string): boolean {
  if (!zone) return false;
  try {
    new Intl.DateTimeFormat("en", { timeZone: zone }).format(0);
    return true;
  } catch {
    return false;
  }
}

export function resolveTimeZone(preference: string, browserZone = detectBrowserTimeZone()): string {
  if (preference && preference !== AUTO_TIME_ZONE && isSupportedTimeZone(preference)) {
    return preference;
  }
  return isSupportedTimeZone(browserZone) ? browserZone : "UTC";
}

export function supportedTimeZones(browserZone = detectBrowserTimeZone()): string[] {
  const intl = Intl as typeof Intl & {
    supportedValuesOf?: (key: "timeZone") => string[];
  };
  let zones: string[] = [];
  try {
    zones = intl.supportedValuesOf?.("timeZone") || [];
  } catch {
    zones = [];
  }
  return [...new Set(["UTC", browserZone, ...zones].filter(isSupportedTimeZone))].sort((a, b) =>
    a.localeCompare(b),
  );
}

export function storedTimeZone(): string {
  let preference = AUTO_TIME_ZONE;
  try {
    preference = localStorage.getItem(TIME_ZONE_STORAGE_KEY) || AUTO_TIME_ZONE;
  } catch {
    // Browser storage can be unavailable in hardened/private contexts.
  }
  return resolveTimeZone(preference);
}
