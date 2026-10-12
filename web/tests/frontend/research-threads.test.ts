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

import { mount, flushPromises } from "@vue/test-utils";
import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "../../src/stores/auth";
import { useI18nStore } from "../../src/stores/i18n";
import { realtime } from "../../src/realtime";
import type { EventHandler } from "../../src/realtime/client";
import { ApiError } from "../../src/api/http";
import ResearchThreadBrowser from "../../src/components/research/ResearchThreadBrowser.vue";
import ResearchThreadNavigation from "../../src/components/research/ResearchThreadNavigation.vue";
import type { ResearchThreadDetail, ResearchThreadSummary } from "../../src/types/researchThreads";

const jobs = vi.hoisted(() => ({ read: vi.fn() }));
vi.mock("../../src/api/http", async (original) => ({
  ...(await original<typeof import("../../src/api/http")>()),
  apiRequest: jobs.read,
}));
const api = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  patch: vi.fn(),
  remove: vi.fn(),
  exportThread: vi.fn(),
}));
const downloads = vi.hoisted(() => ({ blob: vi.fn() }));
vi.mock("../../src/domain/sharedRecordScopes", () => ({ downloadBlob: downloads.blob }));
vi.mock("../../src/api/researchThreads", () => ({ researchThreadsApi: api }));
const thread = (id: string): ResearchThreadDetail => ({
  thread_id: id,
  owner: "owner",
  title: id,
  created_at: "now",
  updated_at: "now",
  archived_at: null,
  originating_response_record_id: null,
  turns: [
    {
      turn_id: `${id}-1`,
      thread_id: id,
      ordinal: 1,
      user_question: `Question ${id}`,
      user_instructions: null,
      status: "completed",
      job_id: `job-${id}`,
      research_run_id: `job-${id}`,
      response_record_id: null,
      parent_turn_id: null,
      contextualized_query: null,
      context_selection: null,
      error: null,
      attempt: 1,
      created_at: "now",
      updated_at: "now",
    },
  ],
});
const summary = (id: string): ResearchThreadSummary => ({
  ...thread(id),
  turn_count: 1,
  first_question: `Question ${id}`,
  last_question: `Question ${id}`,
  last_status: "completed",
});
let client: QueryClient;
const mounted: ReturnType<typeof mount>[] = [];
beforeEach(() => {
  client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  useAuthStore().user = {
    id: 1,
    username: "owner",
    role: "researcher",
    capabilities: ["rag.run"],
    active: true,
    created_at: "now",
    updated_at: "now",
    login_count: 0,
  };
  useI18nStore().dictionary = {
    "research.threads_title": "Research threads",
    "research.thread_inspect_result": "Inspect this answer and its evidence",
    "research.thread_new": "New question",
    "research.thread_open_run": "Open answer",
    "ui.retry": "Retry",
    "research.thread_retry": "Retry turn",
    "research.threads_no_match": "No research threads match “{query}”.",
  };
  jobs.read.mockImplementation(async (path: string) => ({
    id: path.split("/").pop(),
    status: "completed",
    result: {
      answer: `Answer ${path}`,
      evidence: [{ evidence_id: "E0", full_citation: `Citation ${path}` }],
    },
  }));
  api.patch.mockResolvedValue(thread("a"));
  api.remove.mockResolvedValue(undefined);
  api.list.mockResolvedValue({ threads: [summary("a")] });
  api.get.mockImplementation(async (id: string) => thread(id));
});
afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount());
  client.clear();
  vi.useRealTimers();
  vi.restoreAllMocks();
});
function browser(id = "a", jobId = "job-a") {
  const wrapper = mount(ResearchThreadBrowser, {
    props: { threadId: id, jobId },
    global: {
      plugins: [[VueQueryPlugin, { queryClient: client }]],
      stubs: { UiDialog: { template: `<div role="dialog"><slot/><slot name="footer"/></div>` } },
    },
  });
  mounted.push(wrapper);
  return wrapper;
}
describe("Research thread shell", () => {
  it("keeps per-turn evidence inspection local and emits the exact source target", async () => {
    const detail = thread("a");
    detail.turns.push({ ...thread("b").turns[0], thread_id: "a", ordinal: 2 });
    api.get.mockResolvedValue(detail);
    jobs.read.mockImplementation(async (path: string) => ({
      id: path.split("/").pop(),
      status: "completed",
      result: {
        answer: "Supported [[E0]]",
        evidence: [0, 1].map((index) => ({
          evidence_id: `E${index}`,
          collection: "corpus",
          inline_citation: `Citation ${path} ${index}`,
          record: {
            record_id: `${path}-${index}`,
            text: `Exact passage ${path} ${index}`,
            speaker: "Author",
          },
        })),
      },
    }));
    const wrapper = browser();
    await flushPromises();
    const turns = wrapper.findAll("article.research-thread-turn");
    const articles = turns.length
      ? turns
      : wrapper
          .findAll("article[aria-labelledby]")
          .filter((item) => item.find(".thread-answer-text").exists());
    const first = articles[0],
      second = articles[1];
    const boundCitation = first.find(".thread-answer-citation");
    expect(boundCitation.exists()).toBe(true);
    await boundCitation.trigger("click");
    expect(first.find(".research-turn-inspector").exists()).toBe(true);
    expect(second.find(".research-turn-inspector").exists()).toBe(false);
    // No second full answer is mounted by evidence inspection.
    expect(first.findAll(".research-answer-prose")).toHaveLength(1);
    await first.findAll(".research-evidence-index button")[1].trigger("click");
    expect(first.find(".research-evidence-inspector").text()).toContain(
      "Exact passage /api/jobs/job-a 1",
    );
    await first.find(".research-evidence-links button").trigger("click");
    expect(wrapper.emitted("openRecord")?.[0]?.[0]).toMatchObject({
      collection: "corpus",
      record: { record_id: "/api/jobs/job-a-1" },
    });
    await second.find(".thread-answer-inspect-toggle").trigger("click");
    expect(first.find(".research-turn-inspector").exists()).toBe(false);
    expect(second.find(".research-turn-inspector").exists()).toBe(true);
    expect(second.find(".research-evidence-inspector").text()).toContain(
      "Exact passage /api/jobs/job-b 0",
    );
    expect(second.findAll(".research-answer-prose")).toHaveLength(1);
    expect(first.find(".research-answer-actions").exists()).toBe(false);
    await second.find(".research-turn-inspector-header button").trigger("click");
    expect(wrapper.findAll(".research-turn-inspector")).toHaveLength(0);
    expect(wrapper.emitted("selectEvidence")).toBeUndefined();
  });
  it("recovers a missing job through its exact turn result endpoint", async () => {
    jobs.read.mockImplementation(async (path: string) => {
      if (path.startsWith("/api/jobs/")) throw new ApiError("Unavailable", 404);
      return {
        id: "job-a",
        status: "completed",
        result: { answer: "Saved owned answer", evidence: [] },
      };
    });
    const wrapper = browser();
    await flushPromises();
    expect(jobs.read).toHaveBeenCalledWith("/api/research/threads/a/turns/a-1/result");
    expect(wrapper.text()).toContain("Saved owned answer");
  });
  it("does not attempt saved-answer recovery after access revocation", async () => {
    jobs.read.mockRejectedValue(new ApiError("Denied", 403));
    const wrapper = browser();
    await flushPromises();
    expect(jobs.read).toHaveBeenCalledOnce();
    expect(wrapper.find(".thread-answer-text").exists()).toBe(false);
  });

  it("offers in-place retry for failed/cancelled turns and blocks archived or active threads", async () => {
    const detail = thread("a");
    detail.turns[0].status = "failed";
    api.get.mockResolvedValue(detail);
    const wrapper = browser();
    await flushPromises();
    const retryButton = () =>
      wrapper.findAll("article button").find((item) => item.text() === "Retry turn")!;
    await retryButton().trigger("click");
    expect(wrapper.emitted("retryTurn")?.[0]).toEqual([detail.turns[0]]);
    await wrapper.setProps({ retryDisabled: true });
    expect(retryButton().attributes("disabled")).toBeDefined();
    await wrapper.setProps({ retryDisabled: false });
    detail.turns.push({ ...thread("b").turns[0], thread_id: "a", status: "running" });
    await client.invalidateQueries();
    await flushPromises();
    expect(retryButton().attributes("disabled")).toBeDefined();
    detail.turns.pop();
    detail.archived_at = "now";
    await client.invalidateQueries();
    await flushPromises();
    expect(retryButton().attributes("disabled")).toBeDefined();
  });
  it("refreshes after a retry outcome and hides retry after the turn becomes active", async () => {
    const detail = thread("a");
    detail.turns[0].status = "cancelled";
    api.get.mockResolvedValue(detail);
    const wrapper = browser();
    await flushPromises();
    expect(wrapper.text()).toContain("Retry turn");
    api.get.mockResolvedValue({
      ...detail,
      turns: [{ ...detail.turns[0], status: "running", attempt: 2 }],
    });
    api.get.mockClear();
    await wrapper.setProps({ refreshKey: 1 });
    await flushPromises();
    expect(api.get).toHaveBeenCalledOnce();
    expect(wrapper.text()).not.toContain("Retry turn");
  });
  it("keeps each inline answer and citation bound to its own turn", async () => {
    const detail = thread("a");
    detail.turns.push({ ...thread("b").turns[0], thread_id: "a", ordinal: 2 });
    api.get.mockResolvedValue(detail);
    const wrapper = browser();
    await flushPromises();
    const turns = wrapper.findAll("article[aria-labelledby]");
    expect(turns[0].text()).toContain("Answer /api/jobs/job-a");
    expect(turns[0].text()).toContain("Citation /api/jobs/job-a");
    expect(turns[0].text()).not.toContain("job-b");
    expect(turns[1].text()).toContain("Answer /api/jobs/job-b");
    expect(turns[1].text()).toContain("Citation /api/jobs/job-b");
  });
  it("opens only the cited turn's passage when two turns reuse the same evidence marker", async () => {
    const detail = thread("a");
    detail.turns.push({ ...thread("b").turns[0], thread_id: "a", ordinal: 2 });
    api.get.mockResolvedValue(detail);
    jobs.read.mockImplementation(async (path: string) => ({
      id: path.split("/").pop(),
      status: "completed",
      result: {
        answer: "Both turns cite [E1].",
        evidence: [
          {
            evidence_id: "E1",
            collection: "corpus",
            inline_citation: `Citation ${path}`,
            record: { record_id: `${path}-r`, text: `Passage ${path}` },
          },
        ],
      },
    }));
    const wrapper = browser();
    await flushPromises();
    const [first, second] = wrapper
      .findAll("article[aria-labelledby]")
      .filter((item) => item.find(".thread-answer-text").exists());
    await second.find(".thread-answer-citation").trigger("click");
    expect(first.find(".research-turn-inspector").exists()).toBe(false);
    const inspector = second.find(".research-evidence-inspector").text();
    expect(inspector).toContain("Passage /api/jobs/job-b");
    expect(inspector).not.toContain("job-a");
    expect(second.find(".research-evidence-provenance").exists()).toBe(true);
    await first.find(".thread-answer-citation").trigger("click");
    expect(second.find(".research-turn-inspector").exists()).toBe(false);
    expect(first.find(".research-evidence-inspector").text()).toContain("Passage /api/jobs/job-a");
    expect(first.find(".research-evidence-inspector").text()).not.toContain("job-b");
  });
  it("closes the inspector when a retry replaces the inspected attempt", async () => {
    const detail = thread("a");
    api.get.mockResolvedValue(detail);
    const wrapper = browser("a", "");
    await flushPromises();
    await wrapper.find(".thread-answer-inspect-toggle").trigger("click");
    expect(wrapper.find(".research-turn-inspector").exists()).toBe(true);
    api.get.mockResolvedValue({
      ...detail,
      turns: [{ ...detail.turns[0], attempt: 2, job_id: "job-a2", research_run_id: "job-a2" }],
    });
    await wrapper.setProps({ refreshKey: 1 });
    await flushPromises();
    expect(wrapper.find(".research-turn-inspector").exists()).toBe(false);
    expect(wrapper.text()).toContain("Answer /api/jobs/job-a2");
  });
  it("shows explicit empty states for a turn without evidence or claim provenance", async () => {
    jobs.read.mockResolvedValue({
      id: "job-a",
      status: "completed",
      result: { answer: "No supported answer.", evidence: [] },
    });
    useI18nStore().dictionary["research.no_evidence_text"] = "No evidence was retrieved.";
    useI18nStore().dictionary["ui.none"] = "None";
    const wrapper = browser("a", "");
    await flushPromises();
    await wrapper.find(".thread-answer-inspect-toggle").trigger("click");
    const inspector = wrapper.find(".research-turn-inspector");
    expect(inspector.text()).toContain("No evidence was retrieved.");
    expect(wrapper.find(".research-evidence-inspector").exists()).toBe(false);
    const sections = inspector.findAll(".research-turn-inspector-section");
    await sections[1].trigger("click");
    expect(sections[1].attributes("aria-pressed")).toBe("true");
    expect(inspector.find(".research-claim-review").exists()).toBe(false);
    expect(inspector.text()).toContain("None");
  });
  it("does not refetch immutable turn results when thread summaries change", async () => {
    const wrapper = browser();
    await flushPromises();
    expect(wrapper.text()).toContain("Answer /api/jobs/job-a");
    jobs.read.mockClear();
    await client.invalidateQueries({ queryKey: ["data", "research_threads"] });
    await flushPromises();
    expect(jobs.read).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Answer /api/jobs/job-a");
  });

  it("keeps long threads bounded until evidence inspection is opened", async () => {
    const detail = thread("a");
    detail.turns = Array.from({ length: 20 }, (_, index) => ({
      ...thread(String(index)).turns[0],
      turn_id: `a-${index + 1}`,
      thread_id: "a",
      ordinal: index + 1,
      user_question: `Question ${index + 1}`,
    }));
    api.get.mockResolvedValue(detail);
    jobs.read.mockImplementation(async (path: string) => ({
      id: path.split("/").pop(),
      status: "completed",
      result: {
        answer: `Answer ${path}`,
        evidence: Array.from({ length: 24 }, (_, index) => ({
          evidence_id: `E${index}`,
          inline_citation: `Citation ${index}`,
          record: { record_id: `${path}-${index}`, text: `Evidence ${index}` },
        })),
      },
    }));

    const wrapper = browser();
    await flushPromises();
    expect(jobs.read.mock.calls.length).toBeLessThan(20);
    expect(wrapper.findAll(".research-result-presentation")).toHaveLength(0);

    await client.invalidateQueries({ queryKey: ["data", "research_threads"] });
    await flushPromises();
    expect(jobs.read.mock.calls.length).toBeLessThan(20);

    // Explicitly opening a turn hydrates its immutable result without loading all history.
    await wrapper.setProps({ jobId: "job-0" });
    await flushPromises();
    expect(jobs.read).toHaveBeenCalledWith("/api/jobs/job-0");
    expect(wrapper.findAll(".research-turn-inspector")).toHaveLength(1);
  });

  it("clears a revoked inline answer while preserving its durable question", async () => {
    const wrapper = browser();
    await flushPromises();
    expect(wrapper.text()).toContain("Answer /api/jobs/job-a");
    jobs.read.mockRejectedValue(new ApiError("Unavailable", 404));
    await client.invalidateQueries();
    await flushPromises();
    expect(wrapper.text()).not.toContain("Answer /api/jobs/job-a");
    expect(wrapper.text()).toContain("Question a");
  });
  it("does not open a second draft stream for the live job already selected in Research", async () => {
    const handlers = new Map<string, EventHandler>();
    vi.spyOn(realtime, "subscribe").mockImplementation((topic, handler) => {
      handlers.set(topic, handler);
      return vi.fn();
    });
    const detail = thread("a");
    detail.turns[0].status = "running";
    api.get.mockResolvedValue(detail);
    browser("a", "job-a");
    await flushPromises();
    expect(handlers.has("job:job-a")).toBe(false);
  });

  it("binds previews to the active turn, clears on switches, and replaces with the completed answer", async () => {
    vi.useFakeTimers();
    const handlers = new Map<string, EventHandler>();
    const stop = vi.fn();
    vi.spyOn(realtime, "subscribe").mockImplementation((topic, handler) => {
      handlers.set(topic, handler);
      return stop;
    });
    const detail = thread("a");
    detail.turns.push({ ...thread("b").turns[0], thread_id: "a", ordinal: 2, status: "running" });
    api.get.mockResolvedValue(detail);
    const wrapper = browser();
    await flushPromises();
    const oldHandler = handlers.get("job:job-b")!;
    const event = {
      type: "llm.token",
      event_id: 1,
      resource_type: "job",
      resource_id: "job-b",
      revision: 1,
      timestamp: "now",
      payload: { generation: { seq: 1, delta: "Unverified preview", gap: false, final: false } },
    } as const;
    oldHandler(event);
    await vi.advanceTimersByTimeAsync(50);
    await flushPromises();
    expect(wrapper.findAll("article[aria-labelledby]")[0].text()).not.toContain(
      "Unverified preview",
    );
    expect(wrapper.findAll("article[aria-labelledby]")[1].text()).toContain("Unverified preview");
    expect(wrapper.findAll("article[aria-labelledby]")[1].text()).not.toContain("Citation");
    api.get.mockResolvedValue({
      ...detail,
      turns: detail.turns.map((turn) => ({ ...turn, status: "completed" })),
    });
    await client.invalidateQueries();
    await flushPromises();
    expect(stop).toHaveBeenCalled();
    expect(wrapper.text()).not.toContain("Unverified preview");
    expect(wrapper.findAll("article[aria-labelledby]")[1].text()).toContain(
      "Answer /api/jobs/job-b",
    );
    oldHandler(event);
    await flushPromises();
    expect(wrapper.text()).not.toContain("Unverified preview");
    api.get.mockResolvedValue(thread("c"));
    await wrapper.setProps({ threadId: "c" });
    await flushPromises();
    oldHandler(event);
    expect(wrapper.text()).not.toContain("Unverified preview");
    useAuthStore().user = null;
    await flushPromises();
    expect(wrapper.text()).not.toContain("Answer /api/jobs/job-c");
    vi.useRealTimers();
  });
  it("does not read answers for incomplete turns", async () => {
    const detail = thread("a");
    detail.turns[0].status = "running";
    api.get.mockResolvedValue(detail);
    jobs.read.mockClear();
    browser();
    await flushPromises();
    expect(jobs.read).not.toHaveBeenCalled();
  });
  it("opens the correct run without submitting historical answer content", async () => {
    const wrapper = browser();
    await flushPromises();
    await wrapper
      .findAll("article[aria-labelledby] button")
      .find((item) => item.text() === "Open answer")!
      .trigger("click");
    expect(wrapper.emitted("open")?.[0]).toEqual([thread("a").turns[0]]);
    expect(api.get).toHaveBeenCalledWith("a");
    expect(wrapper.find('[aria-current="true"]')).toBeTruthy();
  });
  it("clears old turns immediately on a thread switch and ignores late reads", async () => {
    const wrapper = browser();
    await flushPromises();
    let resolve!: (value: ResearchThreadDetail) => void;
    api.get.mockImplementation((id: string) =>
      id === "b"
        ? new Promise((yes) => {
            resolve = yes;
          })
        : Promise.resolve(thread(id)),
    );
    await wrapper.setProps({ threadId: "b" });
    expect(wrapper.text()).not.toContain("Question a");
    await wrapper.setProps({ threadId: "c" });
    await flushPromises();
    resolve(thread("b"));
    await flushPromises();
    expect(wrapper.text()).toContain("Question c");
    expect(wrapper.text()).not.toContain("Question b");
  });
  it("retains same-thread turns after transient failure, but clears them when access is revoked", async () => {
    const wrapper = browser();
    await flushPromises();
    api.get.mockRejectedValue(new Error("Temporary outage"));
    await client.invalidateQueries({ queryKey: ["data", "research_threads"] });
    await flushPromises();
    expect(wrapper.text()).toContain("Question a");
    expect(wrapper.text()).toContain("Temporary outage");
    api.get.mockRejectedValue(new ApiError("Access denied", 403));
    await wrapper.get('[role="alert"] button').trigger("click");
    await flushPromises();
    expect(wrapper.text()).not.toContain("Question a");
  });
  it("does not carry another account's cached thread across an identity change", async () => {
    const wrapper = browser();
    await flushPromises();
    useAuthStore().user = null;
    await flushPromises();
    expect(wrapper.text()).not.toContain("Question a");
  });
  it("orders turn controls and exposes unavailable runs and page boundaries", async () => {
    const detail = thread("a");
    detail.turns.push({
      ...detail.turns[0],
      turn_id: "a-2",
      ordinal: 2,
      user_question: "Second question",
      status: "failed",
      job_id: null,
      error: "Failed start",
    });
    const wrapper = mount(ResearchThreadNavigation, {
      props: {
        threads: Array.from({ length: 50 }, (_, index) => summary(String(index))),
        thread: detail,
        selectedThreadId: "a",
        offset: 0,
        hasMore: true,
      },
    });
    mounted.push(wrapper);
    expect(wrapper.findAll("article h3").map((heading) => heading.text())).toEqual([
      "Question a",
      "Second question",
    ]);
    expect(
      wrapper.findAll("article button").filter((item) => item.text() === "Open answer"),
    ).toHaveLength(1);
    expect(wrapper.get(".research-thread-pages button").attributes("disabled")).toBeDefined();
    await wrapper.findAll(".research-thread-pages button")[1].trigger("click");
    expect(wrapper.emitted("page")).toEqual([[50]]);
    // An exactly full last page does not offer an empty next page.
    await wrapper.setProps({ hasMore: false });
    expect(
      wrapper.findAll(".research-thread-pages button")[1].attributes("disabled"),
    ).toBeDefined();
    await wrapper.get(".research-thread-sidebar > button").trigger("click");
    expect(wrapper.emitted("new")).toHaveLength(1);
  });
  it("focuses the newly loaded thread heading only when focus is unclaimed", async () => {
    const wrapper = mount(ResearchThreadNavigation, {
      attachTo: document.body,
      props: {
        threads: [summary("a"), summary("b")],
        thread: thread("a"),
        selectedThreadId: "a",
        offset: 0,
      },
    });
    mounted.push(wrapper);
    // Back/Forward: focus is on the body, so the new thread's heading takes it.
    (document.activeElement as HTMLElement | null)?.blur();
    await wrapper.setProps({ thread: thread("b"), selectedThreadId: "b" });
    await flushPromises();
    expect(document.activeElement).toBe(wrapper.get(".research-thread-conversation h2").element);
    // Typing elsewhere is not interrupted by a late thread load.
    const outside = document.createElement("input");
    document.body.append(outside);
    outside.focus();
    await wrapper.setProps({ thread: thread("a"), selectedThreadId: "a" });
    await flushPromises();
    expect(document.activeElement).toBe(outside);
    outside.remove();
  });
  it("searches a thread's questions and loaded answers without fetching more", async () => {
    const detail = thread("a");
    detail.turns.push(
      { ...detail.turns[0], turn_id: "a-2", ordinal: 2, user_question: "On hospitality" },
      { ...detail.turns[0], turn_id: "a-3", ordinal: 3, user_question: "Third" },
    );
    const answerText = vi.fn((turn: { turn_id: string }) =>
      turn.turn_id === "a-1" ? "Hospitality is unconditional." : null,
    );
    const wrapper = mount(ResearchThreadNavigation, {
      props: { threads: [], thread: detail, selectedThreadId: "a", offset: 0, answerText },
    });
    mounted.push(wrapper);
    const visible = () =>
      wrapper
        .findAll(".research-thread-turns > li")
        .filter((item) => (item.element as HTMLElement).style.display !== "none")
        .map((item) => item.get("h3").text());
    await wrapper.get(".research-thread-turn-search input").setValue("HOSPITALITY");
    expect(visible()).toEqual(["Question a", "On hospitality"]);
    const status = wrapper.get(".research-thread-turn-search [role=status]").text();
    expect(status).toContain("2 of 3");
    expect(status).toContain("2 answers are not loaded");
    expect(api.get).not.toHaveBeenCalled();
    await wrapper.get(".research-thread-turn-search input").trigger("keydown", { key: "Escape" });
    expect(visible()).toHaveLength(3);
  });
  it("offers turn comparison only with two completed turns and resets on thread change", async () => {
    const detail = thread("a");
    const wrapper = mount(ResearchThreadNavigation, {
      props: { threads: [], thread: detail, selectedThreadId: "a", offset: 0 },
      slots: { compare: '<div class="compare-slot" />' },
    });
    mounted.push(wrapper);
    expect(wrapper.find(".research-thread-compare-toggle").exists()).toBe(false);
    const two = thread("a");
    two.turns.push({ ...two.turns[0], turn_id: "a-2", ordinal: 2 });
    await wrapper.setProps({ thread: two });
    await wrapper.get(".research-thread-compare-toggle").trigger("click");
    expect(wrapper.find(".compare-slot").exists()).toBe(true);
    await wrapper.setProps({ thread: thread("b"), selectedThreadId: "b" });
    expect(wrapper.find(".compare-slot").exists()).toBe(false);
  });
});

describe("Research thread management", () => {
  it("sends a sparse title patch, rejects blank titles, and keeps failures editable", async () => {
    const wrapper = browser();
    await flushPromises();
    await wrapper.findAll(".research-thread-management button")[0].trigger("click");
    await wrapper.get("#research-thread-title").setValue("   ");
    expect(wrapper.get("button.thread-title-save").attributes("disabled")).toBeDefined();
    await wrapper.get("form").trigger("submit");
    expect(api.patch).not.toHaveBeenCalled();
    await wrapper.get("#research-thread-title").setValue("  Updated inquiry  ");
    api.patch.mockRejectedValueOnce(new Error("Save failed"));
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(api.patch).toHaveBeenLastCalledWith("a", { title: "Updated inquiry" });
    expect(wrapper.get('[role="dialog"]').text()).toContain("Save failed");
    expect(wrapper.get("#research-thread-title").element).toHaveProperty(
      "value",
      "  Updated inquiry  ",
    );
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
  });
  it("exports the server-built thread as Markdown or JSON, even when archived", async () => {
    const wrapper = browser();
    await flushPromises();
    api.exportThread.mockResolvedValue({
      format: "derridai-research-thread-export-v1",
      thread: { thread_id: "a", title: "a", created_at: "", updated_at: "", archived_at: "now" },
      turns: [],
      works_cited: ["Derrida, Jacques. Margins."],
    });
    const buttons = () => wrapper.findAll(".research-thread-export-actions button");
    await buttons()[0].trigger("click");
    await flushPromises();
    expect(api.exportThread).toHaveBeenLastCalledWith("a");
    const [markdown, name] = downloads.blob.mock.calls.at(-1)!;
    expect(name).toBe("research-thread-a.md");
    expect(await (markdown as Blob).text()).toContain("1. Derrida, Jacques. Margins.");
    await buttons()[1].trigger("click");
    await flushPromises();
    const [json, jsonName] = downloads.blob.mock.calls.at(-1)!;
    expect(jsonName).toBe("research-thread-a.json");
    expect(JSON.parse(await (json as Blob).text()).thread.thread_id).toBe("a");
    expect(api.patch).not.toHaveBeenCalled();
  });
  it("archives and unarchives without sending question or answer bodies", async () => {
    const wrapper = browser();
    await flushPromises();
    api.get.mockResolvedValue({ ...thread("a"), archived_at: "now" });
    await wrapper.findAll(".research-thread-management button")[1].trigger("click");
    await flushPromises();
    expect(api.patch).toHaveBeenLastCalledWith("a", { archived: true });
    api.get.mockResolvedValue(thread("a"));
    await wrapper.findAll(".research-thread-management button")[1].trigger("click");
    await flushPromises();
    expect(api.patch).toHaveBeenLastCalledWith("a", { archived: false });
    await wrapper.get(".research-thread-archive-filter input").setValue(true);
    await flushPromises();
    expect(api.list).toHaveBeenLastCalledWith({ offset: 0, includeArchived: true });
  });
  it("only deletes after confirmation and clears selected turns when complete", async () => {
    const wrapper = browser();
    await flushPromises();
    await wrapper.findAll(".research-thread-management button")[2].trigger("click");
    expect(api.remove).not.toHaveBeenCalled();
    await wrapper.get('[role="dialog"] button').trigger("click");
    expect(api.remove).not.toHaveBeenCalled();
    await wrapper.findAll(".research-thread-management button")[2].trigger("click");
    await wrapper.findAll('[role="dialog"] button')[1].trigger("click");
    await flushPromises();
    expect(api.remove).toHaveBeenCalledWith("a");
    expect(wrapper.emitted("removed")).toHaveLength(1);
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
  });
  it("blocks duplicate saves and ignores completion after switching threads", async () => {
    const wrapper = browser();
    await flushPromises();
    let resolve!: (value: ReturnType<typeof thread>) => void;
    api.patch.mockReturnValueOnce(
      new Promise((yes) => {
        resolve = yes;
      }),
    );
    await wrapper.findAll(".research-thread-management button")[0].trigger("click");
    await wrapper.get("form").trigger("submit");
    await wrapper.get("form").trigger("submit");
    expect(api.patch).toHaveBeenCalledTimes(1);
    await wrapper.setProps({ threadId: "b" });
    await flushPromises();
    resolve(thread("a"));
    await flushPromises();
    expect(wrapper.text()).toContain("Question b");
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.emitted("removed")).toBeUndefined();
  });
  it("clears stale thread content when a mutation reports revoked access", async () => {
    const wrapper = browser();
    await flushPromises();
    api.patch.mockRejectedValue(new ApiError("Denied", 403));
    api.get.mockRejectedValue(new ApiError("Denied", 403));
    await wrapper.findAll(".research-thread-management button")[1].trigger("click");
    await flushPromises();
    expect(wrapper.text()).not.toContain("Question a");
  });
});

it("does not apply a pending deletion to a replacement account's workspace", async () => {
  const wrapper = browser();
  await flushPromises();
  let resolve!: () => void;
  api.remove.mockReturnValueOnce(
    new Promise<void>((yes) => {
      resolve = yes;
    }),
  );
  await wrapper.findAll(".research-thread-management button")[2].trigger("click");
  await wrapper.findAll('[role="dialog"] button')[1].trigger("click");
  useAuthStore().user = null;
  await flushPromises();
  resolve();
  await flushPromises();
  expect(wrapper.emitted("removed")).toBeUndefined();
  expect(wrapper.text()).not.toContain("Question a");
});

it("refreshes authoritative state after archive failure without resending a potentially completed mutation", async () => {
  const wrapper = browser();
  await flushPromises();
  api.patch.mockRejectedValueOnce(new Error("Connection interrupted"));
  await wrapper.findAll(".research-thread-management button")[1].trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("Connection interrupted");
  await wrapper.get('[role="alert"] button').trigger("click");
  await flushPromises();
  expect(api.patch).toHaveBeenCalledTimes(1);
  expect(wrapper.text()).not.toContain("Connection interrupted");
});

it("allows follow-ups only for a loaded unarchived thread with no active turn", async () => {
  const wrapper = browser();
  await flushPromises();
  expect(wrapper.emitted("continuable")?.at(-1)).toEqual([true]);
  api.get.mockResolvedValue({ ...thread("a"), archived_at: "2026-10-05" });
  await wrapper.setProps({ refreshKey: 1 });
  await flushPromises();
  expect(wrapper.emitted("continuable")?.at(-1)).toEqual([false]);
  api.get.mockResolvedValue({
    ...thread("a"),
    turns: [{ ...thread("a").turns[0], status: "running" }],
  });
  await wrapper.setProps({ refreshKey: 2 });
  await flushPromises();
  expect(wrapper.emitted("continuable")?.at(-1)).toEqual([false]);
});

describe("Responsive research navigation", () => {
  it("allows opening the thread index and collapses it after selection", async () => {
    const wrapper = mount(ResearchThreadNavigation, {
      props: {
        threads: [summary("a"), summary("b")],
        thread: thread("a"),
        selectedThreadId: "a",
        offset: 0,
      },
    });
    mounted.push(wrapper);
    const toggle = wrapper.get(".research-thread-list-toggle");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    await toggle.trigger("click");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(".research-thread-sidebar").classes()).toContain("is-expanded");
    await wrapper.findAll(".research-thread-index button")[1].trigger("click");
    expect(wrapper.emitted("select")?.[0]).toEqual(["b"]);
    expect(toggle.attributes("aria-expanded")).toBe("false");
  });

  it("keeps destructive actions inside the explicit management disclosure", async () => {
    const wrapper = mount(ResearchThreadNavigation, {
      props: { threads: [], thread: thread("a"), selectedThreadId: "a", offset: 0 },
    });
    mounted.push(wrapper);
    expect(wrapper.get(".research-thread-management").element.tagName).toBe("DETAILS");
    expect(wrapper.find(".research-thread-management summary").exists()).toBe(true);
    expect(wrapper.get(".research-thread-management button").text()).not.toBe("");
  });
});

describe("Research thread list search", () => {
  it("debounces typed search, resets paging, and clears on Escape", async () => {
    vi.useFakeTimers();
    const wrapper = browser("", "");
    await flushPromises();
    api.list.mockClear();
    const input = wrapper.get("input[type='search']");
    for (const value of ["G", "Gl", "Glas"]) await input.setValue(value);
    expect(api.list).not.toHaveBeenCalled();
    api.list.mockResolvedValue({ threads: [] });
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    expect(api.list).toHaveBeenCalledTimes(1);
    expect(api.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Glas", offset: 0 }),
    );
    expect(wrapper.text()).toContain("No research threads match “Glas”.");
    api.list.mockResolvedValue({ threads: [summary("a")] });
    await input.trigger("keydown", { key: "Escape" });
    await flushPromises();
    expect((input.element as HTMLInputElement).value).toBe("");
    expect(api.list).toHaveBeenLastCalledWith(
      expect.not.objectContaining({ search: expect.anything() }),
    );
    expect(wrapper.text()).toContain("a");
  });

  it("restores page offsets when Back/Forward changes search and archive filters", async () => {
    const wrapper = browser("", "");
    await flushPromises();

    await wrapper.setProps({ initialSearch: "Glas", initialOffset: 50, initialArchived: true });
    await flushPromises();
    const navigation = wrapper.getComponent(ResearchThreadNavigation);
    expect(navigation.props("search")).toBe("Glas");
    expect(navigation.props("offset")).toBe(50);
    expect(navigation.props("includeArchived")).toBe(true);
    expect(api.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Glas", offset: 50, includeArchived: true }),
    );

    // This simulates a history restoration, not a new filter selection.
    await wrapper.setProps({ initialSearch: "Trace", initialOffset: 25, initialArchived: false });
    await flushPromises();
    expect(navigation.props("search")).toBe("Trace");
    expect(navigation.props("offset")).toBe(25);
    expect(navigation.props("includeArchived")).toBe(false);
    expect(api.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Trace", offset: 25, includeArchived: false }),
    );

    // A local filter edit, unlike history restoration, resets the page.
    navigation.vm.$emit("includeArchived", true);
    await flushPromises();
    expect(navigation.props("offset")).toBe(0);
  });

  it("discards a pending debounced search when the URL restores another query", async () => {
    vi.useFakeTimers();
    const wrapper = browser("", "");
    await flushPromises();
    await wrapper.get("input[type='search']").setValue("Pending query");
    await wrapper.setProps({ initialSearch: "Restored query", initialOffset: 25 });
    await flushPromises();
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    const navigation = wrapper.getComponent(ResearchThreadNavigation);
    expect(navigation.props("search")).toBe("Restored query");
    expect(navigation.props("offset")).toBe(25);
    expect(api.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Restored query", offset: 25 }),
    );
  });
});
