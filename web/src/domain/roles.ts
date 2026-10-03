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

import type { CapabilityDefinition } from "../api/auth";

export interface CapabilityGroup {
  category: string;
  items: CapabilityDefinition[];
}

export function samePermissions(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false;
  const a = [...left].sort();
  const b = [...right].sort();
  return a.every((item, index) => item === b[index]);
}

export function expandPermissions(permissions: string[], capabilityIds: string[]): string[] {
  if (permissions.includes("*")) return [...capabilityIds];
  const allowed = new Set(permissions);
  return capabilityIds.filter((id) => allowed.has(id));
}

export function groupCapabilities(capabilities: CapabilityDefinition[]): CapabilityGroup[] {
  const byCategory = new Map<string, CapabilityDefinition[]>();
  for (const capability of capabilities) {
    const list = byCategory.get(capability.category) || [];
    list.push(capability);
    byCategory.set(capability.category, list);
  }
  return [...byCategory.entries()].map(([category, items]) => ({ category, items }));
}

export function categorySlug(category: string): string {
  return (
    category
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "") || "other"
  );
}

export function capabilityLabelKey(id: string): string {
  return `roles.capability.${id}`;
}

export function capabilityHelpKey(id: string): string {
  return `roles.capability.${id}.help`;
}

export function categoryLabelKey(category: string): string {
  return `roles.category.${categorySlug(category)}`;
}

export function matchesCapabilityFilter(
  capability: { id: string; label: string; description: string },
  needle: string,
): boolean {
  const query = needle.trim().toLowerCase();
  if (!query) return true;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`, "i");
  return [capability.id, capability.label, capability.description].some((value) =>
    pattern.test(value),
  );
}
