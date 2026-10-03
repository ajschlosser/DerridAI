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

import { flushPromises, shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const pdfCorpusApi = vi.hoisted(() => ({
  listAssets: vi.fn(),
  profiles: vi.fn(),
  listBuilds: vi.fn(),
  build: vi.fn(),
  blocks: vi.fn(),
  markViewed: vi.fn(),
  patchText: vi.fn(),
  patchMetadata: vi.fn(),
  reviewDecision: vi.fn(),
  assetContentUrl: vi.fn((assetId: string) => `/api/pdf/assets/${assetId}/content`),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi: pdfCorpusApi };
});

const corpusReviewReads = vi.hoisted(() => ({
  queuePage: vi.fn(),
  records: vi.fn(),
  rows: vi.fn(),
  texts: vi.fn(),
  metadataFacets: vi.fn(),
}));

vi.mock("../../src/features/corpus-builder/api/reviewReads", async () => {
  const actual = await vi.importActual<
    typeof import("../../src/features/corpus-builder/api/reviewReads")
  >("../../src/features/corpus-builder/api/reviewReads");
  return { ...actual, corpusReviewReads };
});

const systemApi = vi.hoisted(() => ({
  researcherProviders: vi.fn(),
  researcherProviderAvailability: vi.fn(),
}));

vi.mock("../../src/api/system", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/system")>("../../src/api/system");
  return { ...actual, systemApi };
});

const metadataSchemasApi = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
}));

vi.mock("../../src/api/metadataSchemas", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/metadataSchemas")>(
    "../../src/api/metadataSchemas",
  );
  return { ...actual, metadataSchemasApi };
});

const runtime = vi.hoisted(() => ({
  getProviderProfilesForUi: vi.fn(() => []),
  getProviderRequestConfigForUi: vi.fn(() => null),
  getDefaultProviderProfileId: vi.fn(() => ""),
  state: { pdf: { file: null } },
}));

vi.mock("../../src/runtime/runtime.js", () => ({
  ...runtime,
  __v_isRef: false,
  __v_isReadonly: false,
  __v_isShallow: false,
  __v_skip: true,
  __v_raw: undefined,
}));

import PdfCorpusBuilder from "../../src/components/PdfCorpusBuilder.vue";
import DocumentManifestEditor from "../../src/components/DocumentManifestEditor.vue";
import { queueRowFromRecord } from "../../src/features/corpus-builder/domain/queueRows";
import { useI18nStore } from "../../src/stores/i18n";

const defaultSchema = {
  format_version: 1,
  id: "default",
  name: "Default",
  description: "Default metadata schema",
  groups: [],
  fields: [],
};

async function mountBuilder(query = "", renderManifest = false) {
  const pinia = createPinia();
  setActivePinia(pinia);
  useI18nStore().dictionary = {};
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/corpus-builder", name: "corpus-builder", component: { template: "<div />" } },
      { path: "/source-explorer", name: "source-explorer", component: { template: "<div />" } },
      { path: "/schemas", name: "schemas", component: { template: "<div />" } },
    ],
  });
  await router.push(`/corpus-builder${query}`);
  await router.isReady();
  const wrapper = shallowMount(PdfCorpusBuilder, {
    attachTo: document.body,
    global: {
      plugins: [pinia, router],
      stubs: renderManifest
        ? { CorpusBuildWorkspace: { template: '<div><slot name="manifest" /></div>' } }
        : {},
    },
  });
  await flushPromises();
  return Object.assign(wrapper, { router });
}

const reviewBuild = {
  build_id: "build-1",
  asset_id: "asset-1",
  status: "awaiting_review",
  stage: "review",
  record_count: 1,
  metadata_total: 1,
  schema: defaultSchema,
  request: {},
};

const reviewRecord = {
  record_id: "record-1",
  record_revision: 1,
  text: "Original text",
  text_length: 13,
  source_block_ids: ["block-1"],
  source_spans: [{ block_id: "block-1", page: 1 }],
  metadata_field_status: {},
  metadata_evidence: {},
  review_disposition: "pending",
  needs_review: true,
  accepted: false,
  rejected: false,
};

const reviewQueueRow = queueRowFromRecord(reviewRecord as never);

describe("PdfCorpusBuilder characterization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pdfCorpusApi.listAssets.mockResolvedValue({ items: [] });
    pdfCorpusApi.profiles.mockResolvedValue({ items: [] });
    pdfCorpusApi.listBuilds.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100 });
    pdfCorpusApi.build.mockResolvedValue(reviewBuild);
    corpusReviewReads.queuePage.mockResolvedValue({
      rows: [reviewQueueRow],
      total: 1,
      offset: 0,
      limit: 50,
      hasNextPage: false,
      topologyCount: 1,
      counts: {},
    });
    corpusReviewReads.records.mockResolvedValue([reviewRecord]);
    corpusReviewReads.rows.mockResolvedValue([reviewQueueRow]);
    corpusReviewReads.texts.mockResolvedValue([reviewRecord.text]);
    corpusReviewReads.metadataFacets.mockResolvedValue({});
    pdfCorpusApi.blocks.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 500 });
    pdfCorpusApi.markViewed.mockResolvedValue({});
    systemApi.researcherProviders.mockResolvedValue({ profiles: [] });
    systemApi.researcherProviderAvailability.mockResolvedValue({
      available: false,
      model_available: false,
    });
    metadataSchemasApi.list.mockResolvedValue({
      items: [
        {
          id: "default",
          name: "Default",
          description: "Default metadata schema",
          builtin: true,
          field_count: 0,
          groups: [],
          hash: "default",
        },
      ],
    });
    metadataSchemasApi.get.mockResolvedValue(defaultSchema);
  });

  it("loads the empty workspace and exposes the source/configuration workflow", async () => {
    const wrapper = await mountBuilder();

    expect(pdfCorpusApi.listAssets).toHaveBeenCalledTimes(1);
    expect(pdfCorpusApi.profiles).toHaveBeenCalledTimes(1);
    expect(pdfCorpusApi.listBuilds).toHaveBeenCalledWith(0, 100);
    expect(systemApi.researcherProviders).toHaveBeenCalledTimes(1);
    expect(metadataSchemasApi.list).toHaveBeenCalledTimes(1);
    expect(metadataSchemasApi.get).toHaveBeenCalledWith("default");

    expect(wrapper.findComponent({ name: "CorpusBuilderWorkspaceHeader" }).exists()).toBe(true);
    const steps = wrapper.findComponent({ name: "CorpusBuilderWorkspaceHeader" }).props("steps");
    expect(steps.map((step: { id: string }) => step.id)).toEqual([
      "setup",
      "build",
      "review",
      "publish",
    ]);
    // Without a build only Setup can be entered.
    expect(steps.map((step: { available: boolean }) => step.available)).toEqual([
      true,
      false,
      false,
      false,
    ]);
    const setup = wrapper.findComponent({ name: "CorpusSetupWorkspace" });
    expect(setup.props("sections").map((section: { id: string }) => section.id)).toEqual([
      "source",
      "structure",
      "metadata",
      "enrichment",
      "advanced",
    ]);
    expect(setup.props("expanded")).toBe("source");

    wrapper.unmount();
  });

  describe("workspace routing", () => {
    beforeEach(() => {
      pdfCorpusApi.listBuilds.mockResolvedValue({
        items: [reviewBuild],
        total: 1,
        offset: 0,
        limit: 100,
      });
      pdfCorpusApi.build.mockResolvedValue({ ...reviewBuild, publication_readiness: {} });
      pdfCorpusApi.listAssets.mockResolvedValue({
        items: [{ asset_id: "asset-1", filename: "source.pdf", page_count: 1 }],
      });
    });

    it("renders the document manifest editor in the build workspace", async () => {
      pdfCorpusApi.build.mockResolvedValue({ ...reviewBuild, manifest: { title: "Lecture" } });
      const wrapper = await mountBuilder("?workspace=build&build=build-1", true);
      const editor = wrapper.findComponent(DocumentManifestEditor);
      expect(editor.exists()).toBe(true);
      expect(editor.props("manifest")).toEqual({ title: "Lecture" });
      wrapper.unmount();
    });

    it.each([
      ["build", "CorpusBuildWorkspace"],
      ["review", "CorpusReviewWorkspace"],
      ["publish", "CorpusPublishWorkspace"],
    ])("renders %s from ?workspace=%s without a stepper or build rail", async (workspace, name) => {
      const wrapper = await mountBuilder(`?workspace=${workspace}&build=build-1`);
      expect(wrapper.findComponent({ name }).exists()).toBe(true);
      expect(wrapper.find(".build-rail").exists()).toBe(false);
      expect(wrapper.findComponent({ name: "CorpusWorkflowStepper" }).exists()).toBe(false);
      const header = wrapper.findComponent({ name: "CorpusBuilderWorkspaceHeader" });
      expect(header.props("workspace")).toBe(workspace);
      wrapper.unmount();
    });

    it("keeps Publish available for a build that is not yet publishable and switches on request", async () => {
      const wrapper = await mountBuilder("?workspace=build&build=build-1");
      const steps = wrapper
        .findComponent({ name: "CorpusBuilderWorkspaceHeader" })
        .props("steps") as Array<{ id: string; available: boolean }>;
      expect(steps.find((step) => step.id === "publish")?.available).toBe(true);
      wrapper
        .findComponent({ name: "CorpusBuilderWorkspaceHeader" })
        .vm.$emit("workspace", "publish");
      await flushPromises();
      expect(wrapper.router.currentRoute.value.query.workspace).toBe("publish");
      expect(wrapper.router.currentRoute.value.query.build).toBe("build-1");
      wrapper.unmount();
    });

    it("moves publication blockers into Review before opening the queue", async () => {
      const wrapper = await mountBuilder("?workspace=publish&build=build-1");
      wrapper.findComponent({ name: "CorpusPublishWorkspace" }).vm.$emit("reviewRecords");
      await flushPromises();
      expect(wrapper.router.currentRoute.value.query.workspace).toBe("review");
      wrapper.unmount();
    });

    it("preserves the active inspector, evidence field and source page during refresh", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        selectedRecord: typeof reviewRecord | null;
        selectedEvidenceField: string;
        selectedPdfPage: number;
        reviewInspectorTab: string;
        reviewRecords: { refreshRecord: (id: string) => Promise<void> };
      };
      exposed.reviewInspectorTab = "evidence";
      exposed.selectedEvidenceField = "speaker";
      exposed.selectedPdfPage = 4;
      await flushPromises();
      const sourceReads = pdfCorpusApi.blocks.mock.calls.length;
      const viewed = pdfCorpusApi.markViewed.mock.calls.length;
      let release!: (records: unknown[]) => void;
      corpusReviewReads.records.mockImplementationOnce(
        () => new Promise((resolve) => (release = resolve)),
      );
      const refreshing = exposed.reviewRecords.refreshRecord("record-1");
      await flushPromises();
      expect(exposed.selectedRecord?.record_id).toBe("record-1");
      release([{ ...reviewRecord, record_revision: 2, text: "Refreshed text" }]);
      await refreshing;
      await flushPromises();
      expect(exposed.selectedRecord?.text).toBe("Refreshed text");
      expect(exposed.reviewInspectorTab).toBe("evidence");
      expect(exposed.selectedEvidenceField).toBe("speaker");
      expect(exposed.selectedPdfPage).toBe(4);
      expect(pdfCorpusApi.blocks).toHaveBeenCalledTimes(sourceReads);
      expect(pdfCorpusApi.markViewed).toHaveBeenCalledTimes(viewed);
      wrapper.unmount();
    });
  });

  it("keeps working on the built-in schema when the schema list comes back without items", async () => {
    metadataSchemasApi.list.mockResolvedValue({} as never);
    const wrapper = await mountBuilder();
    // Before the fix the list became undefined and reading the chosen schema threw.
    const exposed = wrapper.vm as unknown as { schemaChoices: unknown[]; chosenSchema: unknown };
    expect(exposed.schemaChoices).toEqual([]);
    expect(exposed.chosenSchema).toBeUndefined();
    expect(metadataSchemasApi.get).toHaveBeenCalledWith("default");
    wrapper.unmount();
  });

  it("applies text edits before the unresolved persistence request settles", async () => {
    pdfCorpusApi.listBuilds.mockResolvedValue({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    pdfCorpusApi.listAssets.mockResolvedValue({
      items: [{ asset_id: "asset-1", filename: "source.pdf", page_count: 1 }],
    });
    pdfCorpusApi.blocks.mockResolvedValue({
      items: [{ block_id: "block-1", page: 1, text: "Original text" }],
      total: 1,
      offset: 0,
      limit: 500,
    });
    pdfCorpusApi.patchText.mockReturnValue(new Promise(() => undefined));
    const wrapper = await mountBuilder();
    const exposed = wrapper.vm as unknown as {
      selectedRecord: typeof reviewRecord;
      saveTextFromFocus: (text: string, resolve: boolean) => Promise<void>;
    };

    const queueReadsBeforeSave = corpusReviewReads.queuePage.mock.calls.length;
    await exposed.saveTextFromFocus("Edited immediately", false);

    expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(queueReadsBeforeSave);
    expect(exposed.selectedRecord.text).toBe("Edited immediately");
    expect(exposed.selectedRecord.record_revision).toBe(2);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(pdfCorpusApi.patchText).toHaveBeenCalledWith(
      "build-1",
      "record-1",
      "Edited immediately",
      1,
      false,
    );
    wrapper.unmount();
  });

  it("keeps the local edit and scopes a persistence error to its record and field", async () => {
    pdfCorpusApi.listBuilds.mockResolvedValue({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    pdfCorpusApi.listAssets.mockResolvedValue({
      items: [{ asset_id: "asset-1", filename: "source.pdf", page_count: 1 }],
    });
    pdfCorpusApi.blocks.mockResolvedValue({
      items: [{ block_id: "block-1", page: 1, text: "Original text" }],
      total: 1,
      offset: 0,
      limit: 500,
    });
    pdfCorpusApi.patchText.mockRejectedValue(new Error("offline"));
    const wrapper = await mountBuilder();
    const exposed = wrapper.vm as unknown as {
      selectedRecord: typeof reviewRecord;
      saveTextFromFocus: (text: string, resolve: boolean) => Promise<void>;
      error: string;
    };

    await exposed.saveTextFromFocus("Edited locally", false);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(exposed.selectedRecord.text).toBe("Edited locally");
    expect(exposed.error).toContain("record-1");
    expect(exposed.error).toContain("text");
    expect(exposed.error).toContain("offline");
    expect(pdfCorpusApi.patchText).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it("returns to the record split view when fixing a validation issue found from a full-screen workspace mode", async () => {
    pdfCorpusApi.listBuilds.mockResolvedValue({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    const wrapper = await mountBuilder();
    const exposed = wrapper.vm as unknown as {
      reviewWorkspaceMode: string;
      setReviewWorkspaceMode: (mode: string) => void;
      fixValidationIssue: (issue: {
        code?: string;
        record_id?: string;
        field?: string;
        reason?: string;
      }) => Promise<void>;
    };

    // The reviewer left the split "record" view in a full-screen Source workspace on
    // whatever record they last reviewed. The metadata/evidence panels only render in
    // "record" mode, so fixing a validation finding must force it back, or the
    // reviewer lands on the target record with no visible way to see the problem.
    exposed.setReviewWorkspaceMode("source");
    expect(exposed.reviewWorkspaceMode).toBe("source");

    await exposed.fixValidationIssue({
      code: "metadata_evidence",
      record_id: "record-1",
      field: "speaker",
      reason: "no valid source block",
    });

    expect(exposed.reviewWorkspaceMode).toBe("record");
    wrapper.unmount();
  });

  it("shows acceptance immediately while authoritative review persistence is pending", async () => {
    pdfCorpusApi.listBuilds.mockResolvedValue({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    pdfCorpusApi.listAssets.mockResolvedValue({
      items: [{ asset_id: "asset-1", filename: "source.pdf", page_count: 1 }],
    });
    pdfCorpusApi.blocks.mockResolvedValue({
      items: [{ block_id: "block-1", page: 1, text: "Original text" }],
      total: 1,
      offset: 0,
      limit: 500,
    });
    pdfCorpusApi.reviewDecision.mockReturnValue(new Promise(() => undefined));
    const wrapper = await mountBuilder();
    const exposed = wrapper.vm as unknown as {
      selectedRecord: typeof reviewRecord;
      setDisposition: (disposition: "accepted") => Promise<void>;
    };

    await exposed.setDisposition("accepted");

    expect(exposed.selectedRecord.review_disposition).toBe("accepted");
    expect(exposed.selectedRecord.accepted).toBe(true);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(pdfCorpusApi.reviewDecision).toHaveBeenCalledWith(
      "build-1",
      "record-1",
      "accepted",
      "",
      1,
      "all",
    );
    wrapper.unmount();
  });
});
