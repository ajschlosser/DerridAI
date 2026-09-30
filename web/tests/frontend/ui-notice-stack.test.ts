// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it } from "vitest";
import UiNoticeStack from "../../src/components/ui/UiNoticeStack.vue";
import CorpusReviewRunStatus from "../../src/components/corpus-builder/CorpusReviewRunStatus.vue";

const items = [
  { id: "a", tone: "error" as const, text: "The provider refused the request." },
  { id: "b", tone: "warning" as const, text: "2 of 6 records appear unusable." },
  { id: "c", tone: "info" as const, text: "Metadata enrichment continued." },
];

describe("UiNoticeStack", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("closes one message with its own ×, and all of them with the stack's", async () => {
    const wrapper = mount(UiNoticeStack, {
      props: { items, label: "Messages" },
      attachTo: document.body,
    });
    const closes = wrapper.findAll("[data-notice-dismiss]");
    expect(closes).toHaveLength(3);
    expect(closes[1].attributes("aria-label")).toBe("Dismiss: 2 of 6 records appear unusable.");
    await closes[1].trigger("click");
    await wrapper.get(".notice-all").trigger("click");
    expect(wrapper.emitted("dismiss")).toEqual([["b"]]);
    expect(wrapper.emitted("dismissAll")).toEqual([[["a", "b", "c"]]]);
    wrapper.unmount();
  });

  it("offers no 'all' button for a single message, and announces errors as alerts", () => {
    const wrapper = mount(UiNoticeStack, {
      props: { items: items.slice(0, 1), label: "Messages" },
    });
    expect(wrapper.find(".notice-all").exists()).toBe(false);
    expect(wrapper.get(".notice-text").attributes("role")).toBe("alert");
  });

  it("moves focus to the next message after one is closed", async () => {
    const wrapper = mount(UiNoticeStack, {
      props: { items, label: "Messages" },
      attachTo: document.body,
    });
    await wrapper.findAll("[data-notice-dismiss]")[0].trigger("click");
    await wrapper.setProps({ items: items.slice(1) });
    await nextTick();
    expect(document.activeElement).toBe(wrapper.findAll("[data-notice-dismiss]")[0].element);
    wrapper.unmount();
  });

  it("says that acknowledging keeps a provenance warning, and folds a long list", async () => {
    const many = Array.from({ length: 7 }, (_, n) => ({
      id: `w${n}`,
      tone: "warning" as const,
      text: `Warning ${n}`,
    }));
    const wrapper = mount(UiNoticeStack, {
      props: { items: many, label: "Build warnings", mode: "acknowledge", limit: 3 },
    });
    expect(wrapper.findAll(".notice")).toHaveLength(3);
    expect(wrapper.get("[data-notice-dismiss]").attributes("aria-label")).toBe(
      "Acknowledge: Warning 0",
    );
    expect(wrapper.get(".notice-all").text()).toContain("Acknowledge all");
    await wrapper.get(".notice-more").trigger("click");
    expect(wrapper.findAll(".notice")).toHaveLength(7);
  });
});

describe("build warnings in the run monitor", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("lets a reviewer pause an active build without leaving Review", async () => {
    const build = {
      build_id: "b-running",
      status: "running",
      stage: "enriching",
      progress: 0.42,
      record_count: 12,
    };
    const wrapper = mount(CorpusReviewRunStatus, {
      props: { build: build as never, profiles: [] },
      global: {
        stubs: {
          CorpusRunDiagnostics: true,
        },
      },
    });

    const pause = wrapper.findAll("button").find((button) => button.text().trim() === "Pause");
    expect(pause).toBeDefined();
    await pause!.trigger("click");
    expect(wrapper.emitted("pause")).toEqual([[]]);
  });

  it("lists only unacknowledged warnings and asks for them to be acknowledged, not deleted", async () => {
    const build = {
      build_id: "b1",
      status: "awaiting_review",
      stage: "review",
      progress: 1,
      warnings: ["r6: LLM text touch-up failed.", "2 of 6 records appear unusable."],
      warning_acknowledgements: {
        k1: { warning: "2 of 6 records appear unusable.", acknowledged_by: "aaron" },
      },
      error: "Provider timed out.",
    };
    const wrapper = mount(CorpusReviewRunStatus, {
      props: { build: build as never, profiles: [] },
      global: {
        stubs: {
          CorpusProviderSwitcher: true,
          CorpusMetadataLiveStatus: true,
          CorpusEnrichmentPassStatus: true,
          CorpusHandsFreeReport: true,
          CorpusEnrichmentMetrics: true,
          CorpusTextCleanupSummary: true,
          CorpusLlmEffectivenessPanel: true,
        },
      },
    });
    const stacks = wrapper.findAllComponents(UiNoticeStack);
    const warningStack = stacks.find((stack) => stack.props("mode") === "acknowledge")!;
    expect(warningStack.props("items").map((item: { text: string }) => item.text)).toEqual([
      "r6: LLM text touch-up failed.",
    ]);
    await warningStack.get("[data-notice-dismiss]").trigger("click");
    expect(wrapper.emitted("acknowledgeWarnings")).toEqual([[["r6: LLM text touch-up failed."]]]);
    // The error can be closed too; it comes back only if the build reports a different one.
    const errorStack = stacks.find((stack) => stack.props("mode") !== "acknowledge")!;
    await errorStack.get("[data-notice-dismiss]").trigger("click");
    expect(wrapper.text()).not.toContain("Provider timed out.");
  });
});
