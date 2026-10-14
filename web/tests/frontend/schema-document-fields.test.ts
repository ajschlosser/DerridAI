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

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import SchemaDocumentFieldsPanel from "../../src/components/metadata-schemas/SchemaDocumentFieldsPanel.vue";
import {
  DOCUMENT_FIELD_NAMES,
  completeDocumentFields,
  type MetadataSchema,
} from "../../src/api/metadataSchemas";

const draft = (): MetadataSchema => ({
  format_version: 2,
  id: "s",
  name: "S",
  description: "",
  groups: [],
  fields: [],
  document_fields: completeDocumentFields([{ name: "translator", required_for: ["publication"] }]),
});

describe("document field policies", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("completes missing policies in canonical order and keeps given ones", () => {
    const policies = completeDocumentFields([
      { name: "translator", required_for: ["publication"] },
    ]);
    expect(policies.map((p) => p.name)).toEqual([...DOCUMENT_FIELD_NAMES]);
    expect(policies.find((p) => p.name === "translator")?.required_for).toEqual(["publication"]);
    expect(policies.find((p) => p.name === "document_author")?.required_for).toEqual([
      "evidence",
      "publication",
    ]);
  });

  it("edits requirements in the draft", async () => {
    const schema = draft();
    const wrapper = mount(SchemaDocumentFieldsPanel, { props: { draft: schema, readonly: false } });
    const authorRow = wrapper.findAll("tbody tr")[DOCUMENT_FIELD_NAMES.indexOf("document_author")];
    const [evidence] = authorRow.findAll('input[type="checkbox"]');
    await evidence.setValue(false);
    const author = schema.document_fields!.find((p) => p.name === "document_author")!;
    expect(author).toMatchObject({
      required_for: ["publication"],
    });
  });

  it("disables every control when read-only", () => {
    const wrapper = mount(SchemaDocumentFieldsPanel, { props: { draft: draft(), readonly: true } });
    expect(
      wrapper.findAll("select, input").every((el) => el.attributes("disabled") !== undefined),
    ).toBe(true);
  });
});
