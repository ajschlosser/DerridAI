/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { corpusBuildsApi, type SemanticAliasSet } from "../../src/api/corpus";
import CorpusSemanticAliasPanel from "../../src/components/corpus-builder/CorpusSemanticAliasPanel.vue";

const author: SemanticAliasSet = {
  alias_set_id: "alias-1",
  kind: "person",
  canonical_label: "Jane Author",
  aliases: ["J. Author"],
  created_at: "2026-09-12T10:00:00Z",
};
const kinds = [{ kind: "person", mode: "entity_name", fields: ["speaker", "persons"] }];

async function open(items: SemanticAliasSet[] = [author]) {
  const list = vi.spyOn(corpusBuildsApi, "semanticAliases").mockResolvedValue({ items, kinds });
  const wrapper = mount(CorpusSemanticAliasPanel, {
    props: { buildId: "b1" },
    attachTo: document.body,
  });
  const details = wrapper.find("details").element as HTMLDetailsElement;
  details.open = true;
  details.dispatchEvent(new Event("toggle"));
  await flushPromises();
  return { wrapper, list };
}

describe("Reviewed identities panel", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads only when opened and lists identities by kind", async () => {
    const { wrapper, list } = await open();
    expect(list).toHaveBeenCalledWith("b1");
    expect(wrapper.find(".kind-group h4").text()).toBe("person");
    expect(wrapper.text()).toContain("Jane Author");
    expect(wrapper.text()).toContain("J. Author");
    expect(wrapper.find("select").text()).toContain("person (used by speaker, persons)");
    wrapper.unmount();
  });

  it("saves one form per line, refreshes, and tells the parent", async () => {
    const { wrapper, list } = await open([]);
    const save = vi
      .spyOn(corpusBuildsApi, "saveSemanticAlias")
      .mockResolvedValue({ ...author, alias_set_id: "alias-2" });
    await wrapper.find("input[type=text]").setValue(" Jane Author ");
    await wrapper.find("textarea").setValue("J. Author\n\n Author, Jane ");
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(save).toHaveBeenCalledWith("b1", {
      kind: "person",
      canonical_label: "Jane Author",
      aliases: ["J. Author", "Author, Jane"],
      reason: "",
      replaces: null,
    });
    expect(list).toHaveBeenCalledTimes(2);
    expect(wrapper.emitted("changed")).toHaveLength(1);
    expect(wrapper.find("[role=status]").text()).toContain("Saved “Jane Author”");
    wrapper.unmount();
  });

  it("editing replaces the set, and a conflict is shown without losing the draft", async () => {
    const { wrapper } = await open();
    vi.spyOn(corpusBuildsApi, "saveSemanticAlias").mockRejectedValue(
      new Error("Already part of another reviewed identity of this kind: J. Author"),
    );
    await wrapper.findAll(".alias-actions button")[0].trigger("click");
    expect((wrapper.find("select").element as HTMLSelectElement).disabled).toBe(true);
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(corpusBuildsApi.saveSemanticAlias).toHaveBeenCalledWith(
      "b1",
      expect.objectContaining({ replaces: "alias-1" }),
    );
    expect(wrapper.find("form [role=alert]").text()).toContain("J. Author");
    expect((wrapper.find("textarea").element as HTMLTextAreaElement).value).toBe("J. Author");
    wrapper.unmount();
  });

  it("asks before retiring and keeps the history on the server", async () => {
    const { wrapper } = await open();
    const retire = vi
      .spyOn(corpusBuildsApi, "retireSemanticAlias")
      .mockResolvedValue({ ...author, retired_at: "2026-09-30T00:00:00Z" });
    await wrapper.findAll(".alias-actions button")[1].trigger("click");
    expect(retire).not.toHaveBeenCalled();
    expect(wrapper.find(".alias-actions [role=alert]").text()).toContain(
      "stays in this build's history",
    );
    await wrapper.findAll(".alias-actions button")[0].trigger("click");
    await flushPromises();
    expect(retire).toHaveBeenCalledWith("b1", "alias-1");
    expect(wrapper.emitted("changed")).toHaveLength(1);
    wrapper.unmount();
  });

  it("imports another corpus's identities as copies and reports what it skipped", async () => {
    const { wrapper } = await open([]);
    vi.spyOn(corpusBuildsApi, "semanticAliasSources").mockResolvedValue({
      items: [{ build_id: "b2", title: "Of Grammatology", alias_sets: 2, kinds: ["person"] }],
    });
    const levinas = {
      ...author,
      alias_set_id: "alias-9",
      canonical_label: "Emmanuel Levinas",
      aliases: [],
    };
    vi.spyOn(corpusBuildsApi, "semanticAliases").mockImplementation(async (buildId: string) =>
      buildId === "b2"
        ? { items: [author, levinas], kinds }
        : {
            items: [
              {
                ...author,
                alias_set_id: "alias-new",
                imported_from: {
                  build_id: "b2",
                  alias_set_id: "alias-1",
                  build_title: "Of Grammatology",
                },
              },
            ],
            kinds,
          },
    );
    const run = vi.spyOn(corpusBuildsApi, "importSemanticAliases").mockResolvedValue({
      imported: [{ ...author, alias_set_id: "alias-new" }],
      skipped: [
        {
          build_id: "b2",
          alias_set_id: "alias-9",
          canonical_label: "Emmanuel Levinas",
          reason: "conflict",
        },
      ],
    });
    const openImport = wrapper
      .findAll("button")
      .find((b) => b.text().includes("Import from another corpus"));
    await openImport!.trigger("click");
    await flushPromises();
    expect(wrapper.find(".import-source select").text()).toContain(
      "Of Grammatology (2 identities)",
    );
    const boxes = wrapper.findAll(".import-choices input[type=checkbox]");
    expect(boxes).toHaveLength(2);
    expect(boxes.every((box) => (box.element as HTMLInputElement).checked)).toBe(true);
    await boxes[1].setValue(false);
    const submit = wrapper.findAll("button").find((b) => b.text().startsWith("Import 1 selected"));
    await submit!.trigger("click");
    await flushPromises();
    expect(run).toHaveBeenCalledWith("b1", "b2", ["alias-1"]);
    expect(wrapper.find("[role=status]").text()).toContain("Imported 1; skipped 1.");
    expect(wrapper.find(".skipped").text()).toContain(
      "Emmanuel Levinas: its forms already belong to an identity here.",
    );
    expect(wrapper.find(".alias-set").text()).toContain("Imported from Of Grammatology");
    expect(wrapper.emitted("changed")).toHaveLength(1);
    wrapper.unmount();
  });

  it("says when no other corpus has reviewed identities", async () => {
    const { wrapper } = await open([]);
    vi.spyOn(corpusBuildsApi, "semanticAliasSources").mockResolvedValue({ items: [] });
    const openImport = wrapper
      .findAll("button")
      .find((b) => b.text().includes("Import from another corpus"));
    await openImport!.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("No other corpus build has reviewed identities yet.");
    expect(wrapper.findAll("button").some((b) => b.text().startsWith("Import "))).toBe(false);
    wrapper.unmount();
  });
});
