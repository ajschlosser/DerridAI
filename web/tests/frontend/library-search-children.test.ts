// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LibraryCatalogueStatus from "../../src/components/corpus-builder/LibraryCatalogueStatus.vue";
import LibraryResultList from "../../src/components/corpus-builder/LibraryResultList.vue";
import { groupWikisourceHits } from "../../src/features/corpus-builder/domain/wikisourceGroups";

beforeEach(() => setActivePinia(createPinia()));

const hit = (title: string, words = 100) => ({
  source: "wikisource" as const,
  title,
  page_id: 1,
  snippet: `snippet ${title}`,
  word_count: words,
  url: `https://fr.wikisource.org/wiki/${encodeURIComponent(title)}`,
});

describe("groupWikisourceHits", () => {
  it("groups chapters under their work and keeps the work's own page apart", () => {
    const groups = groupWikisourceHits([
      hit("De la grammatologie/Livre I", 10),
      hit("De la grammatologie/Livre II", 20),
      hit("Autre"),
      hit("Autre"),
    ]);
    expect(groups.map((g) => g.work)).toEqual(["De la grammatologie", "Autre"]);
    expect(groups[0].parts).toHaveLength(2);
    expect(groups[0].words).toBe(30);
    expect(groups[0].workUrl).toBe("https://fr.wikisource.org/wiki/De_la_grammatologie");
    expect(groups[1].isWorkPage).toBe(true);
    expect(groups[1].parts).toHaveLength(0);
  });
});

describe("LibraryResultList", () => {
  const base = {
    library: "wikisource" as const,
    gutenbergHits: [],
    workGroups: groupWikisourceHits([hit("Œuvre/Chapitre 1")]),
    searching: false,
    collectionReady: true,
    disabled: false,
    importing: "",
    languageName: (code: string) => code,
  };

  it("offers the whole work and, for a single matching part, that part", async () => {
    const wrapper = mount(LibraryResultList, { props: base });
    const buttons = wrapper.findAll("button");
    expect(buttons).toHaveLength(2);
    expect(buttons[0].attributes("data-result-primary")).toBeDefined();
    await buttons[0].trigger("click");
    await buttons[1].trigger("click");
    expect(wrapper.emitted("importWikisource")![0]).toEqual([
      `https://fr.wikisource.org/wiki/${encodeURIComponent("Œuvre")}`,
    ]);
    expect(wrapper.emitted("importWikisource")![1][0]).toContain("Chapitre");
  });

  it("disables every import while one is running", () => {
    const wrapper = mount(LibraryResultList, {
      props: { ...base, importing: "wikisource:elsewhere" },
    });
    expect(wrapper.findAll("button").every((b) => b.attributes("disabled") !== undefined)).toBe(
      true,
    );
  });

  it("lists Gutenberg hits with their language name", async () => {
    const wrapper = mount(LibraryResultList, {
      props: {
        ...base,
        library: "gutenberg",
        gutenbergHits: [{ etext_id: 7, title: "Meno", author: "Plato", language: "en" }],
        languageName: () => "English",
      },
    });
    expect(wrapper.text()).toContain("English");
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("importGutenberg")![0]).toEqual([7]);
  });
});

describe("LibraryCatalogueStatus", () => {
  const status = (archive: Record<string, unknown>, catalogue = "ready") => ({
    ready: false,
    search_ready: catalogue === "ready",
    catalogue: { status: catalogue, item_count: 0 },
    archive: { status: "idle", bytes_done: 0, ...archive },
  });
  const mountStatus = (s: unknown, catalogueReady: boolean) =>
    mount(LibraryCatalogueStatus, {
      props: { status: s as never, catalogueReady, disabled: false, busy: "" },
    });

  it("fetches the catalogue first, then the collection", async () => {
    const first = mountStatus(status({}, "missing"), false);
    await first.get("button").trigger("click");
    expect(first.emitted("refreshCatalogue")).toHaveLength(1);
    const second = mountStatus(status({}), true);
    await second.get("button").trigger("click");
    expect(second.emitted("updateArchive")![0]).toEqual(["start"]);
  });

  it("resumes from bytes already on disk and confirms before a re-download", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const wrapper = mountStatus(status({ status: "error", bytes_done: 2048, error: "boom" }), true);
    await wrapper.findAll("button")[0].trigger("click");
    expect(wrapper.emitted("updateArchive")![0]).toEqual(["resume"]);
    await wrapper.get(".quiet").trigger("click");
    expect(confirm).toHaveBeenCalled();
    expect(wrapper.emitted("updateArchive")![1]).toEqual(["refetch"]);
    expect(wrapper.text()).toContain("boom");
    confirm.mockRestore();
  });
});
