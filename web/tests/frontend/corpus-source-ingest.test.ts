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
    await wrapper.get("button.path-web").trigger("click");
    await wrapper.get("#pdf-corpus-source-url").setValue("https://example.edu/hospitality.txt");
    expect(wrapper.emitted("update:sourceUrl")?.[0]).toEqual([
      "https://example.edu/hospitality.txt",
    ]);
    await wrapper.setProps({ sourceUrl: "https://example.edu/hospitality.txt" });
    await wrapper.get("form.url-source").trigger("submit");
    expect(wrapper.emitted("loadUrl")).toHaveLength(1);
    await wrapper.get("button.path-libraries").trigger("click");
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
  await wrapper.get("button.path-libraries").trigger("click");
  const result = wrapper.get(".gutenberg-hits button");
  expect(result.text()).toContain("Pride and Prejudice");
  expect(result.attributes("disabled")).toBeDefined();

  await wrapper.get(".library-tab:nth-child(2)").trigger("click");
  const search = wrapper.get('.gutenberg-source button[type="submit"]');
  expect(search.attributes("disabled")).toBeUndefined();
});

it("keeps digital-library acquisition available while an existing build locks source selection", async () => {
  const wrapper = mount(CorpusSourceIngest, {
    props: { assets: [], hits: [], sourceSelectionDisabled: true },
  });
  expect(wrapper.get("button.source-choose").attributes("disabled")).toBeDefined();
  expect(wrapper.get("button.path-libraries").attributes("disabled")).toBeUndefined();
  await wrapper.get("button.path-libraries").trigger("click");
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
  await wrapper.get("button.path-libraries").trigger("click");
  const choices = wrapper.findAll(".gutenberg-hits button");
  expect(choices[0].text()).toContain("#12");
  expect(choices[1].text()).toContain("#13");
});

describe("Corpus source ingest experience", () => {
  const asset = (n: number, name = `source-${n}.pdf`) => ({
    asset_id: `a${n}`,
    sha256: "abcdef0123456789abcdef",
    filename: name,
    created_at: "2026-09-23T08:00:00Z",
    page_count: 4,
    block_count: 20 + n,
    ocr_pages: 1,
    warnings: [],
    metadata: {},
    media_kind: "pdf",
  });

  it("loads a dropped file and highlights the zone while dragging", async () => {
    const wrapper = mount(CorpusSourceIngest);
    const zone = wrapper.get(".dropzone");
    await zone.trigger("dragenter");
    expect(zone.classes()).toContain("is-over");
    const file = new File(["x"], "essay.txt", { type: "text/plain" });
    await zone.trigger("drop", { dataTransfer: { files: [file], getData: () => "" } });
    expect(zone.classes()).not.toContain("is-over");
    expect(wrapper.emitted("file")?.[0]).toEqual([file]);
  });

  it("turns a dropped link into a URL import", async () => {
    const wrapper = mount(CorpusSourceIngest);
    await wrapper.get(".dropzone").trigger("drop", {
      dataTransfer: { files: [], getData: () => "https://en.wikisource.org/wiki/Balzac/Preface" },
    });
    expect(wrapper.emitted("update:sourceUrl")?.[0]).toEqual([
      "https://en.wikisource.org/wiki/Balzac/Preface",
    ]);
    await Promise.resolve();
    expect(wrapper.emitted("loadUrl")).toHaveLength(1);
  });

  it("ignores drops while source selection is locked", async () => {
    const wrapper = mount(CorpusSourceIngest, { props: { sourceSelectionDisabled: true } });
    await wrapper.get(".dropzone").trigger("drop", {
      dataTransfer: { files: [new File(["x"], "a.txt")], getData: () => "" },
    });
    expect(wrapper.emitted("file")).toBeUndefined();
  });

  it("recognises Wikisource addresses and says they use the official API", async () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: { sourceUrl: "https://en.wikisource.org/wiki/Balzac/Preface" },
    });
    await wrapper.get("button.path-web").trigger("click");
    expect(wrapper.get(".url-detect").attributes("data-kind")).toBe("wikisource");
    expect(wrapper.get(".url-detect").text()).toContain("official API");
    await wrapper.setProps({ sourceUrl: "not a url" });
    expect(wrapper.find(".url-detect").exists()).toBe(false);
  });

  it("shows saved sources as selectable cards and reports the selection", async () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: { assets: [asset(1), asset(2)], assetId: "a1" },
    });
    const cards = wrapper.findAll(".saved-card");
    expect(cards).toHaveLength(2);
    expect(cards[0].attributes("aria-pressed")).toBe("true");
    await cards[1].trigger("click");
    expect(wrapper.emitted("update:assetId")?.at(-1)).toEqual(["a2"]);
    await cards[0].trigger("click");
    expect(wrapper.emitted("update:assetId")?.at(-1)).toEqual([""]);
  });

  it("locks saved sources while a build is running but still explains why", () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: { assets: [asset(1)], sourceSelectionDisabled: true },
    });
    expect(wrapper.get(".saved-card").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".saved-locked").text()).toContain("can’t be switched");
  });

  it("offers a filter only once the library is large", async () => {
    const few = mount(CorpusSourceIngest, { props: { assets: [asset(1), asset(2)] } });
    expect(few.find(".saved-filter").exists()).toBe(false);
    const many = mount(CorpusSourceIngest, {
      props: {
        assets: [1, 2, 3, 4, 5, 6].map((n) => asset(n, n === 3 ? "Hospitality.pdf" : `x${n}.pdf`)),
      },
    });
    await many.get(".saved-filter input").setValue("hosp");
    expect(many.findAll(".saved-card")).toHaveLength(1);
    await many.get(".saved-filter input").setValue("zzz");
    expect(many.get(".saved-none").text()).toContain("No sources match");
  });

  it("presents the current source with its facts and a way forward", async () => {
    const selected = {
      ...asset(1, "Of Hospitality.pdf"),
      deterministic_checked_at: "2026-09-23T08:00:01Z",
    };
    const wrapper = mount(CorpusSourceIngest, {
      props: { selectedAsset: selected, assetId: "a1" },
    });
    expect(wrapper.get(".source-card h5").text()).toBe("Of Hospitality.pdf");
    expect(wrapper.get(".stat-tiles").text()).toContain("21");
    await wrapper.get("button.continue").trigger("click");
    expect(wrapper.emitted("continue")).toHaveLength(1);
    expect(wrapper.find(".source-empty").exists()).toBe(false);
  });

  it("invites the first source when nothing is selected", () => {
    const wrapper = mount(CorpusSourceIngest);
    expect(wrapper.get(".source-empty").text()).toContain("No source yet");
    expect(wrapper.find("button.continue").exists()).toBe(false);
  });
});

describe("page-number detection controls", () => {
  it("is on by default and reports the choice", async () => {
    const wrapper = mount(CorpusSourceIngest);
    const box = wrapper.get('.page-detect input[type="checkbox"]');
    expect((box.element as HTMLInputElement).checked).toBe(true);
    await box.setValue(false);
    expect(wrapper.emitted("update:detectPageNumbers")?.at(-1)).toEqual([false]);
  });

  it("shows what was detected on the current source", () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: {
        selectedAsset: {
          asset_id: "a",
          sha256: "abcdef0123456789abcdef",
          filename: "essay.txt",
          created_at: "2026-09-23T08:00:00Z",
          page_count: 4,
          block_count: 9,
          ocr_pages: 0,
          warnings: [],
          metadata: {},
          media_kind: "text",
          page_number_detection: {
            status: "detected",
            pattern: "bracket",
            marker_count: 4,
            first: 31,
            last: 34,
            confidence: 0.93,
          },
        } as never,
      },
    });
    expect(wrapper.get(".page-detect-result").text()).toContain("4 markers, 31–34");
    expect(wrapper.get(".page-detect-result").attributes("data-status")).toBe("detected");
  });

  it("says when nothing was found", () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: {
        selectedAsset: {
          asset_id: "a",
          sha256: "abcdef0123456789abcdef",
          filename: "essay.txt",
          created_at: "2026-09-23T08:00:00Z",
          page_count: 1,
          block_count: 2,
          ocr_pages: 0,
          warnings: [],
          metadata: {},
          media_kind: "text",
          page_number_detection: { status: "not_found" },
        } as never,
      },
    });
    expect(wrapper.get(".page-detect-result").text()).toContain("No page numbers found");
  });
});

describe("model-assisted page detection control", () => {
  it("is offered under detection, on by default, and can be turned off", async () => {
    const wrapper = mount(CorpusSourceIngest);
    const box = wrapper.get('.page-detect-llm input[type="checkbox"]');
    expect((box.element as HTMLInputElement).checked).toBe(true);
    await box.setValue(false);
    expect(wrapper.emitted("update:llmPageDetection")?.at(-1)).toEqual([false]);
  });

  it("is hidden when page-number detection is off altogether", () => {
    const wrapper = mount(CorpusSourceIngest, { props: { detectPageNumbers: false } });
    expect(wrapper.find(".page-detect-llm").exists()).toBe(false);
  });
});
