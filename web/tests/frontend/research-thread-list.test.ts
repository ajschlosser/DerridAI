/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchThreadList from "../../src/components/research/ResearchThreadList.vue";

const now = Date.parse("2026-10-13T12:00:00Z");
const jobs = [
  {
    id: "old",
    status: "completed",
    prompt: "Older question",
    source_collection: "derrida",
    finished_at: "2026-10-12T12:00:00Z",
  },
  { id: "live", status: "running", prompt: "Live question", stage_detail: "Reranking evidence" },
  { id: "new", status: "completed", prompt: "Newer question", finished_at: "2026-10-13T11:00:00Z" },
];

function list(props: Record<string, unknown> = {}) {
  return mount(ResearchThreadList, {
    props: { jobs: jobs as never, selectedJobId: "new", canManage: true, now, ...props },
    attachTo: document.body,
  });
}

describe("ResearchThreadList", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("lists running threads first, then completed ones newest first", () => {
    const titles = list()
      .findAll(".research-thread-copy b")
      .map((b) => b.text());
    expect(titles).toEqual(["Live question", "Newer question", "Older question"]);
  });

  it("marks the open thread and keeps one tab stop", () => {
    const buttons = list().findAll(".research-thread-main");
    expect(buttons.map((b) => b.attributes("tabindex"))).toEqual(["-1", "0", "-1"]);
    expect(buttons[1].attributes("aria-current")).toBe("true");
  });

  it("moves focus with the arrow keys and selects on click", async () => {
    const wrapper = list();
    const buttons = wrapper.findAll(".research-thread-main");
    await buttons[1].trigger("keydown", { key: "ArrowDown" });
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(buttons[2].element);
    await buttons[2].trigger("click");
    expect(wrapper.emitted("select")?.[0]?.[0]).toMatchObject({ id: "old" });
    wrapper.unmount();
  });

  it("offers cancel only on running threads, and only to managers", () => {
    expect(list().findAll(".research-thread-cancel")).toHaveLength(1);
    expect(list({ canManage: false }).findAll(".research-thread-cancel")).toHaveLength(0);
  });

  it("shows the collection, or evidence only, with a relative time", () => {
    const meta = list()
      .findAll(".research-thread-copy small")
      .map((s) => s.text());
    expect(meta[0]).toBe("Reranking evidence");
    expect(meta[1]).toMatch(/^Evidence only · /);
    expect(meta[2]).toMatch(/^derrida · /);
  });
});
