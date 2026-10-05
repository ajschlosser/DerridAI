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
import { ApiError } from "../../src/api/http";
import ResearchThreadBrowser from "../../src/components/research/ResearchThreadBrowser.vue";
import ResearchThreadNavigation from "../../src/components/research/ResearchThreadNavigation.vue";
import type { ResearchThreadDetail, ResearchThreadSummary } from "../../src/types/researchThreads";

const api = vi.hoisted(() => ({ list: vi.fn(), get: vi.fn() }));
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
    "research.thread_new": "New question",
    "research.thread_open_run": "Open answer",
    "ui.retry": "Retry",
  };
  api.list.mockResolvedValue({ threads: [summary("a")] });
  api.get.mockImplementation(async (id: string) => thread(id));
});
afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount());
  client.clear();
});
function browser(id = "a") {
  const wrapper = mount(ResearchThreadBrowser, {
    props: { threadId: id, jobId: "job-a" },
    global: { plugins: [[VueQueryPlugin, { queryClient: client }]] },
  });
  mounted.push(wrapper);
  return wrapper;
}
describe("Research thread shell", () => {
  it("opens the correct run without submitting historical answer content", async () => {
    const wrapper = browser();
    await flushPromises();
    await wrapper.get("article button").trigger("click");
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
    expect(wrapper.findAll("article button")).toHaveLength(1);
    expect(wrapper.get(".research-thread-pages button").attributes("disabled")).toBeDefined();
    await wrapper.findAll(".research-thread-pages button")[1].trigger("click");
    expect(wrapper.emitted("page")).toEqual([[50]]);
    await wrapper.get("section > button").trigger("click");
    expect(wrapper.emitted("new")).toHaveLength(1);
  });
});
