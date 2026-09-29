/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const documentNlpApi = vi.hoisted(() => ({
  listPacks: vi.fn(),
  addPack: vi.fn(),
  removePack: vi.fn(),
  installPack: vi.fn(),
  cancelInstall: vi.fn(),
  uninstallPack: vi.fn(),
}));
vi.mock("../../src/api/documentNlp", () => ({ documentNlpApi }));

import DocumentNlpLanguagePacks from "../../src/components/settings/DocumentNlpLanguagePacks.vue";

const base = {
  engine: "booknlp",
  origin: "builtin",
  files: [],
  installed: false,
  worker_bundled: true,
  download_bytes: 160_398_571,
};
const catalog = [
  {
    ...base,
    pack_id: "booknlp-en-small",
    language: "en",
    label: "BookNLP English",
    installable: true,
  },
  {
    ...base,
    pack_id: "propp-fr",
    language: "fr",
    engine: "propp-fr",
    label: "Propp",
    installable: false,
    worker_bundled: false,
  },
];

function row(wrapper: ReturnType<typeof mount>, packId: string) {
  return wrapper.get(`[data-pack="${packId}"]`);
}

describe("Document Intelligence language packs", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    documentNlpApi.listPacks.mockResolvedValue({
      packs: catalog,
      models_dir: "/data/models/booknlp",
    });
  });

  it("installs an installable pack on request and never offers to install a reference-only source", async () => {
    documentNlpApi.installPack.mockResolvedValue({ id: "nlp-pack-1", status: "queued" });
    const wrapper = mount(DocumentNlpLanguagePacks);
    await flushPromises();

    expect(row(wrapper, "propp-fr").findAll("button")).toHaveLength(0);
    expect(row(wrapper, "propp-fr").text()).toContain("propp-fr");

    await row(wrapper, "booknlp-en-small").get("button").trigger("click");
    await flushPromises();
    expect(documentNlpApi.installPack).toHaveBeenCalledWith("booknlp-en-small");
    expect(documentNlpApi.listPacks).toHaveBeenCalledTimes(2);
  });

  it("shows install progress and cancels the running job", async () => {
    documentNlpApi.listPacks.mockResolvedValue({
      packs: [
        {
          ...catalog[0],
          active_job: { id: "nlp-pack-1", status: "running", completed: 50, total: 200 },
        },
      ],
      models_dir: "",
    });
    const wrapper = mount(DocumentNlpLanguagePacks);
    await flushPromises();

    expect(row(wrapper, "booknlp-en-small").text()).toContain("25");
    await row(wrapper, "booknlp-en-small").get("button").trigger("click");
    expect(documentNlpApi.cancelInstall).toHaveBeenCalledWith("nlp-pack-1");
    wrapper.unmount();
  });

  it("filters the catalog by language and explains packs that need missing Python packages", async () => {
    documentNlpApi.listPacks.mockResolvedValue({
      packs: [
        ...catalog,
        {
          ...base,
          pack_id: "spacy-ja-md",
          language: "ja",
          engine: "spacy",
          tier: "md",
          label: "spaCy ja_core_news_md 3.8.0",
          installable: false,
          missing_requirements: ["sudachipy"],
        },
      ],
      models_dir: "",
    });
    const wrapper = mount(DocumentNlpLanguagePacks);
    await flushPromises();

    expect(row(wrapper, "spacy-ja-md").text()).toContain("sudachipy");
    expect(row(wrapper, "spacy-ja-md").findAll("button")).toHaveLength(0);
    await wrapper.get('input[type="search"]').setValue("ja");
    expect(wrapper.findAll("tbody tr").map((tr) => tr.attributes("data-pack"))).toEqual([
      "spacy-ja-md",
    ]);
  });

  it("rejects a malformed pack definition without calling the API", async () => {
    const wrapper = mount(DocumentNlpLanguagePacks);
    await flushPromises();
    await wrapper.get("textarea").setValue("{ not json");
    await wrapper.get(".nlp-packs-add button").trigger("click");
    expect(documentNlpApi.addPack).not.toHaveBeenCalled();
    expect(wrapper.get('[role="status"]').text()).toMatch(/JSON/);
  });
});
