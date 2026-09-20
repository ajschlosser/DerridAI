/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { fullHttpErrorDetail } from "../../src/domain/httpErrors";
import { parsePastedRecord } from "../../src/domain/pastedRecord";
import { providerRequestConfig } from "../../src/domain/providerRequest";
import { recordHistoryVersions, upsertAuditDelta } from "../../src/domain/recordHistory";

// These behaviors were checked against the original legacy runtime.js functions across a wide input matrix.
const update = (extra: object) => ({
  field_name: "topics",
  old_value: ["a"],
  new_value: ["b"],
  timestamp: "2026-01-01T00:00:00Z",
  source: "llm",
  ...extra,
});

describe("record history", () => {
  const record = {
    text: "z",
    topics: ["b"],
    updates: [
      update({}),
      update({ field_name: "text", old_value: "o", new_value: "z", batch_id: "b1" }),
    ],
  };
  it("rebuilds every version from the audit trail", () => {
    const versions = recordHistoryVersions(record);
    expect(versions.map((v) => v.label)).toEqual(["Original", "Version 1", "Version 2"]);
    expect(versions[0].record).toMatchObject({ text: "o", topics: ["a"] });
    expect(versions[1].record).toMatchObject({ topics: ["b"] });
    expect(versions[2]).toMatchObject({ source: "llm", record: { text: "z" } });
    expect(versions[2].record).not.toHaveProperty("updates");
  });
  it("sends only new audit entries to the database", () => {
    expect(upsertAuditDelta(record, { updates_count: 1 }, true)).toMatchObject({
      audit_entries: [record.updates[1]],
      replace_updates: null,
      updates_count: 2,
    });
    expect(upsertAuditDelta(record, { updates_count: 5 }, true).replace_updates).toHaveLength(2);
    expect(upsertAuditDelta(record, null, false).replace_updates).toHaveLength(2);
    expect(upsertAuditDelta(record, null, true)).toEqual({
      audit_entries: [],
      replace_updates: null,
      updates_count: 2,
    });
  });
});

describe("provider request config", () => {
  it("returns null without a profile", () => {
    expect(providerRequestConfig(null)).toBeNull();
  });
  it("maps an Ollama profile", () => {
    const config = providerRequestConfig({
      id: "p",
      type: "ollama",
      model: "m",
      num_ctx: 8192,
      num_predict: 100,
      metadata_num_predict: 50,
      think: "low",
      temperature: "",
      extra_options: "{bad",
      max_concurrent_requests: 200,
    });
    expect(config).toMatchObject({
      provider_profile_id: "p",
      provider: "ollama",
      max_concurrent_requests: 64,
      api_key: null,
      ollama: {
        num_ctx: 8192,
        num_predict: 50,
        think: "low",
        temperature: null,
        extra_options: {},
      },
    });
    expect(
      providerRequestConfig({ id: "p", type: "ollama", num_predict: 100 }, { textReview: true })
        ?.ollama.num_predict,
    ).toBe(100);
  });
  it("maps an OpenAI profile", () => {
    expect(
      providerRequestConfig({
        id: "o",
        type: "openai",
        model_mode: "auto",
        api_key: "k",
        model: "x",
      }),
    ).toMatchObject({
      model: "auto",
      api_key: "k",
      max_concurrent_requests: 32,
      ollama: { num_ctx: null, think: null, keep_alive: null },
    });
  });
});

describe("pasted records", () => {
  it("accepts one JSON or JSONL record, with or without a code fence", () => {
    expect(parsePastedRecord("")).toBeNull();
    expect(parsePastedRecord('{"a":1}')).toEqual({ a: 1 });
    expect(parsePastedRecord('[{"a":1}]')).toEqual({ a: 1 });
    expect(parsePastedRecord('```json\n{"a":1}\n```')).toEqual({ a: 1 });
  });
  it("rejects several records or non-objects", () => {
    expect(() => parsePastedRecord('[{"a":1},{"b":2}]')).toThrow(
      "Paste exactly one JSON/JSONL record",
    );
    expect(() => parsePastedRecord("5")).toThrow("Paste exactly one JSON/JSONL record");
    expect(() => parsePastedRecord('{"a":1}\n{"b":2}')).toThrow(
      "Paste exactly one JSON/JSONL record",
    );
    expect(() => parsePastedRecord("not json")).toThrow();
  });
});

describe("HTTP error detail", () => {
  it("prefers the most specific message", () => {
    expect(fullHttpErrorDetail({ detail: " msg " }, "raw")).toBe("msg");
    expect(fullHttpErrorDetail({ detail: [{ loc: ["body", "x"], msg: "bad" }, "str"] }, "")).toBe(
      "body.x: bad; str",
    );
    expect(fullHttpErrorDetail({ detail: { error: "de" } }, "")).toBe("de");
    expect(fullHttpErrorDetail({ detail: { a: 1 } }, "")).toBe('{"a":1}');
    expect(fullHttpErrorDetail(null, " raw ", "Not Found")).toBe("raw");
    expect(fullHttpErrorDetail({}, "", "Not Found")).toBe("Not Found");
    expect(fullHttpErrorDetail({}, "")).toBe("Request failed");
  });
});
