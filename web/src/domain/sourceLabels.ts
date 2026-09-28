/* Copyright 2026 Aaron John Schlosser, PhD. */
/**
 * User-facing labels and status tones for Corpus Capture and Sources enums. Raw enum values are
 * never shown: every value maps to a translated label, and an unknown value falls back to the
 * translated "unknown" label for its kind.
 */
import type { SourceRow } from "../api/corpus";

type Translate = (key: string, fallback?: string) => string;
export type LabelKind =
  | "role"
  | "relationship"
  | "acquisition"
  | "capture_status"
  | "build_status"
  | "provider"
  | "confidence"
  | "reconciliation"
  | "phase"
  | "error";
export type Tone = "neutral" | "info" | "success" | "warning" | "danger";

const KNOWN: Record<LabelKind, readonly string[]> = {
  role: ["author", "coauthor", "translator", "editor", "contributor", "about_author", "unknown"],
  relationship: ["original_language_edition", "translation", "edition", "unknown"],
  acquisition: ["pending", "fetching", "acquired", "registered", "failed", "cancelled", "ready"],
  capture_status: [
    "draft",
    "discovering",
    "awaiting_review",
    "acquiring",
    "partial",
    "complete",
    "cancelled",
    "interrupted",
    "failed",
  ],
  build_status: ["not_built", "building", "built", "failed"],
  provider: ["gutenberg", "wikisource", "upload", "web"],
  confidence: ["exact", "probable", "needs_review"],
  reconciliation: ["exact_identity", "deterministic_match", "possible_match", "separate"],
  phase: [
    "created",
    "resolving_author",
    "discovering_gutenberg",
    "discovering_wikisource",
    "reconciling",
    "awaiting_review",
    "acquiring",
    "discover",
    "acquire",
    "retry",
    "refresh",
  ],
  error: [
    "provider_unavailable",
    "rate_limited",
    "author_not_found",
    "ambiguous_author",
    "catalog_unavailable",
    "invalid_provider_response",
    "source_not_found",
    "unsupported_source",
    "source_too_large",
    "network_timeout",
    "identity_mismatch",
    "acquisition_failed",
    "registration_failed",
    "cancelled",
  ],
};

export function enumLabel(t: Translate, kind: LabelKind, value: string | null | undefined): string {
  const id = String(value || "unknown");
  if (KNOWN[kind].includes(id)) return t(`capture.${kind}.${id}`);
  if (kind === "phase" || kind === "capture_status") return t("capture.phase.working");
  if (kind === "error") return t("capture.error.unknown");
  if (kind === "provider") return t("capture.provider.other");
  return t(`capture.${kind}.unknown`);
}

const TONES: Partial<Record<LabelKind, Record<string, Tone>>> = {
  acquisition: {
    registered: "success",
    ready: "success",
    failed: "danger",
    fetching: "info",
    acquired: "info",
    cancelled: "warning",
  },
  capture_status: {
    complete: "success",
    partial: "warning",
    interrupted: "warning",
    cancelled: "warning",
    failed: "danger",
    discovering: "info",
    acquiring: "info",
    awaiting_review: "info",
  },
  build_status: { built: "success", building: "info", failed: "danger" },
  confidence: { exact: "success", probable: "info", needs_review: "warning" },
  reconciliation: { possible_match: "warning" },
};

export function enumTone(kind: LabelKind, value: string | null | undefined): Tone {
  return TONES[kind]?.[String(value || "")] ?? "neutral";
}

/** A capture that is still running a discovery or acquisition job. */
export function captureIsActive(status: string | null | undefined): boolean {
  return status === "discovering" || status === "acquiring";
}

/** "Translation · tr. Thomas Common" — edition facts for a source row, or "" when none are known. */
export function editionLine(
  t: Translate,
  row: Pick<SourceRow, "relationship_to_work" | "edition" | "translator">,
): string {
  const parts: string[] = [];
  if (row.relationship_to_work && row.relationship_to_work !== "unknown")
    parts.push(enumLabel(t, "relationship", row.relationship_to_work));
  if (row.translator) parts.push(`${t("capture.translated_by")} ${row.translator}`);
  if (row.edition) parts.push(row.edition);
  return parts.join(" · ");
}
