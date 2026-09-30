/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchAnswerWorkspace from "../../src/components/research/ResearchAnswerWorkspace.vue";

describe("ResearchAnswerWorkspace draft pane", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("shows the streamed draft, labelled as unverified, while the job is still running", () => {
    const wrapper = mount(ResearchAnswerWorkspace, {
      props: {
        job: { id: "run-1", status: "running", prompt: "A question" } as never,
        draft: { jobId: "run-1", text: "Partial answer so far.", gap: false, final: false },
      },
    });
    expect(wrapper.find(".research-draft-pane").exists()).toBe(true);
    expect(wrapper.get(".research-draft-text").text()).toBe("Partial answer so far.");
    expect(wrapper.text()).toContain("Drafting the answer");
  });

  it("does not render a draft belonging to a different job", () => {
    const wrapper = mount(ResearchAnswerWorkspace, {
      props: {
        job: { id: "run-2", status: "running", prompt: "A question" } as never,
        draft: {
          jobId: "run-1",
          text: "Stale draft from a previous run.",
          gap: false,
          final: false,
        },
      },
    });
    expect(wrapper.find(".research-draft-pane").exists()).toBe(false);
  });

  it("prefers the failure message over a stale draft", () => {
    const wrapper = mount(ResearchAnswerWorkspace, {
      props: {
        job: { id: "run-1", status: "failed", prompt: "A question", fatal_error: "Boom" } as never,
        draft: { jobId: "run-1", text: "Partial answer.", gap: false, final: false },
      },
    });
    expect(wrapper.find(".research-draft-pane").exists()).toBe(false);
    expect(wrapper.get('[role="alert"]').text()).toContain("Boom");
  });

  it("shows the completed answer instead of the draft once the authoritative result arrives", () => {
    const wrapper = mount(ResearchAnswerWorkspace, {
      props: {
        job: { id: "run-1", status: "completed", prompt: "A question" } as never,
        result: { prompt: "A question", answer: "The verified answer." } as never,
        draft: { jobId: "run-1", text: "Partial answer.", gap: false, final: true },
      },
    });
    expect(wrapper.find(".research-draft-pane").exists()).toBe(false);
    expect(wrapper.text()).toContain("The verified answer.");
  });
});
