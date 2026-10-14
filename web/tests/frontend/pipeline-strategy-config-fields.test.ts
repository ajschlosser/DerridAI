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

import PipelineStrategyConfigFields from "../../src/components/pipelines/PipelineStrategyConfigFields.vue";
import type { PipelineStage, PipelineStrategy } from "../../src/types/pipelines";

const strategy: PipelineStrategy = {
  strategy_id: "llm.structured_metadata",
  version: 1,
  family: "llm",
  scholarly_effect: "generation",
  phase: "generate",
  effect_note: "generation",
  label: "Structured metadata generation",
  description: "Run one schema-derived structured metadata task.",
  input_type: "context_packet",
  output_type: "model_output",
  deterministic: false,
  invokes_llm: true,
  capabilities: ["chat_model", "structured_output"],
  config_schema: {
    type: "object",
    properties: {
      provider_role: { type: "string", enum: ["primary", "review"], default: "primary" },
      attempts: { type: "integer", minimum: 1, maximum: 4, default: 2 },
    },
  },
};

const stage: PipelineStage = {
  id: "review",
  strategy: "llm.structured_metadata",
  enabled: true,
  config: { provider_role: "review" },
  next: [],
};

describe("PipelineStrategyConfigFields", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("offers a declared enumeration as named choices and emits the chosen value", async () => {
    const wrapper = mount(PipelineStrategyConfigFields, { props: { stage, strategy } });

    const select = wrapper.get("select");
    expect(select.findAll("option").map((option) => [option.element.value, option.text()])).toEqual(
      [
        ["primary", "Primary provider"],
        ["review", "Review provider"],
      ],
    );
    expect((select.element as HTMLSelectElement).value).toBe("review");

    await select.setValue("primary");
    expect(wrapper.emitted("updateConfig")?.[0]?.slice(0, 2)).toEqual(["provider_role", "primary"]);
    expect(wrapper.get("input[type=number]").attributes("max")).toBe("4");
  });

  it("labels and bounds evidence recovery shortlist controls", () => {
    const closedChoice: PipelineStrategy = {
      ...strategy,
      strategy_id: "llm.closed_choice_evidence",
      config_schema: {
        type: "object",
        properties: {
          candidate_scope: {
            type: "string",
            enum: ["all", "input_or_all"],
            default: "input_or_all",
          },
          candidate_limit: { type: "integer", minimum: 1, maximum: 32, default: 4 },
        },
      },
    };
    const wrapper = mount(PipelineStrategyConfigFields, {
      props: {
        stage: {
          ...stage,
          strategy: "llm.closed_choice_evidence",
          config: { candidate_scope: "input_or_all", candidate_limit: 4 },
        },
        strategy: closedChoice,
      },
    });

    expect(wrapper.text()).toContain("Candidate scope");
    expect(wrapper.text()).toContain("Candidate limit");
    expect(
      wrapper
        .get("select")
        .findAll("option")
        .map((option) => option.text()),
    ).toEqual(["All Record source units", "Upstream shortlist, otherwise all"]);
    const limit = wrapper.get("input[type=number]");
    expect(limit.attributes("min")).toBe("1");
    expect(limit.attributes("max")).toBe("32");
    expect((limit.element as HTMLInputElement).value).toBe("4");
  });

  it("names evidence recovery's default primary-then-review chain", () => {
    const closedChoice: PipelineStrategy = {
      ...strategy,
      strategy_id: "llm.closed_choice_evidence",
      config_schema: {
        type: "object",
        properties: {
          provider_role: { type: "string", enum: ["chain", "primary", "review"], default: "chain" },
        },
      },
    };
    const wrapper = mount(PipelineStrategyConfigFields, {
      props: {
        stage: { ...stage, strategy: "llm.closed_choice_evidence", config: {} },
        strategy: closedChoice,
      },
    });

    expect(
      wrapper
        .get("select")
        .findAll("option")
        .map((option) => option.text()),
    ).toEqual(["Primary, then review provider", "Primary provider", "Review provider"]);
  });
});
