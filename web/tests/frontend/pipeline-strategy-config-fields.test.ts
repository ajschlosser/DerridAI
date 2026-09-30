/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import PipelineStrategyConfigFields from "../../src/components/pipelines/PipelineStrategyConfigFields.vue";
import type { PipelineStage, PipelineStrategy } from "../../src/types/pipelines";

const strategy: PipelineStrategy = {
  strategy_id: "llm.structured_metadata",
  version: 1,
  family: "llm",
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
