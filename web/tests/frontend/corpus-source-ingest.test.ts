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
        gutenbergStatus: {
          ready: true,
          search_ready: true,
          catalogue: { status: "ready", item_count: 1 },
          archive: { status: "ready", bytes_done: 1, total_bytes: 1 },
        },
        hits: [
          { etext_id: 1342, title: "Pride and Prejudice", author: "Jane Austen", language: "en" },
        ],
      },
    });
    await wrapper.get("button.btn-secondary").trigger("click");
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

it("shows catalogue results before the collection is ready but keeps imports disabled", async () => {
  const wrapper = mount(CorpusSourceIngest, {
    props: {
      gutenbergQuery: "austen",
      gutenbergStatus: {
        ready: false,
        search_ready: true,
        catalogue: { status: "ready", item_count: 1 },
        archive: { status: "downloading", bytes_done: 4, total_bytes: 10 },
      },
      hits: [
        { etext_id: 1342, title: "Pride and Prejudice", author: "Jane Austen", language: "en" },
      ],
    },
  });
  await wrapper.get("button.btn-secondary").trigger("click");
  const result = wrapper.get(".gutenberg-hits button");
  expect(result.text()).toContain("Pride and Prejudice");
  expect(result.attributes("disabled")).toBeDefined();

  await wrapper.get(".library-tab:nth-child(2)").trigger("click");
  const search = wrapper.get('button[type="submit"]');
  expect(search.attributes("disabled")).toBeUndefined();
});

it("keeps digital-library acquisition available while an existing build locks source selection", async () => {
  const wrapper = mount(CorpusSourceIngest, {
    props: { assets: [], hits: [], sourceSelectionDisabled: true },
  });
  expect(wrapper.get("button.source-choose").attributes("disabled")).toBeDefined();
  expect(wrapper.get("button.btn-secondary").attributes("disabled")).toBeUndefined();
  await wrapper.get("button.btn-secondary").trigger("click");
  expect(wrapper.find("dialog.source-search-dialog").exists()).toBe(true);
});

it("uses automatic media detection instead of asking users for a source type", async () => {
  const wrapper = mount(CorpusSourceIngest);
  expect(wrapper.text()).toContain("Format is detected automatically from the file.");
  expect(wrapper.find("#source-format").exists()).toBe(false);
  expect(wrapper.get('input[type="file"]').attributes("accept")).toContain(".wav");
});

it("distinguishes Gutenberg editions in selection controls", async () => {
  const wrapper = mount(CorpusSourceIngest, {
    props: {
      hits: [
        { etext_id: 12, title: "Book", author: "Author", language: "en" },
        { etext_id: 13, title: "Book", author: "Author", language: "fr" },
      ],
    },
  });
  await wrapper.get("button.btn-secondary").trigger("click");
  const choices = wrapper.findAll(".gutenberg-hits button");
  expect(choices[0].text()).toContain("#12");
  expect(choices[1].text()).toContain("#13");
});
