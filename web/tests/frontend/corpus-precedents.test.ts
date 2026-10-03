/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MetadataPrecedents } from "../../src/api/corpus";
import CorpusFieldPrecedents from "../../src/components/CorpusFieldPrecedents.vue";
import CorpusMetadataFieldEditor from "../../src/components/CorpusMetadataFieldEditor.vue";
import { precedentEvidenceSuggestions } from "../../src/domain/metadataPrecedents";
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

    expect(load).toHaveBeenCalledWith("b1", "r1", "mood", false);
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(`#${toggle.attributes("aria-controls")}`).text()).toContain(
      "Measured tone.",
    );
    // A correction shows both the rejected model value and the reviewer's value.
    expect(wrapper.text()).toContain("angry");
    expect(wrapper.text()).toContain("calm");
  });

  it("ignores a late precedent response from a different build", async () => {
    let release!: (result: MetadataPrecedents) => void;
    const load = vi
      .fn()
      .mockImplementationOnce(
        () => new Promise<MetadataPrecedents>((resolve) => (release = resolve)),
      )
      .mockResolvedValue({ ...precedents, items: [] });
    const wrapper = mount(CorpusFieldPrecedents, {
      props: { buildId: "b1", recordId: "r1", field: "mood", fieldLabel: "Mood", load },
    });
    await wrapper.get("button").trigger("click");
    await wrapper.setProps({ buildId: "b2" });
    await flushPromises();
    release(precedents);
    await flushPromises();
    expect(wrapper.text()).not.toContain("Measured tone.");
    wrapper.unmount();
  });

  it("shows the count of kept precedents without opening or loading", async () => {
    const load = vi.fn();
    const wrapper = mount(CorpusFieldPrecedents, {
      props: {
        buildId: "b1",
        recordId: "r1",
        field: "mood",
        fieldLabel: "Mood",
        load,
        preloaded: { ...precedents, source: "enrichment", stale_count: 2 },
      },
    });
    expect(wrapper.get("button").text()).toContain("1 found");
    await wrapper.get("button").trigger("click");
    expect(load).not.toHaveBeenCalled();
    // One status line says where the list came from and what is hidden.
    const status = wrapper.findAll("[role=status]");
    expect(status).toHaveLength(1);
    expect(status[0].text()).toContain("2");
    expect(wrapper.findAll("button").some((button) => button.text() === "Search again")).toBe(
      false,
    );
  });

  it("is not offered when enrichment kept no precedents for the field", () => {
    const wrapper = mount(CorpusFieldPrecedents, {
      props: {
        buildId: "b1",
        recordId: "r1",
        field: "mood",
        fieldLabel: "Mood",
        load: vi.fn(),
        preloaded: { ...precedents, source: "enrichment", items: [] },
      },
    });
    expect(wrapper.find(".field-precedents").exists()).toBe(false);
  });

  it("keeps loaded precedents when a poll re-renders the same record", async () => {
    const load = vi.fn().mockResolvedValue(precedents);
    const wrapper = mount(CorpusFieldPrecedents, {
      props: { buildId: "b1", recordId: "r1", field: "mood", fieldLabel: "Mood", load },
    });
    await wrapper.get("button").trigger("click");
    await flushPromises();
    await wrapper.setProps({ sourceBlockIds: ["b-1"], fieldLabel: "Mood" });
    await flushPromises();
    expect(load).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Measured tone.");
  });

  it("searches again on request instead of trusting the kept list", async () => {
    const load = vi.fn().mockResolvedValue({ ...precedents, source: "live", items: [] });
    const wrapper = mount(CorpusFieldPrecedents, {
      props: {
        buildId: "b1",
        recordId: "r1",
        field: "mood",
        fieldLabel: "Mood",
        load,
        preloaded: precedents,
      },
    });
    await wrapper.get("button").trigger("click");
    const again = wrapper.findAll("button").find((button) => button.text() === "Search again")!;
    await again.trigger("click");
    await flushPromises();
    expect(load).toHaveBeenCalledWith("b1", "r1", "mood", true);
    expect(wrapper.get("button").text()).toContain("0 found");
  });

  it("uses a precedent's value without carrying its evidence, and lists this record's passages", async () => {
    const preloaded: MetadataPrecedents = {
      ...precedents,
      items: [
        {
          record_id: "r2",
          value: "calm",
          evidence_bound: true,
          evidence: "Their words.",
          candidate_source_units: [
            { block_id: "own-2", score: 0.72, method: "precedent-semantic-v1", page: 10 },
            { block_id: "own-3", score: 0.5, method: "precedent-semantic-v1" },
          ],
        },
        { record_id: "r3", value: null, kind: "absence", evidence_bound: true, evidence: "None." },
      ],
    };
    const wrapper = mount(CorpusFieldPrecedents, {
      props: {
        buildId: "b1",
        recordId: "r1",
        field: "mood",
        fieldLabel: "Mood",
        preloaded,
        sourceBlockIds: ["own-1", "own-2", "own-3"],
      },
    });
    await wrapper.get("button").trigger("click");
    const use = wrapper.findAll("button").filter((button) => button.text() === "Use this value");
    expect(use).toHaveLength(1); // a confirmed absence has no value to use
    await use[0].trigger("click");
    expect(wrapper.emitted("use")).toEqual([["calm"]]);
    expect(wrapper.text()).toContain("p. 10 (72%)");
    expect(wrapper.text()).toContain("passage 3 (50%)");
  });

  it("offers only this record's own blocks as evidence suggestions, best score per block", () => {
    const result: MetadataPrecedents = {
      ...precedents,
      items: [
        {
          record_id: "r2",
          value: "calm",
          evidence_bound: true,
          candidate_source_units: [
            { block_id: "own-1", score: 0.4, method: "precedent-lexical-v1" },
            { block_id: "their-9", score: 0.99, method: "precedent-lexical-v1" },
          ],
        },
        {
          record_id: "r3",
          value: "calm",
          evidence_bound: true,
          candidate_source_units: [
            { block_id: "own-1", score: 0.8, method: "precedent-semantic-v1" },
            { block_id: "own-2", score: 0.6, method: "precedent-semantic-v1" },
          ],
        },
      ],
    };
    expect(precedentEvidenceSuggestions(result, ["own-1", "own-2"])).toEqual([
      { block_id: "own-1", score: 0.8, method: "precedent-semantic-v1", reason: "" },
      { block_id: "own-2", score: 0.6, method: "precedent-semantic-v1", reason: "" },
    ]);
  });

  it("fills the field's draft from a used precedent without saving it", async () => {
    const wrapper = mount(CorpusMetadataFieldEditor, {
      props: { field: "mood", value: null, control: "text", open: true },
    });
    await wrapper.setProps({ prefill: { value: "calm", key: 1 } });
    expect((wrapper.get("[role=combobox]").element as HTMLTextAreaElement).value).toBe("calm");
    expect(wrapper.emitted("save")).toBeUndefined();
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
