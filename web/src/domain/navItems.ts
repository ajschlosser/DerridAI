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

import { viewConfig } from "./runtimeConstants";
import { canAccessPage, isResearcher } from "./sharedSession";
import { tr } from "./sharedTranslate";
import { dbUnavailableReason, hasChromaService } from "./storeAvailability";

export function viewDisabledReason(view: string): string {
  if (!canAccessPage(view)) return tr("runtime.disabled.admin_only");
  if (view === "vector" && isResearcher() && !hasChromaService()) return dbUnavailableReason();
  if (view === "faq" && !hasChromaService()) return tr("runtime.disabled.response_library_chroma");
  return "";
}
function translatedNavLabel(item: { id: string; label: string }) {
  const keys: Record<string, string> = {
    home: "nav.dashboard",
    list: "nav.records",
    record: "nav.record",
    works: "nav.works",
    global: "nav.search",
    annotations: "nav.annotations",
    semanticmap: "nav.semantic_map",
    pdf: "nav.pdf",
    compare: "nav.compare",
    vector: "nav.vector",
    rag: "nav.rag",
    faq: "nav.faq",
    responsecache: "runtime.system_data",
    providers: "nav.providers",
    schemas: "nav.schemas",
    config: "nav.config",
  };
  return keys[item.id] ? tr(keys[item.id], item.label) : item.label;
}
function translatedSectionLabel(section: string) {
  const keys: Record<string, string> = {
    Overview: "section.overview",
    Corpus: "section.corpora",
    Corpora: "section.corpora",
    Research: "section.research",
    Tools: "section.corpus_management",
    Build: "section.corpus_management",
    "Corpus Management": "section.corpus_management",
    "AI & Automation": "section.ai_automation",
    System: "section.system",
  };
  return keys[section] ? tr(keys[section], section) : section;
}
// Navigation membership depends only on the signed-in user, the static view list,
// and translations, never on workspace/bootstrap state. The Vue shell calls this as
// soon as a user exists so the menu is complete before the slow runtime bootstrap.
export function getNavItems() {
  return viewConfig
    .filter((item) => canAccessPage(item.id))
    .map((item) => ({
      ...item,
      label:
        item.id === "home"
          ? tr("nav.home")
          : isResearcher() && item.id === "vector"
            ? tr("research.corpus_search")
            : translatedNavLabel(item),
      section: translatedSectionLabel(item.section),
      disabledReason: viewDisabledReason(item.id),
    }));
}
