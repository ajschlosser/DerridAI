/* Copyright 2026 Aaron John Schlosser, PhD. */
import { FIELD_LABELS } from "./runtimeConstants";

// Field labels, value display and the parsers that report errors by field label. Moved verbatim from the
// legacy runtime; translation is passed in.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  tr: (key: string, fallback?: string) => string;
}

export function createFieldFormatting(deps: Deps) {
  const { tr } = deps;
  const label = (key: string): string =>
    tr(
      `field.${key}`,
      (FIELD_LABELS as Record<string, string>)[key] ||
        key.replaceAll("_", " ").replace(/\b\w/g, (m: string) => m.toUpperCase()),
    );
  const display = (value: unknown): string => {
    if (value === null || value === undefined || value === "") return "—";
    if (Array.isArray(value))
      return value.length
        ? value.map((v) => (typeof v === "object" ? JSON.stringify(v) : String(v))).join(", ")
        : "—";
    if (typeof value === "object") return JSON.stringify(value);
    if (typeof value === "boolean")
      return value ? tr("runtime.yes") : tr("runtime.no");
    return String(value);
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function normalizeRagGrade(value: any) {
    let grade = value;
    if (grade && typeof grade === "object" && !Array.isArray(grade)) {
      if (grade.grade && typeof grade.grade === "object" && !Array.isArray(grade.grade))
        grade = grade.grade;
      else if (grade.result && typeof grade.result === "object" && !Array.isArray(grade.result))
        grade = grade.result;
    }
    if (!grade || typeof grade !== "object" || Array.isArray(grade))
      grade = { summary: grade == null ? "" : String(grade) };
    const scores =
      grade.scores && typeof grade.scores === "object" && !Array.isArray(grade.scores)
        ? grade.scores
        : {};
    const list = (value: unknown): string[] => {
      if (value == null || value === "") return [];
      if (Array.isArray(value)) return value.flatMap((item) => list(item));
      if (typeof value === "object")
        return Object.entries(value).map(([key, item]) => `${label(key)}: ${display(item)}`);
      return [String(value)];
    };
    const score = (key: string): unknown => {
      const raw = grade[key] ?? scores[key];
      if (raw == null || raw === "") return "—";
      if (typeof raw === "object") {
        const nested = raw.score ?? raw.value ?? raw.rating;
        return nested == null ? display(raw) : nested;
      }
      return raw;
    };
    return {
      raw: grade,
      score,
      summary: String(grade.summary ?? grade.overall_summary ?? grade.assessment ?? ""),
      strengths: list(grade.strengths ?? grade.strength),
      weaknesses: list(grade.weaknesses ?? grade.weakness),
      unsupported_or_risky_claims: list(
        grade.unsupported_or_risky_claims ?? grade.risky_claims ?? grade.unsupported_claims,
      ),
    };
  }
  function parseBulkFieldValue(field: string, raw: unknown, rows: Loose[]) {
    const sample = rows
      .map((row) => row.record?.[field])
      .find((value) => value !== undefined && value !== null);
    const text = String(raw ?? "");
    if (text.trim() === "__NULL__") return null;
    if (typeof sample === "boolean") {
      const token = text.trim().toLowerCase();
      if (["true", "1", "yes", "on"].includes(token)) return true;
      if (["false", "0", "no", "off"].includes(token)) return false;
      throw new Error(`Enter true or false for ${label(field)}.`);
    }
    if (typeof sample === "number") {
      const value = Number(text);
      if (!Number.isFinite(value)) throw new Error(`${label(field)} requires a number.`);
      return value;
    }
    if (Array.isArray(sample) || (sample && typeof sample === "object")) {
      try {
        const value = JSON.parse(text);
        if (Array.isArray(sample) && !Array.isArray(value)) throw new Error("Expected JSON array.");
        if (!Array.isArray(sample) && (Array.isArray(value) || !value || typeof value !== "object"))
          throw new Error("Expected JSON object.");
        return value;
      } catch (error) {
        throw new Error(`${label(field)} requires valid JSON: ${(error as Error).message}`);
      }
    }
    return text;
  }
  function parseWorkMetadataValue(field: string, control: { value: string }, rows: Loose[]) {
    const exemplar = rows
      .map((row) => row.record[field])
      .find((value) => value !== undefined && value !== null);
    const raw = control.value;
    if (typeof exemplar === "boolean" || field === "document_is_translation") {
      if (raw === "") return null;
      return raw === "true";
    }
    if (Array.isArray(exemplar) || (exemplar && typeof exemplar === "object")) {
      const parsed = JSON.parse(raw || "null");
      if (exemplar && Array.isArray(exemplar) && !Array.isArray(parsed))
        throw new Error(`${label(field)} must be a JSON array.`);
      return parsed;
    }
    if (typeof exemplar === "number" || ["year", "publication_year"].includes(field)) {
      if (raw.trim() === "") return null;
      const value = Number(raw);
      if (!Number.isFinite(value)) throw new Error(`${label(field)} must be numeric.`);
      return value;
    }
    return raw;
  }
  return { label, display, normalizeRagGrade, parseBulkFieldValue, parseWorkMetadataValue };
}
