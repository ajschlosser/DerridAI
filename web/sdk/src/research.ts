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

import { formatCitation } from "./citations";
import { EventBus } from "./events";
import { isAbortError } from "./errors";
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

function optionalText(value: unknown): string | undefined {
  return value == null || value === "" ? undefined : String(value);
}

function evidenceRef(
  manifest: PublicationManifest,
  record: SearchResponse["results"][number]["record"],
  index: number,
): EvidenceRef {
  return {
    evidenceId: `E${index + 1}`,
    recordId: String(record.record_id),
    recordRevision: optionalText(record.record_revision),
    publicationId: manifest.publication_id,
    work: optionalText(record.work),
    citation: formatCitation(record).plain,
    text: String(record.text ?? ""),
    documentAuthor: optionalText(record.document_author),
    speaker: optionalText(record.speaker),
    quotedSpeaker: optionalText(record.quoted_speaker),
    quotedAuthor: optionalText(record.quoted_author),
    quotedWork: optionalText(record.quoted_work),
    positionHolder: optionalText(record.position_holder),
    stance: optionalText(record.stance),
    target: optionalText(record.target),
    discourseRole: optionalText(record.discourse_role),
    propositionStatus: optionalText(record.proposition_status),
  };
}

function normalizedScopeText(value: unknown): string {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase("en-US")
    .replace(/[’']s\b/gu, "")
    .replace(/[’']/gu, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function mentionsAuthor(question: string, author: string): boolean {
  const query = normalizedScopeText(question);
  const normalizedAuthor = normalizedScopeText(author);
  if (!query || !normalizedAuthor) return false;
  if (query.includes(normalizedAuthor)) return true;
  const authorParts = normalizedAuthor.split(/\s+/).filter(Boolean);
  const surname = authorParts[authorParts.length - 1];
  return Boolean(surname && surname.length >= 4 && new Set(query.split(/\s+/)).has(surname));
}

function mentionedWorkGroups(manifest: PublicationManifest, question: string): string[][] {
  const query = normalizedScopeText(question);
  if (!query) return [];

  const groups: string[][] = [];
  const authorWorks = new Map<string, Set<string>>();

  for (const summary of manifest.works ?? []) {
    const work = String(summary.work ?? "").trim();
    if (!work) continue;
    const normalizedWork = normalizedScopeText(work);
    if (normalizedWork && query.includes(normalizedWork)) groups.push([work]);

    for (const rawAuthor of summary.authors ?? []) {
      const author = String(rawAuthor ?? "").trim();
      if (!author || !mentionsAuthor(question, author)) continue;
      const key = normalizedScopeText(author);
      const works = authorWorks.get(key) ?? new Set<string>();
      works.add(work);
      authorWorks.set(key, works);
    }
  }

  for (const works of authorWorks.values()) groups.push([...works]);

  const distinct: string[][] = [];
  for (const works of groups.map((group) => [...new Set(group)].sort())) {
    if (!works.length) continue;
    if (distinct.some((existing) => existing.some((work) => works.includes(work)))) continue;
    distinct.push(works);
    if (distinct.length === 4) break;
  }
  return distinct;
}

function publicationScope(manifest: PublicationManifest): string {
  const works = manifest.works ?? [];
  const visible = works.slice(0, 40).map((summary) => {
    const authors = (summary.authors ?? []).map(String).filter(Boolean);
    return `- ${summary.work}${authors.length ? ` — ${authors.join(", ")}` : ""}`;
  });
  if (works.length > visible.length) {
    visible.push(`- … ${works.length - visible.length} additional works`);
  }
  return visible.join("\n");
}

function prompt(question: string, packet: EvidencePacket, manifest: PublicationManifest): string {
  const evidence = packet.evidence
    .map(
      (item) => `[${item.evidenceId}] ${item.citation}
Record ID: ${item.recordId}
Record revision: ${item.recordRevision ?? ""}
Document author: ${item.documentAuthor ?? ""}
Speaker: ${item.speaker ?? ""}
Quoted speaker: ${item.quotedSpeaker ?? ""}
Quoted author: ${item.quotedAuthor ?? ""}
Quoted work: ${item.quotedWork ?? ""}
Position holder: ${item.positionHolder ?? ""}
Stance: ${item.stance ?? ""}
Target: ${item.target ?? ""}
Discourse role: ${item.discourseRole ?? ""}
Proposition status: ${item.propositionStatus ?? ""}
TEXT:
${item.text}`,
    )
    .join("\n\n");

  return `Answer the research question using only the supplied evidence for substantive claims. Preserve attribution: distinguish document author, passage speaker, quoted speaker/author/work, position holder, stance, target, discourse role, and proposition status. Do not equate document authorship with proposition ownership, and do not assign a quoted, reconstructed, analyzed, endorsed, questioned, or criticized position to the source author unless the evidence supports that attribution. Cite evidence IDs such as [E1]. If the evidence is insufficient, say so rather than inventing support.

The publication inventory below is authoritative only for which works/authors are present in this published corpus. It is not substantive evidence and must not be cited. Do not claim that an author or work is absent from the publication merely because it is absent from the retrieved evidence packet.

Publication inventory:
${publicationScope(manifest)}

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

    const retrievalLimit = request.retrieval?.limit ?? 24;
    const evidenceLimit = request.retrieval?.evidenceLimit ?? 10;
    const retrievalMode = request.retrieval?.mode ?? "hybrid";
    const filters = request.retrieval?.filters;
    const retrieval = await this.searchEngine.search(
      {
        query: question,
        mode: retrievalMode,
        filters,
        limit: retrievalLimit,
        fetchLimit: request.retrieval?.fetchLimit,
        signal: request.signal,
      },
      runId,
    );

    // Named authors and works are deterministic corpus-scope signals, not semantic claims.
    // Reserve one evidence slot for a named in-publication scope when broad retrieval missed it,
    // while retaining the broader result set for comparison/cross-author questions.
    const hasExplicitWorkFilter = Boolean(
      filters?.work && (!Array.isArray(filters.work) || filters.work.length),
    );
    const scopeSeeds: SearchResponse["results"] = [];
    if (!hasExplicitWorkFilter) {
      const seededIds = new Set<string>();
      for (const [index, works] of mentionedWorkGroups(this.manifest, question).entries()) {
        let seed = retrieval.results.find(
          (item) =>
            works.includes(String(item.record.work ?? "")) &&
            !seededIds.has(String(item.record.record_id)),
        );
        if (!seed) {
          const scoped = await this.searchEngine.search(
            {
              query: question,
              mode: retrievalMode,
              filters: { ...(filters ?? {}), work: works },
              limit: Math.min(4, retrievalLimit),
              fetchLimit: request.retrieval?.fetchLimit,
              signal: request.signal,
            },
            `${runId}-scope-${index + 1}`,
          );
          seed = scoped.results.find((item) => !seededIds.has(String(item.record.record_id)));
        }
        if (!seed) continue;
        scopeSeeds.push(seed);
        seededIds.add(String(seed.record.record_id));
      }
    }

    if (scopeSeeds.length) {
      const seedIds = new Set(scopeSeeds.map((item) => String(item.record.record_id)));
      retrieval.results = [
        ...scopeSeeds,
        ...retrieval.results.filter((item) => !seedIds.has(String(item.record.record_id))),
      ]
        .slice(0, retrievalLimit)
        .map((item, index) => ({ ...item, rank: index + 1 }));
    }

    const reserved = scopeSeeds.slice(0, evidenceLimit);
    const reservedIds = new Set(reserved.map((item) => String(item.record.record_id)));
    const selected = [
      ...reserved,
      ...this.searchEngine.diversify(
        retrieval.results.filter((item) => !reservedIds.has(String(item.record.record_id))),
        Math.max(0, evidenceLimit - reserved.length),
        request.retrieval?.mmrLambda ?? 0.72,
      ),
    ].map((item, index) => ({ ...item, rank: index + 1 }));
    const evidencePacket: EvidencePacket = {
      publicationId: this.manifest.publication_id,
      evidence: selected.map((item, index) => evidenceRef(this.manifest, item.record, index)),
    };
    this.events.emit({
      type: "evidence-selected",
      runId,
      evidenceCount: evidencePacket.evidence.length,
    });

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

    this.events.emit({
      type: "generation-start",
      runId,
      evidenceCount: evidencePacket.evidence.length,
    });
    try {
      const generated = await this.generation.generate(
        {
          prompt: prompt(question, evidencePacket, this.manifest),
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
      if (isAbortError(error)) throw error;
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
