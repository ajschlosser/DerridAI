// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MetadataPrecedents } from "../../src/api/corpus";
import CorpusFieldPrecedents from "../../src/components/CorpusFieldPrecedents.vue";
import CorpusRecordResearchClaims from "../../src/components/CorpusRecordResearchClaims.vue";
import SchemaFieldForm from "../../src/components/metadata-schemas/SchemaFieldForm.vue";
import { blankField } from "../../src/api/metadataSchemas";
import { describeDecisionResult } from "../../src/features/corpus-builder/domain/metadataDecisions";

const precedents: MetadataPrecedents = {
  field: "mood",
  record_id: "r1",
  mode: "semantic",
  fallback_reason: "",
  items: [
    {
      record_id: "r2",
      value: "calm",
      kind: "correction",
      rejected_value: "angry",
      similarity: 0.8,
      evidence_bound: true,
      evidence: "Measured tone.",
    },
  ],
};

describe("reviewed precedents in Record Review", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads only when opened and exposes the disclosure state", async () => {
    const load = vi.fn().mockResolvedValue(precedents);
    const wrapper = mount(CorpusFieldPrecedents, {
      props: { buildId: "b1", recordId: "r1", field: "mood", fieldLabel: "Mood", load },
    });
    const toggle = wrapper.get("button");
    expect(load).not.toHaveBeenCalled();
    expect(toggle.attributes("aria-expanded")).toBe("false");

    await toggle.trigger("click");
    await flushPromises();

    expect(load).toHaveBeenCalledWith("b1", "r1", "mood");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(`#${toggle.attributes("aria-controls")}`).text()).toContain(
      "Measured tone.",
    );
    // A correction shows both the rejected model value and the reviewer's value.
    expect(wrapper.text()).toContain("angry");
    expect(wrapper.text()).toContain("calm");
  });

  it("reports a load failure as an alert instead of an empty list", async () => {
    const load = vi.fn().mockRejectedValue(new Error("store offline"));
    const wrapper = mount(CorpusFieldPrecedents, {
      props: { buildId: "b1", recordId: "r1", field: "mood", fieldLabel: "Mood", load },
    });
    await wrapper.get("button").trigger("click");
    await flushPromises();
    expect(wrapper.get("[role=alert]").text()).toContain("store offline");
  });

  it("marks Research claims bound to an earlier revision as stale", async () => {
    const load = vi.fn().mockResolvedValue({
      items: [
        { claim_id: "c1", claim_text: "Current", citation: {}, binding_status: "current" },
        { claim_id: "c2", claim_text: "Old", citation: {}, binding_status: "stale" },
      ],
    });
    const wrapper = mount(CorpusRecordResearchClaims, {
      props: { buildId: "b1", recordId: "r1", load },
    });
    await wrapper.get("button").trigger("click");
    await flushPromises();
    const tones = wrapper.findAll(".ui-status-badge").map((badge) => badge.attributes("data-tone"));
    expect(tones).toEqual(["success", "warning"]);
  });
});

describe("retrieval policy editor", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("adds and removes analogy conditions by stable field identity", async () => {
    const field = blankField();
    const wrapper = mount(SchemaFieldForm, {
      props: {
        field,
        groupKeys: ["discourse"],
        matchOptions: [{ fieldId: "field-genre", label: "Genre" }],
      },
    });
    const genre = wrapper
      .findAll("label.check")
      .find((label) => label.text() === "Genre")!
      .get("input");
    await genre.setValue(true);
    expect(field.retrieval_profile.match_field_ids).toEqual(["field-genre"]);
    await genre.setValue(false);
    expect(field.retrieval_profile.match_field_ids).toEqual([]);
  });
});

describe("batch decision summary", () => {
  const tf = (key: string, values?: unknown) => `${key}:${JSON.stringify(values ?? {})}`;

  it("never reports a deferred field as saved and escalates memory warnings", () => {
    const summary = describeDecisionResult(
      { changed_fields: ["mood"], deferred_fields: ["genre"], warnings: ["store offline"] },
      tf as never,
    );
    expect(summary.message).toContain('pdf_corpus.llm_suggestions_saved:{"count":1}');
    expect(summary.message).toContain('pdf_corpus.metadata_decisions_deferred:{"count":1}');
    expect(summary.message).toContain("store offline");
    expect(summary.tone).toBe("error");
  });

  it("is a notice when everything was saved", () => {
    const summary = describeDecisionResult(
      { changed_fields: ["mood", "genre"], deferred_fields: [], warnings: [] },
      tf as never,
    );
    expect(summary.tone).toBe("notice");
  });
});
