/* Copyright 2026 Aaron John Schlosser, PhD. */
/**
 * Pure Corpus Capture review logic: which wizard step a stored capture resumes at, how candidates
 * group into works and languages, and what the acquisition outcome is. Grouping never merges:
 * every candidate stays its own row with its own selection and acquisition state.
 */
import type { CaptureCandidate, CaptureOptions, CorpusCapture } from "../api/corpus";
import { languageName } from "./languages";

export type CaptureStep = "author" | "options" | "discovering" | "review" | "acquiring" | "done";

/** The step a reopened capture belongs on, from its durable status. */
export function stepForCapture(
  capture: Pick<CorpusCapture, "status" | "discovery_completed_at" | "active_job">,
): CaptureStep {
  const discovered = Boolean(capture.discovery_completed_at);
  if (capture.active_job)
    return capture.active_job.mode === "acquire" || capture.active_job.mode === "retry"
      ? "acquiring"
      : "discovering";
  switch (capture.status) {
    case "awaiting_review":
      return "review";
    case "acquiring":
      return "acquiring";
    case "partial":
    case "complete":
      return "done";
    case "discovering":
      return "discovering";
    default:
      // draft, interrupted, cancelled, failed: review what was found, or show discovery to restart it.
      return discovered ? "review" : "discovering";
  }
}

/** Include checkboxes in the options step, mapped onto the capture contract. */
export interface CaptureIncludes {
  authored: boolean;
  translations: boolean;
  translator: boolean;
  editor: boolean;
  other: boolean;
}

export function optionsFromIncludes(
  providers: CaptureOptions["providers"],
  includes: CaptureIncludes,
  languages: string[] | null,
): CaptureOptions {
  const roles: CaptureOptions["roles"] = [];
  if (includes.authored || includes.translations) roles.push("author", "coauthor");
  if (includes.translator) roles.push("translator");
  if (includes.editor) roles.push("editor");
  if (includes.other) roles.push("contributor");
  return {
    providers,
    roles,
    include_translations: includes.translations,
    include_originals: includes.authored,
    languages: languages && languages.length ? languages : null,
  };
}

export function includesFromOptions(options: CaptureOptions): CaptureIncludes {
  const roles = new Set(options.roles);
  return {
    authored: roles.has("author") || roles.has("coauthor"),
    translations: options.include_translations,
    translator: roles.has("translator"),
    editor: roles.has("editor"),
    other: roles.has("contributor"),
  };
}

export interface LanguageGroup {
  key: string;
  codes: string[];
  label: string;
  items: CaptureCandidate[];
}
export interface WorkGroup {
  workId: string;
  title: string;
  /** How the group was formed (exact identity, title match needing review, or a lone source). */
  status: CaptureCandidate["reconciliation_status"];
  languages: LanguageGroup[];
  items: CaptureCandidate[];
}

function languageKey(candidate: CaptureCandidate) {
  return [...(candidate.document_languages || [])].sort().join("+") || "und";
}

/**
 * Candidates grouped by `canonical_work_id`, then by document language. Originals come before
 * translations within a work so a reader sees the source text first; groups keep discovery order.
 */
export function groupCandidates(
  candidates: readonly CaptureCandidate[],
  locale = "en",
  unknownLanguage = "und",
): WorkGroup[] {
  const works = new Map<string, WorkGroup>();
  for (const candidate of candidates) {
    const workId = candidate.canonical_work_id || `cand:${candidate.candidate_id}`;
    let work = works.get(workId);
    if (!work) {
      work = {
        workId,
        title: candidate.title,
        status: candidate.reconciliation_status,
        languages: [],
        items: [],
      };
      works.set(workId, work);
    }
    work.items.push(candidate);
    if (candidate.reconciliation_status === "possible_match") work.status = "possible_match";
    const key = languageKey(candidate);
    let language = work.languages.find((group) => group.key === key);
    if (!language) {
      const codes = key === "und" ? [] : key.split("+");
      language = {
        key,
        codes,
        label: codes.length
          ? codes.map((code) => languageName(code, locale)).join(" · ")
          : unknownLanguage,
        items: [],
      };
      work.languages.push(language);
    }
    language.items.push(candidate);
  }
  for (const work of works.values()) {
    const original = work.items.find(
      (item) => item.relationship_to_work === "original_language_edition",
    );
    if (original) work.title = original.title;
    const rank = (group: LanguageGroup) =>
      group.items.some((item) => item.relationship_to_work === "original_language_edition")
        ? 0
        : group.items.every((item) => item.relationship_to_work === "translation")
          ? 2
          : 1;
    work.languages.sort((a, b) => rank(a) - rank(b));
  }
  return [...works.values()];
}

export interface AcquisitionOutcome {
  registered: number;
  failed: number;
  cancelled: number;
  pending: number;
  selected: number;
  registeredSourceIds: string[];
}

export function acquisitionOutcome(candidates: readonly CaptureCandidate[]): AcquisitionOutcome {
  const outcome: AcquisitionOutcome = {
    registered: 0,
    failed: 0,
    cancelled: 0,
    pending: 0,
    selected: 0,
    registeredSourceIds: [],
  };
  for (const candidate of candidates) {
    if (candidate.selection_status === "selected") outcome.selected += 1;
    if (candidate.acquisition_status === "registered") {
      outcome.registered += 1;
      if (
        candidate.source_document_id &&
        !outcome.registeredSourceIds.includes(candidate.source_document_id)
      )
        outcome.registeredSourceIds.push(candidate.source_document_id);
    } else if (candidate.acquisition_status === "failed") outcome.failed += 1;
    else if (candidate.acquisition_status === "cancelled") outcome.cancelled += 1;
    else if (candidate.selection_status === "selected") outcome.pending += 1;
  }
  return outcome;
}

/** Candidates that a new "Capture selected" run would fetch (mirrors the API's acquisition queue). */
export function acquirableCount(candidates: readonly CaptureCandidate[]): number {
  return candidates.filter(
    (candidate) =>
      candidate.selection_status === "selected" &&
      ["pending", "failed", "cancelled"].includes(candidate.acquisition_status),
  ).length;
}
