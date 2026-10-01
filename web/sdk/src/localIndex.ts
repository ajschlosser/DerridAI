// Copyright 2026 Aaron John Schlosser, PhD.

import { EventBus } from "./events";
import { RecordRepository } from "./repository";
import type {
  EmbeddingProvider,
  LocalIndexBuildOptions,
  LocalIndexStatus,
  PublicationManifest,
  PublicationRecord,
  VectorIndexStore,
} from "./types";
import { embeddingFingerprint, matchesPublicationModel } from "./vectorIndex";

const DEFAULT_BATCH_SIZE = 16;

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
}

/**
 * Vectors computed in this client with the reader's own embedding model. They are derived from the published
 * Records, keyed by publication and exact model, and never replace or alter the publication's own vectors.
 */
export class LocalVectorIndex {
  private readonly loaded = new Map<
    string,
    { dimension: number; vectors: Map<string, Float32Array> }
  >();

  constructor(
    private readonly manifest: PublicationManifest,
    private readonly repository: RecordRepository,
    private readonly store: VectorIndexStore,
    private readonly events: EventBus,
  ) {}

  private get publicationId(): string {
    return this.manifest.publication_id;
  }

  private textOf(record: PublicationRecord): string {
    const field = String(this.manifest.vector_index?.text_field || "text");
    return String(record[field] ?? "").trim();
  }

  usesPublishedVectors(provider: EmbeddingProvider): boolean {
    return Boolean(
      this.manifest.features?.semantic_search &&
        this.manifest.vector_index?.dimension &&
        matchesPublicationModel(provider.descriptor(), this.manifest.vector_index),
    );
  }

  async status(provider: EmbeddingProvider): Promise<LocalIndexStatus> {
    const descriptor = provider.descriptor();
    const fingerprint = embeddingFingerprint(descriptor);
    const total = this.repository.totalRecords();
    const usesPublishedVectors = this.usesPublishedVectors(provider);
    const indexed = (await this.store.ids(this.publicationId, fingerprint)).size;
    return {
      usesPublishedVectors,
      complete: usesPublishedVectors || (total > 0 && indexed >= total),
      indexed: usesPublishedVectors ? total : indexed,
      total,
      persistent: this.store.persistent,
      model: descriptor.model,
    };
  }

  async vectorsFor(
    provider: EmbeddingProvider,
  ): Promise<{ dimension: number; vectors: Map<string, Float32Array> } | null> {
    const fingerprint = embeddingFingerprint(provider.descriptor());
    const cached = this.loaded.get(fingerprint);
    if (cached) return cached;
    const stored = await this.store.load(this.publicationId, fingerprint);
    if (stored) this.loaded.set(fingerprint, stored);
    return stored;
  }

  async build(
    provider: EmbeddingProvider,
    runId: string,
    options: LocalIndexBuildOptions = {},
  ): Promise<LocalIndexStatus> {
    const { signal } = options;
    const batchSize = Math.max(1, Math.min(128, options.batchSize ?? DEFAULT_BATCH_SIZE));
    const descriptor = provider.descriptor();
    const fingerprint = embeddingFingerprint(descriptor);
    const total = this.repository.totalRecords();
    const existing = await this.store.ids(this.publicationId, fingerprint);
    const summary = (await this.store.summaries(this.publicationId)).find(
      (item) => item.fingerprint === fingerprint,
    );
    let dimension = summary?.dimension ?? 0;
    let indexed = existing.size;
    const deferredEmpty: string[] = [];
    this.loaded.delete(fingerprint);
    this.events.emit({ type: "index-progress", runId, indexed, total });

    const writeEmpty = async (ids: string[]): Promise<void> => {
      if (!ids.length || !dimension) return;
      await this.store.put(
        this.publicationId,
        fingerprint,
        descriptor,
        ids.map((recordId) => ({ recordId, vector: new Float32Array(dimension) })),
      );
      indexed += ids.length;
    };

    await this.repository.eachChunk(signal, async (records) => {
      const pending = records.filter((record) => !existing.has(String(record.record_id)));
      const embeddable = pending.filter((record) => this.textOf(record));
      const empty = pending
        .filter((record) => !this.textOf(record))
        .map((record) => String(record.record_id));
      for (let start = 0; start < embeddable.length; start += batchSize) {
        throwIfAborted(signal);
        const batch = embeddable.slice(start, start + batchSize);
        const result = await provider.embed(
          batch.map((record) => this.textOf(record)),
          { signal, purpose: "document" },
        );
        if (result.vectors.length !== batch.length) {
          throw new Error("The embedding provider returned the wrong number of vectors.");
        }
        const entries = batch.map((record, index) => {
          const vector = Float32Array.from(result.vectors[index] ?? []);
          if (!vector.length || vector.some((value) => !Number.isFinite(value))) {
            throw new Error("The embedding provider returned an invalid vector.");
          }
          if (!dimension) dimension = vector.length;
          if (vector.length !== dimension) {
            throw new Error("The embedding provider returned vectors of differing sizes.");
          }
          return { recordId: String(record.record_id), vector };
        });
        await this.store.put(this.publicationId, fingerprint, descriptor, entries);
        indexed += entries.length;
        this.events.emit({ type: "index-progress", runId, indexed, total });
      }
      if (dimension) await writeEmpty(empty);
      else deferredEmpty.push(...empty);
      this.events.emit({ type: "index-progress", runId, indexed, total });
    });

    await writeEmpty(deferredEmpty);
    this.events.emit({ type: "index-progress", runId, indexed, total });
    return this.status(provider);
  }

  async clear(provider?: EmbeddingProvider): Promise<void> {
    if (provider) {
      const fingerprint = embeddingFingerprint(provider.descriptor());
      this.loaded.delete(fingerprint);
      await this.store.clear(this.publicationId, fingerprint);
      return;
    }
    this.loaded.clear();
    await this.store.clear(this.publicationId);
  }

  async summaries(): ReturnType<VectorIndexStore["summaries"]> {
    return this.store.summaries(this.publicationId);
  }
}
