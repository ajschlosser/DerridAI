import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import OperationsPanel from "../../src/components/OperationsPanel.vue";
import { useI18nStore } from "../../src/stores/i18n";
import type { OperationView, OperationsBridge } from "../../src/domain/operationsPanel";

const NOW = new Date("2026-09-20T15:00:00").getTime();
const iso = (seconds: number) => new Date(NOW + seconds * 1000).toISOString();

function job(over: Partial<OperationView> = {}): OperationView {
  return {
    id: "j1", type: "llm_tool", status: "completed", label: "Languages · Français", icon: "language", subtitle: "Completed",
    facts: [{ name: "Provider", value: "ollama" }], owner: "admin", createdAt: iso(-700), startedAt: iso(-600), finishedAt: iso(-300),
    total: 1, completed: 1, progressLabel: "1 of 1 (100%)", cancelRequested: false, error: "", result: { kind: "result" }, ...over,
  };
}

function makeBridge(initial: OperationView[]) {
  let jobs = initial;
  const listeners = new Set<() => void>();
  const bridge = {
    snapshot: () => jobs.map((item) => ({ ...item })),
    subscribe: (fn: () => void) => { listeners.add(fn); return () => listeners.delete(fn); },
    refresh: vi.fn(async () => {}),
    openDetails: vi.fn(),
    openResult: vi.fn(),
    cancel: vi.fn(async () => {}),
    remove: vi.fn(async () => {}),
    clearFinished: vi.fn(async () => {}),
  } satisfies OperationsBridge;
  const set = (next: OperationView[]) => { jobs = next; listeners.forEach((fn) => fn()); };
  return { bridge, set };
}

async function mountPanel(jobs: OperationView[], props: Record<string, unknown> = {}) {
  setActivePinia(createPinia());
  const fake = makeBridge(jobs);
  const wrapper = mount(OperationsPanel, { props: { bridge: fake.bridge, ...props }, attachTo: document.body, global: { stubs: { TransitionGroup: false } } });
  await flushPromises();
  return { wrapper, ...fake };
}

const running = (over: Partial<OperationView> = {}) => job({ id: "run", label: "PDF corpus build", type: "pdf_corpus", icon: "pdf", status: "running", finishedAt: null, result: null, total: 100, completed: 40, progressLabel: "40% overall", ...over });

describe("Operations panel semantics", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("has one level-2 heading, section headings, and real lists", async () => {
    const { wrapper } = await mountPanel([running(), job({ id: "bad", status: "failed", error: "Provider unreachable", result: null }), job()]);
    expect(wrapper.findAll("h2")).toHaveLength(1);
    expect(wrapper.findAll("h3").map((h) => h.text().replace(/\d+$/, "").trim())).toEqual(["Needs attention", "In progress", "History"]);
    expect(wrapper.findAll("ul.ops-list").length).toBeGreaterThanOrEqual(3);
    expect(wrapper.findAll("li.ops-row")).toHaveLength(3);
    expect(wrapper.get("section.ops").attributes("aria-labelledby")).toBe("ops-heading");
  });

  it("exposes progress as a progressbar with a name, range, value and readable text", async () => {
    const { wrapper } = await mountPanel([running()]);
    const bar = wrapper.get('[role="progressbar"]');
    expect(bar.attributes("aria-valuemin")).toBe("0");
    expect(bar.attributes("aria-valuemax")).toBe("100");
    expect(bar.attributes("aria-valuenow")).toBe("40");
    expect(bar.attributes("aria-label")).toBe("Progress of PDF corpus build");
    expect(bar.attributes("aria-valuetext")).toContain("40% overall");
  });

  it("marks a queued operation's progress as indeterminate (no value)", async () => {
    const { wrapper } = await mountPanel([running({ id: "q", status: "queued", startedAt: null, completed: 0 })]);
    const bar = wrapper.get('[role="progressbar"]');
    expect(bar.attributes("aria-valuenow")).toBeUndefined();
    expect(bar.attributes("aria-valuetext")).toBe("Waiting to start");
  });

  it("gives every action a name that says which operation and still contains its visible label", async () => {
    const { wrapper } = await mountPanel([job({ id: "a", label: "Languages · Français" }), job({ id: "b", label: "Chroma upsert", type: "upsert" })]);
    for (const button of wrapper.findAll(".ops-row button")) {
      const name = button.attributes("aria-label") ?? "";
      const visible = button.text();
      expect(name, `button "${visible}"`).toContain(visible); // WCAG 2.5.3 Label in Name
      expect(name).toMatch(/Languages · Français|Chroma upsert/);
    }
    const names = wrapper.findAll(".ops-row button").map((b) => b.attributes("aria-label"));
    expect(new Set(names).size).toBe(names.length); // no two identical accessible names
  });

  it("shows status as text with an icon, never colour alone", async () => {
    const { wrapper } = await mountPanel([job(), job({ id: "f", status: "failed", result: null, error: "x" })]);
    for (const status of wrapper.findAll(".ops-status")) {
      expect(status.text().length).toBeGreaterThan(0);
      expect(status.find(".ops-status-icon").exists()).toBe(true);
    }
  });

  it("shows the reason for a failure inline", async () => {
    const { wrapper } = await mountPanel([job({ status: "failed", result: null, error: "Provider unreachable" })]);
    expect(wrapper.get(".ops-error").text()).toContain("What went wrong");
    expect(wrapper.get(".ops-error").text()).toContain("Provider unreachable");
  });

  it("shows a friendly empty state, and a different message when only the filter is empty", async () => {
    const empty = await mountPanel([]);
    expect(empty.wrapper.get(".ops-empty h3").text()).toBe("Nothing in flight");
    const filtered = await mountPanel([job()]);
    await filtered.wrapper.findAll(".ops-chip").find((c) => c.text().startsWith("Running"))!.trigger("click");
    expect(filtered.wrapper.get(".ops-empty-inline").text()).toContain("No operations match");
  });
});

describe("filters", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("exposes the selected filter with aria-pressed and shows counts", async () => {
    const { wrapper } = await mountPanel([running(), job({ id: "bad", status: "failed", result: null }), job({ id: "ok" })]);
    const chips = wrapper.findAll(".ops-chip");
    expect(chips.map((c) => c.text())).toEqual(["All 3", "Running 1", "Needs attention 1", "Finished 2"]);
    expect(chips[0].attributes("aria-pressed")).toBe("true");
    await chips[1].trigger("click");
    expect(chips[1].attributes("aria-pressed")).toBe("true");
    expect(chips[0].attributes("aria-pressed")).toBe("false");
    expect(wrapper.findAll("li.ops-row")).toHaveLength(1);
  });
});

describe("keyboard focus survives updates", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("keeps focus on the same button while progress updates", async () => {
    const { wrapper, set } = await mountPanel([running(), job({ id: "ok" })]);
    const button = wrapper.get('[data-op-id="ok"] button').element as HTMLButtonElement;
    button.focus();
    expect(document.activeElement).toBe(button);
    for (let completed = 41; completed <= 60; completed += 5) {
      set([running({ completed }), job({ id: "ok" })]);
      await flushPromises();
    }
    expect(document.activeElement).toBe(button);
    expect(button.isConnected).toBe(true);
  });

  it("moves focus somewhere sensible, not <body>, when the focused button disappears", async () => {
    const { wrapper, set } = await mountPanel([running()]);
    const cancel = wrapper.get('[data-op-id="run"] .is-danger').element as HTMLButtonElement;
    cancel.focus();
    set([running({ status: "completed", finishedAt: iso(-5), result: { kind: "build" }, completed: 100 })]); // Cancel is replaced by Remove
    await flushPromises();
    expect(document.activeElement).not.toBe(document.body);
    expect(wrapper.element.contains(document.activeElement)).toBe(true);
  });
});

describe("removal is undoable, not confirmed", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); document.body.innerHTML = ""; });

  it("hides the row at once, offers Undo, and deletes only after the undo window", async () => {
    const { wrapper, bridge } = await mountPanel([job()], { undoMs: 5000 });
    await wrapper.get('button[aria-label^="Remove"]').trigger("click");
    expect(wrapper.findAll("li.ops-row")).toHaveLength(0);
    expect(wrapper.get(".ops-undo").text()).toContain("Removed Languages · Français.");
    expect(bridge.remove).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(5001);
    expect(bridge.remove).toHaveBeenCalledWith("j1");
    expect(wrapper.find(".ops-undo").exists()).toBe(false);
  });

  it("brings the row back and never deletes when Undo is used", async () => {
    const { wrapper, bridge } = await mountPanel([job()], { undoMs: 5000 });
    await wrapper.get('button[aria-label^="Remove"]').trigger("click");
    await wrapper.get(".ops-undo button").trigger("click");
    await vi.advanceTimersByTimeAsync(10_000);
    expect(bridge.remove).not.toHaveBeenCalled();
    expect(wrapper.findAll("li.ops-row")).toHaveLength(1);
  });

  it("commits a pending removal when the panel goes away, instead of dropping it", async () => {
    const { wrapper, bridge } = await mountPanel([job()], { undoMs: 5000 });
    await wrapper.get('button[aria-label^="Remove"]').trigger("click");
    wrapper.unmount();
    await flushPromises();
    expect(bridge.remove).toHaveBeenCalledWith("j1");
  });

  it("settles the previous removal before starting a new one (one undo window at a time)", async () => {
    const { wrapper, bridge } = await mountPanel([job({ id: "a" }), job({ id: "b", label: "Second" })], { undoMs: 5000 });
    await wrapper.get('[data-op-id="a"] button[aria-label^="Remove"]').trigger("click");
    await wrapper.get('[data-op-id="b"] button[aria-label^="Remove"]').trigger("click");
    await flushPromises();
    expect(bridge.remove).toHaveBeenCalledWith("a");
    expect(bridge.remove).not.toHaveBeenCalledWith("b");
  });

  it("clears all finished operations with the same undo, and leaves running ones alone", async () => {
    const { wrapper, bridge } = await mountPanel([running(), job({ id: "a" }), job({ id: "b" })], { undoMs: 5000 });
    await wrapper.get("#clearFinishedJobs").trigger("click");
    expect(wrapper.findAll("li.ops-row")).toHaveLength(1);
    expect(wrapper.get(".ops-undo").text()).toContain("Cleared 2 finished operation(s).");
    await vi.advanceTimersByTimeAsync(5001);
    expect(bridge.clearFinished).toHaveBeenCalledTimes(1);
  });

  it("puts the row back if the server refuses the removal, and says so", async () => {
    const { wrapper, bridge } = await mountPanel([job()], { undoMs: 1000 });
    bridge.remove.mockRejectedValueOnce(new Error("HTTP 500"));
    await wrapper.get('button[aria-label^="Remove"]').trigger("click");
    await vi.advanceTimersByTimeAsync(1001);
    await vi.advanceTimersByTimeAsync(400);
    expect(wrapper.findAll("li.ops-row")).toHaveLength(1);
    expect(wrapper.get('[role="status"]').text()).toContain("Could not remove: HTTP 500");
  });
});

describe("announcements", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); document.body.innerHTML = ""; });

  it("announces an outcome once through a single polite live region, and never a progress tick", async () => {
    const { wrapper, set } = await mountPanel([running()]);
    const live = wrapper.get('.sr-only[role="status"]');
    expect(live.attributes("aria-live")).toBe("polite");
    set([running({ completed: 55 })]);
    await vi.advanceTimersByTimeAsync(600);
    expect(live.text()).toBe("");
    set([running({ status: "completed", finishedAt: iso(-1), completed: 100, result: { kind: "build" } })]);
    await vi.advanceTimersByTimeAsync(600);
    expect(live.text()).toBe("PDF corpus build completed.");
    expect(wrapper.findAll('[role="status"]').filter((n) => n.classes().includes("sr-only"))).toHaveLength(1);
  });

  it("announces a failure", async () => {
    const { wrapper, set } = await mountPanel([running()]);
    set([running({ status: "failed", finishedAt: iso(-1), result: null, error: "boom" })]);
    await vi.advanceTimersByTimeAsync(600);
    expect(wrapper.get('.sr-only[role="status"]').text()).toBe("PDF corpus build failed.");
  });
});

describe("language and formatting", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("formats times and durations in the interface language", async () => {
    setActivePinia(createPinia());
    useI18nStore().locale = "fr-CA";
    const fake = makeBridge([job({ startedAt: new Date(Date.now() - 600_000).toISOString(), finishedAt: new Date(Date.now() - 300_000).toISOString() })]);
    const wrapper = mount(OperationsPanel, { props: { bridge: fake.bridge }, attachTo: document.body, global: { stubs: { TransitionGroup: false } } });
    await flushPromises();
    const meta = wrapper.get(".ops-meta").text();
    expect(meta).toMatch(/il y a\s*5\s*min/i);          // relative time from Intl.RelativeTimeFormat
    expect(meta).toMatch(/5\s*min/);                     // duration from Intl unit formatting
    expect(wrapper.get(".ops-meta time").attributes("title")).toBeTruthy(); // absolute time on hover/long-press
  });

  it("caps a long history and reveals the rest on request", async () => {
    const many = Array.from({ length: 9 }, (_, i) => job({ id: `h${i}`, finishedAt: iso(-300 - i) }));
    const { wrapper } = await mountPanel(many, { historyLimit: 4 });
    expect(wrapper.findAll("li.ops-row")).toHaveLength(4);
    const more = wrapper.get(".ops-more");
    expect(more.attributes("aria-expanded")).toBe("false");
    expect(more.text()).toBe("Show all 9");
    await more.trigger("click");
    expect(wrapper.findAll("li.ops-row")).toHaveLength(9);
    expect(more.attributes("aria-expanded")).toBe("true");
  });
});
