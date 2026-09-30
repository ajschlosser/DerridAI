import { DOMWrapper, mount, shallowMount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import CorpusSourceIngest from "../../src/components/CorpusSourceIngest.vue";
import SourceTable from "../../src/components/sources/SourceTable.vue";

const body = () => new DOMWrapper(document.body);

describe("Corpus source ingest", () => {
  it("places the OCR strategy radios before choose source PDF", () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: {
        assets: [],
        hits: [],
        selectedAsset: { media_kind: "pdf", filename: "source.pdf" } as never,
      },
    });
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
    const wrapper = mount(CorpusSourceIngest, {
      props: { selectedAsset: { media_kind: "image", filename: "source.png" } as never },
    });
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
    await body().get('[data-action="open-library"]').trigger("click");
    await nextTick();
    await nextTick();
    const importButton = wrapper.get(".ls-results [data-result-primary]");
    expect(importButton.attributes("aria-label")).toContain("Pride and Prejudice");
    await importButton.trigger("click");
    expect(wrapper.emitted("importGutenberg")?.[0]).toEqual([1342]);
  });
});

it("keeps Gutenberg imports available before the local collection is ready", async () => {
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
  await body().get('[data-action="open-library"]').trigger("click");
  await nextTick();
  await nextTick();
  const row = wrapper.get(".ls-results .ls-row");
  expect(row.text()).toContain("Pride and Prejudice");
  // The full local archive is optional: one exact Gutenberg text can be fetched and verified directly.
  expect(row.get("[data-result-primary]").attributes("disabled")).toBeUndefined();
  expect(wrapper.get(".ls-collection").text()).toMatch(/one verified text/i);
  await row.get("[data-result-primary]").trigger("click");
  expect(wrapper.emitted("importGutenberg")?.[0]).toEqual([1342]);

  await wrapper.get("#library-tab-wikisource").trigger("click");
  expect(wrapper.get(".ls-input").attributes("disabled")).toBeUndefined();
});

it("keeps digital-library acquisition available while an existing build locks source selection", async () => {
  const wrapper = mount(CorpusSourceIngest, {
    props: { assets: [], hits: [], sourceSelectionDisabled: true },
  });
  expect(wrapper.get("button.source-choose").attributes("disabled")).toBeDefined();
  expect(wrapper.get("button.path-libraries").attributes("disabled")).toBeUndefined();
  await wrapper.get("button.path-libraries").trigger("click");
  await body().get('[data-action="open-library"]').trigger("click");
  await nextTick();
  await nextTick();
  expect(wrapper.find("dialog.library-search").exists()).toBe(true);
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
  await body().get('[data-action="open-library"]').trigger("click");
  await nextTick();
  await nextTick();
  const rows = wrapper.findAll(".ls-results .ls-row");
  expect(rows[0].text()).toContain("#12");
  expect(rows[1].text()).toContain("#13");
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

  it("renders saved sources through the compact source table and reports the selection", async () => {
    const wrapper = shallowMount(CorpusSourceIngest, {
      props: {
        assets: [asset(1), asset(2)],
        assetId: "a1",
        queuedSourceIds: ["a2"],
      },
    });
    const table = wrapper.getComponent(SourceTable);
    expect(table.props("compact")).toBe(true);
    expect(table.props("deletable")).toBe(true);
    expect(table.props("activeId")).toBe("a1");
    expect(table.props("queuedIds")).toEqual(["a2"]);
    expect(table.props("pageSize")).toBe(10);

    table.vm.$emit("choose", "a2");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("update:assetId")?.at(-1)).toEqual(["a2"]);
  });

  it("locks the compact source table while a build is running and supplies the reason", () => {
    const wrapper = shallowMount(CorpusSourceIngest, {
      props: { assets: [asset(1)], sourceSelectionDisabled: true },
    });
    const table = wrapper.getComponent(SourceTable);
    expect(table.props("disabled")).toBe(true);
    expect(String(table.props("lockedReason"))).toMatch(/switch/i);
  });

  it("refreshes the compact source table when registered source ids change", async () => {
    const wrapper = shallowMount(CorpusSourceIngest, {
      props: { assets: [asset(1), asset(2)] },
    });
    expect(wrapper.getComponent(SourceTable).props("refreshKey")).toBe("a1,a2");
    await wrapper.setProps({ assets: [asset(1), asset(2), asset(3)] });
    expect(wrapper.getComponent(SourceTable).props("refreshKey")).toBe("a1,a2,a3");
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

describe("page-number detection", () => {
  it("is automatic and has no user toggle", () => {
    const wrapper = mount(CorpusSourceIngest);
    expect(wrapper.find('.page-detect input[type="checkbox"]').exists()).toBe(false);
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

describe("automatic page detection", () => {
  it("does not ask the user to configure model-assisted detection", () => {
    const wrapper = mount(CorpusSourceIngest);
    expect(wrapper.find(".page-detect-llm").exists()).toBe(false);
    expect(wrapper.find(".page-detect").exists()).toBe(false);
  });

  it("hides OCR controls for non-image sources", () => {
    const wrapper = mount(CorpusSourceIngest, {
      props: {
        selectedAsset: {
          asset_id: "text-source",
          sha256: "abcdef0123456789abcdef",
          filename: "source.txt",
          created_at: "2026-09-23T08:00:00Z",
          page_count: 0,
          block_count: 1,
          ocr_pages: 0,
          warnings: [],
          metadata: {},
          media_kind: "text",
        },
      },
    });
    expect(wrapper.find(".ocr-choice").exists()).toBe(false);
  });

  it("hides OCR controls until a source media kind is selected", () => {
    const wrapper = mount(CorpusSourceIngest, { props: { assets: [], hits: [] } });
    expect(wrapper.find(".ocr-choice").exists()).toBe(false);
  });
});
