import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";
import VectorBackendPanel from "../../src/components/vector/VectorBackendPanel.vue";
import type { ChromaHealth } from "../../src/types/vector";

const health: ChromaHealth = {
  available: true,
  mode: "embedded",
  path: "/data/chroma",
  host_path_hint: "./data/chroma",
  data_root: "/data",
  url: null,
  tenant: null,
  database: null,
  token_configured: false,
  writable: true,
  heartbeat_ok: true,
  chroma_version: "1.1.0",
  collection_count: 1,
  identity: "Local Chroma · ./data/chroma",
  error: null,
};

function mountPanel(props: Record<string, unknown> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(VectorBackendPanel, {
    props: { health, probing: false, applying: false, probeResult: null, error: "", ...props },
    global: { plugins: [pinia] },
  });
}

describe("VectorBackendPanel", () => {
  it("probes and applies an embedded path", async () => {
    const wrapper = mountPanel();
    expect(wrapper.find("#chroma-url").exists()).toBe(false);
    await wrapper.get("#chroma-path").setValue("/data/chroma-lab");
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("apply")?.[0]?.[0]).toEqual({
      mode: "embedded",
      path: "/data/chroma-lab",
    });
  });

  it("rejects credentials in the Chroma URL instead of probing", async () => {
    const wrapper = mountPanel({
      health: { ...health, mode: "http", path: null, url: "http://chroma:8000" },
    });
    await flushPromises();
    await wrapper.get("#chroma-url").setValue("http://user:secret@chroma:8000");
    await wrapper.get("button[type=button]").trigger("click");
    expect(wrapper.text()).toContain("Do not put credentials");
    expect(wrapper.emitted("probe")).toBeUndefined();
  });
});
