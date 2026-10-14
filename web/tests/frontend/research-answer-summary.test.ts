/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchAnswerWorkspace from "../../src/components/research/ResearchAnswerWorkspace.vue";
import { inferResearchPreset } from "../../src/components/research/researchPreset";

const result = {
  prompt: "What is the gift?",
  answer: "The gift annuls itself (GT 7).",
  provider: "ollama",
  model: "qwen3.5:4b",
  elapsed_seconds: 12.34,
  response_cache: { record_id: "cache-1" },
  evidence: [{ inline_citation: "(GT 7)" }, { inline_citation: "(GT 9)" }],
  rag_request: { source_collection: "derrida", k: 40, fetch_k: 320, rerank_top_n: 16 },
};

function summary(props: Record<string, unknown>) {
  const wrapper = mount(ResearchAnswerWorkspace, { props: props as never });
  return Object.fromEntries(
    wrapper
      .findAll(".research-run-summary > div")
      .map((row) => [row.find("dt").text(), row.find("dd").text()]),
  );
}

describe("research answer summary", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("shows corpus, preset, cited evidence, model, time and cache state", () => {
    expect(summary({ result })).toEqual({
      Corpus: "derrida",
      Retrieval: "High precision",
      Evidence: "1 cited of 2",
      Model: "ollama · qwen3.5:4b",
      Time: "12.3 s",
      Cached: "Cached",
    });
  });

  it("labels evidence-only runs and omits what the run did not record", () => {
    const rows = summary({
      result: {
        ...result,
        response_cache: null,
        elapsed_seconds: 0,
        rag_request: { skip_retrieval: true },
      },
    });
    expect(rows.Corpus).toBe("Evidence only");
    expect(rows.Retrieval).toBe("Selected evidence only");
    expect(rows.Cached).toBeUndefined();
    expect(rows.Time).toBeUndefined();
    expect(summary({ result: { ...result, rag_request: {} } }).Retrieval).toBeUndefined();
  });

  it("infers presets only from exact parameters", () => {
    expect(inferResearchPreset({ k: 64, fetch_k: 500, rerank_top_n: 24, lambda_mult: 0.7 })).toBe(
      "balanced",
    );
    expect(inferResearchPreset({ k: "96", fetch_k: "1000", rerank_top_n: "32" })).toBe("recall");
    expect(inferResearchPreset({ k: 64, fetch_k: 500, rerank_top_n: 24, lambda_mult: 0.5 })).toBe(
      "custom",
    );
  });
});

describe("citation highlighting", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("highlights the answer's citations for the active or previewed evidence item", async () => {
    const { default: ResearchResultPresentation } = await import(
      "../../src/components/research/ResearchResultPresentation.vue"
    );
    const twoCited = { ...result, answer: "A (GT 7). B (GT 9). C (GT 7)." };
    const wrapper = mount(ResearchResultPresentation, {
      props: { result: twoCited, activeEvidenceIndex: 0 } as never,
    });
    const highlighted = () =>
      wrapper.findAll(".research-inline-citation.highlighted").map((b) => b.text());
    expect(highlighted()).toEqual(["(GT 7)", "(GT 7)"]);
    const items = wrapper.findAll(".research-evidence-index button");
    await items[1].trigger("mouseenter");
    expect(highlighted()).toEqual(["(GT 9)"]);
    await items[1].trigger("mouseleave");
    expect(highlighted()).toEqual(["(GT 7)", "(GT 7)"]);
  });
});
