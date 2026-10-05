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
const api = vi.hoisted(() => ({ list: vi.fn(), get: vi.fn(), patch: vi.fn(), remove: vi.fn() }));
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
  vi.restoreAllMocks();
});
function browser(id = "a") {
  const wrapper = mount(ResearchThreadBrowser, {
    props: { threadId: id, jobId: "job-a" },
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
    await first.findAll(".research-evidence-index button")[1].trigger("click");
    expect(first.find(".research-evidence-inspector").text()).toContain(
      "Exact passage /api/jobs/job-a 1",
    );
    expect(second.find(".research-evidence-inspector").text()).toContain(
      "Exact passage /api/jobs/job-b 0",
    );
    expect(first.find(".research-answer-actions").exists()).toBe(false);
    expect(first.find("h5").exists()).toBe(true);
    expect(first.find("aside").attributes("id")).not.toBe(second.find("aside").attributes("id"));
    expect(first.find("aside").attributes("aria-label")).not.toBe(
      second.find("aside").attributes("aria-label"),
    );
    await first.find(".research-evidence-links button").trigger("click");
    expect(wrapper.emitted("openRecord")?.[0]?.[0]).toMatchObject({
      collection: "corpus",
      record: { record_id: "/api/jobs/job-a-1" },
    });
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
  it("binds previews to the active turn, clears on switches, and replaces with the completed answer", async () => {
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
      },
    });
    mounted.push(wrapper);
    expect(wrapper.findAll("article h4").map((heading) => heading.text())).toEqual([
      "Question a",
      "Second question",
    ]);
    expect(
      wrapper.findAll("article button").filter((item) => item.text() === "Open answer"),
    ).toHaveLength(1);
    expect(wrapper.get(".research-thread-pages button").attributes("disabled")).toBeDefined();
    await wrapper.findAll(".research-thread-pages button")[1].trigger("click");
    expect(wrapper.emitted("page")).toEqual([[50]]);
    await wrapper.get("section > button").trigger("click");
    expect(wrapper.emitted("new")).toHaveLength(1);
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
