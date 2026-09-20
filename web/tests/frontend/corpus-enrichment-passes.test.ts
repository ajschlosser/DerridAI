import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusEnrichmentPassStatus from "../../src/components/CorpusEnrichmentPassStatus.vue";
import MetadataEnrichmentDialog from "../../src/components/MetadataEnrichmentDialog.vue";

const build = (operation: Record<string, unknown>): any => ({
  build_id: "b",
  metadata_operation: {
    operation_id: "op-1",
    kind: "metadata_enrichment_rerun",
    records_total: 60,
    passes_requested: 3,
    ...operation,
  },
});
const buttonByText = (wrapper: any, text: string) => {
  const button = wrapper.findAll("button").find((node: any) => node.text().includes(text));
  if (!button) throw new Error("Button not found: " + text);
  return button;
};

describe("Metadata enrichment passes", () => {
  it("announces the running pass, shows per-pass progress, and lets the reviewer stop it", async () => {
    const wrapper = mount(CorpusEnrichmentPassStatus, {
      props: {
        build: build({
          state: "running",
          current_pass: 2,
          records_processed: 90,
          pass_results: [{ pass: 1, records_processed: 60 }],
        }),
      },
    });
    expect(wrapper.attributes("role")).toBe("status");
    expect(wrapper.text()).toContain("Pass 2 of 3 is running");
    expect(wrapper.text()).toContain("30 of 60 records");
    expect(wrapper.get("progress").attributes("value")).toBe("30");
    await buttonByText(wrapper, "Stop enrichment").trigger("click");
    expect(wrapper.emitted("stop")).toHaveLength(1);
  });

  it("offers another pass once finished, and can be dismissed", async () => {
    const wrapper = mount(CorpusEnrichmentPassStatus, {
      props: {
        build: build({
          state: "completed",
          passes_completed: 2,
          converged: true,
          fields_replaced: 4,
        }),
      },
    });
    expect(wrapper.text()).toContain("Passes run: 2");
    expect(wrapper.text()).toContain("nothing new");
    await buttonByText(wrapper, "Run another pass").trigger("click");
    expect(wrapper.emitted("run-another")).toHaveLength(1);
    await buttonByText(wrapper, "Dismiss").trigger("click");
    expect(wrapper.find("section").exists()).toBe(false);
  });

  it("ignores builds whose last operation is not an enrichment pass", () => {
    const wrapper = mount(CorpusEnrichmentPassStatus, {
      props: { build: build({ kind: "metadata_retry", state: "running" }) },
    });
    expect(wrapper.find("section").exists()).toBe(false);
  });

  it("sends a single pass by default and a bounded chain when chosen", async () => {
    const wrapper = mount(MetadataEnrichmentDialog, {
      props: { open: true, profiles: [], providerProfileId: "p1" },
      global: {
        stubs: {
          UiDialog: { template: "<div><slot/><slot name='footer'/></div>" },
          LlmExecutionControl: true,
        },
      },
    });
    await buttonByText(wrapper, "Run enrichment").trigger("click");
    expect((wrapper.emitted("run")![0][0] as any).passes).toBe(1);
    await wrapper
      .findAll("input[type=radio]")
      .find((node: any) => node.element.value === "true")!
      .setValue(true);
    await wrapper.get("input[type=number]").setValue(99);
    await buttonByText(wrapper, "Run enrichment").trigger("click");
    expect((wrapper.emitted("run")![1][0] as any).passes).toBe(10);
  });
});
