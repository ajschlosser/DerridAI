// Copyright 2026 Aaron John Schlosser, PhD.

import type { ProviderDescriptor, VectorIndexStore, VectorIndexSummary } from "./types";

const SEPARATOR = "\u0000";

/** Stable identity of the embedding model that produced a set of vectors. */
export function embeddingFingerprint(descriptor: ProviderDescriptor): string {
  return [
    descriptor.type ?? "",
    descriptor.model ?? "",
    descriptor.revision ?? "",
    descriptor.variant ?? "",
  ].join("|");
}

// Ollama reports an untagged model as ":latest"; the two names identify the same model.
function modelName(value: unknown): string {
  return String(value ?? "").replace(/:latest$/, "");
}

/** Vectors are comparable only when the model is exactly the one that embedded the publication. */
export function matchesPublicationModel(
  descriptor: ProviderDescriptor,
  contract: { model?: string; revision?: string } | undefined,
): boolean {
  const expected = modelName(contract?.model);
  const actual = modelName(descriptor.model);
  if (!expected || !actual || expected !== actual) return false;
  // Prefixes and similar changes alter the vectors, so they no longer match what was published.
  if (descriptor.variant) return false;
  const expectedRevision = String(contract?.revision ?? "");
  const actualRevision = String(descriptor.revision ?? "");
  return !expectedRevision || !actualRevision || expectedRevision === actualRevision;
}

function indexKey(publicationId: string, fingerprint: string): string {
  return `${publicationId}${SEPARATOR}${fingerprint}`;
}

function summaryOf(
  publicationId: string,
  fingerprint: string,
  descriptor: ProviderDescriptor,
  dimension: number,
  count: number,
): VectorIndexSummary {
  return {
    publicationId,
    fingerprint,
    model: String(descriptor.model ?? ""),
    provider: String(descriptor.type ?? ""),
    dimension,
    count,
    updatedAt: new Date().toISOString(),
  };
}

export class MemoryVectorStore implements VectorIndexStore {
  readonly persistent = false;
  private readonly indexes = new Map<
    string,
    { summary: VectorIndexSummary; vectors: Map<string, Float32Array> }
  >();

  async ids(publicationId: string, fingerprint: string): Promise<Set<string>> {
    return new Set(this.indexes.get(indexKey(publicationId, fingerprint))?.vectors.keys() ?? []);
  }

  async load(
    publicationId: string,
    fingerprint: string,
  ): Promise<{ dimension: number; vectors: Map<string, Float32Array> } | null> {
    const entry = this.indexes.get(indexKey(publicationId, fingerprint));
    if (!entry) return null;
    return { dimension: entry.summary.dimension, vectors: new Map(entry.vectors) };
  }

  async put(
    publicationId: string,
    fingerprint: string,
    descriptor: ProviderDescriptor,
    entries: { recordId: string; vector: Float32Array }[],
  ): Promise<void> {
    const key = indexKey(publicationId, fingerprint);
    let entry = this.indexes.get(key);
    if (!entry) {
      entry = {
        summary: summaryOf(
          publicationId,
          fingerprint,
          descriptor,
          entries[0]?.vector.length ?? 0,
          0,
        ),
        vectors: new Map(),
      };
      this.indexes.set(key, entry);
    }
    for (const item of entries) entry.vectors.set(item.recordId, new Float32Array(item.vector));
    entry.summary = {
      ...entry.summary,
      count: entry.vectors.size,
      updatedAt: new Date().toISOString(),
    };
  }

  async summaries(publicationId: string): Promise<VectorIndexSummary[]> {
    return [...this.indexes.values()]
      .map((entry) => entry.summary)
      .filter((summary) => summary.publicationId === publicationId);
  }

  async clear(publicationId: string, fingerprint?: string): Promise<void> {
    for (const key of [...this.indexes.keys()]) {
      const [id, print] = key.split(SEPARATOR);
      if (id === publicationId && (fingerprint === undefined || print === fingerprint)) {
        this.indexes.delete(key);
      }
    }
  }
}

function request<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error("IndexedDB request failed."));
  });
}

function transactionDone(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed."));
    tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted."));
  });
}

/**
 * Persistent browser store for locally computed embeddings. One index per publication and embedding model;
 * these are derived data and can always be rebuilt from the published Records.
 */
export class IndexedDbVectorStore implements VectorIndexStore {
  readonly persistent = true;
  private opened?: Promise<IDBDatabase>;

  constructor(
    private readonly name = "derridai-sdk-vectors",
    private readonly factory: IDBFactory = globalThis.indexedDB,
  ) {}

  private database(): Promise<IDBDatabase> {
    if (!this.opened) {
      this.opened = new Promise((resolve, reject) => {
        const open = this.factory.open(this.name, 1);
        open.onupgradeneeded = () => {
          open.result.createObjectStore("vectors");
          open.result.createObjectStore("indexes");
        };
        open.onsuccess = () => resolve(open.result);
        open.onerror = () => reject(open.error ?? new Error("IndexedDB could not be opened."));
        open.onblocked = () => reject(new Error("IndexedDB upgrade was blocked."));
      });
      this.opened.catch(() => {
        this.opened = undefined;
      });
    }
    return this.opened;
  }

  private range(publicationId: string, fingerprint: string): IDBKeyRange {
    const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
    return IDBKeyRange.bound(prefix, `${prefix}￿`);
  }

  async ids(publicationId: string, fingerprint: string): Promise<Set<string>> {
    const db = await this.database();
    const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
    const keys = await request(
      db
        .transaction("vectors", "readonly")
        .objectStore("vectors")
        .getAllKeys(this.range(publicationId, fingerprint)),
    );
    return new Set(keys.map((key) => String(key).slice(prefix.length)));
  }

  async load(
    publicationId: string,
    fingerprint: string,
  ): Promise<{ dimension: number; vectors: Map<string, Float32Array> } | null> {
    const db = await this.database();
    const tx = db.transaction(["vectors", "indexes"], "readonly");
    const meta = (await request(
      tx.objectStore("indexes").get(indexKey(publicationId, fingerprint)),
    )) as VectorIndexSummary | undefined;
    if (!meta) return null;
    const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
    const range = this.range(publicationId, fingerprint);
    const store = tx.objectStore("vectors");
    const [keys, values] = await Promise.all([
      request(store.getAllKeys(range)),
      request(store.getAll(range)),
    ]);
    const vectors = new Map<string, Float32Array>();
    keys.forEach((key, index) => {
      vectors.set(String(key).slice(prefix.length), values[index] as Float32Array);
    });
    return { dimension: meta.dimension, vectors };
  }

  async put(
    publicationId: string,
    fingerprint: string,
    descriptor: ProviderDescriptor,
    entries: { recordId: string; vector: Float32Array }[],
  ): Promise<void> {
    const db = await this.database();
    const tx = db.transaction(["vectors", "indexes"], "readwrite");
    // Install completion handlers before awaiting individual requests: a fast IndexedDB implementation can
    // otherwise complete the transaction before transactionDone() starts listening, leaving index builds hung.
    const done = transactionDone(tx);
    const vectors = tx.objectStore("vectors");
    const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
    for (const item of entries) vectors.put(item.vector, `${prefix}${item.recordId}`);
    const count = await request(vectors.count(this.range(publicationId, fingerprint)));
    const indexes = tx.objectStore("indexes");
    const key = indexKey(publicationId, fingerprint);
    const existing = (await request(indexes.get(key))) as VectorIndexSummary | undefined;
    indexes.put(
      {
        ...summaryOf(
          publicationId,
          fingerprint,
          descriptor,
          existing?.dimension || entries[0]?.vector.length || 0,
          count,
        ),
      },
      key,
    );
    await done;
  }

  async summaries(publicationId: string): Promise<VectorIndexSummary[]> {
    const db = await this.database();
    const all = (await request(
      db.transaction("indexes", "readonly").objectStore("indexes").getAll(),
    )) as VectorIndexSummary[];
    return all.filter((summary) => summary.publicationId === publicationId);
  }

  async clear(publicationId: string, fingerprint?: string): Promise<void> {
    const targets =
      fingerprint !== undefined
        ? [fingerprint]
        : (await this.summaries(publicationId)).map((summary) => summary.fingerprint);
    const db = await this.database();
    const tx = db.transaction(["vectors", "indexes"], "readwrite");
    const done = transactionDone(tx);
    for (const print of targets) {
      tx.objectStore("vectors").delete(this.range(publicationId, print));
      tx.objectStore("indexes").delete(indexKey(publicationId, print));
    }
    await done;
  }
}

/**
 * Uses a persistent store until it fails (opaque origins, privacy modes, or quota can all reject IndexedDB
 * at first use), then continues in memory for the session so search and index building keep working.
 */
class FallbackVectorStore implements VectorIndexStore {
  private active: VectorIndexStore;
  private readonly fallback = new MemoryVectorStore();

  constructor(primary: VectorIndexStore) {
    this.active = primary;
  }

  get persistent(): boolean {
    return this.active.persistent;
  }

  private async run<T>(operation: (store: VectorIndexStore) => Promise<T>): Promise<T> {
    if (this.active === this.fallback) return operation(this.active);
    try {
      return await operation(this.active);
    } catch {
      this.active = this.fallback;
      return operation(this.active);
    }
  }

  ids(publicationId: string, fingerprint: string) {
    return this.run((store) => store.ids(publicationId, fingerprint));
  }

  load(publicationId: string, fingerprint: string) {
    return this.run((store) => store.load(publicationId, fingerprint));
  }

  put(
    publicationId: string,
    fingerprint: string,
    descriptor: ProviderDescriptor,
    entries: { recordId: string; vector: Float32Array }[],
  ) {
    return this.run((store) => store.put(publicationId, fingerprint, descriptor, entries));
  }

  summaries(publicationId: string) {
    return this.run((store) => store.summaries(publicationId));
  }

  clear(publicationId: string, fingerprint?: string) {
    return this.run((store) => store.clear(publicationId, fingerprint));
  }
}

/** IndexedDB when the browser offers and allows it; otherwise a session-only memory store. */
export function defaultVectorStore(): VectorIndexStore {
  try {
    if (typeof globalThis.indexedDB !== "undefined" && globalThis.indexedDB) {
      return new FallbackVectorStore(new IndexedDbVectorStore());
    }
  } catch {
    // Privacy modes and opaque origins can throw on access; fall back to memory.
  }
  return new MemoryVectorStore();
}

export const vectorIndex = {
  indexedDb: (name?: string): VectorIndexStore => new IndexedDbVectorStore(name),
  /** IndexedDB that degrades to memory for the session if the browser refuses it. */
  resilient: (name?: string): VectorIndexStore =>
    new FallbackVectorStore(new IndexedDbVectorStore(name)),
  memory: (): VectorIndexStore => new MemoryVectorStore(),
};
