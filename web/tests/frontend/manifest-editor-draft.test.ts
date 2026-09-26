import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import DocumentManifestEditor from "../../src/components/DocumentManifestEditor.vue";

// The build is polled while it runs, and every poll hands the editor a new manifest object. The draft
// must survive that, or a reader's edits vanish while they type.
const manifest = (over: Record<string, unknown> = {}) => ({
  title: "On Cosmopolitanism",
  document_author: "Jacques Derrida",
  main_text_start_page: 53,
  ...over,
});
const field = (wrapper: any, label: RegExp) =>
  wrapper
    .findAll("label")
    .find((l: any) => label.test(l.text()))!
    .find("input,textarea");

describe("Document manifest editor drafts", () => {
  it("keeps an unsaved edit when the same manifest is handed in again", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: manifest() } });
    await field(wrapper, /main text starts/i).setValue("18");
    await wrapper.setProps({ manifest: manifest() }); // a poll: a new object, the same contents
    expect((field(wrapper, /main text starts/i).element as HTMLInputElement).value).toBe("18");
    expect(wrapper.text()).toContain("1 unsaved change");
  });

  it("keeps an unsaved edit while another field is updated by the server", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: manifest() } });
    await field(wrapper, /main text starts/i).setValue("18");
    await wrapper.setProps({ manifest: manifest({ title: "On Cosmopolitanism and Forgiveness" }) });
    expect((field(wrapper, /main text starts/i).element as HTMLInputElement).value).toBe("18");
    // A field the reader has not touched follows the server.
    expect((field(wrapper, /^title/i).element as HTMLInputElement).value).toBe(
      "On Cosmopolitanism and Forgiveness",
    );
    expect(wrapper.text()).toContain("1 unsaved change");
  });

  it("says so, and keeps the draft, when the server value changes under an edit", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: manifest() } });
    await field(wrapper, /main text starts/i).setValue("18");
    await wrapper.setProps({ manifest: manifest({ main_text_start_page: 40 }) });
    expect((field(wrapper, /main text starts/i).element as HTMLInputElement).value).toBe("18");
    const notice = wrapper.get(".manifest-server-change");
    expect(notice.attributes("role")).toBe("status");
    expect(notice.text()).toContain("40");
    await notice.get("button").trigger("click");
    expect((field(wrapper, /main text starts/i).element as HTMLInputElement).value).toBe("40");
    expect(wrapper.find(".manifest-server-change").exists()).toBe(false);
    expect(wrapper.text()).toContain("No unsaved changes");
  });

  it("clears the notice when the server comes to agree with the edit", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: manifest() } });
    await field(wrapper, /main text starts/i).setValue("18");
    await wrapper.setProps({ manifest: manifest({ main_text_start_page: 40 }) });
    expect(wrapper.find(".manifest-server-change").exists()).toBe(true);
    await wrapper.setProps({ manifest: manifest({ main_text_start_page: 18 }) });
    expect(wrapper.find(".manifest-server-change").exists()).toBe(false);
    expect(wrapper.text()).toContain("No unsaved changes");
  });

  it("saves only what the reader changed", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: manifest() } });
    await field(wrapper, /main text starts/i).setValue("18");
    await wrapper.setProps({ manifest: manifest({ title: "A newer title" }) });
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("save")![0][0]).toEqual({ main_text_start_page: 18 });
  });

  it("saves a changed page number (a number input hands back a number, not text)", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: manifest() } });
    await field(wrapper, /main text starts/i).setValue("18");
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("save")![0][0]).toEqual({ main_text_start_page: 18 });
  });

  it("does not count a page number typed back to its old value as a change", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: manifest() } });
    await field(wrapper, /main text starts/i).setValue("18");
    await field(wrapper, /main text starts/i).setValue("53");
    expect(wrapper.text()).toContain("No unsaved changes");
  });
});

describe("Document manifest editor origins", () => {
  const withOrigins = () =>
    manifest({
      publication_place: "Baltimore",
      publication_year: 1967,
      deterministic_ingest: {
        applied: {
          publication_place: {
            value: "Baltimore",
            method: "nlp:spacy:en_core_web_lg:place_near_publisher",
            confidence: 0.7,
            derivation: "nlp_derived",
            alternatives: [{ value: "London", confidence: 0.5, derivation: "nlp_derived" }],
          },
          publication_year: {
            value: "1967",
            method: "pattern:copyright_year",
            confidence: 0.9,
            derivation: "computed",
            alternatives: [{ value: "1976", confidence: 0.55, derivation: "computed" }],
          },
        },
      },
    });

  it("labels pre-filled values as NLP-derived or computed", () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: withOrigins() } });
    const chips = wrapper.findAll(".origin-chip").map((chip) => chip.text());
    expect(chips.some((text) => text.includes("NLP-derived") && text.includes("70%"))).toBe(true);
    expect(chips.some((text) => text.includes("Computed") && text.includes("90%"))).toBe(true);
  });

  it("offers the less certain alternatives, which fill the field on click", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: withOrigins() } });
    const alternative = wrapper
      .findAll(".origin-alt")
      .find((button) => button.text().includes("London"))!;
    await alternative.trigger("click");
    expect(
      (field(wrapper, /place of publication|publication place|^place/i).element as HTMLInputElement)
        .value,
    ).toBe("London");
  });

  it("drops the origin chip once the reviewer changes the value, but keeps the suggestions", async () => {
    const wrapper = mount(DocumentManifestEditor, { props: { manifest: withOrigins() } });
    await field(wrapper, /place of publication|publication place|^place/i).setValue("Paris");
    expect(wrapper.findAll(".origin-chip").some((chip) => chip.text().includes("70%"))).toBe(false);
    expect(wrapper.findAll(".origin-alt").length).toBeGreaterThan(0);
  });
});
