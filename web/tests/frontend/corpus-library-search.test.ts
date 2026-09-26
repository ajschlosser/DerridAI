// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CorpusLibrarySearch from "../../src/components/corpus-builder/CorpusLibrarySearch.vue";

const ready = {
  ready: true,
  search_ready: true,
  catalogue: { status: "ready", item_count: 70000 },
  archive: { status: "ready", bytes_done: 1, total_bytes: 1 },
};
const hit = (title: string, url: string, words = 500) => ({
  source: "wikisource" as const,
  language: "fr",
  title,
  page_id: title.length,
  snippet: "…l’hospitalité…",
  word_count: words,
  url,
});
function mountSearch(props: Record<string, unknown> = {}) {
  return mount(CorpusLibrarySearch, {
    props: { query: "", gutenbergStatus: ready, ...props },
    attachTo: document.body,
  });
}
async function wikisource(wrapper: ReturnType<typeof mountSearch>) {
  await wrapper.get("#library-tab-wikisource").trigger("click");
}

describe("the digital-library search", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  it("offers a chapter's whole work first, and the chapter alone as an alternative", async () => {
    const wrapper = mountSearch({
      query: "lettres",
      searched: { gutenberg: "", wikisource: "lettres" },
      wikisourceHits: [
        hit(
          "Lettres persanes/Lettre 129",
          "https://fr.wikisource.org/wiki/Lettres_persanes/Lettre_129",
        ),
      ],
    });
    await wikisource(wrapper);
    const row = wrapper.get(".ls-row");
    expect(row.text()).toContain("Lettres persanes");
    expect(row.text()).toContain("Lettre 129");
    await row.get("[data-result-primary]").trigger("click");
    await row.findAll("button")[1].trigger("click");
    expect(wrapper.emitted("importWikisource")).toEqual([
      ["https://fr.wikisource.org/wiki/Lettres_persanes"],
      ["https://fr.wikisource.org/wiki/Lettres_persanes/Lettre_129"],
    ]);
    wrapper.unmount();
  });

  it("groups several matching chapters of one work into a single row", async () => {
    const wrapper = mountSearch({
      query: "lettre",
      searched: { gutenberg: "", wikisource: "lettre" },
      wikisourceHits: [
        hit(
          "Lettres persanes/Lettre 1",
          "https://fr.wikisource.org/wiki/Lettres_persanes/Lettre_1",
        ),
        hit(
          "Lettres persanes/Lettre 2",
          "https://fr.wikisource.org/wiki/Lettres_persanes/Lettre_2",
        ),
        hit("Émile", "https://fr.wikisource.org/wiki/%C3%89mile"),
      ],
    });
    await wikisource(wrapper);
    const rows = wrapper.findAll(".ls-row");
    expect(rows).toHaveLength(2);
    expect(rows[0].text()).toContain("2 matching parts");
    // A work's own page has no separate "part" to offer.
    expect(rows[1].findAll("button")).toHaveLength(1);
    wrapper.unmount();
  });

  it("searches as the reviewer types, after a pause, and at once on Enter", async () => {
    const wrapper = mountSearch();
    await wrapper.setProps({ query: "rou" });
    expect(wrapper.emitted("search")).toBeUndefined();
    vi.advanceTimersByTime(400);
    expect(wrapper.emitted("search")).toEqual([["gutenberg"]]);
    await wrapper.setProps({ query: "rousseau" });
    await wrapper.get("form.ls-search").trigger("submit");
    expect(wrapper.emitted("search")).toHaveLength(2);
    wrapper.unmount();
  });

  it("shows errors and empty results inside the dialog, not behind it", async () => {
    const wrapper = mountSearch({
      query: "zzzz",
      searched: { gutenberg: "zzzz", wikisource: "" },
    });
    expect(wrapper.get(".ls-empty").text()).toContain("zzzz");
    await wrapper.setProps({ error: "Wikisource search failed: HTTP 503" });
    expect(wrapper.get('[role="alert"]').text()).toContain("HTTP 503");
    wrapper.unmount();
  });

  it("marks the row being imported, locks the others, and closes once the import lands", async () => {
    const wrapper = mountSearch({
      query: "austen",
      searched: { gutenberg: "austen", wikisource: "" },
      gutenbergHits: [
        { etext_id: 1342, title: "Pride and Prejudice", author: "Jane Austen", language: "en" },
        { etext_id: 105, title: "Persuasion", author: "Jane Austen", language: "en" },
      ],
      importing: "gutenberg:1342",
    });
    const [first, second] = wrapper.findAll("[data-result-primary]");
    expect(first.text()).toBe("Importing…");
    expect(first.attributes("aria-busy")).toBe("true");
    expect(second.attributes("disabled")).toBeDefined();
    await wrapper.setProps({ importing: "", imported: 1 });
    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
  });

  it("moves from the search box into the results with the arrow keys", async () => {
    const wrapper = mountSearch({
      query: "austen",
      searched: { gutenberg: "austen", wikisource: "" },
      gutenbergHits: [
        { etext_id: 1342, title: "Pride and Prejudice", author: "Jane Austen", language: "en" },
        { etext_id: 105, title: "Persuasion", author: "Jane Austen", language: "en" },
      ],
    });
    await nextTick(); // the dialog puts focus in the search box as it opens
    expect(document.activeElement).toBe(wrapper.get(".ls-input").element);
    await wrapper.get(".ls-input").trigger("keydown", { key: "ArrowDown" });
    const buttons = wrapper.findAll("[data-result-primary]");
    expect(document.activeElement).toBe(buttons[0].element);
    await buttons[0].trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement).toBe(buttons[1].element);
    await buttons[1].trigger("keydown", { key: "ArrowUp" });
    await buttons[0].trigger("keydown", { key: "ArrowUp" });
    expect(document.activeElement).toBe(wrapper.get(".ls-input").element);
    wrapper.unmount();
  });

  it("searches the chosen Wikisource language edition", async () => {
    const wrapper = mountSearch({ query: "Rousseau", language: "en" });
    await wikisource(wrapper);
    await wrapper.get(".ls-language").setValue("fr");
    expect(wrapper.emitted("update:language")).toEqual([["fr"]]);
    await wrapper.setProps({ language: "fr" });
    await nextTick();
    vi.runAllTimers();
    expect(wrapper.emitted("search")?.at(-1)).toEqual(["wikisource"]);
    expect(wrapper.text()).toContain("fr.wikisource.org");
    wrapper.unmount();
  });
});

describe("the Project Gutenberg collection after a failed download", () => {
  beforeEach(() => setActivePinia(createPinia()));
  const failed = {
    ready: false,
    search_ready: true,
    catalogue: { status: "ready", item_count: 1 },
    archive: { status: "error", bytes_done: 11_291_965_468, total_bytes: null, error: "416" },
  };

  it("resumes from the bytes on disk, and offers a confirmed Redownload", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const wrapper = mount(CorpusLibrarySearch, {
      props: { query: "", gutenbergStatus: failed as never },
      attachTo: document.body,
    });
    const buttons = wrapper.findAll(".ls-collection-actions button");
    expect(buttons[0].text()).toBe("Resume collection download");
    await buttons[0].trigger("click");
    await buttons[1].trigger("click");
    expect(confirm).toHaveBeenCalledOnce();
    expect(wrapper.emitted("updateGutenbergArchive")).toEqual([["resume"], ["refetch"]]);
    confirm.mockRestore();
    wrapper.unmount();
  });
});
