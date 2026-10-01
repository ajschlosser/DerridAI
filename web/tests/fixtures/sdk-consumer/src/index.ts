import {
  createClient,
  dataSources,
  MemoryStorage,
  type EmbeddingProvider,
  type GenerationProvider,
  type PublicationRecord,
} from "@derridai/sdk";

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

const record: PublicationRecord = {
  record_id: "consumer-r1",
  source_document_id: "consumer-source",
  source_spans: [
    {
      source_document_id: "consumer-source",
      source_unit_id: "consumer-unit",
      printed_page: 12,
    },
  ],
  work: "Glas",
  citation: "Derrida, Jacques. Glas.",
  text: "Hospitality exceeds conditional exchange.",
  speaker: "Derrida",
  position_holder: "Derrida",
  stance: "argues",
};

const publication = {
  manifest: {
    format: "derridai-static-site-v4",
    publication_id: "consumer-publication",
    title: "SDK consumer fixture",
    locale: "en-US",
    works: [{ work: "Glas", record_count: 1 }],
    vector_index: {
      model: "fixture-embedding",
      revision: "1",
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
      records_b64: base64Json([record]),
      vector_ids: ["consumer-r1"],
      vectors_b64: base64Float32([[1, 0]]),
    },
  ],
};

const embeddings: EmbeddingProvider = {
  descriptor: () => ({ type: "fixture", model: "fixture-embedding", revision: "1" }),
  async embed() {
    return {
      vectors: [[1, 0]],
      provider: { type: "fixture", model: "fixture-embedding", revision: "1" },
    };
  },
};

const generation: GenerationProvider = {
  descriptor: () => ({ type: "fixture", model: "fixture-generation" }),
  async generate() {
    return {
      text: "The fixture answer is grounded in [E1].",
      provider: { type: "fixture", model: "fixture-generation" },
    };
  },
};

const client = await createClient({
  dataSource: dataSources.inline(publication),
  storage: new MemoryStorage(),
  embeddings,
  generation,
});

const search = await client.search({ query: "hospitality", mode: "hybrid" });
if (search.results[0]?.record.record_id !== "consumer-r1") {
  throw new Error("Installed SDK failed its external-consumer search smoke test.");
}

const research = await client.research({
  question: "What does the passage say about hospitality?",
  retrieval: { mode: "hybrid", evidenceLimit: 1 },
});
if (!research.answer?.includes("[E1]") || research.evidencePacket.evidence[0]?.recordId !== "consumer-r1") {
  throw new Error("Installed SDK failed its external-consumer Research smoke test.");
}

if (typeof document !== "undefined") {
  document.querySelector("#app")?.replaceChildren("DerridAI SDK consumer OK");
}
