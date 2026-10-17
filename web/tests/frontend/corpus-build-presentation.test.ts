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

// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import type { CorpusBuild } from "../../src/api/pdfCorpus";
import { corpusRecordCounts, metadataTaskProgress } from "../../src/domain/corpusBuildPresentation";
import CorpusMetadataLiveStatus from "../../src/components/CorpusMetadataLiveStatus.vue";

const tasks = {
  metadata_tasks_total: 1110,
  metadata_tasks_completed: 900,
  metadata_tasks_failed: 70,
  metadata_tasks_skipped: 3,
  metadata_tasks_running: 0,
  metadata_tasks_queued: 137,
};
const build = (overrides: Partial<CorpusBuild> = {}): CorpusBuild => ({
  build_id: "b1",
  asset_id: "a1",
  source_filename: "source.pdf",
  source_sha256: "sha",
  status: "running",
  stage: "enriching",
  progress: 0.85,
  created_at: "",
  record_count: 370,
  accepted_count: 0,
  needs_review_count: 251,
  profile_id: "test",
  ...tasks,
  ...overrides,
});

describe("Corpus build presentation", () => {
  it("counts settlement separately from success and preserves explicit zero", () => {
    expect(metadataTaskProgress(tasks)).toMatchObject({
      settled: 973,
      complete: 900,
      queued: 137,
      running: 0,
      determinate: true,
    });
    expect(metadataTaskProgress({ ...tasks, metadata_tasks_queued: 0 }).queued).toBe(0);
  });
  it("does not estimate missing totals or counters from record counts", () => {
    expect(metadataTaskProgress({ record_count: 370 }).total).toBeNull();
    expect(metadataTaskProgress({ ...tasks, metadata_tasks_skipped: undefined }).determinate).toBe(
      false,
    );
    expect(metadataTaskProgress({ ...tasks, metadata_tasks_queued: undefined }).queued).toBeNull();
  });
  it.each([0, -1, NaN, Infinity, 1.5])("keeps invalid or zero total %s indeterminate", (total) => {
    expect(metadataTaskProgress({ ...tasks, metadata_tasks_total: total }).determinate).toBe(false);
  });
  it("rejects over-total settlement and overcommitted snapshots without hiding raw counts", () => {
    expect(metadataTaskProgress({ ...tasks, metadata_tasks_completed: 1251 })).toMatchObject({
      settled: 1324,
      inconsistent: true,
      fraction: null,
    });
    expect(metadataTaskProgress({ ...tasks, metadata_tasks_running: 1 }).inconsistent).toBe(true);
  });
  it("keeps overlapping issue queues independent of record totals", () => {
    expect(
      corpusRecordCounts(
        build({ review_queue_counts: { issues: 251, metadata: 200, source: 100 } }),
      ),
    ).toMatchObject({ total: 370, issues: 251, metadata: 200, source: 100, ready: null });
  });
});

describe("Metadata task status", () => {
  it("exposes valid settlement with bounded progress semantics and separate outcomes", () => {
    const wrapper = mount(CorpusMetadataLiveStatus, { props: { build: build() } });
    expect(wrapper.get('[role="progressbar"]').attributes()).toMatchObject({
      "aria-valuenow": "973",
      "aria-valuemax": "1110",
    });
    expect(wrapper.text()).toContain("70 failed");
    expect(wrapper.text()).toContain("3 skipped");
  });
  it("makes inconsistent progress indeterminate and retains original diagnostics", () => {
    const wrapper = mount(CorpusMetadataLiveStatus, {
      props: { build: build({ metadata_tasks_completed: 1251 }) },
    });
    expect(wrapper.text()).toContain("Updating task counts");
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuenow")).toBeUndefined();
    expect(wrapper.text()).toContain("1251");
  });
  it("does not invent a total or saved checkpoint from last task progress", () => {
    const wrapper = mount(CorpusMetadataLiveStatus, {
      props: {
        build: build({
          metadata_tasks_total: undefined,
          metadata_last_progress_at: "2026-10-15T20:00:00Z",
        }),
      },
    });
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuemax")).toBeUndefined();
    expect(wrapper.find(".saved-indicator").exists()).toBe(false);
  });
  it("preserves settle/cancel emissions and disabled actions", async () => {
    const wrapper = mount(CorpusMetadataLiveStatus, { props: { build: build() } });
    await wrapper.get(".status-actions button").trigger("click");
    await wrapper.findAll(".status-actions button")[1].trigger("click");
    expect(wrapper.emitted("settle")).toHaveLength(1);
    expect(wrapper.emitted("cancel")).toHaveLength(1);
    await wrapper.setProps({ disabled: true });
    expect(
      wrapper
        .findAll(".status-actions button")
        .every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
  });
});
