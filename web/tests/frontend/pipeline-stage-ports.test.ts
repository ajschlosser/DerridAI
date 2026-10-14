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

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import PipelineStagePorts from "../../src/components/pipelines/PipelineStagePorts.vue";
import { bindInput } from "../../src/domain/pipelineBindings";
import type {
  PipelineDefinition,
  PipelineStage,
  PipelineStageWiring,
  PipelineWiringInput,
} from "../../src/types/pipelines";

const stage: PipelineStage = {
  id: "pick",
  strategy: "select.top_k",
  enabled: true,
  config: {},
  next: [],
};

function limitRow(overrides: Partial<PipelineWiringInput> = {}): PipelineWiringInput {
  return {
    port: "limit",
    data_type: "number",
    required: false,
    multiple: false,
    accepts_constant: true,
    minimum: 1,
    maximum: 1000,
    explicit: false,
    status: "optional_unbound",
    sources: [],
    options: [],
    ...overrides,
  };
}

const wiringOf = (row: PipelineWiringInput): PipelineStageWiring => ({
  inputs: [row],
  outputs: [],
});

describe("fixed values on tuning ports", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("offers a fixed number only on ports that accept one", () => {
    const tuning = mount(PipelineStagePorts, { props: { stage, wiring: wiringOf(limitRow()) } });
    expect(tuning.find('option[value="constant"]').exists()).toBe(true);
    const plain = mount(PipelineStagePorts, {
      props: { stage, wiring: wiringOf(limitRow({ accepts_constant: false })) },
    });
    expect(plain.find('option[value="constant"]').exists()).toBe(false);
  });

  it("choosing it binds the port's minimum, then the number input rebinds", async () => {
    const wrapper = mount(PipelineStagePorts, { props: { stage, wiring: wiringOf(limitRow()) } });
    await wrapper.get("select").setValue("constant");
    expect(wrapper.emitted("bind")?.[0]).toEqual(["limit", { kind: "constant", value: 1 }]);

    const bound = limitRow({
      explicit: true,
      status: "bound",
      sources: [
        {
          kind: "constant",
          value: 5,
          stage: null,
          output: null,
          name: null,
          data_type: "number",
          via: "constant",
          explicit: true,
          producer_enabled: true,
        },
      ],
    });
    await wrapper.setProps({ wiring: wiringOf(bound) });
    const input = wrapper.get('input[type="number"]');
    expect((input.element as HTMLInputElement).value).toBe("5");
    expect(input.attributes("min")).toBe("1");
    await input.setValue("12");
    expect(wrapper.emitted("bind")?.[1]).toEqual(["limit", { kind: "constant", value: 12 }]);
  });

  it("ignores an empty or non-numeric entry", async () => {
    const bound = limitRow({
      explicit: true,
      status: "bound",
      sources: [
        {
          kind: "constant",
          value: 5,
          stage: null,
          output: null,
          name: null,
          data_type: "number",
          via: "constant",
          explicit: true,
          producer_enabled: true,
        },
      ],
    });
    const wrapper = mount(PipelineStagePorts, { props: { stage, wiring: wiringOf(bound) } });
    await wrapper.get('input[type="number"]').setValue("");
    expect(wrapper.emitted("bind")).toBeUndefined();
  });

  it("stores a constant binding in the definition and clears it with null", () => {
    const pipeline: PipelineDefinition = {
      pipeline_id: "p",
      version: 1,
      name: "P",
      purpose: "vector_store_search",
      status: "draft",
      entry_stage_ids: ["pick"],
      stages: [stage],
    };
    const bound = bindInput(pipeline, "pick", "limit", { kind: "constant", value: 3 });
    expect(bound?.pipeline.stages[0].inputs).toEqual({ limit: [{ source: "constant", value: 3 }] });
    expect(bound?.added).toBeNull();
    expect(
      bindInput(bound!.pipeline, "pick", "limit", null)?.pipeline.stages[0].inputs,
    ).toBeUndefined();
    expect(
      bindInput(pipeline, "pick", "limit", { kind: "constant", value: Number.NaN }),
    ).toBeNull();
  });
});
