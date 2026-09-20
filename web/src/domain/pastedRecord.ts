/* Copyright 2026 Aaron John Schlosser, PhD. */
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
