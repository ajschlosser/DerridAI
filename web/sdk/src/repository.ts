// Copyright 2026 Aaron John Schlosser, PhD.

import { LruCache } from "./cache";
import { EventBus } from "./events";
import type {
  ChunkDescriptor,
  PublicationDataSource,
  PublicationRecord,
  SearchFilters,
  VectorChunk,
} from "./types";

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
}

async function yieldToBrowser(): Promise<void> {
  const scheduler = (
    globalThis as typeof globalThis & {
      scheduler?: { yield?: () => Promise<void> };
    }
  ).scheduler;
  if (scheduler?.yield) {
    await scheduler.yield();
    return;
  }
  await new Promise<void>((resolve) => setTimeout(resolve, 0));
}

function scalarText(value: unknown): string {
  if (Array.isArray(value)) return value.map(scalarText).join(" ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}

function normalized(value: unknown, locale: string): string {
  return scalarText(value).toLocaleLowerCase(locale);
}

function matchesFilter(
  record: PublicationRecord,
  field: string,
  expected: unknown,
  locale: string,
): boolean {
  if (expected == null || expected === "") return true;
  const actual = record[field];
  if (Array.isArray(expected)) {
    const candidates = expected.map((value) => normalized(value, locale));
    if (Array.isArray(actual)) {
      const values = actual.map((value) => normalized(value, locale));
      return candidates.some((candidate) => values.includes(candidate));
    }
    return candidates.includes(normalized(actual, locale));
  }
  if (typeof expected === "string") {
    const needle = expected.toLocaleLowerCase(locale);
    if (field === "work") return normalized(actual, locale) === needle;
    return normalized(actual, locale).includes(needle);
  }
  return actual === expected;
}

export class RecordRepository {
  private readonly recordChunks: LruCache<string, PublicationRecord[]>;
  private readonly vectorChunks: LruCache<string, VectorChunk | null>;
  private readonly vectorsByRecordId = new Map<string, Float32Array>();

  constructor(
    private readonly dataSource: PublicationDataSource,
    private readonly descriptors: ChunkDescriptor[],
    private readonly events: EventBus,
    cache: { recordChunks?: number; vectorChunks?: number } = {},
  ) {
    this.recordChunks = new LruCache(cache.recordChunks ?? 8);
    this.vectorChunks = new LruCache(cache.vectorChunks ?? 4);
  }

  private selectedDescriptors(filters: SearchFilters = {}): ChunkDescriptor[] {
    const requested = filters.work;
    if (requested == null || requested === "") return this.descriptors;
    const works = (Array.isArray(requested) ? requested : [requested]).map(String);
    return this.descriptors.filter(
      (descriptor) => descriptor.work && works.includes(descriptor.work),
    );
  }

  private async loadRecords(chunkId: string, signal?: AbortSignal): Promise<PublicationRecord[]> {
    throwIfAborted(signal);
    const cached = this.recordChunks.get(chunkId);
    if (cached) return cached;
    const records = await this.dataSource.loadRecords(chunkId, { signal });
    throwIfAborted(signal);
    this.recordChunks.set(chunkId, records);
    return records;
  }

  private async loadVectors(chunkId: string, signal?: AbortSignal): Promise<VectorChunk | null> {
    throwIfAborted(signal);
    const cached = this.vectorChunks.get(chunkId);
    if (cached !== undefined) return cached;
    const chunk = this.dataSource.loadVectors
      ? await this.dataSource.loadVectors(chunkId, { signal })
      : null;
    throwIfAborted(signal);
    if (chunk) {
      chunk.ids.forEach((id, index) => {
        const recordId = String(id);
        if (this.vectorsByRecordId.has(recordId)) return;
        const start = index * chunk.dimension;
        this.vectorsByRecordId.set(recordId, chunk.values.subarray(start, start + chunk.dimension));
      });
    }
    this.vectorChunks.set(chunkId, chunk);
    return chunk;
  }

  async candidates(
    filters: SearchFilters,
    locale: string,
    runId: string,
    signal?: AbortSignal,
  ): Promise<{ records: PublicationRecord[]; chunksLoaded: number }> {
    const descriptors = this.selectedDescriptors(filters);
    const records: PublicationRecord[] = [];
    for (let index = 0; index < descriptors.length; index += 1) {
      throwIfAborted(signal);
      const descriptor = descriptors[index];
      const chunkRecords = await this.loadRecords(descriptor.id, signal);
      for (const record of chunkRecords) {
        if (
          Object.entries(filters).every(([field, expected]) =>
            matchesFilter(record, field, expected, locale),
          )
        ) {
          records.push(record);
        }
      }
      this.events.emit({
        type: "load-progress",
        runId,
        stage: "records",
        chunkId: descriptor.id,
        work: descriptor.work,
        completed: index + 1,
        total: descriptors.length,
      });
      if (index + 1 < descriptors.length) await yieldToBrowser();
    }
    return { records, chunksLoaded: descriptors.length };
  }

  async ensureVectors(filters: SearchFilters, runId: string, signal?: AbortSignal): Promise<void> {
    const descriptors = this.selectedDescriptors(filters);
    for (let index = 0; index < descriptors.length; index += 1) {
      throwIfAborted(signal);
      const descriptor = descriptors[index];
      await this.loadVectors(descriptor.id, signal);
      this.events.emit({
        type: "load-progress",
        runId,
        stage: "vectors",
        chunkId: descriptor.id,
        work: descriptor.work,
        completed: index + 1,
        total: descriptors.length,
      });
      if (index + 1 < descriptors.length) await yieldToBrowser();
    }
  }

  vector(recordId: string): Float32Array | undefined {
    return this.vectorsByRecordId.get(recordId);
  }

  async get(recordId: string, signal?: AbortSignal): Promise<PublicationRecord | null> {
    for (const descriptor of this.descriptors) {
      const records = await this.loadRecords(descriptor.id, signal);
      const record = records.find((item) => String(item.record_id) === String(recordId));
      if (record) return record;
      await yieldToBrowser();
    }
    return null;
  }

  clear(): void {
    this.recordChunks.clear();
    this.vectorChunks.clear();
    this.vectorsByRecordId.clear();
  }

  stats(): { recordChunks: number; vectorChunks: number; vectors: number } {
    return {
      recordChunks: this.recordChunks.size,
      vectorChunks: this.vectorChunks.size,
      vectors: this.vectorsByRecordId.size,
    };
  }
}
