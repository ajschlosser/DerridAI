// Copyright 2026 Aaron John Schlosser, PhD.

import "fake-indexeddb/auto";
import { describe, expect, it, vi } from "vitest";
import {
  IndexedDbVectorStore,
  MemoryStorage,
  createClient,
  dataSources,
  embeddingFingerprint,
  matchesPublicationModel,
  vectorIndex,
  type ClientEvent,
  type EmbeddingProvider,
  type PublicationRecord,
} from "../../sdk/src";

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function json64(value: unknown): string {
  return bytesToBase64(new TextEncoder().encode(JSON.stringify(value)));
}

function floats64(rows: number[][]): string {
  const flat = rows.flat();
  const view = new DataView(new ArrayBuffer(flat.length * 4));
  flat.forEach((value, index) => view.setFloat32(index * 4, value, true));
  return bytesToBase64(new Uint8Array(view.buffer));
}

function record(id: string, work: string, text: string): PublicationRecord {
  return {
    record_id: id,
    source_document_id: "source-1",
    source_spans: [{ source_document_id: "source-1", printed_page: 1 }],
    work,
    citation: `Jacques Derrida, ${work}`,
    text,
  };
}

/** Three Records; the published vectors place g1 near [1,0] and r1 near [0,1]. */
function publication(id = "pub-local") {
  const glas = [record("g1", "Glas", "hospitality gift"), record("g2", "Glas", "mourning remains")];
  const rogues = [record("r1", "Rogues", "democracy sovereignty")];
  return {
    manifest: {
      format: "derridai-static-site-v5",
      publication_id: id,
      title: "Local index",
      works: [
        { work: "Glas", record_count: 2 },
        { work: "Rogues", record_count: 1 },
      ],
      vector_index: { model: "bge-m3:latest", dimension: 2, text_field: "text" },
      features: { semantic_search: true },
    },
    chunks: [
      {
        id: "w1",
        work: "Glas",
        record_count: 2,
        records_b64: json64(glas),
        vector_ids: ["g1", "g2"],
        vectors_b64: floats64([
          [1, 0],
          [0.7, 0.7],
        ]),
      },
      {
        id: "w2",
        work: "Rogues",
        record_count: 1,
        records_b64: json64(rogues),
        vector_ids: ["r1"],
        vectors_b64: floats64([[0, 1]]),
      },
    ],
  };
}

/** Embeds by keyword so tests can predict similarity without a model. */
function keywordProvider(model = "tiny-local", spy = vi.fn()): EmbeddingProvider {
  const axis = (text: string): number[] =>
    /democracy|sovereignty/i.test(text)
      ? [0, 0, 1]
      : /mourning/i.test(text)
        ? [0, 1, 0]
        : [1, 0, 0];
  return {
    descriptor: () => ({ type: "transformers", model }),
    async embed(input) {
      spy(input);
      return { vectors: input.map(axis) };
    },
  };
}

describe("local vector index", () => {
  it("matches only the exact publication model", () => {
    const contract = { model: "bge-m3:latest" };
    expect(matchesPublicationModel({ model: "bge-m3:latest" }, contract)).toBe(true);
    expect(matchesPublicationModel({ model: "bge-m4" }, contract)).toBe(false);
    expect(matchesPublicationModel({ model: "bge-m3:latest" }, {})).toBe(false);
    expect(matchesPublicationModel({}, contract)).toBe(false);
    expect(
      matchesPublicationModel({ model: "m", revision: "2" }, { model: "m", revision: "1" }),
    ).toBe(false);
    expect(embeddingFingerprint({ type: "ollama", model: "m" })).not.toBe(
      embeddingFingerprint({ type: "transformers", model: "m" }),
    );
  });

  it("uses published vectors for the exact model without building an index", async () => {
    const embed = vi.fn(async () => ({ vectors: [[1, 0]] }));
    const client = await createClient({
      dataSource: dataSources.inline(publication()),
      storage: new MemoryStorage(),
      vectorIndex: vectorIndex.memory(),
      embeddings: { descriptor: () => ({ type: "ollama", model: "bge-m3:latest" }), embed },
    });
    const response = await client.search({ query: "gift", mode: "semantic" });
    expect(response.modeUsed).toBe("semantic");
    expect(response.results[0].record.record_id).toBe("g1");
    expect((await client.capabilities()).localIndex?.usesPublishedVectors).toBe(true);
  });

  it("requires a local index for a different model, then searches in the new vector space", async () => {
    const embed = vi.fn();
    const client = await createClient({
      dataSource: dataSources.inline(publication()),
      storage: new MemoryStorage(),
      vectorIndex: vectorIndex.memory(),
      embeddings: keywordProvider("tiny-local", embed),
    });
    const before = await client.search({ query: "democracy", mode: "semantic" });
    expect(before.modeUsed).toBe("keyword");
    expect(before.warnings[0]).toMatchObject({
      code: "local_index_required",
      details: { expectedModel: "bge-m3:latest", actualModel: "tiny-local", indexed: 0, total: 3 },
    });
    expect(embed).not.toHaveBeenCalled();

    const events: ClientEvent[] = [];
    client.events.subscribe((event) => events.push(event));
    const status = await client.index.build({ batchSize: 2 });
    expect(status).toMatchObject({
      complete: true,
      indexed: 3,
      total: 3,
      usesPublishedVectors: false,
    });
    expect(events.some((event) => event.type === "index-progress")).toBe(true);

    const after = await client.search({ query: "democracy", mode: "semantic" });
    expect(after.modeUsed).toBe("semantic");
    expect(after.results[0].record.record_id).toBe("r1");
  });

  it("resumes an interrupted build and embeds only Records that are still missing", async () => {
    const store = vectorIndex.memory();
    const spy = vi.fn();
    const controller = new AbortController();
    const provider = keywordProvider("tiny-local", spy);
    const aborting: EmbeddingProvider = {
      descriptor: provider.descriptor,
      async embed(input, options) {
        const result = await provider.embed(input, options);
        controller.abort();
        return result;
      },
    };
    const first = await createClient({
      dataSource: dataSources.inline(publication()),
      storage: new MemoryStorage(),
      vectorIndex: store,
      embeddings: aborting,
    });
    await expect(first.index.build({ batchSize: 1, signal: controller.signal })).rejects.toThrow();
    expect((await first.index.status())?.indexed).toBe(1);

    spy.mockClear();
    const second = await createClient({
      dataSource: dataSources.inline(publication()),
      storage: new MemoryStorage(),
      vectorIndex: store,
      embeddings: provider,
    });
    const status = await second.index.build({ batchSize: 1 });
    expect(status.complete).toBe(true);
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it("rejects malformed provider output instead of storing it", async () => {
    const client = await createClient({
      dataSource: dataSources.inline(publication()),
      storage: new MemoryStorage(),
      vectorIndex: vectorIndex.memory(),
      embeddings: {
        descriptor: () => ({ type: "ollama", model: "broken" }),
        async embed() {
          return { vectors: [[1, 0]] };
        },
      },
    });
    await expect(client.index.build({ batchSize: 3 })).rejects.toThrow(/wrong number/);
    expect((await client.index.status())?.indexed).toBe(0);
  });

  it("keeps indexes for different models separate and can clear them", async () => {
    const store = vectorIndex.memory();
    const make = (model: string) =>
      createClient({
        dataSource: dataSources.inline(publication()),
        storage: new MemoryStorage(),
        vectorIndex: store,
        embeddings: keywordProvider(model),
      });
    const a = await make("model-a");
    const b = await make("model-b");
    await a.index.build();
    expect((await b.index.status())?.indexed).toBe(0);
    await a.index.clear();
    expect((await a.index.status())?.indexed).toBe(0);
  });

  it("completes when a Record has no embeddable text", async () => {
    const pkg = publication();
    pkg.chunks[0].records_b64 = json64([
      record("g1", "Glas", "hospitality"),
      record("g2", "Glas", "  "),
    ]);
    const client = await createClient({
      dataSource: dataSources.inline(pkg),
      storage: new MemoryStorage(),
      vectorIndex: vectorIndex.memory(),
      embeddings: keywordProvider(),
    });
    expect((await client.index.build()).complete).toBe(true);
  });
});

describe("IndexedDB vector store", () => {
  it("falls back to a session-only store after the first failure", async () => {
    const original = globalThis.indexedDB;
    Object.defineProperty(globalThis, "indexedDB", {
      configurable: true,
      value: {
        open() {
          throw new DOMException("The operation is insecure.", "SecurityError");
        },
      },
    });
    try {
      const client = await createClient({
        dataSource: dataSources.inline(publication("pub-refused")),
        storage: new MemoryStorage(),
        embeddings: keywordProvider("tiny"),
      });
      const status = await client.index.build();
      expect(status).toMatchObject({ complete: true, persistent: false });
    } finally {
      Object.defineProperty(globalThis, "indexedDB", { configurable: true, value: original });
    }
  });

  it("persists vectors across store instances and scopes them by publication and model", async () => {
    const name = `test-${Math.random()}`;
    const descriptor = { type: "transformers", model: "tiny" };
    const fingerprint = embeddingFingerprint(descriptor);
    const first = new IndexedDbVectorStore(name);
    await first.put("pub-a", fingerprint, descriptor, [
      { recordId: "r1", vector: new Float32Array([1, 2]) },
      { recordId: "r2", vector: new Float32Array([3, 4]) },
    ]);
    await first.put("pub-b", fingerprint, descriptor, [
      { recordId: "r1", vector: new Float32Array([9, 9]) },
    ]);

    const second = new IndexedDbVectorStore(name);
    expect([...(await second.ids("pub-a", fingerprint))].sort()).toEqual(["r1", "r2"]);
    const loaded = await second.load("pub-a", fingerprint);
    expect(loaded?.dimension).toBe(2);
    expect([...(loaded?.vectors.get("r2") ?? [])]).toEqual([3, 4]);
    expect((await second.summaries("pub-a"))[0]).toMatchObject({ count: 2, model: "tiny" });
    expect(await second.load("pub-c", fingerprint)).toBeNull();

    await second.clear("pub-a");
    expect((await second.ids("pub-a", fingerprint)).size).toBe(0);
    expect((await second.ids("pub-b", fingerprint)).size).toBe(1);
  });
});

describe("embedding model identity", () => {
  it("treats Ollama's :latest tag as the untagged model name", () => {
    expect(matchesPublicationModel({ model: "bge-m3" }, { model: "bge-m3:latest" })).toBe(true);
    expect(matchesPublicationModel({ model: "bge-m3:latest" }, { model: "bge-m3" })).toBe(true);
    expect(matchesPublicationModel({ model: "bge-m3:567m" }, { model: "bge-m3:latest" })).toBe(
      false,
    );
  });

  it("does not reuse published vectors when a variant such as a prefix changes the embedding", () => {
    expect(
      matchesPublicationModel(
        { model: "bge-m3:latest", variant: "q=query: " },
        { model: "bge-m3:latest" },
      ),
    ).toBe(false);
    expect(embeddingFingerprint({ type: "t", model: "m", variant: "a" })).not.toBe(
      embeddingFingerprint({ type: "t", model: "m", variant: "b" }),
    );
  });

  it("asks providers to embed queries and documents for their purpose", async () => {
    const purposes: (string | undefined)[] = [];
    const client = await createClient({
      dataSource: dataSources.inline(publication()),
      storage: new MemoryStorage(),
      vectorIndex: vectorIndex.memory(),
      embeddings: {
        descriptor: () => ({ type: "transformers", model: "tiny" }),
        async embed(input, options) {
          purposes.push(options?.purpose);
          return { vectors: input.map(() => [1, 0, 0]) };
        },
      },
    });
    await client.index.build();
    await client.search({ query: "gift", mode: "semantic" });
    expect(purposes).toContain("document");
    expect(purposes[purposes.length - 1]).toBe("query");
  });
});
