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

// Which capability each legacy runtime view needs, and the rule for whether a user holds one. Pure, so navigation can
// ask without the runtime's state object.
export type CapabilityUser = { role?: string; capabilities?: readonly string[] } | null | undefined;

export const pageCapabilities: Readonly<Record<string, string>> = {
  home: "page.dashboard",
  list: "page.records",
  record: "page.record",
  works: "page.works",
  global: "page.search",
  annotations: "page.annotations",
  semanticmap: "page.semantic_map",
  pdf: "page.pdf",
  compare: "page.compare",
  vector: "page.vector",
  rag: "page.research",
  faq: "page.faq",
  responsecache: "page.response_cache",
  providers: "page.providers",
  schemas: "page.schemas",
  config: "page.settings",
};

export function userHasCapability(user: CapabilityUser, capability: string): boolean {
  if (!user) return false;
  if (user.role === "admin") return true;
  const capabilities = new Set(user.capabilities || []);
  return capabilities.has("*") || capabilities.has(capability);
}

export function canAccessView(user: CapabilityUser, view: string): boolean {
  const capability = pageCapabilities[view];
  return !capability || userHasCapability(user, capability);
}
