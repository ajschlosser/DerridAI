/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  finiteResearchNumber,
  normalizedResearchConfig,
  researchEvidenceForUi,
  researchJobForUi,
  researchProfileForUi,
  sanitizeResearchGeneration,
} from "../../src/domain/researchPayloads";

// These behaviors were checked against the original legacy runtime.js functions across a wide input matrix.
describe("research payloads", () => {
  it("clamps numbers and falls back on invalid input", () => {
    expect(finiteResearchNumber("abc", 5)).toBe(5);
    expect(finiteResearchNumber("", null)).toBeNull();
    expect(finiteResearchNumber(7.9, 0, { integer: true, min: 0, max: 5 })).toBe(5);
    expect(finiteResearchNumber(-3, 0, { min: 0 })).toBe(0);
  });

  it("sanitizes generation options", () => {
    expect(
      sanitizeResearchGeneration({
        num_ctx: "100",
        temperature: 9,
        think: "HIGH",
        keep_alive: " 5m ",
        stop: ["x", ""],
      }),
    ).toEqual({
      num_ctx: 512,
      temperature: 2,
      think: "high",
      keep_alive: "5m",
      stop: ["x"],
      extra_options: {},
    });
    expect(sanitizeResearchGeneration({ think: "false", extra_options: '{"a":1}' })).toEqual({
      think: false,
      extra_options: { a: 1 },
    });
    expect(sanitizeResearchGeneration(null)).toEqual({ extra_options: {} });
  });

  it("normalizes the Research configuration", () => {
    const cfg = normalizedResearchConfig({
      k: 9999,
      locales: ["en", "xx"],
      reranker: "nope",
      bind_citations: false,
    });
    expect(cfg).toMatchObject({
      k: 500,
      locales: ["en"],
      reranker: "cross_encoder",
      response_language: "auto",
      bind_citations: false,
      include_works_cited: true,
      fetch_k: 500,
      lambda_mult: 0.7,
    });
    expect(normalizedResearchConfig().search_types).toEqual(["similarity", "lexical", "mmr"]);
  });

  it("shapes profiles, evidence and jobs for the UI", () => {
    expect(researchProfileForUi(null)).toBeNull();
    expect(researchProfileForUi({ id: "p", seed: 0, api_key: "secret" })).toEqual({
      id: "p",
      seed: 0,
    });
    expect(researchEvidenceForUi({ key: "k", kind: "workspace", page_start: 0 })).toMatchObject({
      key: "k",
      page_start: 0,
      page_end: null,
      work: "",
    });
    expect(researchJobForUi({ id: "j", result: { prompt: "p" }, completed: "3" })).toMatchObject({
      id: "j",
      prompt: "p",
      completed: 3,
      events: [],
      request: null,
    });
    expect(researchJobForUi(undefined)).toBeNull();
  });
});
