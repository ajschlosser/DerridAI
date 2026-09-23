import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusSourceIngest from "../../src/components/CorpusSourceIngest.vue";

describe("Corpus source ingest", () => {
  it("places the illegibility slider before choose source PDF and keeps both keyboard-labeled", () => {
    const wrapper = mount(CorpusSourceIngest, { props: { assets: [], hits: [] } });
    const slider = wrapper.get("#source-illegibility");
    const choose = wrapper.get("button.source-choose");
    expect(slider.attributes("aria-valuetext")).toContain("0");
    expect(slider.attributes("aria-describedby")).toBe("source-illegibility-help");
    expect(choose.text()).toContain("Choose source");
    expect(wrapper.text()).toContain("Leave this at 0");
    const following = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(slider.element.compareDocumentPosition(choose.element) & following).toBe(following);
    expect(wrapper.get('input[type="file"]').attributes("tabindex")).toBe("-1");
  });

  it("emits a URL load and a Gutenberg selection without leaving the slider behind the file control", async () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: {
        sourceUrl: "",
        gutenbergQuery: "austen",
        hits: [{ etext_id: 1342, title: "Pride and Prejudice", author: "Jane Austen", language: "en" }],
      },
    });
    await wrapper.get("#pdf-corpus-source-url").setValue("https://example.edu/hospitality.txt");
    expect(wrapper.emitted("update:sourceUrl")?.[0]).toEqual(["https://example.edu/hospitality.txt"]);
    await wrapper.setProps({ sourceUrl: "https://example.edu/hospitality.txt" });
    await wrapper.get("form.url-source").trigger("submit");
    expect(wrapper.emitted("loadUrl")).toHaveLength(1);
    await wrapper.get(".gutenberg-hits button").trigger("click");
    await wrapper.setProps({ busy: "gutenberg" });
    expect(wrapper.get(".ingest-status").text()).toContain("Searching Project Gutenberg");
    expect(wrapper.emitted("importGutenberg")?.[0]).toEqual([1342]);
    expect(wrapper.get(".gutenberg-hits button").attributes("aria-label")).toContain("Pride and Prejudice");
  });
});
