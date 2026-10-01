/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import PipelineRunTracePanel from "../../src/components/pipelines/PipelineRunTracePanel.vue";
import type { PipelineRunTrace } from "../../src/types/pipelines";

function trace(warnings: string[]): PipelineRunTrace {
  return {
    run_id: "run-1",
    feature: "evidence_recovery",
    pipeline_id: "evidence.recovery.bound",
    pipeline_version: 1,
    resolved_pipeline: {},
    resolved_hash: "abc",
    status: "completed",
    started_at: "2026-10-01T00:00:00Z",
    finished_at: "2026-10-01T00:00:01Z",
    total_elapsed_ms: 10,
    warnings,
    stages: [],
  };
}

describe("PipelineRunTracePanel rewired runs", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("flags rewired ports outside the collapsed warnings and keeps other warnings", () => {
    const wrapper = mount(PipelineRunTracePanel, {
      props: {
        trace: trace([
          "rewired_inputs: provenance.candidates, select.candidates",
          "Something else.",
        ]),
      },
    });
    const notice = wrapper.get(".rewired-notice");
    expect(notice.attributes("role")).toBe("note");
    expect(notice.findAll("code").map((c) => c.text())).toEqual([
      "provenance.candidates",
      "select.candidates",
    ]);
    const details = wrapper.get(".run-warnings");
    expect(details.text()).toContain("Something else.");
    expect(details.text()).not.toContain("rewired_inputs");
  });

  it("shows nothing for a run without rewiring", () => {
    const wrapper = mount(PipelineRunTracePanel, { props: { trace: trace([]) } });
    expect(wrapper.find(".rewired-notice").exists()).toBe(false);
    expect(wrapper.find(".run-warnings").exists()).toBe(false);
  });
});
