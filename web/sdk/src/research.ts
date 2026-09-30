// Copyright 2026 Aaron John Schlosser, PhD.

import { formatCitation } from "./citations";
import { EventBus } from "./events";
import { SearchEngine } from "./search";
import type {
  EvidencePacket,
  EvidenceRef,
  GenerationProvider,
  PublicationManifest,
  ResearchRequest,
  ResearchResponse,
  ResearchWarning,
  SearchResponse,
} from "./types";

function evidenceRef(
  manifest: PublicationManifest,
  record: SearchResponse["results"][number]["record"],
  index: number,
): EvidenceRef {
  return {
    evidenceId: `E${index + 1}`,
    recordId: String(record.record_id),
    recordRevision: record.record_revision == null ? undefined : String(record.record_revision),
    publicationId: manifest.publication_id,
    work: record.work == null ? undefined : String(record.work),
    citation: formatCitation(record).plain,
    text: String(record.text ?? ""),
    speaker: record.speaker == null ? undefined : String(record.speaker),
    quotedSpeaker: record.quoted_speaker == null ? undefined : String(record.quoted_speaker),
    positionHolder: record.position_holder == null ? undefined : String(record.position_holder),
    stance: record.stance == null ? undefined : String(record.stance),
    target: record.target == null ? undefined : String(record.target),
    discourseRole: record.discourse_role == null ? undefined : String(record.discourse_role),
  };
}

function prompt(question: string, packet: EvidencePacket): string {
  const evidence = packet.evidence
    .map(
      (item) => `[${item.evidenceId}] ${item.citation}
Record ID: ${item.recordId}
Record revision: ${item.recordRevision ?? ""}
Speaker: ${item.speaker ?? ""}
Quoted speaker: ${item.quotedSpeaker ?? ""}
Position holder: ${item.positionHolder ?? ""}
Stance: ${item.stance ?? ""}
Target: ${item.target ?? ""}
Discourse role: ${item.discourseRole ?? ""}
TEXT:
${item.text}`,
    )
    .join("\n\n");

  return `Answer the research question using only the supplied evidence. Preserve attribution: distinguish the passage speaker, quoted speaker, position holder, stance, target, and discourse role. Do not attribute a quoted or analyzed position to Derrida unless the evidence supports that attribution. Cite evidence IDs such as [E1]. If the evidence is insufficient, say so rather than inventing support.

Question: ${question}

Evidence:
${evidence}`;
}

export class ResearchEngine {
  constructor(
    private readonly manifest: PublicationManifest,
    private readonly searchEngine: SearchEngine,
    private readonly events: EventBus,
    private readonly generation?: GenerationProvider,
  ) {}

  async run(request: ResearchRequest, runId: string): Promise<ResearchResponse> {
    const question = String(request.question ?? "").trim();
    if (!question) throw new Error("Research question is required.");

    const retrieval = await this.searchEngine.search(
      {
        query: question,
        mode: request.retrieval?.mode ?? "hybrid",
        filters: request.retrieval?.filters,
        limit: request.retrieval?.limit ?? 24,
        signal: request.signal,
      },
      runId,
    );

    const selected = this.searchEngine.diversify(
      retrieval.results,
      request.retrieval?.evidenceLimit ?? 10,
      request.retrieval?.mmrLambda ?? 0.72,
    );
    const evidencePacket: EvidencePacket = {
      publicationId: this.manifest.publication_id,
      evidence: selected.map((item, index) => evidenceRef(this.manifest, item.record, index)),
    };

    const warnings: ResearchWarning[] = [];
    if (retrieval.warnings.length) {
      warnings.push({
        code: "semantic_fallback",
        message: retrieval.warnings.map((warning) => warning.message).join(" "),
      });
    }

    if (!evidencePacket.evidence.length) {
      return {
        runId,
        publicationId: this.manifest.publication_id,
        question,
        answer: null,
        evidencePacket,
        retrieval,
        generation: null,
        warnings,
      };
    }

    if (!this.generation) {
      warnings.push({
        code: "generation_unavailable",
        message:
          "No generation capability was supplied. The retrieved evidence packet remains available.",
      });
      return {
        runId,
        publicationId: this.manifest.publication_id,
        question,
        answer: null,
        evidencePacket,
        retrieval,
        generation: null,
        warnings,
      };
    }

    this.events.emit({ type: "generation-start", runId });
    try {
      const generated = await this.generation.generate(
        {
          prompt: prompt(question, evidencePacket),
          question,
          evidencePacket,
        },
        { signal: request.signal },
      );
      this.events.emit({ type: "generation-complete", runId });
      return {
        runId,
        publicationId: this.manifest.publication_id,
        question,
        answer: String(generated.text ?? "") || null,
        evidencePacket,
        retrieval,
        generation: generated.provider ?? this.generation.descriptor(),
        warnings,
      };
    } catch (error) {
      warnings.push({
        code: "generation_unavailable",
        message:
          error instanceof Error
            ? error.message
            : "Generation failed. The retrieved evidence packet remains available.",
      });
      return {
        runId,
        publicationId: this.manifest.publication_id,
        question,
        answer: null,
        evidencePacket,
        retrieval,
        generation: this.generation.descriptor(),
        warnings,
      };
    }
  }
}
