/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  CORPUS_BUILD_ID,
  CORPUS_RECORDS,
  STORE_RECORDS,
  graphqlDefaults,
} from "../e2e/support/mock-backend";

describe("mock-backend GraphQL derivation", () => {
  it("derives CorpusReviewQueue rows and counts from the REST corpus-builds default", () => {
    const result = graphqlDefaults(
      "CorpusReviewQueue",
      { build_id: CORPUS_BUILD_ID, filter: { queue: "all", query: "" }, offset: 0, limit: 5 },
      {},
      "admin",
    ) as any;
    const queue = result.data.corpus_build.review_queue;
    expect(queue.rows).toHaveLength(5);
    expect(queue.total).toBe(CORPUS_RECORDS.length);
    expect(queue.rows[0].record_id).toBe(CORPUS_RECORDS[0].record_id);
    expect(queue.counts.all).toBeGreaterThan(0);
  });

  it("reflects a scenario's REST fixture override in the derived GraphQL row", () => {
    const result = graphqlDefaults(
      "CorpusReviewQueue",
      { build_id: CORPUS_BUILD_ID, filter: { queue: "all", query: "" }, offset: 0, limit: 50 },
      {
        [`GET /api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: {
          items: [
            {
              record_id: "custom-1",
              text: "Custom overridden text",
              text_length: 23,
              review_state: "ready",
              review_disposition: "pending",
            },
          ],
          total: 1,
          offset: 0,
          limit: 50,
        },
      },
      "admin",
    ) as any;
    const queue = result.data.corpus_build.review_queue;
    expect(queue.rows).toHaveLength(1);
    expect(queue.rows[0].record_id).toBe("custom-1");
    expect(queue.rows[0].text_preview).toBe("Custom overridden text");
  });

  it("filters CorpusQueueRows, CorpusReviewRecords and CorpusQueueTexts by record_ids", () => {
    const ids = [CORPUS_RECORDS[3].record_id, CORPUS_RECORDS[7].record_id];
    const variables = { build_id: CORPUS_BUILD_ID, record_ids: ids };

    const rows = (graphqlDefaults("CorpusQueueRows", variables, {}, "admin") as any).data
      .corpus_build.rows;
    expect(rows.map((r: any) => r.record_id).sort()).toEqual([...ids].sort());

    const records = (graphqlDefaults("CorpusReviewRecords", variables, {}, "admin") as any).data
      .corpus_build.records;
    expect(records).toHaveLength(2);
    expect(records[0].review_document.record_id).toBe(records[0].record_id);

    const texts = (graphqlDefaults("CorpusQueueTexts", variables, {}, "admin") as any).data
      .corpus_build.records;
    expect(texts.map((r: any) => r.record_id).sort()).toEqual([...ids].sort());
  });

  it("derives VectorStoreBrowse works and a paginated row page from the REST store default", () => {
    const result = graphqlDefaults(
      "VectorStoreBrowse",
      { name: "derrida_primary", include_records: true, offset: 0, limit: 2 },
      {},
      "admin",
    ) as any;
    const store = result.data.vector_store;
    expect(store.works).toEqual([
      { work: "On Cosmopolitanism and Forgiveness", record_count: STORE_RECORDS.length },
    ]);
    expect(store.records.rows).toHaveLength(2);
    expect(store.records.total).toBe(STORE_RECORDS.length);
    expect(store.records.rows[0].chroma_id).toBe(STORE_RECORDS[0]._chroma_id);
  });

  it("omits the records page when include_records is false", () => {
    const result = graphqlDefaults(
      "VectorStoreBrowse",
      { name: "derrida_primary", include_records: false, offset: 0, limit: 50 },
      {},
      "admin",
    ) as any;
    expect(result.data.vector_store.records).toBeNull();
  });

  it("resolves StoredRecordTrace to the matching stored record by chroma_id", () => {
    const result = graphqlDefaults(
      "StoredRecordTrace",
      { name: "derrida_primary", chroma_id: "r2" },
      {},
      "admin",
    ) as any;
    const record = result.data.vector_store.record;
    expect(record.record_id).toBe(STORE_RECORDS[1].record_id);
    expect(record.document).toEqual(STORE_RECORDS[1]);
    expect(record.graph.nodes).toEqual([]);
  });

  it("returns null for a chroma_id that is not in the store", () => {
    const result = graphqlDefaults(
      "StoredRecordTrace",
      { name: "derrida_primary", chroma_id: "missing" },
      {},
      "admin",
    ) as any;
    expect(result.data.vector_store.record).toBeNull();
  });

  it("still reports a helpful error for an operation with no fixture", () => {
    const result = graphqlDefaults("SomeFutureOperation", {}, {}, "admin") as any;
    expect(result.errors[0].message).toContain("SomeFutureOperation");
  });
});
