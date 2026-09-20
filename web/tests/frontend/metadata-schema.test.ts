import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CorpusMetadataResolutionPanel from "../../src/components/CorpusMetadataResolutionPanel.vue";
import MetadataSchemaEditor from "../../src/components/MetadataSchemaEditor.vue";
import MetadataEnrichmentDialog from "../../src/components/MetadataEnrichmentDialog.vue";
import { metadataSchemasApi, type MetadataSchema } from "../../src/api/metadataSchemas";
import { schemaFieldSpec } from "../../src/domain/metadataFieldRegistry";

const field = (over: Record<string, unknown>) => ({ name: "x_field", label: "X", type: "text", group: "discourse", values: [], strict: false, instruction: "", definitions_heading: "", evidence: false, assess: false, review: false, ...over });
const group = (key: string, label: string) => ({ key, label, intro: "Read.", fields_heading: "", notes: [], trailer: "", footer: "" });
const schema = (): MetadataSchema => ({
  format_version: 1, id: "notes", name: "Reading notes", description: "",
  groups: [group("discourse", "Notes"), group("ideas", "Ideas")],
  fields: [
    field({ name: "mood", label: "Mood", type: "choice", strict: true, values: [{ value: "calm", definition: "" }, { value: "angry", definition: "" }], review: true }),
    field({ name: "ideas", label: "Ideas", type: "list", group: "ideas" }),
  ] as never,
});
const builtinSchema = (): MetadataSchema => ({ ...schema(), id: "default", name: "DerridAI scholarly default" });

describe("the review panel follows the build's schema", () => {
  beforeEach(() => setActivePinia(createPinia()));
  const record = { record_id: "r1", text: "t", mood: "calm", metadata_field_status: { mood: { status: "llm_inferred", method: "llm" } }, metadata_incomplete_fields: [], metadata_review_fields: [] };
  const mountPanel = () => mount(CorpusMetadataResolutionPanel, { props: { record: record as never, regionTypes: ["main_text"], discourseRoles: ["assertion"], schema: schema() }, attachTo: document.body });

  it("shows a custom field with its own label and a fixed list of choices, and offers the empty ones to add", () => {
    const wrapper = mountPanel();
    const mood = wrapper.findAllComponents({ name: "CorpusMetadataFieldEditor" }).find(e => e.props("field") === "mood")!;
    expect(mood.props("control")).toBe("enum");
    expect(mood.text()).toContain("Mood");
    const add = wrapper.find("details.add-metadata");
    expect(add.text()).toContain("Ideas");
    wrapper.unmount();
  });
  it("does not offer a field the schema leaves out", () => {
    const wrapper = mountPanel();
    const all = wrapper.findAllComponents({ name: "CorpusMetadataFieldEditor" }).map(e => e.props("field"));
    expect(all).not.toContain("speaker");
    expect(all).not.toContain("quoted_speaker");
    expect(all).toContain("mood");
    wrapper.unmount();
  });
});

describe("how a schema field is edited", () => {
  const spec = (over: Record<string, unknown>) => schemaFieldSpec(field(over) as never);
  it("maps each type to a control", () => {
    expect(spec({ type: "boolean" }).control).toBe("boolean");
    expect(spec({ type: "number" }).control).toBe("number");
    expect(spec({ type: "list" }).control).toBe("multi-combobox");
    expect(spec({ type: "text" }).control).toBe("combobox");
    expect(spec({ type: "choice", strict: true, values: [{ value: "a", definition: "" }] })).toMatchObject({ control: "enum", allowedValues: ["a"] });
    expect(spec({ type: "choice", strict: false, values: [{ value: "a", definition: "" }] })).toMatchObject({ control: "combobox", allowCustom: true });
  });
});

describe("the schema editor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    const listing = [{ id: "default", name: "DerridAI scholarly default", description: "", builtin: true, field_count: 23, groups: [], hash: "a" }, { id: "notes", name: "Reading notes", description: "", builtin: false, field_count: 5, groups: [], hash: "b" }];
    vi.spyOn(metadataSchemasApi, "list").mockResolvedValue({ items: listing });
    vi.spyOn(metadataSchemasApi, "get").mockImplementation(async (id: string) => (id === "default" ? builtinSchema() : schema()));
  });
  const mountEditor = async () => { const w = mount(MetadataSchemaEditor, { attachTo: document.body }); await flushPromises(); return w; };
  const button = (w: ReturnType<typeof mount>, label: string) => w.findAll("button").find(b => b.text() === label)!;

  it("shows the built-in schema read-only, with the locked core stated", async () => {
    const w = await mountEditor();
    expect(w.text()).toContain("The built-in schema describes the fields DerridAI has always produced");
    expect(w.text()).toContain("Locked core");
    for (const name of ["region_type", "primary_text", "discourse_role"]) expect(w.text()).toContain(name);
    expect(button(w, "Save schema").attributes("disabled")).toBeDefined();
    expect(button(w, "Delete").attributes("disabled")).toBeDefined();
    expect(w.get("fieldset").attributes("disabled")).toBeDefined();
    w.unmount();
  });

  it("duplicates the built-in schema into an unsaved copy that can be edited and saved", async () => {
    const create = vi.spyOn(metadataSchemasApi, "create").mockResolvedValue({ ...schema(), id: "copy" });
    const w = await mountEditor();
    await button(w, "Duplicate").trigger("click");
    expect(w.text()).toContain("Not saved yet");
    expect(w.get("fieldset").attributes("disabled")).toBeUndefined();
    await button(w, "Add a field").trigger("click");
    const name = w.findAll('input[maxlength="40"]').find(i => (i.element as HTMLInputElement).value === "")!;
    await name.setValue("new_field");
    await button(w, "Save schema").trigger("click");
    await flushPromises();
    const sent = create.mock.calls[0][0];
    expect(sent.name).toBe("DerridAI scholarly default (copy)");
    expect(sent.fields.some(f => f.name === "new_field")).toBe(true);
    w.unmount();
  });

  it("shows a validation message from the server and keeps the draft", async () => {
    vi.spyOn(metadataSchemasApi, "create").mockRejectedValue(new Error("'region_type' is used by DerridAI itself and cannot be a field name."));
    const w = await mountEditor();
    await button(w, "Duplicate").trigger("click");
    await button(w, "Save schema").trigger("click");
    await flushPromises();
    expect(w.get('[role="alert"]').text()).toContain("used by DerridAI itself");
    w.unmount();
  });

  it("previews a group's prompt and runs it on a passage", async () => {
    const preview = vi.spyOn(metadataSchemasApi, "preview").mockResolvedValue({ prompt: "THE PROMPT", answer_schema: {}, ran: true, answer: { metadata: { mood: "calm" } }, seconds: 2 });
    const w = await mountEditor();
    await w.get("textarea[rows='5']").setValue("A calm evening.");
    await button(w, "Run on this passage").trigger("click");
    await flushPromises();
    expect(preview.mock.calls[0][0]).toMatchObject({ group: "discourse", text: "A calm evening.", run: true });
    expect(w.text()).toContain("THE PROMPT");
    expect(w.text()).toContain("calm");
    w.unmount();
  });
});

describe("the enrichment dialog lists the schema's groups", () => {
  beforeEach(() => setActivePinia(createPinia()));
  it("offers one checkbox per group and sends the chosen ones", async () => {
    const w = mount(MetadataEnrichmentDialog, {
      props: { open: true, profiles: [], providerProfileId: "p", groups: [{ key: "discourse", label: "Notes" }, { key: "ideas", label: "Ideas" }] },
      attachTo: document.body, global: { stubs: { LlmExecutionControl: true } },
    });
    await flushPromises();
    const boxes = [...document.body.querySelectorAll<HTMLInputElement>('fieldset input[type="checkbox"]')];
    expect(boxes.length).toBe(2);
    expect(document.body.textContent).toContain("Ideas");
    w.unmount();
  });
});
