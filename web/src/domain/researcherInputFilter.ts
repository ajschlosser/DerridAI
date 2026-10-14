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

import { toast } from "../composables/notifications";
import { sessionState } from "../state/workspaceState";
import { api } from "./legacyApi";
import { normalizeResearcherToken } from "./researcherContentFilter";
import { isResearcher } from "./sharedSession";
import { tr } from "./sharedTranslate";

type ContextualRule = {
  term_hash?: string;
  allow_title_case?: boolean;
  allow_if_surrounding?: string[];
  allow_if_before_markers?: string[];
};
type ResearcherPolicy = { ready: boolean; blocked: Set<string>; contextual: ContextualRule[] };
let researcherPolicy: ResearcherPolicy = { ready: false, blocked: new Set(), contextual: [] };
let researcherPolicyToastAt = 0;
async function researcherTokenDigest(value: string) {
  if (!globalThis.crypto?.subtle) return "";
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(normalizeResearcherToken(value)),
  );
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");
}
export async function refreshResearcherContentPolicy() {
  if (!sessionState.userContext) {
    researcherPolicy = { ready: false, blocked: new Set(), contextual: [] };
    return;
  }
  try {
    const data = await api("/api/i18n/content-policy");
    researcherPolicy = {
      ready: Boolean(data?.ready),
      blocked: new Set(Array.isArray(data?.blocked_term_hashes) ? data.blocked_term_hashes : []),
      contextual: Array.isArray(data?.contextual) ? data.contextual : [],
    };
  } catch {
    researcherPolicy = { ready: false, blocked: new Set(), contextual: [] };
  }
}
async function filterResearcherInputElement(target: EventTarget | null) {
  if (!isResearcher() || !(target instanceof HTMLElement) || !researcherPolicy.ready) return;
  const acceptsText =
    target instanceof HTMLTextAreaElement ||
    (target instanceof HTMLInputElement &&
      ["text", "search", "url", "email", "tel"].includes(target.type)) ||
    target.isContentEditable;
  if (!acceptsText) return;
  const original = target.isContentEditable
    ? target.textContent || ""
    : (target as HTMLInputElement | HTMLTextAreaElement).value || "";
  const words = [...original.matchAll(/[\w'’]+/g)];
  const remove = [];
  for (const match of words) {
    const raw = match[0];
    const digest = await researcherTokenDigest(raw);
    if (!digest) continue;
    if (researcherPolicy.blocked.has(digest)) {
      remove.push(raw);
      continue;
    }
    const rule = researcherPolicy.contextual.find((item) => item.term_hash === digest);
    if (!rule) continue;
    if (
      rule.allow_title_case &&
      raw === raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase() &&
      raw !== raw.toLowerCase()
    )
      continue;
    const index = words.indexOf(match);
    const surrounding = words
      .slice(Math.max(0, index - 3), index + 4)
      .map((item) => normalizeResearcherToken(item[0]))
      .join(" ");
    if (
      (rule.allow_if_surrounding || []).some((marker: string) =>
        surrounding.includes(normalizeResearcherToken(marker)),
      )
    )
      continue;
    const before = normalizeResearcherToken(
      original.slice(Math.max(0, match.index - 20), match.index),
    );
    if (
      (rule.allow_if_before_markers || []).some((marker: string) =>
        before.includes(normalizeResearcherToken(marker)),
      )
    )
      continue;
    remove.push(raw);
  }
  if (!remove.length) return;
  let filtered = original;
  for (const token of remove)
    filtered = filtered.replace(
      new RegExp(`\\b${token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`),
      "",
    );
  filtered = filtered.replace(/ {2,}/g, " ");
  if (target.isContentEditable) target.textContent = filtered;
  else (target as HTMLInputElement | HTMLTextAreaElement).value = filtered;
  target.dispatchEvent(new Event("change", { bubbles: true }));
  const now = Date.now();
  if (now - researcherPolicyToastAt > 1200) {
    researcherPolicyToastAt = now;
    toast(tr("content_filter.warning"), { tone: "warning" });
  }
}
// Registered on import, as the runtime did; the runtime imports this module.
document.addEventListener(
  "input",
  (event) => {
    void filterResearcherInputElement(event.target);
  },
  true,
);
