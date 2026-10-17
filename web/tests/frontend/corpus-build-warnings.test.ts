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
import CorpusBuildWarnings from "../../src/components/CorpusBuildWarnings.vue";
import {
  groupBuildWarnings,
  currentWarningRecordIds,
} from "../../src/domain/corpusBuildPresentation";

const warning = (id: string) =>
  `${id}: work_profile metadata failed (structured_output_invalid); review required.`;
describe("Grouped build warnings", () => {
  it("acknowledges original messages without changing the current issue state", async () => {
    const messages = [warning("r1"), warning("r2")];
    const wrapper = mount(CorpusBuildWarnings, {
      props: { warnings: messages, issueSummary: { issues: [{ record_id: "r2" }] } },
    });
    await wrapper.get(".warning-groups > button").trigger("click");
    expect(wrapper.emitted("acknowledgeWarnings")).toEqual([[messages]]);
    expect(wrapper.findAll("li")).toHaveLength(2);
    expect(wrapper.findAll(".warning-records button")).toHaveLength(1);
    await wrapper.setProps({ disabled: true });
    expect(
      wrapper.findAll("button").every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
  });
  it("requires current structured membership and a recognized warning format", () => {
    const messages = [
      warning("r1"),
      warning("r1"),
      warning("r2"),
      warning("r3"),
      "r4: arbitrary failure",
      "r1-other: work_profile metadata failed (structured_output_invalid); review required.",
    ];
    expect(
      currentWarningRecordIds(messages, {
        issues: [
          { record_id: "r1", field: "stance" },
          { record_id: "r1", field: "target" },
          { record_id: "r4" },
        ],
        records: [{ record_id: "r2" }],
      }),
    ).toEqual(["r1", "r2"]);
    expect(currentWarningRecordIds(messages, undefined)).toEqual([]);
    expect(currentWarningRecordIds([warning("r3")], { issues: [{ record_id: "r30" }] })).toEqual(
      [],
    );
  });
  it("offers read navigation only for current records and updates it on refresh", async () => {
    const wrapper = mount(CorpusBuildWarnings, {
      props: {
        warnings: [warning("r1"), warning("r2")],
        issueSummary: { issues: [{ record_id: "r2", field: "stance" }] },
      },
    });
    expect(wrapper.findAll(".warning-records button")).toHaveLength(1);
    await wrapper.get(".warning-records button").trigger("click");
    expect(wrapper.emitted("review")).toEqual([["r2"]]);
    await wrapper.setProps({ disabled: true });
    expect(wrapper.get(".warning-records button").attributes("disabled")).toBeDefined();
    await wrapper.setProps({ issueSummary: { issues: [] } });
    expect(wrapper.findAll(".warning-records button")).toHaveLength(0);
    expect(wrapper.findAll("li").map((row) => row.text())).toEqual([warning("r1"), warning("r2")]);
    wrapper.unmount();
  });
  it("groups matching causes while retaining every original entry", () => {
    const messages = Array.from({ length: 100 }, (_, i) => warning(`record-${i}`));
    const groups = groupBuildWarnings(messages);
    expect(groups).toHaveLength(1);
    expect(groups[0].messages).toEqual(messages);
  });
  it("preserves unknown messages and does not infer links from arbitrary strings", () => {
    const messages = [
      "Source coverage failed.",
      "Source coverage failed.",
      "<script>alert(1)</script>",
      "record: metadata unknown",
    ];
    expect(groupBuildWarnings(messages).map((group) => group.messages.length)).toEqual([2, 1, 1]);
    const wrapper = mount(CorpusBuildWarnings, { props: { warnings: messages } });
    expect(wrapper.findAll("a,script")).toHaveLength(0);
    expect(wrapper.text()).toContain(messages[2]);
    expect(wrapper.text()).toContain("Source coverage failed.");
  });
  it("renders one collapsed summary, expands raw messages, and refreshes counts", async () => {
    const wrapper = mount(CorpusBuildWarnings, {
      props: { warnings: [warning("r1"), warning("r2")] },
    });
    expect(wrapper.get("details").attributes("open")).toBeUndefined();
    expect(wrapper.findAll(".warning-group")).toHaveLength(1);
    wrapper.get("details").element.open = true;
    expect(wrapper.findAll("li").map((row) => row.text())).toEqual([warning("r1"), warning("r2")]);
    await wrapper.setProps({ warnings: [warning("r1"), warning("r2"), warning("r3")] });
    expect(wrapper.get("details").element.open).toBe(true);
    expect(wrapper.get("details>summary").text()).toContain("3 build warning");
    await wrapper.setProps({ warnings: [] });
    expect(wrapper.find("details").exists()).toBe(false);
  });
});
