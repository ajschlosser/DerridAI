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

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Parses a JSON or JSONL record pasted into the Compare view, moved verbatim from the legacy runtime.

export function parsePastedRecord(value: unknown): Loose | null {
  let text = String(value || "").trim();
  if (!text) return null;
  text = text
    .replace(/^```(?:json|jsonl)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      if (
        parsed.length !== 1 ||
        !parsed[0] ||
        typeof parsed[0] !== "object" ||
        Array.isArray(parsed[0])
      ) {
        throw new Error("Paste exactly one JSON record, not an array of multiple records.");
      }
      return parsed[0];
    }
    if (!parsed || typeof parsed !== "object")
      throw new Error("Pasted value is not a JSON object.");
    return parsed;
  } catch (error) {
    const lines = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    const parsedLines = [];
    for (const line of lines) {
      try {
        parsedLines.push(JSON.parse(line));
      } catch {
        throw error;
      }
    }
    if (
      parsedLines.length !== 1 ||
      !parsedLines[0] ||
      typeof parsedLines[0] !== "object" ||
      Array.isArray(parsedLines[0])
    ) {
      throw new Error("Paste exactly one JSON/JSONL record on each side.");
    }
    return parsedLines[0];
  }
}
