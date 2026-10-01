// Copyright 2026 Aaron John Schlosser, PhD.

import { describe, expect, it, vi } from "vitest";
import {
  createClient,
  dataSources,
  MemoryStorage,
  type GenerationRequest,
  type PublicationDataSource,
  type PublicationRecord,
} from "../../sdk/src";

function base64Bytes(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function base64Json(value: unknown): string {
  return base64Bytes(new TextEncoder().encode(JSON.stringify(value)));
}

function base64Float32(rows: number[][]): string {
  const flat = rows.flat();
  const buffer = new ArrayBuffer(flat.length * 4);
  const view = new DataView(buffer);
  flat.forEach((value, index) => view.setFloat32(index * 4, value, true));
  return base64Bytes(new Uint8Array(buffer));
}

function record(
  recordId: string,
  work: string,
  text: string,
  extra: Partial<PublicationRecord> = {},
): PublicationRecord {
  return {
    record_id: recordId,
    source_document_id: "source-1",
    source_spans: [
      {
        source_document_id: "source-1",
        source_unit_id: `unit-${recordId}`,
        printed_page: 12,
      },
    ],
    work,
    citation: `Jacques Derrida, ${work}`,
    text,
    ...extra,
  };
}

function publicationPackage() {
  const glas = [
    record("g1", "Glas", "hospitality gift responsibility", {
      speaker: "Derrida",
      position_holder: "Hegel",
      stance: "questions",
      discourse_role: "analysis",
    }),
  ];
  const rogues = [record("r1", "Rogues", "democracy sovereignty")];
  return {
    manifest: {
      format: "derridai-static-site-v2",
      publication_id: "pub-1",
      title: "Test publication",
      locale: "en-US",
      works: [
        { work: "Glas", record_count: 1 },
        { work: "Rogues", record_count: 1 },
      ],
      vector_index: {
        model: "bge-m3:latest",
        revision: "fixture-revision",
        dimension: 2,
        distance_metric: "cosine",
        text_field: "text",
      },
      features: {
        browse: true,
        lexical_search: true,
        semantic_search: true,
        local_annotations: true,
        research: true,
      },
    },
    chunks: [
      {
        id: "work-1",
        work: "Glas",
        record_count: 1,
        records_b64: base64Json(glas),
        vector_ids: ["g1"],
        vectors_b64: base64Float32([[1, 0]]),
      },
      {
        id: "work-2",
        work: "Rogues",
        record_count: 1,
        records_b64: base64Json(rogues),
        vector_ids: ["r1"],
        vectors_b64: base64Float32([[0, 1]]),
      },
    ],
  };
}

describe("DerridAI SDK", () => {
  it("searches publication records without a DerridAI server", async () => {
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
    });

    const response = await client.search({
      query: "hospitality",
      mode: "keyword",
      filters: { work: ["Glas"] },
    });

    expect(response.modeUsed).toBe("keyword");
    expect(response.results.map((item) => item.record.record_id)).toEqual(["g1"]);
    expect(response.diagnostics.chunksLoaded).toBe(1);
    expect(client.citations.format(response.results[0].record).plain).toContain("p. 12");
  });

  it("uses injected embedding and generation capabilities rather than endpoint configuration", async () => {
    const generationRequests: GenerationRequest[] = [];
    const embed = vi.fn(async () => ({
      vectors: [[1, 0]],
      provider: { type: "host", model: "bge-m3:latest" },
    }));
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
      embeddings: {
        descriptor: () => ({ type: "host", model: "bge-m3:latest" }),
        embed,
      },
      generation: {
        descriptor: () => ({ type: "host", model: "qwen3:8b" }),
        async generate(request) {
          generationRequests.push(request);
          return {
            text: "The evidence distinguishes the attributed position [E1].",
            provider: { type: "host", model: "qwen3:8b" },
          };
        },
      },
    });

    const response = await client.research({
      question: "What does the passage say about hospitality?",
      retrieval: { mode: "hybrid", evidenceLimit: 1 },
    });

    expect(embed).toHaveBeenCalledOnce();
    expect(response.answer).toContain("[E1]");
    expect(response.evidencePacket.evidence[0]).toMatchObject({
      recordId: "g1",
      speaker: "Derrida",
      positionHolder: "Hegel",
      stance: "questions",
      discourseRole: "analysis",
    });
    expect(generationRequests[0]?.evidencePacket.evidence[0].recordId).toBe("g1");
    expect(generationRequests[0]?.prompt).toContain("Position holder: Hegel");
  });

  it("falls back to keyword retrieval when the host embedding contract is incompatible", async () => {
    const embed = vi.fn(async () => ({ vectors: [[1, 0]] }));
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
      embeddings: {
        descriptor: () => ({ type: "host", model: "other-model" }),
        embed,
      },
    });

    const response = await client.search({
      query: "hospitality",
      mode: "hybrid",
    });

    expect(response.modeUsed).toBe("keyword");
    expect(response.warnings[0].code).toBe("embedding_contract_mismatch");
    expect(embed).not.toHaveBeenCalled();
  });

  it("keeps generation failure separate from the retrieved evidence packet", async () => {
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
      embeddings: {
        descriptor: () => ({ type: "host", model: "bge-m3:latest" }),
        async embed() {
          return { vectors: [[1, 0]] };
        },
      },
    });

    const response = await client.research({
      question: "hospitality",
      retrieval: { evidenceLimit: 1 },
    });

    expect(response.answer).toBeNull();
    expect(response.evidencePacket.evidence).toHaveLength(1);
    expect(response.warnings.some((warning) => warning.code === "generation_unavailable")).toBe(
      true,
    );
  });

  it("deduplicates stable record identities before scoring and reports the removal", async () => {
    const publication = publicationPackage();
    publication.chunks.push({
      id: "work-3",
      work: "Glas",
      record_count: 1,
      records_b64: base64Json([
        record("g1", "Glas", "duplicate transport copy that must not become a second result"),
      ]),
      vector_ids: ["g1"],
      vectors_b64: base64Float32([[0, 1]]),
    });

    const client = await createClient({
      dataSource: dataSources.inline(publication),
      storage: new MemoryStorage(),
    });
    const response = await client.search({
      query: "hospitality",
      mode: "keyword",
      filters: { work: ["Glas"] },
    });

    expect(response.results.map((item) => item.record.record_id)).toEqual(["g1"]);
    expect(response.diagnostics.candidateCount).toBe(2);
    expect(response.diagnostics.duplicatesRemoved).toBe(1);
    expect(response.results[0].record.text).toBe("hospitality gift responsibility");
  });

  it("rejects an explicitly incompatible embedding revision before calling the provider", async () => {
    const embed = vi.fn(async () => ({ vectors: [[1, 0]] }));
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
      embeddings: {
        descriptor: () => ({
          type: "host",
          model: "bge-m3:latest",
          revision: "different-revision",
        }),
        embed,
      },
    });

    const response = await client.search({ query: "hospitality", mode: "hybrid" });

    expect(response.modeUsed).toBe("keyword");
    expect(response.warnings[0]).toMatchObject({
      code: "embedding_contract_mismatch",
      details: {
        mismatches: [
          {
            field: "revision",
            expected: "fixture-revision",
            actual: "different-revision",
          },
        ],
      },
    });
    expect(embed).not.toHaveBeenCalled();
  });

  it("propagates embedding cancellation and emits operation-cancelled", async () => {
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
      embeddings: {
        descriptor: () => ({ type: "host", model: "bge-m3:latest" }),
        async embed() {
          throw new DOMException("cancelled", "AbortError");
        },
      },
    });
    const events: string[] = [];
    client.events.subscribe((event) => events.push(event.type));

    await expect(client.search({ query: "hospitality", mode: "hybrid" })).rejects.toMatchObject({
      name: "AbortError",
    });
    expect(events).toContain("operation-cancelled");
  });

  it("propagates generation cancellation and preserves cancellation as an operation event", async () => {
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
      generation: {
        descriptor: () => ({ type: "host", model: "qwen3:8b" }),
        async generate() {
          throw new DOMException("cancelled", "AbortError");
        },
      },
    });
    const events: string[] = [];
    client.events.subscribe((event) => events.push(event.type));

    await expect(
      client.research({
        question: "What does the passage say about hospitality?",
        retrieval: { mode: "keyword", evidenceLimit: 1 },
      }),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(events).toContain("operation-cancelled");
  });

  it("propagates cancellation raised while loading publication records", async () => {
    const base = dataSources.inline(publicationPackage());
    const dataSource: PublicationDataSource = {
      getManifest: (options) => base.getManifest(options),
      getChunkDescriptors: (options) => base.getChunkDescriptors(options),
      async loadRecords() {
        throw new DOMException("cancelled", "AbortError");
      },
      loadVectors: (chunkId, options) => base.loadVectors(chunkId, options),
    };
    const client = await createClient({
      dataSource,
      storage: new MemoryStorage(),
    });
    const events: string[] = [];
    client.events.subscribe((event) => events.push(event.type));

    await expect(client.search({ query: "hospitality", mode: "keyword" })).rejects.toMatchObject({
      name: "AbortError",
    });
    expect(events).toContain("operation-cancelled");
  });

  it("stores annotations through the injected storage contract", async () => {
    const client = await createClient({
      dataSource: dataSources.inline(publicationPackage()),
      storage: new MemoryStorage(),
    });

    const annotation = await client.annotations.add({
      recordId: "g1",
      work: "Glas",
      quote: "hospitality gift responsibility",
      note: "Compare attribution.",
      tags: ["hospitality", "attribution"],
    });

    expect((await client.annotations.get(annotation.id))?.record_id).toBe("g1");
    expect(await client.annotations.list({ work: "Glas" })).toHaveLength(1);

    await client.annotations.remove(annotation.id);
    expect(await client.annotations.list()).toEqual([]);
  });
});
