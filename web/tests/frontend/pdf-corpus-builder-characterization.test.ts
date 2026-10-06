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
import type { ProviderProfile } from "../../src/api/system";

const pdfCorpusApi = vi.hoisted(() => ({
  listAssets: vi.fn(),
  profiles: vi.fn(),
  listBuilds: vi.fn(),
  build: vi.fn(),
  blocks: vi.fn(),
  markViewed: vi.fn(),
  patchText: vi.fn(),
  patchMetadata: vi.fn(),
  switchProviderProfile: vi.fn(),
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
  llmStatus: vi.fn(),
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
  getProviderProfilesForUi: vi.fn<() => ProviderProfile[]>(() => []),
  getProviderRequestConfigForUi: vi.fn<() => Record<string, unknown> | null>(() => null),
  getDefaultProviderProfileId: vi.fn(() => ""),
  state: { pdf: { file: null } },
}));

vi.mock("../../src/domain/sharedProviderProfiles", () => ({
  getProviderProfilesForUi: runtime.getProviderProfilesForUi,
  getProviderRequestConfigForUi: runtime.getProviderRequestConfigForUi,
  getDefaultProviderProfileId: runtime.getDefaultProviderProfileId,
}));

vi.mock("../../src/domain/appBootstrap", () => ({
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
import * as recordMetadataDomain from "../../src/features/corpus-builder/domain/recordMetadata";

const defaultSchema = {
  format_version: 1,
  id: "default",
  name: "Default",
  description: "Default metadata schema",
  groups: [],
  fields: [],
};

async function mountBuilder(
  query = "",
  renderManifest = false,
  renderReview = false,
  renderHeaderActions = false,
) {
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
      stubs: {
        ...(renderManifest
          ? { CorpusBuildWorkspace: { template: '<div><slot name="manifest" /></div>' } }
          : {}),
        ...(renderReview
          ? {
              CorpusReviewWorkspace: {
                template: '<div><slot name="header" /><slot name="inspector" /></div>',
              },
              CorpusReviewHeader: { template: '<div><slot name="run-status" /></div>' },
              CorpusReviewInspector: { template: "<div><slot /></div>" },
            }
          : {}),
        ...(renderHeaderActions
          ? {
              CorpusBuilderWorkspaceHeader: {
                template: '<header data-test="workspace-actions"><slot name="actions" /></header>',
              },
            }
          : {}),
      },
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
    runtime.getProviderProfilesForUi.mockReturnValue([]);
    runtime.getProviderRequestConfigForUi.mockReturnValue(null);
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
    systemApi.llmStatus.mockResolvedValue({ available: true, models: [{ name: "old-model" }] });
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

  it("distinguishes another build from choosing another source", async () => {
    const asset = {
      asset_id: "asset-1",
      filename: "Source.pdf",
      media_kind: "pdf",
      page_count: 1,
      block_count: 1,
      pages: [],
    };
    pdfCorpusApi.listAssets.mockResolvedValueOnce({ items: [asset] });
    pdfCorpusApi.listBuilds.mockResolvedValueOnce({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });

    const retain = await mountBuilder("?workspace=build&build=build-1", false, false, true);
    const retainButtons = retain.findAllComponents({ name: "UiButton" });
    const fromSource = retainButtons.find(
      (button) => button.props("label") === "New build from this source",
    );
    const chooseSource = retainButtons.find(
      (button) => button.props("label") === "Choose another source",
    );
    expect(fromSource).toBeTruthy();
    expect(chooseSource).toBeTruthy();

    fromSource!.vm.$emit("click");
    await flushPromises();

    expect(retain.router.currentRoute.value.query.workspace).toBe("setup");
    expect(retain.router.currentRoute.value.query.build).toBeUndefined();
    expect(retain.findComponent({ name: "CorpusSourceIngest" }).props("assetId")).toBe("asset-1");
    retain.unmount();

    pdfCorpusApi.listAssets.mockResolvedValueOnce({ items: [asset] });
    pdfCorpusApi.listBuilds.mockResolvedValueOnce({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    const change = await mountBuilder("?workspace=build&build=build-1", false, false, true);
    const changeButtons = change.findAllComponents({ name: "UiButton" });
    const chooseAnother = changeButtons.find(
      (button) => button.props("label") === "Choose another source",
    );
    chooseAnother!.vm.$emit("click");
    await flushPromises();

    expect(change.router.currentRoute.value.query.workspace).toBe("setup");
    expect(change.findComponent({ name: "CorpusSourceIngest" }).props("assetId")).toBe("");
    change.unmount();
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

    it.each([false, true])(
      "sends the selected model instead of the profile default (server managed: %s)",
      async (serverManaged) => {
        const profile = { id: "local", name: "Local", type: "ollama" as const, model: "old-model" };
        runtime.getProviderProfilesForUi.mockReturnValue([profile]);
        runtime.getProviderRequestConfigForUi.mockReturnValue({
          provider: "ollama",
          model: "old-model",
          base_url: "http://localhost:11434",
          api_key: "test-key",
          ollama: { num_ctx: 8192 },
        });
        systemApi.researcherProviders.mockResolvedValue({
          profiles: serverManaged ? [profile] : [],
        });
        pdfCorpusApi.switchProviderProfile.mockResolvedValue({
          ...reviewBuild,
          model: "new-model",
          request: { provider_profile_id: "local", model: "new-model" },
        });
        const wrapper = await mountBuilder("?workspace=review&build=build-1", false, true);
        try {
          const status = wrapper.findComponent({ name: "CorpusReviewRunStatus" });
          expect(status.exists()).toBe(true);
          status.vm.$emit("switch-profile", "local", "  new-model  ");
          await flushPromises();
          expect(pdfCorpusApi.switchProviderProfile).toHaveBeenCalledWith(
            "build-1",
            expect.objectContaining({
              provider_profile_id: "local",
              model: "new-model",
              base_url: "http://localhost:11434",
              api_key: "test-key",
            }),
          );
          expect(status.props("activeModel")).toBe("new-model");
        } finally {
          wrapper.unmount();
        }
      },
    );

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

    it("does not reload review rows when a phase switch leaves Review", async () => {
      const wrapper = await mountBuilder(
        "?workspace=review&build=build-1&queue=all&record=record-1",
      );
      corpusReviewReads.queuePage.mockClear();

      wrapper
        .findComponent({ name: "CorpusBuilderWorkspaceHeader" })
        .vm.$emit("workspace", "publish");
      await flushPromises();

      expect(wrapper.router.currentRoute.value.query.workspace).toBe("publish");
      expect(corpusReviewReads.queuePage).not.toHaveBeenCalled();
      wrapper.unmount();
    });

    it("applies a build, queue and record route change with one review-page read", async () => {
      pdfCorpusApi.build.mockImplementation(async (buildId: string) => ({
        ...reviewBuild,
        build_id: buildId,
        publication_readiness: {},
      }));
      const wrapper = await mountBuilder(
        "?workspace=review&build=build-1&queue=all&record=record-1",
      );
      pdfCorpusApi.build.mockClear();
      corpusReviewReads.queuePage.mockClear();

      await wrapper.router.push({
        name: "corpus-builder",
        query: {
          workspace: "review",
          build: "build-2",
          queue: "metadata",
          record: "record-2",
        },
      });
      await flushPromises();

      expect(pdfCorpusApi.build).toHaveBeenCalledTimes(1);
      expect(pdfCorpusApi.build).toHaveBeenCalledWith("build-2");
      expect(corpusReviewReads.queuePage).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("defers autocomplete outside Review and loads when the metadata inspector becomes visible", async () => {
      const wrapper = await mountBuilder("?workspace=build&build=build-1");
      expect(corpusReviewReads.metadataFacets).not.toHaveBeenCalled();
      wrapper
        .findComponent({ name: "CorpusBuilderWorkspaceHeader" })
        .vm.$emit("workspace", "review");
      await flushPromises();
      expect(corpusReviewReads.metadataFacets).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("does not persist clean advanced metadata on activation or authoritative refresh", async () => {
      const writes = vi.spyOn(Storage.prototype, "setItem");
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        applyAuthoritativeRecord: (record: typeof reviewRecord) => void;
      };
      exposed.applyAuthoritativeRecord({ ...reviewRecord, record_revision: 2 });
      await flushPromises();
      expect(
        writes.mock.calls.filter(([key]) => key.startsWith("derridai.pdf-corpus.metadata-draft.")),
      ).toEqual([]);
      wrapper.unmount();
      writes.mockRestore();
    });

    it("formats clean advanced metadata only while its disclosure is visible", async () => {
      const formatting = vi.spyOn(recordMetadataDomain, "editableRecordMetadata");
      const wrapper = await mountBuilder("?workspace=review&build=build-1", false, true);
      const exposed = wrapper.vm as unknown as {
        metadataDraft: string;
        activateRecord: (record: typeof reviewRecord) => void;
        applyAuthoritativeRecord: (record: typeof reviewRecord) => void;
        reviewInspectorTab: string;
        reviewWorkspaceMode: string;
      };
      exposed.reviewWorkspaceMode = "record";
      expect(exposed.metadataDraft).toBe("");
      expect(formatting).not.toHaveBeenCalled();
      exposed.applyAuthoritativeRecord({ ...reviewRecord, record_revision: 2 });
      await flushPromises();
      expect(formatting).not.toHaveBeenCalled();
      const advanced = wrapper.findComponent({ name: "CorpusReviewAdvancedMetadata" });
      advanced.vm.$emit("disclosure", true);
      await flushPromises();
      expect(formatting).toHaveBeenCalledTimes(1);
      expect(exposed.metadataDraft).toBe(JSON.stringify(formatting.mock.results[0].value, null, 2));
      exposed.reviewInspectorTab = "evidence";
      await flushPromises();
      formatting.mockClear();
      exposed.activateRecord({ ...reviewRecord, record_revision: 3 });
      await flushPromises();
      expect(formatting).not.toHaveBeenCalled();
      exposed.reviewInspectorTab = "metadata";
      await flushPromises();
      expect(formatting).toHaveBeenCalledTimes(1);
      expect(formatting.mock.calls[0][0].record_revision).toBe(3);
      advanced.vm.$emit("disclosure", false);
      await flushPromises();
      formatting.mockClear();
      exposed.activateRecord({ ...reviewRecord, record_revision: 4 });
      expect(formatting).not.toHaveBeenCalled();
      wrapper.unmount();
      formatting.mockRestore();
    });

    it("recovers unsaved advanced metadata and preserves it after a failed save", async () => {
      const key = "derridai.pdf-corpus.metadata-draft.build-1.record-1";
      const draft = '{ "speaker": "Unsaved author" }';
      localStorage.setItem(key, draft);
      pdfCorpusApi.patchMetadata.mockRejectedValue(new Error("offline"));
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        metadataDraft: string;
        advancedMetadataDirty: boolean;
        saveAdvancedMetadata: () => Promise<void>;
        error: string;
      };
      expect(exposed.metadataDraft).toBe(draft);
      expect(exposed.advancedMetadataDirty).toBe(true);
      await exposed.saveAdvancedMetadata();
      await flushPromises();
      expect(exposed.error).toContain("offline");
      expect(exposed.metadataDraft).toBe(draft);
      expect(exposed.advancedMetadataDirty).toBe(true);
      expect(localStorage.getItem(key)).toBe(draft);
      wrapper.unmount();
      localStorage.removeItem(key);
    });

    it("removes a saved advanced draft without recreating it from optimistic metadata", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        metadataDraft: string;
        advancedMetadataDirty: boolean;
        saveAdvancedMetadata: () => Promise<void>;
      };
      pdfCorpusApi.patchMetadata.mockResolvedValue({ ...reviewRecord, record_revision: 2 });
      exposed.metadataDraft = '{ "speaker": "Saved author" }';
      exposed.advancedMetadataDirty = true;
      await flushPromises();
      await exposed.saveAdvancedMetadata();
      await flushPromises();
      expect(exposed.advancedMetadataDirty).toBe(false);
      expect(
        localStorage.getItem("derridai.pdf-corpus.metadata-draft.build-1.record-1"),
      ).toBeNull();
      wrapper.unmount();
    });

    it("keeps newer edits dirty when an earlier advanced save completes", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        metadataDraft: string;
        advancedMetadataDirty: boolean;
        saveAdvancedMetadata: () => Promise<void>;
      };
      let finish!: (value: unknown) => void;
      pdfCorpusApi.patchMetadata.mockImplementationOnce(
        () => new Promise((resolve) => (finish = resolve)),
      );
      exposed.metadataDraft = '{ "speaker": "First edit" }';
      exposed.advancedMetadataDirty = true;
      const saving = exposed.saveAdvancedMetadata();
      await flushPromises();
      const newer = '{ "speaker": "Later edit" }';
      exposed.metadataDraft = newer;
      exposed.advancedMetadataDirty = true;
      await flushPromises();
      finish({ ...reviewRecord, record_revision: 2 });
      await saving;
      expect(exposed.metadataDraft).toBe(newer);
      expect(exposed.advancedMetadataDirty).toBe(true);
      expect(localStorage.getItem("derridai.pdf-corpus.metadata-draft.build-1.record-1")).toBe(
        newer,
      );
      wrapper.unmount();
      localStorage.removeItem("derridai.pdf-corpus.metadata-draft.build-1.record-1");
    });

    it("persists edited advanced metadata without replacing it on a same-Record refresh", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        metadataDraft: string;
        advancedMetadataDirty: boolean;
        activateRecord: (record: typeof reviewRecord) => void;
      };
      const draft = '{ "speaker": "Edited author" }';
      exposed.metadataDraft = draft;
      exposed.advancedMetadataDirty = true;
      await flushPromises();
      const key = "derridai.pdf-corpus.metadata-draft.build-1.record-1";
      expect(localStorage.getItem(key)).toBe(draft);
      exposed.activateRecord({ ...reviewRecord, record_revision: 2 });
      await flushPromises();
      expect(exposed.metadataDraft).toBe(draft);
      wrapper.unmount();
      localStorage.removeItem(key);
    });

    it("loads source blocks only for visible consumers and reuses the current context", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        reviewInspectorTab: string;
        reviewWorkspaceMode: string;
      };
      expect(pdfCorpusApi.blocks).not.toHaveBeenCalled();
      exposed.reviewWorkspaceMode = "record";
      exposed.reviewInspectorTab = "evidence";
      await flushPromises();
      expect(pdfCorpusApi.blocks).toHaveBeenCalledTimes(1);
      exposed.reviewInspectorTab = "metadata";
      await flushPromises();
      exposed.reviewInspectorTab = "source";
      await flushPromises();
      expect(pdfCorpusApi.blocks).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("loads selected-text evidence on explicit demand and reports a failed load without saving", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        resolveMetadataWithSelectionEvidence: (
          field: string,
          value: unknown,
          text: string,
        ) => Promise<void>;
        error: string;
        selectedRecord: typeof reviewRecord;
      };
      expect(pdfCorpusApi.blocks).not.toHaveBeenCalled();
      pdfCorpusApi.blocks.mockRejectedValueOnce(new Error("Source load failed"));
      const record = exposed.selectedRecord;
      await exposed.resolveMetadataWithSelectionEvidence("speaker", "Author", "Selected text");
      expect(pdfCorpusApi.blocks).toHaveBeenCalledTimes(1);
      expect(exposed.error).toBe("Source load failed");
      expect(exposed.selectedRecord).toBe(record);
      wrapper.unmount();
    });

    it("discards source blocks returned after their consumer is hidden", async () => {
      let finish!: (result: { items: Array<{ block_id: string }> }) => void;
      pdfCorpusApi.blocks.mockImplementationOnce(
        () => new Promise((resolve) => (finish = resolve)),
      );
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        reviewInspectorTab: string;
        reviewWorkspaceMode: string;
        sourceBlocks: Array<{ block_id: string }>;
      };
      exposed.reviewWorkspaceMode = "record";
      exposed.reviewInspectorTab = "evidence";
      await flushPromises();
      exposed.reviewInspectorTab = "metadata";
      await flushPromises();
      finish({ items: [{ block_id: "block-1" }] });
      await flushPromises();
      expect(exposed.sourceBlocks).toEqual([]);
      exposed.reviewInspectorTab = "source";
      await flushPromises();
      expect(pdfCorpusApi.blocks).toHaveBeenCalledTimes(2);
      wrapper.unmount();
    });

    it("keeps autocomplete available for the bulk editor when the metadata inspector is hidden", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        reviewInspectorTab: string;
        bulkMetadataOpen: boolean;
        metadataFacetsActive: boolean;
      };
      exposed.reviewInspectorTab = "evidence";
      await flushPromises();
      expect(exposed.metadataFacetsActive).toBe(false);
      exposed.bulkMetadataOpen = true;
      await flushPromises();
      expect(exposed.metadataFacetsActive).toBe(true);
      exposed.bulkMetadataOpen = false;
      await flushPromises();
      expect(exposed.metadataFacetsActive).toBe(false);
      wrapper.unmount();
    });

    it("enables metadata assistance only for the visible inspector", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1", false, true);
      const exposed = wrapper.vm as unknown as {
        reviewInspectorTab: string;
        reviewWorkspaceMode: string;
      };
      exposed.reviewWorkspaceMode = "record";
      exposed.reviewInspectorTab = "evidence";
      await flushPromises();
      const panel = wrapper.findComponent({ name: "CorpusMetadataResolutionPanel" });
      expect(panel.props("active")).toBe(false);
      exposed.reviewInspectorTab = "metadata";
      await flushPromises();
      expect(panel.props("active")).toBe(true);
      exposed.reviewInspectorTab = "evidence";
      await flushPromises();
      expect(panel.props("active")).toBe(false);
      expect(wrapper.findComponent({ name: "CorpusMetadataResolutionPanel" }).vm).toBe(panel.vm);
      wrapper.unmount();
    });

    it("opens different Records without posting viewed activity", async () => {
      const wrapper = await mountBuilder("?workspace=review&build=build-1");
      const exposed = wrapper.vm as unknown as {
        selectedRecord: typeof reviewRecord | null;
        reviewRecords: { selectRecord: (record: typeof reviewRecord) => Promise<void> };
      };
      expect(exposed.selectedRecord?.record_id).toBe("record-1");
      await exposed.reviewRecords.selectRecord({ ...reviewRecord, record_id: "record-2" });
      await flushPromises();
      expect(exposed.selectedRecord?.record_id).toBe("record-2");
      await exposed.reviewRecords.selectRecord(reviewRecord);
      await flushPromises();
      expect(exposed.selectedRecord?.record_id).toBe("record-1");
      expect(pdfCorpusApi.markViewed).not.toHaveBeenCalled();
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
      expect(viewed).toBe(0);
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
      expect(pdfCorpusApi.blocks).toHaveBeenCalledTimes(sourceReads + 1);
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
