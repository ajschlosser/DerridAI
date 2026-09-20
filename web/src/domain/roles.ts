/* Copyright 2026 Aaron John Schlosser, PhD. */
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
  return capabilityIds.filter(id => allowed.has(id));
}

export function groupCapabilities(capabilities: CapabilityDefinition[]): CapabilityGroup[] {
  const byCategory = new Map<string, CapabilityDefinition[]>();
  for (const capability of capabilities) {
    const list = byCategory.get(capability.category) || [];
    list.push(capability);
    byCategory.set(capability.category, list);
  }
  return [...byCategory.entries()].map(([category, items]) => ({category, items}));
}

export function categorySlug(category: string): string {
  return category.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "other";
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
  capability: {id: string; label: string; description: string},
  needle: string,
): boolean {
  const query = needle.trim().toLowerCase();
  if (!query) return true;
  return [capability.id, capability.label, capability.description].some(value => value.toLowerCase().includes(query));
}
