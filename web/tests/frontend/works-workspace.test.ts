/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createNavigation } from "../../src/domain/navigation";
import { createWorksWorkspace } from "../../src/domain/worksWorkspace";
import { createRuntimeState } from "../../src/runtime/runtimeState";

// The rendered Works view is covered by the legacy baseline's works scenarios (recorded before this logic moved);
// these pin the commands themselves.
function setup(overrides: Record<string, unknown> = {}) {
  const state = createRuntimeState() as unknown as Record<string, any>;
  // createRuntimeState binds the shared Vue Works store, so reset its view state for test isolation.
  Object.assign(state, {
    worksSearch: "",
    workOverview: "",
    worksSort: "title-asc",
    worksNeedsReview: false,
    worksDbStatus: "",
    worksAuthor: "",
    worksView: "cards",
  });
  const calls: string[] = [];
  const spies: Record<string, ReturnType<typeof vi.fn>> = {};
  let ids = 0;
  const deps = new Proxy(
    { state, uid: () => `id${++ids}`, ...overrides } as Record<string, unknown>,
    {
      get: (target, name: string) => {
        if (name in target) return target[name];
        spies[name] ??= vi.fn(() => {
          if (name === "persistPrefs" || name === "syncUrl" || name === "navigateTo")
            calls.push(name);
        });
        return spies[name];
      },
    },
  );
  const workspace = createWorksWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => unknown
  >;
  return { state, calls, spies, workspace };
}

describe("works workspace commands", () => {
  it("sets the works filter and the overview, saving and syncing the URL", () => {
    const { state, calls, workspace } = setup();
    workspace.setWorksSearch("Glas");
    workspace.setWorksOverview("Of Grammatology");
    expect(state.worksSearch).toBe("Glas");
    expect(state.workOverview).toBe("Of Grammatology");
    expect(calls).toEqual(["persistPrefs", "syncUrl", "persistPrefs", "syncUrl"]);
    workspace.setWorksSearch(null);
    expect(state.worksSearch).toBe("");
  });

  it("opens a work's records in Search, optionally only those needing review", () => {
    const { state, calls, workspace } = setup();
    workspace.searchWorkRecords("Glas");
    expect(state.globalSearchMode).toBe("traditional");
    expect(state.globalFilters).toEqual([{ id: "id1", field: "work", op: "eq", value: "Glas" }]);
    expect(calls).toEqual(["persistPrefs", "navigateTo"]);
    workspace.searchWorkRecords("Glas", { needsReview: true });
    expect(state.globalFilters.map((filter: { field: string }) => filter.field)).toEqual([
      "work",
      "needs_review",
    ]);
    expect(state.globalPage).toBe(1);
  });

  it("opens a work's annotations by its name", () => {
    const { state, spies, workspace } = setup();
    workspace.openWorkAnnotations("Glas");
    expect(state.annotationSearch).toBe("Glas");
    expect(state.annotationView).toBe("works");
    expect(spies.navigateTo).toHaveBeenCalledWith("annotations");
  });

  it("reviews only a work's flagged records", () => {
    const rows = [{ record: { needs_review: true } }];
    const { spies, workspace } = setup({
      workIndex: () => new Map([["Glas", { rows }]]),
      needsReviewItems: (items: unknown[]) => items,
    });
    workspace.reviewFlaggedWork("Glas");
    expect(spies.openTouchup).toHaveBeenCalledWith(rows);
    workspace.reviewFlaggedWork("Unknown work");
    expect(spies.openTouchup).toHaveBeenLastCalledWith([]);
  });

  describe("library snapshot", () => {
    function work(name: string, count: number, review: number, year: string, status = "synced") {
      return {
        work: name,
        count,
        review,
        files: [`${name}.jsonl`],
        authors: ["Jacques Derrida"],
        years: year ? [year] : [],
        rows: [{ record: { work: name } }],
        status,
      };
    }
    const items = [
      work("Glas", 400, 12, "1974"),
      work("Of Grammatology", 900, 0, "1967", "absent"),
      work("Aporias", 50, 3, ""),
    ];
    function snapshotSetup(view: Record<string, unknown> = {}) {
      const { state, workspace } = setup({
        isResearcher: () => false,
        providerProfiles: () => [],
        recordStores: () => [],
        hasCorpusDb: () => true,
        workIndex: () => new Map(items.map((item) => [item.work, item])),
        allAnnotations: () => [],
        worksBiblioValue: () => ({ value: "", mixed: false }),
        workDbStatus: (rows: Array<{ record: { work: string } }>) => ({
          kind: items.find((item) => item.work === rows[0].record.work)!.status,
          label: "",
        }),
        label: (key: string) => key,
        display: String,
        uniqueWorkValues: () => [],
        workInsightMetrics: () => [],
        tr: (key: string) => key,
        dbUnavailableReason: () => "",
      });
      state.files = [{ id: "f" }];
      // The runtime state object is shared between tests, so every view field starts from its default.
      Object.assign(state, {
        worksSearch: "",
        workOverview: "",
        worksSort: "title-asc",
        worksNeedsReview: false,
        worksDbStatus: "",
        worksAuthor: "",
        worksView: "cards",
        ...view,
      });
      return { state, workspace };
    }
    const titles = (snapshot: any) => snapshot.works.map((item: { work: string }) => item.work);

    it("keeps page-wide totals stable while the query narrows the visible works", () => {
      const { workspace } = snapshotSetup({ worksSearch: "gla" });
      const snapshot = workspace.getWorksWorkspaceSnapshot() as any;
      expect(titles(snapshot)).toEqual(["Glas"]);
      expect(snapshot.visibleWorks).toBe(1);
      expect(snapshot.scopeWorks.map((item: { work: string }) => item.work).sort()).toEqual([
        "Aporias",
        "Glas",
        "Of Grammatology",
      ]);
      expect(snapshot.totalWorks).toBe(3);
      expect(snapshot.totalRecords).toBe(1350);
      expect(snapshot.sourceFileCount).toBe(3);
      expect(snapshot.totalReview).toBe(15);
      expect(snapshot.indexFreshness).toMatchObject({
        state: "stale",
        totalRecords: 1350,
        currentRecords: 450,
        absentRecords: 900,
      });
    });

    it("sorts by the real fields and leaves works without a year last", () => {
      const order = (sort: string) => {
        const { workspace } = snapshotSetup({ worksSort: sort });
        return titles(workspace.getWorksWorkspaceSnapshot());
      };
      expect(order("title-asc")).toEqual(["Aporias", "Glas", "Of Grammatology"]);
      expect(order("title-desc")).toEqual(["Of Grammatology", "Glas", "Aporias"]);
      expect(order("records-desc")).toEqual(["Of Grammatology", "Glas", "Aporias"]);
      expect(order("review-desc")).toEqual(["Glas", "Aporias", "Of Grammatology"]);
      expect(order("year-asc")).toEqual(["Of Grammatology", "Glas", "Aporias"]);
      expect(order("bogus")).toEqual(["Aporias", "Glas", "Of Grammatology"]);
    });

    it("filters by review need, database status and author", () => {
      const only = (view: Record<string, unknown>) =>
        titles(snapshotSetup(view).workspace.getWorksWorkspaceSnapshot());
      expect(only({ worksNeedsReview: true })).toEqual(["Aporias", "Glas"]);
      expect(only({ worksDbStatus: "absent" })).toEqual(["Of Grammatology"]);
      expect(only({ worksAuthor: "Nobody" })).toEqual([]);
      expect(only({ worksNeedsReview: true, worksDbStatus: "synced" })).toEqual([
        "Aporias",
        "Glas",
      ]);
    });

    it("stores safe view state and normalizes unknown values", () => {
      const { state, calls, workspace } = setup();
      workspace.setWorksView({ sort: "records-desc", needsReview: true, viewMode: "list" });
      expect([state.worksSort, state.worksNeedsReview, state.worksView]).toEqual([
        "records-desc",
        true,
        "list",
      ]);
      expect(calls).toEqual(["persistPrefs", "syncUrl"]);
      workspace.setWorksView({ sort: "nonsense", viewMode: "grid", dbStatus: "", author: "X" });
      expect([state.worksSort, state.worksView, state.worksAuthor]).toEqual([
        "title-asc",
        "cards",
        "X",
      ]);
    });
  });

  it("restores Works sort, filters and view mode from the URL state", () => {
    const { state } = setup();
    const navigation = createNavigation({
      state,
      persistPrefs: vi.fn(),
    } as never);
    Object.assign(state, {
      view: "works",
      worksSearch: "gla",
      workOverview: "Glas",
      worksSort: "review-desc",
      worksNeedsReview: true,
      worksDbStatus: "changed",
      worksAuthor: "Jacques Derrida",
      worksView: "list",
    });
    const encoded = JSON.parse(JSON.stringify(navigation.currentTableUrlState("works")));
    Object.assign(state, {
      worksSearch: "",
      workOverview: "",
      worksSort: "title-asc",
      worksNeedsReview: false,
      worksDbStatus: "",
      worksAuthor: "",
      worksView: "cards",
    });
    navigation.applyCompressedTableUrlState(encoded, "works");
    expect(state).toMatchObject({
      worksSearch: "gla",
      workOverview: "Glas",
      worksSort: "review-desc",
      worksNeedsReview: true,
      worksDbStatus: "changed",
      worksAuthor: "Jacques Derrida",
      worksView: "list",
    });
    navigation.applyCompressedTableUrlState({ v: "compact" }, "works");
    expect(state.worksView).toBe("list");
    // Hand-edited or stale values fall back to safe defaults rather than corrupting the view.
    navigation.applyCompressedTableUrlState({ s: "drop table", d: "weird", v: "grid" }, "works");
    expect(state).toMatchObject({ worksSort: "title-asc", worksDbStatus: "", worksView: "cards" });
  });
  it("builds cheap library summaries and computes expensive detail only for the selected work", () => {
    const item = (work: string, topic: string) => ({
      work,
      count: 1,
      review: 0,
      files: new Set([`${work}.jsonl`]),
      authors: new Set(["Author"]),
      years: new Set(["2020"]),
      rows: [{ record: { work, topics: [topic], document_author: "Author" } }],
    });
    const insightSpy = vi.fn((rows: Array<{ record: { topics?: string[] } }>) => [
      {
        id: "topics",
        field: "topics",
        title: "Topics",
        heading: "Top topics",
        type: "bars",
        values: [{ key: rows[0]?.record.topics?.[0] || "", value: 1 }],
      },
    ]);
    const annotationsSpy = vi.fn(() => [
      { work: "Glas" },
      { work: "Glas" },
      { work: "Margins" },
    ]);
    const { state, workspace } = setup({
      isResearcher: () => false,
      recordStores: () => [],
      providerProfiles: () => [],
      dbUnavailableReason: () => "",
      hasCorpusDb: () => false,
      canUse: () => true,
      allAnnotations: annotationsSpy,
      workDbStatus: () => ({ kind: "absent", label: "Not synced" }),
      worksBiblioValue: () => ({
        field_label: "Publisher",
        value: "",
        mixed: false,
        unique_count: 0,
      }),
      label: (field: string) => field,
      display: (value: unknown) => String(value ?? ""),
      tr: (key: string, fallback = "") => fallback || key,
      workInsightMetrics: insightSpy,
      workIndex: () =>
        new Map([
          ["Glas", item("Glas", "hospitality")],
          ["Margins", item("Margins", "ethics")],
        ]),
    });
    state.workOverview = "Glas";

    const snapshot = workspace.getWorksWorkspaceSnapshot() as {
      works: Array<{ work: string; annotations: number; insights?: unknown[]; metadata?: unknown[] }>;
      selected: { work: string; annotations: number; insights: Array<{ field: string; values: unknown[] }> };
    };

    expect(snapshot.works).toHaveLength(2);
    expect(snapshot.works.every((work) => !("insights" in work) && !("metadata" in work))).toBe(true);
    expect(snapshot.works.map((work) => [work.work, work.annotations])).toEqual([
      ["Glas", 2],
      ["Margins", 1],
    ]);
    expect(snapshot.selected.work).toBe("Glas");
    expect(snapshot.selected.annotations).toBe(2);
    expect(snapshot.selected.insights.find((item) => item.field === "topics")?.values).toEqual([
      { key: "hospitality", value: 1, other: false },
    ]);
    expect(insightSpy).toHaveBeenCalledTimes(1);
    expect(annotationsSpy).toHaveBeenCalledTimes(1);
  });
});
