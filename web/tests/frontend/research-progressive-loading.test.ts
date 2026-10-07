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

import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, reactive, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({
  start: vi.fn(),
  push: vi.fn(),
  snapshot: vi.fn(),
  update: vi.fn(),
  runs: vi.fn(),
  pipelines: vi.fn(),
  job: vi.fn(),
  follow: vi.fn(() => vi.fn()),
  loadComposerDraft: vi.fn(),
  saveComposerDraft: vi.fn(),
  auth: { user: { id: 1, role: "researcher" }, allowed: true },
  route: { name: "rag", query: {} as Record<string, string> },
}));
vi.mock("vue-router", () => ({
  useRoute: () => reactive(mocks.route),
  useRouter: () => ({ push: mocks.push, replace: vi.fn() }),
}));
vi.mock("../../src/stores/auth", () => ({
  useAuthStore: () => {
    const state = reactive(mocks.auth);
    return {
      get user() {
        return state.user;
      },
      can: () => state.allowed,
      isAdmin: false,
    };
  },
}));
vi.mock("../../src/stores/i18n", () => ({
  useI18nStore: () => ({ t: (key: string) => key, tf: (key: string) => key, locale: "en-US" }),
}));
vi.mock("../../src/domain/researchActions", () => ({
  startResearchRun: mocks.start,
  getResearchWorkspaceSnapshot: mocks.snapshot,
  refreshResearchJobs: mocks.runs,
  updateResearchConfig: mocks.update,
}));
vi.mock("../../src/domain/sharedAnnotations", () => ({ annotationsWorkspace: {} }));
vi.mock("../../src/domain/sharedResearchJobs", () => ({ getResearchJob: mocks.job }));
vi.mock("../../src/realtime/follow", () => ({ followResource: mocks.follow }));
vi.mock("../../src/features/research/useResearchDraft", () => ({
  useResearchDraft: () => ({ draft: ref(null), follow: vi.fn(), clear: vi.fn() }),
}));
vi.mock("../../src/features/research/researchComposerDraft", () => ({
  loadResearchComposerDraft: mocks.loadComposerDraft,
  saveResearchComposerDraft: mocks.saveComposerDraft,
}));
vi.mock("../../src/api/pipelines", () => ({ pipelinesApi: { researchOptions: mocks.pipelines } }));
import ResearchView from "../../src/views/ResearchView.vue";
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const snapshot = () => ({
  config: {
    prompt: "Saved prompt",
    instructions: "",
    provider_profile_id: "p",
    source_collection: "corpus",
    prompt_metadata: { evidence: [], context: [], record: [] },
  },
  stores: [{ name: "corpus" }],
  profiles: [{ id: "p" }],
  jobs: [],
  selected_evidence: [],
  history: [],
  pipeline_options: [],
  can_run: true,
  can_manage_jobs: true,
  is_researcher: false,
});
const Composer = defineComponent({
  inheritAttrs: false,
  props: ["prompt", "canRun", "pipelineOverride"],
  emits: [
    "update:prompt",
    "run",
    "settings",
    "pipelineSettings",
    "promptMetadata",
    "runs",
    "history",
  ],
  template:
    '<input class="composer" :value="prompt" @input="$emit(\'update:prompt\', $event.target.value)" /><button class="run" :disabled="!canRun" @click="$emit(\'run\')">Run</button>',
});
const ThreadBrowser = defineComponent({
  name: "ResearchThreadBrowser",
  props: ["threadId", "jobId", "retryDisabled", "refreshKey"],
  emits: ["retryTurn"],
  template: '<div class="thread-browser" />',
});
const Result = defineComponent({
  props: ["job", "result"],
  template: '<div class="answer">{{ job?.id }} {{ result?.answer }}</div>',
});
const mounted: ReturnType<typeof mount>[] = [];
function render() {
  const w = mount(ResearchView, {
    global: {
      stubs: {
        UiPageHeader: { template: '<header><h1 id="research-page-title">Research</h1></header>' },
        UiLoadingState: { props: ["label"], template: '<div role="status">{{ label }}</div>' },
        ResearchThreadBrowser: ThreadBrowser,
        ResearchComposer: Composer,
        ResearchResultPresentation: Result,
        ResearchPipelineBar: true,
        ResearchSettingsDrawer: true,
        ResearchRunsDrawer: true,
        AccessibleEmptyState: true,
      },
    },
  });
  mounted.push(w);
  return w;
}
beforeEach(() => {
  vi.clearAllMocks();
  mocks.auth.allowed = true;
  mocks.auth.user = { id: 1, role: "researcher" };
  reactive(mocks.route).name = "rag";
  reactive(mocks.route).query = {};
  mocks.snapshot.mockResolvedValue(snapshot());
  mocks.loadComposerDraft.mockResolvedValue(null);
  mocks.saveComposerDraft.mockResolvedValue(undefined);
  mocks.update.mockImplementation((patch) => ({ ...snapshot().config, ...patch }));
  mocks.runs.mockResolvedValue([]);
  mocks.pipelines.mockResolvedValue({
    assignment: null,
    pipelines: [],
    strategies: [],
    override_allowed: false,
  });
});
afterEach(() => mounted.splice(0).forEach((w) => w.unmount()));
describe("Research progressive reads", () => {
  it("persists typing through the Research draft repository without updating global config", async () => {
    vi.useFakeTimers();
    try {
      const w = render();
      await flushPromises();
      await w.get(".composer").setValue("Local draft");
      await vi.advanceTimersByTimeAsync(300);

      expect(mocks.saveComposerDraft).toHaveBeenLastCalledWith({
        prompt: "Local draft",
        instructions: "",
      });
      expect(mocks.update).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not turn streamed token events into REST job refreshes", async () => {
    const liveJob = { id: "live", status: "running" };
    mocks.snapshot.mockResolvedValue({ ...snapshot(), jobs: [liveJob] });
    mocks.runs.mockResolvedValue([liveJob]);
    render();
    await flushPromises();
    const calls = mocks.follow.mock.calls as unknown as Array<
      [{ topic: string; onEvent: (event: { type: string }) => boolean }]
    >;
    const options = calls.map((call) => call[0]).find((item) => item.topic === "job:live");
    expect(options).toBeDefined();
    expect(options!.onEvent({ type: "llm.token" })).toBe(false);
    expect(options!.onEvent({ type: "job.updated" })).toBe(true);
  });

  it("retries the original turn without enabling follow-ups or duplicating a click", async () => {
    reactive(mocks.route).query = { thread: "t" };
    const pending = deferred<any>();
    mocks.start.mockReturnValue(pending.promise);
    const w = render();
    await flushPromises();
    await w.get(".composer").setValue("Unrelated draft");
    const browser = w.findComponent(ThreadBrowser);
    const turn = {
      thread_id: "t",
      turn_id: "turn",
      status: "failed",
      user_question: "Original question",
      user_instructions: "Original instructions",
    };
    browser.vm.$emit("retryTurn", turn);
    browser.vm.$emit("retryTurn", turn);
    await flushPromises();
    expect(mocks.start).toHaveBeenCalledOnce();
    expect(mocks.start.mock.calls[0][0]).toMatchObject({
      prompt: "Original question",
      instructions: "Original instructions",
      retry_thread_id: "t",
      retry_turn_id: "turn",
    });
    expect(browser.props("retryDisabled")).toBe(true);
    expect(w.get(".run").attributes("disabled")).toBeDefined();
    pending.resolve({ id: "retried", status: "running", thread_id: "t", turn_id: "turn" });
    await flushPromises();
    expect(mocks.push).toHaveBeenCalledWith({
      path: "/rag",
      query: { thread: "t", job: "retried" },
    });
  });
  it("discards a late retry submission after an account switch", async () => {
    reactive(mocks.route).query = { thread: "t" };
    const pending = deferred<any>();
    mocks.start.mockReturnValue(pending.promise);
    const w = render();
    await flushPromises();
    w.findComponent(ThreadBrowser).vm.$emit("retryTurn", {
      thread_id: "t",
      turn_id: "turn",
      status: "cancelled",
      user_question: "Original",
    });
    await flushPromises();
    reactive(mocks.auth).user = { id: 2, role: "researcher" };
    await flushPromises();
    pending.resolve({ id: "old-account-job", status: "running", thread_id: "t", turn_id: "turn" });
    await flushPromises();
    expect(mocks.push).not.toHaveBeenCalled();
    expect(w.text()).not.toContain("old-account-job");
  });
  it("refreshes authoritative thread state after an uncertain retry without repeating it", async () => {
    reactive(mocks.route).query = { thread: "t" };
    mocks.start.mockRejectedValue(new Error("Connection interrupted"));
    const w = render();
    await flushPromises();
    const browser = w.findComponent(ThreadBrowser);
    browser.vm.$emit("retryTurn", {
      thread_id: "t",
      turn_id: "turn",
      status: "failed",
      user_question: "Original",
    });
    await flushPromises();
    expect(browser.props("refreshKey")).toBe(1);
    expect(mocks.start).toHaveBeenCalledOnce();
  });
  it("links a newly submitted run to the server-created thread", async () => {
    mocks.start.mockResolvedValue({
      id: "new-job",
      status: "running",
      thread_id: "new-thread",
      turn_id: "new-turn",
    });
    const w = render();
    await flushPromises();
    await w.get(".composer").setValue("A new inquiry");
    await w.get(".run").trigger("click");
    await flushPromises();
    expect(mocks.start).toHaveBeenCalledOnce();
    expect(mocks.start.mock.calls[0][0].prompt).toBe("A new inquiry");
    expect(mocks.push).toHaveBeenCalledWith({
      path: "/rag",
      query: { thread: "new-thread", job: "new-job" },
    });
  });
  it("clears an unavailable pipeline override locally after visibility succeeds", async () => {
    mocks.snapshot.mockResolvedValue({
      ...snapshot(),
      config: { ...snapshot().config, pipeline_id: "retired", pipeline_version: 1 },
    });
    const pending = deferred<any>();
    mocks.pipelines.mockReturnValue(pending.promise);
    const w = render();
    await flushPromises();
    expect(mocks.update).not.toHaveBeenCalled();
    pending.resolve({ assignment: null, pipelines: [], strategies: [], override_allowed: false });
    await flushPromises();
    // Research controls are now a one-run draft: clearing a stale pipeline selection
    // must not mutate the Settings defaults persisted through updateResearchConfig.
    expect(mocks.update).not.toHaveBeenCalled();
    expect(w.findComponent(Composer).props("pipelineOverride")).toBe(false);
    expect(w.find(".research-pipelines-status").exists()).toBe(false);
  });
  it("keeps optional run and pipeline reads independent of the composer", async () => {
    const runs = deferred<any[]>(),
      pipelines = deferred<any>();
    mocks.runs.mockReturnValue(runs.promise);
    mocks.pipelines.mockReturnValue(pipelines.promise);
    const w = render();
    await flushPromises();
    expect((w.get(".composer").element as HTMLInputElement).value).toBe("Saved prompt");
    expect(mocks.snapshot).toHaveBeenCalledWith(
      expect.objectContaining({
        includeJobs: false,
        includePipelines: false,
        strictCollections: true,
      }),
    );
    runs.reject(new Error("Runs unavailable"));
    pipelines.reject(new Error("Pipelines unavailable"));
    await flushPromises();
    expect(w.get(".research-runs-status").text()).toContain("Runs unavailable");
    expect(w.get(".research-pipelines-status").text()).toContain("Pipelines unavailable");
    mocks.runs.mockResolvedValue([]);
    await w.get(".research-runs-status button").trigger("click");
    await flushPromises();
    expect(mocks.snapshot).toHaveBeenCalledTimes(1);
    expect(mocks.pipelines).toHaveBeenCalledTimes(1);
  });
  it("retains the composer and draft when a refresh fails", async () => {
    const w = render();
    await flushPromises();
    const input = w.get(".composer").element;
    await w.get(".composer").setValue("Unsaved draft");
    mocks.snapshot.mockRejectedValueOnce(new Error("Refresh unavailable"));
    reactive(mocks.route).query = { job: "a" };
    mocks.job.mockResolvedValue({ id: "a", status: "completed" });
    await flushPromises();
    expect(w.get(".composer").element).toBe(input);
    expect((input as HTMLInputElement).value).toBe("Unsaved draft");
    expect(w.get(".research-workspace-status").text()).toContain("loading.stale");
    expect(w.get(".research-workspace-status").text()).toContain("Refresh unavailable");
  });
  it("does not apply a pending workspace read after leaving Research", async () => {
    const pending = deferred<ReturnType<typeof snapshot>>();
    mocks.snapshot.mockReturnValue(pending.promise);
    const w = render();
    reactive(mocks.route).name = "other";
    await flushPromises();
    pending.resolve(snapshot());
    await flushPromises();
    expect((w.get(".composer").element as HTMLInputElement).value).toBe("");
    reactive(mocks.route).name = "rag";
  });
  it("shows the header and disabled composer before the first read completes", async () => {
    const pending = deferred<ReturnType<typeof snapshot>>();
    mocks.snapshot.mockReturnValue(pending.promise);
    const w = render();
    expect(w.find("#research-page-title").exists()).toBe(true);
    expect(w.find(".composer").exists()).toBe(true);
    expect(w.get(".run").attributes("disabled")).toBeDefined();
    pending.resolve(snapshot());
    await flushPromises();
  });
  it("keeps a prompt typed during the initial read", async () => {
    const pending = deferred<ReturnType<typeof snapshot>>();
    mocks.snapshot.mockReturnValue(pending.promise);
    const w = render();
    await w.get(".composer").setValue("My draft");
    pending.resolve(snapshot());
    await flushPromises();
    expect((w.get(".composer").element as HTMLInputElement).value).toBe("My draft");
  });
  it("makes an initial read failure visible and retryable", async () => {
    mocks.snapshot.mockRejectedValueOnce(new Error("Offline"));
    const w = render();
    await flushPromises();
    expect(w.get("[role=alert]").text()).toContain("Offline");
    mocks.snapshot.mockResolvedValue(snapshot());
    await w.get("[role=alert] button").trigger("click");
    await flushPromises();
    expect(w.find("[role=alert]").exists()).toBe(false);
  });
  it("does not hold the workspace loading state while a saved answer loads", async () => {
    mocks.route.query = { job: "a" };
    const pending = deferred<any>();
    mocks.job.mockReturnValue(pending.promise);
    const w = render();
    await flushPromises();
    expect(w.get(".composer").attributes("value")).toBe("Saved prompt");
    expect(w.find(".research-workspace-status").exists()).toBe(false);
    expect(w.findAll("[role=status]")).toHaveLength(1);
    pending.resolve({ id: "a", status: "completed", result: { answer: "Answer A" } });
    await flushPromises();
    expect(w.get(".answer").text()).toContain("Answer A");
  });
  it("keeps answer failure local and retries without rereading the workspace", async () => {
    mocks.route.query = { job: "a" };
    mocks.job.mockRejectedValueOnce(new Error("Answer unavailable"));
    const w = render();
    await flushPromises();
    expect(w.get(".research-answer-status").text()).toContain("Answer unavailable");
    mocks.job.mockResolvedValue({ id: "a", status: "completed", result: { answer: "Recovered" } });
    await w.get(".research-answer-status button").trigger("click");
    await flushPromises();
    expect(mocks.snapshot).toHaveBeenCalledTimes(1);
    expect(w.get(".answer").text()).toContain("Recovered");
  });
  it("ignores a late answer after a different answer is selected", async () => {
    mocks.route.query = { job: "a" };
    const pending = deferred<any>();
    mocks.job
      .mockReturnValueOnce(pending.promise)
      .mockResolvedValueOnce({ id: "b", status: "completed", result: { answer: "Answer B" } });
    const w = render();
    await flushPromises();
    w.findComponent({ name: "ResearchPipelineBar" }).vm.$emit("select", {
      id: "b",
      status: "completed",
    });
    await flushPromises();
    pending.resolve({ id: "a", status: "completed", result: { answer: "Answer A" } });
    await flushPromises();
    expect(w.get(".answer").text()).toContain("Answer B");
    expect(w.get(".answer").text()).not.toContain("Answer A");
  });
});

describe("Research thread URL state", () => {
  it("blocks follow-up submission until advisory context exists", async () => {
    mocks.route.query = { thread: "thread-a" };
    const w = render();
    await flushPromises();
    expect(w.get(".run").attributes("disabled")).toBeDefined();
    expect(w.findComponent({ name: "ResearchThreadBrowser" }).exists()).toBe(true);
    expect(mocks.job).not.toHaveBeenCalled();
  });
  it("restores the URL's run and discards a late answer from the previous thread", async () => {
    mocks.route.query = { thread: "thread-a", job: "a" };
    const pending = deferred<any>();
    mocks.job
      .mockReturnValueOnce(pending.promise)
      .mockResolvedValue({ id: "b", status: "completed", result: { answer: "Answer B" } });
    const w = render();
    await flushPromises();
    reactive(mocks.route).query = { thread: "thread-b", job: "b" };
    await flushPromises();
    pending.resolve({ id: "a", status: "completed", result: { answer: "Answer A" } });
    await flushPromises();
    expect(w.get(".answer").text()).toContain("Answer B");
    expect(w.get(".answer").text()).not.toContain("Answer A");
  });
});

it("clears the selected thread answer when Research access is revoked", async () => {
  mocks.route.query = { thread: "thread-a", job: "a" };
  mocks.job.mockResolvedValue({
    id: "a",
    status: "completed",
    result: { answer: "Private answer" },
  });
  const w = render();
  await flushPromises();
  expect(w.get(".answer").text()).toContain("Private answer");
  reactive(mocks.auth).allowed = false;
  await flushPromises();
  expect(w.text()).not.toContain("Private answer");
});
