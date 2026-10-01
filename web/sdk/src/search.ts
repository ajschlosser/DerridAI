// Copyright 2026 Aaron John Schlosser, PhD.

import { validateEmbeddingDescriptor } from "./embeddingContract";
import { EventBus } from "./events";
import { isAbortError } from "./errors";
import { RecordRepository } from "./repository";
import type {
  EmbeddingProvider,
  PublicationManifest,
  PublicationRecord,
  SearchMode,
  SearchRequest,
  SearchResponse,
  SearchResult,
  SearchWarning,
} from "./types";

interface ScoredRecord {
  record: PublicationRecord;
  score: number;
  lexicalScore?: number;
  semanticScore?: number;
}

function tokens(value: unknown, locale: string): string[] {
  return (
    String(value ?? "")
      .toLocaleLowerCase(locale)
      .match(/[\p{L}\p{N}’'_-]+/gu) ?? []
  );
}

function searchable(record: PublicationRecord): string {
  return Object.entries(record)
    .filter(([key]) => !["source_spans", "field_assertions", "updates"].includes(key))
    .map(([, value]) => {
      if (Array.isArray(value)) return value.map(String).join(" ");
      if (value && typeof value === "object") return "";
      return String(value ?? "");
    })
    .join(" ");
}

function lexicalScores(
  query: string,
  candidates: PublicationRecord[],
  locale: string,
): ScoredRecord[] {
  const queryTerms = [...new Set(tokens(query, locale))];
  if (!queryTerms.length) {
    return candidates.map((record) => ({ record, score: 0, lexicalScore: 0 }));
  }

  const docs = candidates.map((record) => {
    const body = searchable(record);
    return {
      record,
      body: body.toLocaleLowerCase(locale),
      terms: tokens(body, locale),
    };
  });
  const count = docs.length || 1;
  const averageLength = Math.max(1, docs.reduce((sum, item) => sum + item.terms.length, 0) / count);
  const documentFrequency = new Map(
    queryTerms.map((term) => [term, docs.filter((doc) => doc.terms.includes(term)).length]),
  );

  return docs
    .map((doc) => {
      const frequencies = new Map<string, number>();
      for (const term of doc.terms) {
        if (!queryTerms.includes(term)) continue;
        frequencies.set(term, (frequencies.get(term) ?? 0) + 1);
      }
      let score = 0;
      for (const term of queryTerms) {
        const tf = frequencies.get(term) ?? 0;
        if (!tf) continue;
        const df = documentFrequency.get(term) ?? 0;
        const idf = Math.log(1 + (count - df + 0.5) / (df + 0.5));
        const k1 = 1.2;
        const b = 0.75;
        score +=
          (idf * (tf * (k1 + 1))) / (tf + k1 * (1 - b + (b * doc.terms.length) / averageLength));
      }
      if (query && doc.body.includes(query.toLocaleLowerCase(locale))) score += 2.5;
      return { record: doc.record, score, lexicalScore: score };
    })
    .sort(compareScored);
}

function cosine(a?: ArrayLike<number>, b?: ArrayLike<number>): number {
  if (!a || !b || !a.length || a.length !== b.length) return -1;
  let dot = 0;
  let aa = 0;
  let bb = 0;
  for (let index = 0; index < a.length; index += 1) {
    const x = Number(a[index]);
    const y = Number(b[index]);
    dot += x * y;
    aa += x * x;
    bb += y * y;
  }
  return aa && bb ? dot / Math.sqrt(aa * bb) : -1;
}

function compareScored(left: ScoredRecord, right: ScoredRecord): number {
  if (right.score !== left.score) return right.score - left.score;
  return String(left.record.record_id).localeCompare(String(right.record.record_id));
}

function fallbackWarning(
  code: SearchWarning["code"],
  message: string,
  details?: Record<string, unknown>,
): SearchWarning {
  return { code, message, details };
}


function deduplicateRecords(records: PublicationRecord[]): {
  records: PublicationRecord[];
  duplicatesRemoved: number;
} {
  const seen = new Set<string>();
  const unique: PublicationRecord[] = [];
  for (const record of records) {
    const id = String(record.record_id);
    if (seen.has(id)) continue;
    seen.add(id);
    unique.push(record);
  }
  return { records: unique, duplicatesRemoved: records.length - unique.length };
}

export class SearchEngine {
  constructor(
    private readonly manifest: PublicationManifest,
    private readonly repository: RecordRepository,
    private readonly events: EventBus,
    private readonly embeddings?: EmbeddingProvider,
    private readonly locale = "en-US",
  ) {}

  async search(request: SearchRequest, runId: string): Promise<SearchResponse> {
    const query = String(request.query ?? "");
    const modeRequested: SearchMode = request.mode ?? "hybrid";
    const filters = request.filters ?? {};
    const limit = Math.max(1, Math.min(500, request.limit ?? 30));
    const signal = request.signal;
    this.events.emit({ type: "search-start", runId, query });

    const candidateSet = await this.repository.candidates(filters, this.locale, runId, signal);
    const deduplicated = deduplicateRecords(candidateSet.records);
    const candidates = deduplicated.records;
    const duplicatesRemoved = deduplicated.duplicatesRemoved;
    const lexical = lexicalScores(query, candidates, this.locale);
    const semanticAvailable = Boolean(
      this.manifest.features?.semantic_search && this.manifest.vector_index?.dimension,
    );

    if (modeRequested === "keyword" || !query.trim()) {
      return this.finish(
        lexical.slice(0, limit),
        modeRequested,
        "keyword",
        [],
        candidates.length,
        candidateSet.chunksLoaded,
        duplicatesRemoved,
        semanticAvailable,
        runId,
      );
    }

    if (!semanticAvailable) {
      return this.finish(
        lexical.slice(0, limit),
        modeRequested,
        "keyword",
        [
          fallbackWarning(
            "semantic_unavailable",
            "This publication has no compatible semantic vectors; keyword results were returned.",
          ),
        ],
        candidates.length,
        candidateSet.chunksLoaded,
        duplicatesRemoved,
        false,
        runId,
      );
    }

    if (!this.embeddings) {
      return this.finish(
        lexical.slice(0, limit),
        modeRequested,
        "keyword",
        [
          fallbackWarning(
            "embedding_provider_unavailable",
            "No embedding capability was supplied; keyword results were returned.",
          ),
        ],
        candidates.length,
        candidateSet.chunksLoaded,
        duplicatesRemoved,
        true,
        runId,
      );
    }

    const descriptor = this.embeddings.descriptor();
    const contractMismatch = validateEmbeddingDescriptor(this.manifest.vector_index, descriptor);
    if (contractMismatch) {
      return this.finish(
        lexical.slice(0, limit),
        modeRequested,
        "keyword",
        [
          fallbackWarning(
            "embedding_contract_mismatch",
            "The supplied embedding capability does not match the publication embedding contract; keyword results were returned.",
            { ...contractMismatch },
          ),
        ],
        candidates.length,
        candidateSet.chunksLoaded,
        duplicatesRemoved,
        true,
        runId,
      );
    }

    this.events.emit({ type: "embedding-start", runId });
    let vector: number[];
    try {
      const embedded = await this.embeddings.embed([query], { signal });
      vector = embedded.vectors[0] ?? [];
    } catch (error) {
      if (isAbortError(error)) throw error;
      return this.finish(
        lexical.slice(0, limit),
        modeRequested,
        "keyword",
        [
          fallbackWarning(
            "embedding_provider_unavailable",
            error instanceof Error
              ? error.message
              : "Embedding generation failed; keyword results were returned.",
          ),
        ],
        candidates.length,
        candidateSet.chunksLoaded,
        duplicatesRemoved,
        true,
        runId,
      );
    }

    const expectedDimension = Number(this.manifest.vector_index?.dimension || 0);
    if (expectedDimension && vector.length !== expectedDimension) {
      return this.finish(
        lexical.slice(0, limit),
        modeRequested,
        "keyword",
        [
          fallbackWarning(
            "embedding_dimension_mismatch",
            "The supplied embedding dimension does not match the publication; keyword results were returned.",
            { expected: expectedDimension, actual: vector.length },
          ),
        ],
        candidates.length,
        candidateSet.chunksLoaded,
        duplicatesRemoved,
        true,
        runId,
      );
    }

    await this.repository.ensureVectors(filters, runId, signal);
    const semantic = candidates
      .map((record) => {
        const semanticScore = cosine(vector, this.repository.vector(String(record.record_id)));
        return {
          record,
          score: semanticScore,
          semanticScore,
        };
      })
      .filter((item) => item.semanticScore > -1)
      .sort(compareScored);

    if (modeRequested === "semantic") {
      return this.finish(
        semantic.slice(0, limit),
        modeRequested,
        "semantic",
        [],
        candidates.length,
        candidateSet.chunksLoaded,
        duplicatesRemoved,
        true,
        runId,
      );
    }

    const lexicalMax = Math.max(...lexical.map((item) => item.score), 1);
    const semanticById = new Map(
      semantic.map((item) => [String(item.record.record_id), item.semanticScore]),
    );
    const lexicalById = new Map(
      lexical.map((item) => [String(item.record.record_id), item.lexicalScore ?? 0]),
    );

    const merged: ScoredRecord[] = candidates.map((record) => {
      const id = String(record.record_id);
      const lexicalScore = lexicalById.get(id) ?? 0;
      const semanticScore = semanticById.get(id);
      const semanticNormalized = semanticScore == null ? 0 : (semanticScore + 1) / 2;
      return {
        record,
        lexicalScore,
        semanticScore,
        score: 0.45 * (lexicalScore / lexicalMax) + 0.55 * semanticNormalized,
      };
    });

    return this.finish(
      merged.sort(compareScored).slice(0, limit),
      modeRequested,
      "hybrid",
      [],
      candidates.length,
      candidateSet.chunksLoaded,
      duplicatesRemoved,
      true,
      runId,
    );
  }

  diversify(items: SearchResult[], limit = 10, lambda = 0.72): SearchResult[] {
    const remaining = [...items];
    const selected: SearchResult[] = [];
    const boundedLambda = Math.max(0, Math.min(1, lambda));

    while (remaining.length && selected.length < limit) {
      let bestIndex = 0;
      let bestScore = Number.NEGATIVE_INFINITY;
      for (let index = 0; index < remaining.length; index += 1) {
        const item = remaining[index];
        const vector = this.repository.vector(String(item.record.record_id));
        const redundancy =
          selected.length && vector
            ? Math.max(
                ...selected.map((chosen) =>
                  cosine(vector, this.repository.vector(String(chosen.record.record_id))),
                ),
              )
            : 0;
        const score =
          boundedLambda * Number(item.score || 0) - (1 - boundedLambda) * Math.max(0, redundancy);
        if (
          score > bestScore ||
          (score === bestScore &&
            String(item.record.record_id).localeCompare(
              String(remaining[bestIndex]?.record.record_id ?? ""),
            ) < 0)
        ) {
          bestScore = score;
          bestIndex = index;
        }
      }
      selected.push(remaining.splice(bestIndex, 1)[0]);
    }

    return selected.map((item, index) => ({ ...item, rank: index + 1 }));
  }

  private finish(
    items: ScoredRecord[],
    modeRequested: SearchMode,
    modeUsed: SearchMode,
    warnings: SearchWarning[],
    candidateCount: number,
    chunksLoaded: number,
    duplicatesRemoved: number,
    semanticAvailable: boolean,
    runId: string,
  ): SearchResponse {
    const results = items.map((item, index) => ({
      record: item.record,
      score: item.score,
      lexicalScore: item.lexicalScore,
      semanticScore: item.semanticScore,
      rank: index + 1,
    }));
    this.events.emit({ type: "retrieval-complete", runId, resultCount: results.length });
    return {
      results,
      modeRequested,
      modeUsed,
      warnings,
      diagnostics: {
        candidateCount,
        chunksLoaded,
        duplicatesRemoved,
        semanticAvailable,
      },
    };
  }
}
