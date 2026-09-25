/* Copyright 2026 Aaron John Schlosser, PhD. */

import { englishDefault } from "../i18n/englishDefault";

const UI_COLOR_THEMES = new Set(["green", "blue", "slate"]);
const UI_COLOR_SCHEMES = new Set(["system", "light", "dark"]);
const UI_CONTRAST_PREFS = new Set(["system", "more"]);
let appearanceMediaWired = false;

function mediaMatches(query) {
  try {
    return Boolean(window.matchMedia?.(query)?.matches);
  } catch {
    return false;
  }
}

export function syncColorScheme(state) {
  const pref = UI_COLOR_SCHEMES.has(String(state.appConfig.ui_color_scheme || ""))
    ? String(state.appConfig.ui_color_scheme)
    : "system";
  const contrastPref = UI_CONTRAST_PREFS.has(String(state.appConfig.ui_contrast || ""))
    ? String(state.appConfig.ui_contrast)
    : "system";
  const scheme =
    pref === "light" || pref === "dark"
      ? pref
      : mediaMatches("(prefers-color-scheme: dark)")
        ? "dark"
        : "light";
  const contrast =
    contrastPref === "more" ||
    (contrastPref === "system" && mediaMatches("(prefers-contrast: more)"))
      ? "more"
      : "default";
  try {
    document.documentElement.dataset.uiTheme = state.appConfig.ui_color_theme || "green";
    document.documentElement.dataset.colorScheme = scheme;
    if (contrast === "more") document.documentElement.dataset.contrast = "more";
    else delete document.documentElement.dataset.contrast;
  } catch {
    // document may be unavailable during early bootstrap
  }
  return { scheme, contrast };
}

export function wireAppearanceMedia(state) {
  if (appearanceMediaWired || typeof window === "undefined" || !window.matchMedia) return;
  appearanceMediaWired = true;
  const sync = () => syncColorScheme(state);
  try {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", sync);
    window.matchMedia("(prefers-contrast: more)").addEventListener("change", sync);
  } catch {
    // matchMedia listeners are best-effort in non-browser test hosts
  }
}

export function applyUiTheme(state, theme) {
  const next = UI_COLOR_THEMES.has(String(theme || "")) ? String(theme) : "green";
  state.appConfig.ui_color_theme = next;
  try {
    document.documentElement.dataset.uiTheme = next;
  } catch {
    // document may be unavailable during early bootstrap
  }
  try {
    localStorage.setItem("derridai.ui.theme", next);
  } catch {
    // localStorage can be blocked
  }
  syncColorScheme(state);
  return next;
}

export function applyAppearance(state, patch = {}) {
  if (patch.ui_color_theme != null) applyUiTheme(state, patch.ui_color_theme);
  if (patch.ui_color_scheme != null) {
    const next = UI_COLOR_SCHEMES.has(String(patch.ui_color_scheme))
      ? String(patch.ui_color_scheme)
      : "system";
    state.appConfig.ui_color_scheme = next;
    try {
      localStorage.setItem("derridai.ui.scheme", next);
    } catch {
      // localStorage can be blocked
    }
  }
  if (patch.ui_contrast != null) {
    const next = UI_CONTRAST_PREFS.has(String(patch.ui_contrast))
      ? String(patch.ui_contrast)
      : "system";
    state.appConfig.ui_contrast = next;
    try {
      localStorage.setItem("derridai.ui.contrast", next);
    } catch {
      // localStorage can be blocked
    }
  }
  wireAppearanceMedia(state);
  return syncColorScheme(state);
}

export function setTranslationDictionary(state, locale, dictionary = {}, base = {}, info = {}) {
  const canonical = base || {};
  const reverse = new Map();
  for (const [key, value] of Object.entries(canonical)) {
    const text = String(value ?? "").trim();
    if (text && !reverse.has(text)) reverse.set(text, key);
  }
  state.translations = {
    locale: String(locale || "en-US"),
    dictionary: dictionary || {},
    base: canonical,
    reverse,
    info: info || {},
  };
}

export function tr(state, key, fallback = "") {
  return (
    state.translations?.dictionary?.[key] ||
    state.translations?.base?.[key] ||
    fallback ||
    englishDefault(key) ||
    key
  );
}

export function trf(state, key, fallback, values = {}) {
  if (fallback && typeof fallback === "object") {
    values = fallback;
    fallback = "";
  }
  let text = String(tr(state, key, fallback));
  for (const [name, value] of Object.entries(values))
    text = text.replaceAll(`{${name}}`, String(value));
  return text;
}

export function translateExactUiValue(state, value) {
  const raw = String(value ?? "");
  if (state.translations?.locale === "en-US") return raw;
  const trimmed = raw.trim();
  const key = state.translations?.reverse?.get?.(trimmed);
  if (!key || state.translations?.dictionary?.[key] == null) return raw;
  const translated = String(state.translations.dictionary[key]);
  const prefix = raw.match(/^\s*/)?.[0] || "";
  const suffix = raw.match(/\s*$/)?.[0] || "";
  return `${prefix}${translated}${suffix}`;
}

export function translateDynamicUiValue(state, value) {
  const raw = String(value ?? "");
  const exact = translateExactUiValue(state, raw);
  if (exact !== raw || state.translations?.locale === "en-US") return exact;
  const prefix = raw.match(/^\s*/)?.[0] || "";
  const suffix = raw.match(/\s*$/)?.[0] || "";
  const text = raw.trim();
  const numericCount = (input) => Number(String(input).replace(/[^0-9.-]/g, ""));
  const noun = (oneKey, manyKey, oneFallback, manyFallback, count) =>
    tr(
      state,
      numericCount(count) === 1 ? oneKey : manyKey,
      numericCount(count) === 1 ? oneFallback : manyFallback,
    );
  let match;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) records$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.record_one", "dynamic.records", "record", "records", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) works$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.work_one", "dynamic.works", "work", "works", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) models$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.model_one", "dynamic.models", "model", "models", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) profiles$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.profile_one", "dynamic.profiles", "profile", "profiles", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) words$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.word_one", "dynamic.words", "word", "words", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) characters$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.character_one", "dynamic.characters", "character", "characters", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) changes$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.change_one", "dynamic.changes", "change", "changes", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) annotations$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.annotation_one", "dynamic.annotations", "annotation", "annotations", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) cached responses$/i)))
    return `${prefix}${match[1]} ${noun("dynamic.cached_response_one", "dynamic.cached_responses", "cached response", "cached responses", match[1])}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) selected evidence$/i)))
    return `${prefix}${match[1]} ${tr(state, "dynamic.selected_evidence", "selected evidence")}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) selected$/i)))
    return `${prefix}${trf(state, "dynamic.selected_count", "{count} selected", { count: match[1] })}${suffix}`;
  if ((match = text.match(/^([0-9][0-9., \u00a0]*) of ([0-9][0-9., \u00a0]*) records$/i)))
    return `${prefix}${trf(state, "dynamic.record_range_count", "{shown} of {total} records", { shown: match[1], total: match[2] })}${suffix}`;
  if ((match = text.match(/^Page ([0-9]+) \/ ([0-9]+)$/i)))
    return `${prefix}${trf(state, "dynamic.page_of_pages", "Page {page} / {pages}", { page: match[1], pages: match[2] })}${suffix}`;
  if ((match = text.match(/^Ready · ([0-9][0-9., \u00a0]*) models$/i)))
    return `${prefix}${trf(state, "dynamic.ready_models", "Ready · {count} models", { count: match[1] })}${suffix}`;
  if (
    (match = text.match(
      /^Showing latest ([0-9]+) of ([0-9]+) changes\. Full history is preserved in the record's updates field\.$/i,
    ))
  )
    return `${prefix}${trf(state, "dynamic.history_latest", "Showing latest {shown} of {total} changes. Full history is preserved in the record's updates field.", { shown: match[1], total: match[2] })}${suffix}`;
  if ((match = text.match(/^Cleared updates history from ([0-9][0-9., \u00a0]*) records$/i)))
    return `${prefix}${trf(state, "dynamic.cleared_history_records", "Cleared updates history from {count} records", { count: match[1] })}${suffix}`;
  if (
    (match = text.match(
      /^Restored original record state · ([0-9][0-9., \u00a0]*) fields changed$/i,
    ))
  )
    return `${prefix}${trf(state, "dynamic.restored_fields", "Restored original record state · {count} fields changed", { count: match[1] })}${suffix}`;
  if (
    (match = text.match(
      /^Loaded ([0-9][0-9., \u00a0]*) records(?: · ([0-9][0-9., \u00a0]*) parse issues)?$/i,
    ))
  )
    return `${prefix}${trf(state, match[2] ? "dynamic.loaded_records_issues" : "dynamic.loaded_records", match[2] ? "Loaded {count} records · {issues} parse issues" : "Loaded {count} records", { count: match[1], issues: match[2] || "0" })}${suffix}`;
  if (
    (match = text.match(
      /^Merged and replaced ([0-9][0-9., \u00a0]*) tabs · ([0-9][0-9., \u00a0]*) records$/i,
    ))
  )
    return `${prefix}${trf(state, "dynamic.merged_tabs_records", "Merged and replaced {tabs} tabs · {records} records", { tabs: match[1], records: match[2] })}${suffix}`;
  if (
    (match = text.match(
      /^([0-9][0-9., \u00a0]*) records cleaned · ([0-9][0-9., \u00a0]*) tracked changes$/i,
    ))
  )
    return `${prefix}${trf(state, "dynamic.cleaned_records", "{records} records cleaned · {changes} tracked changes", { records: match[1], changes: match[2] })}${suffix}`;
  if ((match = text.match(/^Exported ([0-9][0-9., \u00a0]*) records from (.+)$/i)))
    return `${prefix}${trf(state, "dynamic.exported_records", "Exported {count} records from {collection}", { count: match[1], collection: match[2] })}${suffix}`;
  if ((match = text.match(/^Grading ([0-9]+) of ([0-9]+) · (.+)$/i)))
    return `${prefix}${trf(state, "dynamic.grading_progress", "Grading {current} of {total} · {question}", { current: match[1], total: match[2], question: match[3] })}${suffix}`;
  if ((match = text.match(/^Translating ([0-9][0-9., \u00a0]*) interface strings to (.+)$/i)))
    return `${prefix}${trf(state, "dynamic.translating_interface", "Translating {count} interface strings to {locale}", { count: match[1], locale: match[2] })}${suffix}`;
  if ((match = text.match(/^Running (.+)$/i)))
    return `${prefix}${trf(state, "dynamic.running_operation", "Running {label}", { label: match[1] })}${suffix}`;
  if (
    (match = text.match(
      /^Completed · ([0-9][0-9., \u00a0]*) graded, ([0-9][0-9., \u00a0]*) failed$/i,
    ))
  )
    return `${prefix}${trf(state, "dynamic.completed_grading", "Completed · {graded} graded, {failed} failed", { graded: match[1], failed: match[2] })}${suffix}`;
  if (
    (match = text.match(
      /^Completed · ([0-9][0-9., \u00a0]*) works, ([0-9][0-9., \u00a0]*) failed$/i,
    ))
  )
    return `${prefix}${trf(state, "dynamic.completed_works", "Completed · {works} works, {failed} failed", { works: match[1], failed: match[2] })}${suffix}`;
  if ((match = text.match(/^Waiting for provider slot: ([0-9]+) active \/ ([0-9]+) allowed$/i)))
    return `${prefix}${trf(state, "dynamic.waiting_provider_active", "Waiting for provider slot: {active} active / {allowed} allowed", { active: match[1], allowed: match[2] })}${suffix}`;
  if ((match = text.match(/^Waiting for provider slot \(([0-9]+)\/([0-9]+) active\)$/i)))
    return `${prefix}${trf(state, "dynamic.waiting_provider_active_paren", "Waiting for provider slot ({active}/{allowed} active)", { active: match[1], allowed: match[2] })}${suffix}`;
  if ((match = text.match(/^Waiting for Ollama slot: ([0-9]+) active \/ ([0-9]+) allowed$/i)))
    return `${prefix}${trf(state, "dynamic.waiting_ollama_active", "Waiting for Ollama slot: {active} active / {allowed} allowed", { active: match[1], allowed: match[2] })}${suffix}`;
  return raw;
}

/**
 * Translate application-owned legacy UI labels after a compatibility renderer
 * has painted. Exact dictionary values are preferred; a deliberately small set
 * of count/status patterns handles legacy strings that contain runtime numbers.
 * Corpus passages, record text, source evidence, code and user input are blocked
 * from this bridge. New Vue-native components should call the i18n store directly.
 */
export function translateLegacyDom(state, root = document.querySelector("#main")) {
  if (!root || state.translations?.locale === "en-US") return;
  const selectors = [
    "button",
    "label",
    "th",
    "option",
    ".section-label",
    ".side-section-label",
    ".dialog-title",
    ".dialog-subtitle",
    ".empty-store > b",
    ".ui-collapse-title",
  ];
  root.querySelectorAll(selectors.join(",")).forEach((element) => {
    // Controls with nested icons/counts keep their structured children; translating
    // only pure text labels avoids destroying SVG or status badges.
    if (element.childElementCount === 0 && element.textContent) {
      const next = translateDynamicUiValue(state, element.textContent);
      if (next !== element.textContent) element.textContent = next;
    }
    for (const attr of ["title", "aria-label", "placeholder"]) {
      if (!element.hasAttribute(attr)) continue;
      const current = element.getAttribute(attr) || "";
      const next = translateDynamicUiValue(state, current);
      if (next !== current) element.setAttribute(attr, next);
    }
  });
  root
    .querySelectorAll("input[placeholder],textarea[placeholder],select[title]")
    .forEach((element) => {
      for (const attr of ["placeholder", "title", "aria-label"]) {
        if (!element.hasAttribute(attr)) continue;
        const current = element.getAttribute(attr) || "";
        const next = translateDynamicUiValue(state, current);
        if (next !== current) element.setAttribute(attr, next);
      }
    });
  // Compatibility views still contain substantial vanilla-DOM markup. Translate
  // exact UI phrases even when an icon or badge makes the containing element
  // non-leaf, but never walk record/evidence/source-text regions.
  const blocked =
    ".textcell,.recordtext,.pdftext,.researcher-summary-text,[data-annotatable-field],pre,code,svg,script,style,textarea,input";
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let node;
  while ((node = walker.nextNode())) nodes.push(node);
  for (const textNode of nodes) {
    const parent = textNode.parentElement;
    if (!parent || parent.closest(blocked)) continue;
    const next = translateDynamicUiValue(state, textNode.nodeValue || "");
    if (next !== textNode.nodeValue) textNode.nodeValue = next;
  }
}
