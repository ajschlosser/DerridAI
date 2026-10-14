/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CorpusMetadataResolutionPanel from "../../src/components/CorpusMetadataResolutionPanel.vue";
import MetadataSchemaEditor from "../../src/components/MetadataSchemaEditor.vue";
import MetadataEnrichmentDialog from "../../src/components/MetadataEnrichmentDialog.vue";
import {
  metadataSchemasApi,
  type MetadataSchema,
  type SchemaSummary,
} from "../../src/api/metadataSchemas";
import {
  metadataFieldSpec,
  metadataRegistryFields,
  metadataRegistryGroups,
  schemaFieldSpec,
} from "../../src/domain/metadataFieldRegistry";

const field = (over: Record<string, unknown>) => ({
  name: "x_field",
  label: "X",
  type: "text",
  group: "discourse",
  values: [],
  strict: false,
  instruction: "",
  definitions_heading: "",
  evidence: false,
  assess: false,
  review: false,
  ...over,
});
const group = (key: string, label: string) => ({
  key,
  label,
  intro: "Read.",
  fields_heading: "",
  notes: [],
  trailer: "",
  footer: "",
});
const schema = (): MetadataSchema => ({
  format_version: 1,
  id: "notes",
  name: "Reading notes",
  description: "",
  groups: [group("discourse", "Notes"), group("ideas", "Ideas")],
  fields: [
    field({
      name: "mood",
      label: "Mood",
      type: "choice",
      strict: true,
      values: [
        { value: "calm", definition: "" },
        { value: "angry", definition: "" },
      ],
      review: true,
    }),
    field({ name: "ideas", label: "Ideas", type: "list", group: "ideas" }),
  ] as never,
});
const builtinSchema = (): MetadataSchema => ({
  ...schema(),
  id: "default",
  name: "DerridAI scholarly default",
});
const fictionBuiltinSchema = (): MetadataSchema => ({
  ...schema(),
  id: "derridai-fiction",
  name: "Fiction",
});

describe("the review panel follows the build's schema", () => {
  beforeEach(() => setActivePinia(createPinia()));
  const record = {
    record_id: "r1",
    text: "t",
    mood: "calm",
    metadata_field_status: { mood: { status: "model_inferred", method: "llm" } },
    metadata_incomplete_fields: [],
    metadata_review_fields: [],
  };
  const mountPanel = () =>
    mount(CorpusMetadataResolutionPanel, {
      props: {
        record: record as never,
        regionTypes: ["main_text"],
        discourseRoles: ["assertion"],
        schema: schema(),
      },
      attachTo: document.body,
    });

  it("shows a custom field with its own label and a fixed list of choices, and offers the empty ones to add", () => {
    const wrapper = mountPanel();
    const mood = wrapper
      .findAllComponents({ name: "CorpusMetadataFieldEditor" })
      .find((e) => e.props("field") === "mood")!;
    expect(mood.props("control")).toBe("enum");
    expect(mood.text()).toContain("Mood");
    const add = wrapper.find("details.add-metadata");
    expect(add.text()).toContain("Ideas");
    wrapper.unmount();
  });
  it("does not offer a field the schema leaves out", () => {
    const wrapper = mountPanel();
    const all = wrapper
      .findAllComponents({ name: "CorpusMetadataFieldEditor" })
      .map((e) => e.props("field"));
    expect(all).not.toContain("speaker");
    expect(all).not.toContain("quoted_speaker");
    expect(all).toContain("mood");
    wrapper.unmount();
  });
});

describe("schema-derived frontend metadata registry", () => {
  it("keeps group order, stable identity, field type and control policy in one projection", () => {
    const configured = schema();
    configured.fields = [
      {
        ...field({
          field_id: "field-mood",
          name: "mood",
          label: "Mood",
          type: "choice",
          strict: true,
          values: [
            { value: "calm", definition: "" },
            { value: "angry", definition: "" },
          ],
          review: true,
          semantic_compatibility_id: "example.mood",
        }),
      },
      {
        ...field({
          field_id: "field-ideas",
          name: "ideas",
          label: "Ideas",
          type: "list",
          group: "ideas",
          scope: "corpus",
        }),
      },
    ] as never;

    const fields = metadataRegistryFields(configured, ["main_text"], ["analysis"]);
    const mood = fields.find((item) => item.name === "mood")!;
    const ideas = fields.find((item) => item.name === "ideas")!;

    expect(fields.slice(0, 3).map((item) => item.name)).toEqual([
      "region_type",
      "primary_text",
      "discourse_role",
    ]);
    expect(mood).toMatchObject({
      fieldId: "field-mood",
      semanticCompatibilityId: "example.mood",
      group: "discourse",
      scope: "record",
      control: "enum",
      allowedValues: ["calm", "angry"],
      review: true,
    });
    expect(ideas).toMatchObject({
      fieldId: "field-ideas",
      group: "ideas",
      scope: "corpus",
      control: "multi-combobox",
    });
    expect(
      metadataRegistryGroups(configured, ["main_text"], ["analysis"]).map((item) => [
        item.key,
        item.fields.map((field) => field.name),
      ]),
    ).toEqual([
      ["discourse", ["region_type", "primary_text", "discourse_role", "mood"]],
      ["ideas", ["ideas"]],
    ]);
  });
});

describe("how a schema field is edited", () => {
  const spec = (over: Record<string, unknown>) => schemaFieldSpec(field(over) as never);
  it("maps each type to a control", () => {
    expect(spec({ type: "boolean" }).control).toBe("boolean");
    expect(spec({ type: "number" }).control).toBe("number");
    expect(spec({ type: "list" }).control).toBe("multi-combobox");
    expect(spec({ type: "text" }).control).toBe("combobox");
    expect(
      spec({ type: "choice", strict: true, values: [{ value: "a", definition: "" }] }),
    ).toMatchObject({ control: "enum", allowedValues: ["a"] });
    expect(
      spec({ type: "choice", strict: false, values: [{ value: "a", definition: "" }] }),
    ).toMatchObject({ control: "combobox", allowCustom: true });
  });
});

describe("metadata field cardinality", () => {
  it("keeps scalar legacy and document fields scalar while preserving genuine lists", () => {
    expect(metadataFieldSpec("quoted_speaker", [], []).control).toBe("combobox");
    expect(metadataFieldSpec("quoted_work", [], []).control).toBe("combobox");
    expect(metadataFieldSpec("document_language", [], []).control).toBe("combobox");
    expect(metadataFieldSpec("original_language", [], []).control).toBe("combobox");
    expect(metadataFieldSpec("quotation_chain", [], []).control).toBe("multi-combobox");
    expect(metadataFieldSpec("topics", [], []).control).toBe("multi-combobox");
  });

  it("lets a pinned schema override compatibility cardinality", () => {
    const customQuotedSpeaker = field({
      name: "quoted_speaker",
      type: "list",
      group: "quotation",
    });
    expect(metadataFieldSpec("quoted_speaker", [], [], customQuotedSpeaker as never).control).toBe(
      "multi-combobox",
    );
  });
});

describe("review autocomplete hygiene", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("uses exact field-local NLP spans and excludes POS/NER labels and foreign enums", () => {
    const tagged = schema();
    tagged.fields.push(
      field({
        name: "person_name",
        label: "Person name",
        type: "text",
        group: "discourse",
        pos_tags: ["PROPN"],
        ner_tags: ["PERSON"],
        review: true,
      }) as never,
    );
    const reviewRecord = {
      record_id: "r1",
      text: "The passage names Jacques Derrida.",
      person_name: "",
      metadata_field_status: { person_name: { status: "unresolved" } },
      metadata_incomplete_fields: ["person_name"],
      metadata_review_fields: ["person_name"],
      nlp_candidates: {
        status: "ok",
        engine: "spacy",
        engine_version: "3.8.7",
        model: "fr_core_news_lg",
        language: "fr",
        fields: {
          person_name: [
            { start: 18, end: 32, text: "Jacques Derrida", source: "ner", tag: "PERSON" },
          ],
        },
      },
    };
    const w = mount(CorpusMetadataResolutionPanel, {
      props: {
        record: reviewRecord as never,
        regionTypes: ["main_text"],
        discourseRoles: ["assertion", "analysis"],
        schema: tagged,
        knownValues: {
          person_name: ["PROPN", "PERSON", "analysis", "Jacques Derrida"],
        },
      },
      attachTo: document.body,
    });
    const editor = w
      .findAllComponents({ name: "CorpusMetadataFieldEditor" })
      .find((item) => item.props("field") === "person_name")!;
    expect(editor.props("options")).toContain("Jacques Derrida");
    expect(editor.props("options")).not.toContain("PROPN");
    expect(editor.props("options")).not.toContain("PERSON");
    expect(editor.props("options")).not.toContain("analysis");
    expect(w.text()).toContain("fr_core_news_lg");
    w.unmount();
  });
});

describe("the schema editor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    const listing = [
      {
        id: "default",
        name: "DerridAI scholarly default",
        description: "",
        builtin: true,
        field_count: 23,
        groups: [],
        hash: "a",
      },
      {
        id: "derridai-fiction",
        name: "Fiction",
        description: "Narrative metadata",
        builtin: true,
        field_count: 26,
        groups: [],
        hash: "fiction",
      },
      {
        id: "notes",
        name: "Reading notes",
        description: "",
        builtin: false,
        field_count: 5,
        groups: [],
        hash: "b",
      },
    ];
    vi.spyOn(metadataSchemasApi, "list").mockResolvedValue({ items: listing });
    vi.spyOn(metadataSchemasApi, "get").mockImplementation(async (id: string) => {
      if (id === "default") return builtinSchema();
      if (id === "derridai-fiction") return fictionBuiltinSchema();
      return schema();
    });
  });
  const mountEditor = async () => {
    const w = mount(MetadataSchemaEditor, { attachTo: document.body });
    await flushPromises();
    return w;
  };
  const button = (w: ReturnType<typeof mount>, label: string) =>
    w.findAll("button").find((b) => b.text() === label)!;

  it("restores schema selection and editor tab from route-facing props", async () => {
    const w = mount(MetadataSchemaEditor, {
      props: { initialSchemaId: "notes", initialTab: "groups" },
      attachTo: document.body,
    });
    await flushPromises();

    expect(metadataSchemasApi.get).toHaveBeenCalledWith("notes");
    expect(w.get("#schema-tab-groups").attributes("aria-selected")).toBe("true");
    expect(w.emitted("selection")?.at(-1)).toEqual(["notes"]);

    await w.get("#schema-tab-preview").trigger("click");
    expect(w.emitted("tab")?.at(-1)).toEqual(["preview"]);
    w.unmount();
  });

  it("withholds false empty/editor state while the schema catalog is unresolved", async () => {
    let resolveList!: (value: { items: SchemaSummary[] }) => void;
    vi.spyOn(metadataSchemasApi, "list").mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveList = (value) => resolve(value);
        }),
    );
    const w = mount(MetadataSchemaEditor, { attachTo: document.body });
    await flushPromises();

    expect(w.find(".ui-loading-state").exists()).toBe(true);
    expect(w.findComponent({ name: "SchemaListTable" }).exists()).toBe(false);
    expect(w.find(".schema-form fieldset").exists()).toBe(false);

    resolveList({
      items: [
        {
          id: "default",
          name: "DerridAI scholarly default",
          description: "",
          builtin: true,
          field_count: 23,
          groups: [],
          hash: "a",
        },
      ],
    });
    await flushPromises();

    expect(w.findComponent({ name: "SchemaListTable" }).exists()).toBe(true);
    expect(w.find(".schema-form fieldset").exists()).toBe(true);
    w.unmount();
  });

  it("clears the old schema immediately and ignores a late superseded detail response", async () => {
    let resolveNotes!: (value: MetadataSchema) => void;
    vi.spyOn(metadataSchemasApi, "get")
      .mockResolvedValueOnce(builtinSchema())
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveNotes = resolve;
          }),
      )
      .mockResolvedValueOnce(fictionBuiltinSchema());

    const w = await mountEditor();
    expect(w.text()).toContain("DerridAI scholarly default");

    const rows = w.findAll("button.schema-name");
    await rows.find((button) => button.text().includes("Reading notes"))!.trigger("click");
    await flushPromises();

    expect(w.text()).not.toContain("Editing schemaReading notes");
    expect(w.find(".ui-loading-state").exists()).toBe(true);

    await rows.find((button) => button.text().includes("Fiction"))!.trigger("click");
    await flushPromises();
    expect(w.text()).toContain("Fiction");

    resolveNotes(schema());
    await flushPromises();

    expect(w.text()).toContain("Fiction");
    expect(w.text()).not.toContain("Editing schemaReading notes");
    w.unmount();
  });

  it("shows the built-in schema read-only, with the locked core stated", async () => {
    const w = await mountEditor();
    expect(w.text()).toContain(
      "The built-in schema describes the fields DerridAI has always produced",
    );
    expect(w.text()).toContain("Locked core");
    for (const name of ["region_type", "primary_text", "discourse_role"])
      expect(w.text()).toContain(name);
    expect(button(w, "Save schema").attributes("disabled")).toBeDefined();
    expect(button(w, "Delete").attributes("disabled")).toBeDefined();
    expect(w.get("fieldset").attributes("disabled")).toBeDefined();
    w.unmount();
  });

  it("keeps every built-in profile read-only", async () => {
    const w = mount(MetadataSchemaEditor, {
      props: { initialSchemaId: "derridai-fiction" },
      attachTo: document.body,
    });
    await flushPromises();
    expect(metadataSchemasApi.get).toHaveBeenCalledWith("derridai-fiction");
    expect(button(w, "Save schema").attributes("disabled")).toBeDefined();
    expect(button(w, "Delete").attributes("disabled")).toBeDefined();
    expect(w.get("fieldset").attributes("disabled")).toBeDefined();
    w.unmount();
  });

  it("keeps built-in fields navigable while their inspector controls remain disabled", async () => {
    const w = await mountEditor();
    const fieldButtons = w.findAll("button.field-select");
    expect(fieldButtons.length).toBeGreaterThan(1);
    await fieldButtons[1].trigger("click");
    expect(fieldButtons[1].attributes("aria-current")).toBe("true");
    expect(w.get(".field-inspector fieldset").attributes("disabled")).toBeDefined();
    w.unmount();
  });

  it("shows only implemented reviewed-precedent controls in the selected field inspector", async () => {
    const w = await mountEditor();
    const selected = w.get("button.field-select[aria-current='true']");
    expect(selected.text()).toContain("Mood");
    expect(w.text()).toContain("Memory & retrieval");
    expect(w.text()).toContain("Most examples to show");
    expect(w.text()).toContain("How alike an example must be");
    const thresholds = w.findAll('input[type="number"][min="0"][max="1"][step="0.05"]');
    expect(thresholds.length).toBeGreaterThan(0);
    expect(w.text()).not.toContain("Response memory");
    expect(w.text()).not.toContain("Claim memory");
    w.unmount();
  });

  it("duplicates the built-in schema into an unsaved copy that can be edited and saved", async () => {
    const create = vi
      .spyOn(metadataSchemasApi, "create")
      .mockResolvedValue({ ...schema(), id: "copy" });
    const w = await mountEditor();
    const routeSelectionsBeforeDraft = w.emitted("selection")?.length || 0;
    await button(w, "Duplicate").trigger("click");
    expect(w.emitted("selection")?.length || 0).toBe(routeSelectionsBeforeDraft);
    expect(w.text()).toContain("Not saved yet");
    expect(w.get("fieldset").attributes("disabled")).toBeUndefined();
    await button(w, "Add a field").trigger("click");
    const name = w
      .findAll('input[maxlength="40"]')
      .find((i) => (i.element as HTMLInputElement).value === "")!;
    await name.setValue("new_field");
    await button(w, "Save schema").trigger("click");
    await flushPromises();
    const sent = create.mock.calls[0][0];
    expect(sent.name).toBe("DerridAI scholarly default (copy)");
    expect(sent.fields.some((f) => f.name === "new_field")).toBe(true);
    w.unmount();
  });

  it("keeps focus in the field inspector while typing a new field's name", async () => {
    const w = await mountEditor();
    await button(w, "Duplicate").trigger("click");
    await button(w, "Add a field").trigger("click");
    const name = w
      .findAll('input[maxlength="40"]')
      .find((i) => (i.element as HTMLInputElement).value === "")!;
    for (const ch of "new_field") {
      await name.setValue((name.element as HTMLInputElement).value + ch);
      expect(document.activeElement).toBe(name.element);
    }
    expect((name.element as HTMLInputElement).value).toBe("new_field");
    w.unmount();
  });

  it("shows a validation message from the server and keeps the draft", async () => {
    vi.spyOn(metadataSchemasApi, "create").mockRejectedValue(
      new Error("'region_type' is used by DerridAI itself and cannot be a field name."),
    );
    const w = await mountEditor();
    await button(w, "Duplicate").trigger("click");
    await button(w, "Save schema").trigger("click");
    await flushPromises();
    expect(w.get('[role="alert"]').text()).toContain("used by DerridAI itself");
    w.unmount();
  });

  it("sends the browser OpenAI key when a schema preview runs", async () => {
    const preview = vi
      .spyOn(metadataSchemasApi, "preview")
      .mockResolvedValue({ prompt: "THE PROMPT", answer_schema: {}, ran: false });
    const w = mount(MetadataSchemaEditor, {
      props: {
        providerProfiles: [
          {
            id: "openai-1",
            name: "OpenAI",
            type: "openai",
            model: "gpt-4.1",
            base_url: "https://api.openai.com/v1",
            api_key: "sk-browser",
          },
        ],
        defaultProviderId: "openai-1",
      },
      attachTo: document.body,
    });
    await flushPromises();
    await w.get("[role=tab]#schema-tab-preview").trigger("click");
    await w.get("textarea[rows='5']").setValue("A calm evening.");
    await button(w, "Run on this passage").trigger("click");
    await flushPromises();
    expect(preview.mock.calls[0][0]).toMatchObject({
      run: true,
      provider_profile_id: "openai-1",
      provider: "openai",
      base_url: "https://api.openai.com/v1",
      api_key: "sk-browser",
    });
    w.unmount();
  });

  it("previews a group's prompt and runs it on a passage", async () => {
    const preview = vi.spyOn(metadataSchemasApi, "preview").mockResolvedValue({
      prompt: "THE PROMPT",
      answer_schema: {},
      ran: true,
      answer: { metadata: { mood: "calm" } },
      seconds: 2,
    });
    const w = await mountEditor();
    await w.get("[role=tab]#schema-tab-preview").trigger("click");
    await w.get("textarea[rows='5']").setValue("A calm evening.");
    await button(w, "Run on this passage").trigger("click");
    await flushPromises();
    expect(preview.mock.calls[0][0]).toMatchObject({
      group: "discourse",
      text: "A calm evening.",
      run: true,
    });
    expect(w.text()).toContain("THE PROMPT");
    expect(w.text()).toContain("calm");
    w.unmount();
  });
});

describe("the enrichment dialog lists the schema's groups", () => {
  beforeEach(() => setActivePinia(createPinia()));
  it("offers one checkbox per group and sends the chosen ones", async () => {
    const w = mount(MetadataEnrichmentDialog, {
      props: {
        open: true,
        profiles: [],
        providerProfileId: "p",
        groups: [
          { key: "discourse", label: "Notes" },
          { key: "ideas", label: "Ideas" },
        ],
      },
      attachTo: document.body,
      global: { stubs: { LlmExecutionControl: true } },
    });
    await flushPromises();
    const boxes = [
      ...document.body.querySelectorAll<HTMLInputElement>('fieldset input[type="checkbox"]'),
    ];
    expect(boxes.length).toBe(2);
    expect(document.body.textContent).toContain("Ideas");
    w.unmount();
  });
});
