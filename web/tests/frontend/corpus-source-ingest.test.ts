import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusSourceIngest from "../../src/components/CorpusSourceIngest.vue";

describe("Corpus source ingest", () => {
  it("places the OCR strategy radios before choose source PDF", () => {
    const wrapper = mount(CorpusSourceIngest, { props: { assets: [], hits: [] } });
    const radios = wrapper.findAll('input[name="source-ocr-strategy"]');
    const choose = wrapper.get("button.source-choose");
    expect(radios).toHaveLength(3);
    expect((radios[0].element as HTMLInputElement).checked).toBe(true);
    expect(wrapper.text()).toContain("Use embedded text when available");
    expect(choose.text()).toContain("Choose source file");
    const following = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(radios[0].element.compareDocumentPosition(choose.element) & following).toBe(following);
    expect(wrapper.get('input[type="file"]').attributes("tabindex")).toBe("-1");
  });

  it("emits the selected OCR strategy as a numeric compatibility value", async () => {
    const wrapper = mount(CorpusSourceIngest);
    await wrapper.find('input[value="difficult"]').setValue(true);
    expect(wrapper.emitted("update:illegibility")?.at(-1)).toEqual([50]);
    await wrapper.find('input[value="always"]').setValue(true);
    expect(wrapper.emitted("update:illegibility")?.at(-1)).toEqual([100]);
  });

  it("emits a URL load and a Gutenberg selection", async () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: {
        sourceUrl: "",
        gutenbergQuery: "austen",
        hits: [
          { etext_id: 1342, title: "Pride and Prejudice", author: "Jane Austen", language: "en" },
        ],
      },
    });
    await wrapper.get("#pdf-corpus-source-url").setValue("https://example.edu/hospitality.txt");
    expect(wrapper.emitted("update:sourceUrl")?.[0]).toEqual([
      "https://example.edu/hospitality.txt",
    ]);
    await wrapper.setProps({ sourceUrl: "https://example.edu/hospitality.txt" });
    await wrapper.get("form.url-source").trigger("submit");
    expect(wrapper.emitted("loadUrl")).toHaveLength(1);
    await wrapper.get(".gutenberg-hits button").trigger("click");
    expect(wrapper.emitted("importGutenberg")?.[0]).toEqual([1342]);
    expect(wrapper.get(".gutenberg-hits button").attributes("aria-label")).toContain(
      "Pride and Prejudice",
    );
  });
});

it("offers audio controls without OCR or Explorer actions", async () => {
  const wrapper = mount(CorpusSourceIngest);
  await wrapper.get("#source-format").setValue("audio");
  expect(wrapper.find('input[name="source-ocr-strategy"]').exists()).toBe(false);
  expect(wrapper.text()).not.toContain("Use current Explorer PDF");
  expect(wrapper.get('input[type="file"]').attributes("accept")).toContain(".wav");
  expect(wrapper.text()).toContain("timed speaker spans");
  await wrapper.get("#source-format").setValue("image");
  expect(wrapper.find('input[name="source-ocr-strategy"]').exists()).toBe(true);
});

it("distinguishes Gutenberg editions in selection controls", () => {
  const wrapper = mount(CorpusSourceIngest, {
    props: {
      hits: [
        { etext_id: 12, title: "Book", author: "Author", language: "en" },
        { etext_id: 13, title: "Book", author: "Author", language: "fr" },
      ],
    },
  });
  const choices = wrapper.findAll(".gutenberg-hits button");
  expect(choices[0].text()).toContain("#12");
  expect(choices[1].text()).toContain("#13");
});
