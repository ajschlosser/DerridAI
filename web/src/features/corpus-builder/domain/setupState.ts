/* Copyright 2026 Aaron John Schlosser, PhD. */
import { hasPages } from "../../../domain/sourceMedia";
import type { PresentationText } from "./workflowPresentation";

export type CorpusSetupSectionId = "source" | "structure" | "metadata" | "enrichment" | "advanced";

export const CORPUS_SETUP_SECTIONS: readonly CorpusSetupSectionId[] = [
  "source",
  "structure",
  "metadata",
  "enrichment",
  "advanced",
] as const;

export interface CorpusSetupIssue {
  id: string;
  section: CorpusSetupSectionId;
  severity: "blocking" | "warning";
  message: string;
}

export interface CorpusSetupSectionState {
  id: CorpusSetupSectionId;
  state: "incomplete" | "complete" | "warning" | "optional";
  summary: string;
}

export interface CorpusSetupInput {
  asset: {
    filename: string;
    media_kind?: string;
    page_count?: number;
    block_count?: number | null;
    /** Time-based media only. */
    duration_seconds?: number;
  } | null;
  /** Source has printed-page structure the reviewer is expected to confirm before building. */
  structureNeedsReview: boolean;
  structureSummary: string;
  recordSizingValid: boolean;
  targetChars: number;
  toleranceChars: number;
  schemaName: string;
  schemaVersion: string;
  guidanceFieldCount: number;
  missingDocumentFieldCount: number;
  providerLabel: string;
  modelLabel: string;
  enrichmentMode: "fast" | "deep";
  documentIntelligenceProfile: string;
  /** Builds already running against the selected provider profile. */
  profileActiveBuildCount: number;
  contextSafe: boolean;
}

const MEDIA_LABELS: Record<string, string> = {
  pdf: "PDF",
  image: "Image",
  audio: "Audio",
  text: "Text",
  rtf: "RTF",
  docx: "DOCX",
  html: "HTML",
  url: "URL",
  gutenberg: "Gutenberg",
};

function mediaLabel(kind: string | undefined, text: PresentationText): string {
  const key = String(kind || "").toLowerCase();
  return text.t(`pdf_corpus.setup.media.${key}`, MEDIA_LABELS[key] || key.toUpperCase());
}

/** Problems with the current setup, each attached to the section that can fix it. */
export function corpusSetupIssues(
  input: CorpusSetupInput,
  text: PresentationText,
): CorpusSetupIssue[] {
  const issues: CorpusSetupIssue[] = [];
  if (!input.asset) {
    issues.push({
      id: "source_missing",
      section: "source",
      severity: "blocking",
      message: text.t("pdf_corpus.setup.issue.choose_source", "Choose a source to continue"),
    });
  }
  if (input.structureNeedsReview) {
    issues.push({
      id: "structure_review",
      section: "structure",
      severity: "warning",
      message: text.t("pdf_corpus.readiness.review_structure"),
    });
  }
  if (!input.recordSizingValid) {
    issues.push({
      id: "record_sizing_invalid",
      section: "structure",
      severity: "blocking",
      message: text.t("pdf_corpus.record_sizing.invalid"),
    });
  }
  if (input.asset && input.missingDocumentFieldCount > 0) {
    issues.push({
      id: "document_fields_missing",
      section: "metadata",
      severity: "warning",
      message: text.tf("pdf_corpus.setup.issue.document_fields", {
        count: input.missingDocumentFieldCount,
      }),
    });
  }
  if (input.profileActiveBuildCount > 0) {
    issues.push({
      id: "profile_busy",
      section: "enrichment",
      severity: "warning",
      message: text.tf("pdf_corpus.profile_active_builds", {
        count: input.profileActiveBuildCount,
      }),
    });
  }
  if (!input.contextSafe) {
    issues.push({
      id: "context_unsafe",
      section: "advanced",
      severity: "blocking",
      message: text.t("pdf_corpus.context_unsafe"),
    });
  }
  return issues;
}

/** The blocking issue to surface first, in setup order. */
export function firstBlockingIssue(issues: CorpusSetupIssue[]): CorpusSetupIssue | null {
  for (const section of CORPUS_SETUP_SECTIONS) {
    const found = issues.find(
      (issue) => issue.section === section && issue.severity === "blocking",
    );
    if (found) return found;
  }
  return null;
}

export function corpusSetupSectionStates(
  input: CorpusSetupInput,
  issues: CorpusSetupIssue[],
  text: PresentationText,
): CorpusSetupSectionState[] {
  const has = (section: CorpusSetupSectionId, severity?: CorpusSetupIssue["severity"]) =>
    issues.some((issue) => issue.section === section && (!severity || issue.severity === severity));
  const asset = input.asset;
  const summaries: Record<CorpusSetupSectionId, string> = {
    source: asset
      ? [
          asset.filename,
          mediaLabel(asset.media_kind, text),
          // Page semantics belong to paginated media only.
          hasPages(asset.media_kind) && Number(asset.page_count || 0) > 0
            ? text.tf("pdf_corpus.setup.summary.pages", { count: Number(asset.page_count) })
            : Number(asset.duration_seconds || 0) > 0
              ? text.tf("pdf_corpus.setup.summary.minutes", {
                  count: Math.max(1, Math.round(Number(asset.duration_seconds) / 60)),
                })
              : Number(asset.block_count || 0) > 0
                ? text.tf("pdf_corpus.setup.summary.blocks", { count: Number(asset.block_count) })
                : "",
        ]
          .filter(Boolean)
          .join(" · ")
      : text.t("pdf_corpus.setup.summary.no_source", "No source selected"),
    structure: !asset
      ? text.t("pdf_corpus.setup.summary.structure_waiting", "Choose a source first")
      : [
          hasPages(asset.media_kind) ? input.structureSummary : "",
          input.targetChars
            ? text.tf("pdf_corpus.readiness.sizing", {
                target: input.targetChars.toLocaleString(),
                tolerance: input.toleranceChars.toLocaleString(),
              })
            : "",
        ]
          .filter(Boolean)
          .join(" · ") || text.t("pdf_corpus.setup.summary.structure_source_interpretation"),
    metadata: [
      input.schemaName || text.t("pdf_corpus.setup.summary.schema_default", "Default schema"),
      input.schemaVersion ? `v${input.schemaVersion}` : "",
      input.guidanceFieldCount
        ? text.tf("pdf_corpus.setup.summary.guidance", { count: input.guidanceFieldCount })
        : "",
      input.missingDocumentFieldCount
        ? text.tf("pdf_corpus.setup.summary.document_fields", {
            count: input.missingDocumentFieldCount,
          })
        : "",
    ]
      .filter(Boolean)
      .join(" · "),
    enrichment: [
      input.providerLabel || text.t("pdf_corpus.provider_default"),
      input.modelLabel,
      input.enrichmentMode === "deep"
        ? text.t("pdf_corpus.enrichment_deep")
        : text.t("pdf_corpus.enrichment_fast"),
      // Off is the absence of Document Intelligence, so it adds nothing to the summary.
      input.documentIntelligenceProfile && input.documentIntelligenceProfile !== "none"
        ? `${text.t("pdf_corpus.document_intelligence")}: ${text.t(
            `pdf_corpus.document_intelligence_${input.documentIntelligenceProfile}`,
          )}`
        : "",
    ]
      .filter(Boolean)
      .join(" · "),
    advanced: text.t("pdf_corpus.setup.summary.advanced", "Run policy defaults"),
  };
  return CORPUS_SETUP_SECTIONS.map((id) => {
    let state: CorpusSetupSectionState["state"];
    if (id === "advanced")
      state = has(id, "blocking") ? "incomplete" : has(id, "warning") ? "warning" : "optional";
    else if (id === "source") state = asset ? "complete" : "incomplete";
    else if (!asset && id === "structure") state = "incomplete";
    else if (has(id, "blocking")) state = "incomplete";
    else if (has(id, "warning")) state = "warning";
    else state = "complete";
    return { id, state, summary: summaries[id] };
  });
}
