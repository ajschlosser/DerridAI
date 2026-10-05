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

import { describe, expect, it, vi } from "vitest";
import { createNavigation } from "../../src/domain/navigation";
import { createWorksWorkspace } from "../../src/domain/worksWorkspace";
import { createRuntimeState } from "../../src/state/runtimeState";
import { metadataSchemasApi } from "../../src/api/metadataSchemas";

// The modern Works Playwright workflow covers rendered search/actions/handoffs; these tests pin the commands.
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
        rows: [
          {
            record: {
              work: name,
              publisher: name === "Glas" ? "Galilée" : "",
              translator: name === "Glas" ? "John P. Leavey" : "",
            },
          },
        ],
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

    it("searches deterministic bibliographic metadata with case and diacritic normalization", () => {
      const byAuthor = snapshotSetup({
        worksSearch: "JACQUES DERRIDA",
      }).workspace.getWorksWorkspaceSnapshot();
      expect(titles(byAuthor)).toEqual(["Aporias", "Glas", "Of Grammatology"]);

      const byPublisher = snapshotSetup({
        worksSearch: "galilee",
      }).workspace.getWorksWorkspaceSnapshot();
      expect(titles(byPublisher)).toEqual(["Glas"]);

      const byTranslator = snapshotSetup({
        worksSearch: "leavey",
      }).workspace.getWorksWorkspaceSnapshot();
      expect(titles(byTranslator)).toEqual(["Glas"]);
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

  it("loads the pinned schema before presenting scoped work metadata", async () => {
    const assertion = (fieldId: string, fieldName: string, value: string) => ({
      assertion_id: `a-${fieldName}`,
      field_id: fieldId,
      field_name: fieldName,
      value,
      derivation_method: "model",
      evaluation_status: "value_supported",
      authority_status: "human_confirmed",
      value_status: "present",
      schema_id: "scope-test",
    });
    const rows = [
      {
        record: {
          work: "Scoped work",
          document_author: "Author",
          corpus_theme: "hospitality",
          passage_theme: "gift",
          field_assertions: {
            "field-corpus-theme": [
              assertion("field-corpus-theme", "corpus_theme", "hospitality"),
            ],
            "field-passage-theme": [assertion("field-passage-theme", "passage_theme", "gift")],
          },
          current_field_assertions: {
            "field-corpus-theme": "a-corpus_theme",
            "field-passage-theme": "a-passage_theme",
          },
        },
      },
    ];
    const item = {
      work: "Scoped work",
      count: 1,
      review: 0,
      files: ["scoped.jsonl"],
      authors: ["Author"],
      years: [],
      rows,
    };
    vi.spyOn(metadataSchemasApi, "get").mockResolvedValue({
      format_version: 2,
      id: "scope-test",
      name: "Scoped",
      description: "",
      groups: [{ key: "custom", label: "Custom", intro: "", fields_heading: "", notes: [], trailer: "", footer: "" }],
      fields: [
        {
          field_id: "field-corpus-theme",
          name: "corpus_theme",
          label: "Corpus theme",
          type: "text",
          group: "custom",
          role: "scholarly",
          review_visibility: "primary",
          scope: "corpus",
          values: [],
          strict: false,
          instruction: "",
          definitions_heading: "",
          evidence: false,
          assess: false,
          review: false,
          retrieval_profile: {
            enabled: true,
            max_items: 6,
            min_similarity: 0,
            include_corrections: true,
            include_confirmed_absence: true,
          },
          pos_tags: [],
          ner_tags: [],
        },
        {
          field_id: "field-passage-theme",
          name: "passage_theme",
          label: "Passage theme",
          type: "text",
          group: "custom",
          role: "scholarly",
          review_visibility: "primary",
          scope: "record",
          values: [],
          strict: false,
          instruction: "",
          definitions_heading: "",
          evidence: false,
          assess: false,
          review: false,
          retrieval_profile: {
            enabled: true,
            max_items: 6,
            min_similarity: 0,
            include_corrections: true,
            include_confirmed_absence: true,
          },
          pos_tags: [],
          ner_tags: [],
        },
      ],
    });

    const { state, workspace } = setup({
      isResearcher: () => false,
      providerProfiles: () => [],
      recordStores: () => [],
      hasCorpusDb: () => false,
      workIndex: () => new Map([[item.work, item]]),
      allAnnotations: () => [],
      worksBiblioValue: () => ({ value: "", mixed: false }),
      workDbStatus: () => ({ kind: "none", label: "" }),
      label: (key: string) => key,
      display: String,
      workInsightMetrics: () => [],
      tr: (key: string) => key,
      dbUnavailableReason: () => "",
    });
    state.files = [{ id: "f" }];
    state.workOverview = item.work;

    await workspace.prepareWorksWorkspace();
    const snapshot = workspace.getWorksWorkspaceSnapshot() as any;
    const fields = snapshot.selected.metadata.map((entry: { field: string }) => entry.field);

    expect(metadataSchemasApi.get).toHaveBeenCalledWith("scope-test");
    expect(fields).toContain("corpus_theme");
    expect(fields).not.toContain("passage_theme");
  });

  it("lets researchers search bibliographic metadata and facet by author", () => {
    const { state, workspace } = setup({
      isResearcher: () => true,
      recordStores: () => [{ name: "research-index", count: 2 }],
      providerProfiles: () => [],
      dbUnavailableReason: () => "",
      describeResearcherWork: (item: Record<string, unknown>) => ({
        work: String(item.work || ""),
        count: Number(item.count || 0),
        review: 0,
        year_label: String(item.publication_year || ""),
      }),
    });
    state.storeWorkStats = [
      {
        work: "Glas",
        count: 1,
        document_author: "Jacques Derrida",
        publication_year: "1974",
        publisher: "Galilée",
      },
      {
        work: "Otherwise than Being",
        count: 1,
        document_author: "Emmanuel Levinas",
        publication_year: "1974",
        publisher: "Duquesne University Press",
      },
    ];
    state.worksSearch = "galilee";
    state.worksAuthor = "Jacques Derrida";

    const snapshot = workspace.getWorksWorkspaceSnapshot() as {
      works: Array<{ work: string }>;
      authors: string[];
    };

    expect(snapshot.works.map((item) => item.work)).toEqual(["Glas"]);
    expect(snapshot.authors).toEqual(["Emmanuel Levinas", "Jacques Derrida"]);
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
    const annotationsSpy = vi.fn(() => [{ work: "Glas" }, { work: "Glas" }, { work: "Margins" }]);
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
      works: Array<{
        work: string;
        annotations: number;
        insights?: unknown[];
        metadata?: unknown[];
      }>;
      selected: {
        work: string;
        annotations: number;
        insights: Array<{ field: string; values: unknown[] }>;
      };
    };

    expect(snapshot.works).toHaveLength(2);
    expect(snapshot.works.every((work) => !("insights" in work) && !("metadata" in work))).toBe(
      true,
    );
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
