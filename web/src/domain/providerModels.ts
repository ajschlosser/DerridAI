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

// Which of an endpoint's models fit a "kind" the reviewer chose. The endpoint only reports names, so the kind is a
// judgement from the name; it narrows the list, it does not promise anything about the model.
export type ModelKind = "any" | "general" | "reasoning" | "coding" | "fast";
export const MODEL_KINDS: ModelKind[] = ["any", "general", "reasoning", "coding", "fast"];
const PATTERNS: Record<Exclude<ModelKind, "any">, string[]> = {
  reasoning: ["reason", "deepseek", "r1", "qwq", "o1", "o3", "thinking"],
  coding: ["code", "coder", "codex", "devstral", "starcoder"],
  fast: ["mini", "small", "flash", "haiku", "fast", "3b", "4b", "7b", "8b"],
  general: ["gpt", "gemma", "llama", "qwen", "mistral", "claude", "general", "chat"],
};
export function modelMatchesKind(name: string, kind: string | undefined): boolean {
  if (!kind || kind === "any") return true;
  const value = name.toLocaleLowerCase();
  return (PATTERNS[kind as Exclude<ModelKind, "any">] ?? []).some((token) => value.includes(token));
}
export interface DiscoveredModel {
  name?: string;
  parameter_size?: string;
  quantization_level?: string;
}
