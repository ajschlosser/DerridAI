import {
  createClient,
  dataSources,
  MemoryStorage,
  type EmbeddingProvider,
  type GenerationProvider,
} from "@derridai/sdk";

const publication = {
  manifest: {
    format: "derridai-static-site-v4",
    publication_id: "consumer-fixture",
    title: "Consumer fixture",
    locale: "en-US",
    works: [{ work: "Glas", record_count: 1 }],
    vector_index: {
      model: "fixture-embed",
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
      id: "glas",
      work: "Glas",
      record_count: 1,
      records_b64: btoa(
        JSON.stringify([
          {
            record_id: "r1",
            source_document_id: "source-1",
            source_spans: [{ source_document_id: "source-1", source_unit_id: "unit-r1" }],
            work: "Glas",
            citation: "Derrida, Jacques. Glas.",
            text: "Hospitality and responsibility.",
          },
        ]),
      ),
      vector_ids: ["r1"],
      vectors_b64: (() => {
        const bytes = new Uint8Array(new Float32Array([1, 0]).buffer);
        let binary = "";
        for (const byte of bytes) binary += String.fromCharCode(byte);
        return btoa(binary);
      })(),
    },
  ],
};

const embeddings: EmbeddingProvider = {
  descriptor: () => ({ type: "fixture", model: "fixture-embed" }),
  async embed() {
    return { vectors: [[1, 0]], provider: this.descriptor() };
  },
};

const generation: GenerationProvider = {
  descriptor: () => ({ type: "fixture", model: "fixture-generate" }),
  async generate() {
    return { text: "Fixture answer [E1].", provider: this.descriptor() };
  },
};

async function smokeTest() {
  const client = await createClient({
    dataSource: dataSources.inline(publication),
    storage: new MemoryStorage(),
    embeddings,
    generation,
  });

  const search = await client.search({ query: "hospitality", mode: "hybrid" });
  if (search.results[0]?.record.record_id !== "r1") {
    throw new Error("SDK consumer fixture search failed.");
  }

  const research = await client.research({
    question: "What does the record say about hospitality?",
    retrieval: { evidenceLimit: 1 },
  });
  if (research.answer !== "Fixture answer [E1]." || research.evidencePacket.evidence.length !== 1) {
    throw new Error("SDK consumer fixture Research failed.");
  }
}

void smokeTest();
