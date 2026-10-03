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
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

import { expect, test, type Page } from "@playwright/test";
import { runAxe } from "./support/axe";
import { mockBackend, type Fixtures } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

const GROUP = {
  key: "discourse",
  label: "Discourse and attribution",
  intro: "Infer only discourse metadata supported by the record.",
  fields_heading: "Discourse fields",
  notes: ["Preserve uncertainty rather than guessing."],
  trailer: "",
  footer: "Return an assessment for every assessed field.",
};

const DEFAULT_SCHEMA = {
  format_version: 2,
  schema_version: "1.0.0",
  id: "default",
  name: "DerridAI scholarly default",
  description: "Default scholarly metadata contract.",
  groups: [GROUP],
  fields: [
    {
      field_id: "field-speaker",
      name: "speaker",
      label: "Speaker",
      type: "text",
      group: "discourse",
      role: "scholarly",
      scope: "record",
      review_visibility: "primary",
      values: [],
      strict: false,
      instruction: "Identify the speaker.",
      definitions_heading: "",
      evidence: true,
      assess: true,
      review: true,
      pos_tags: ["PROPN"],
      ner_tags: ["PERSON"],
      retrieval_profile: {
        enabled: false,
        include_corrections: true,
        include_confirmed_absence: false,
        max_items: 4,
        max_corrections: 2,
        min_similarity: 0.65,
        match_field_ids: [],
      },
      equivalence_profile: null,
      members: [],
      max_items: null,
      instance_label: "{label} {number}",
    },
    {
      field_id: "field-stance",
      name: "stance",
      label: "Stance",
      type: "choice",
      group: "discourse",
      role: "scholarly",
      scope: "record",
      review_visibility: "primary",
      values: [
        { value: "affirm", definition: "Affirms the attributed position." },
        { value: "reject", definition: "Rejects the attributed position." },
      ],
      strict: false,
      instruction: "Identify the stance.",
      definitions_heading: "",
      evidence: true,
      assess: true,
      review: true,
      pos_tags: [],
      ner_tags: [],
      retrieval_profile: {
        enabled: false,
        include_corrections: true,
        include_confirmed_absence: false,
        max_items: 4,
        max_corrections: 2,
        min_similarity: 0.65,
        match_field_ids: [],
      },
      equivalence_profile: null,
      members: [],
      max_items: null,
      instance_label: "{label} {number}",
    },
  ],
};

const SAVED_SCHEMA = {
  ...DEFAULT_SCHEMA,
  id: "scholarly-copy",
  name: "DerridAI scholarly default (copy)",
};

function summary(schema: typeof DEFAULT_SCHEMA, builtin = false) {
  return {
    id: schema.id,
    name: schema.name,
    description: schema.description,
    builtin,
    field_count: schema.fields.length,
    groups: schema.groups.map((group) => group.key),
    hash: schema.id,
    schema_version: schema.schema_version,
  };
}

function schemaFixtures(): Fixtures {
  let saved = false;
  return {
    "GET /api/pdf/metadata-schemas": () => ({
      items: saved
        ? [summary(DEFAULT_SCHEMA, true), summary(SAVED_SCHEMA)]
        : [summary(DEFAULT_SCHEMA, true)],
    }),
    "GET /api/pdf/metadata-schemas/default": DEFAULT_SCHEMA,
    "GET /api/pdf/metadata-schemas/scholarly-copy": SAVED_SCHEMA,
    "POST /api/pdf/metadata-schemas": () => {
      saved = true;
      return SAVED_SCHEMA;
    },
  };
}

async function openSchemas(page: Page, options: { french?: boolean } = {}) {
  if (options.french) {
    await page.addInitScript(() => localStorage.setItem("derridai-locale", "fr-CA"));
  }
  await mockBackend(page, { fixtures: schemaFixtures() });
  if (options.french) {
    await page.route("**/api/i18n/languages/fr-CA", (route) =>
      route.fulfill({
        json: {
          code: "fr-CA",
          name: "Français",
          flag: "ca",
          dictionary: {
            "section.corpus_management": "Gestion du corpus",
            "schemas.manage_title": "Schémas de métadonnées",
            "schemas.manage_help":
              "Définissez les champs, leurs règles de révision et les groupes d’instructions.",
            "schemas.saved_schemas": "Schémas enregistrés",
            "schemas.editing_schema": "Schéma en cours de modification",
            "schemas.tab_fields": "Champs",
            "schemas.tab_document_fields": "Champs du document",
            "schemas.tab_prompts": "Groupes d’instructions",
            "schemas.tab_preview": "Tester le schéma",
            "schemas.field_configuration": "Configuration du champ",
            "schemas.field_configuration_help":
              "Définissez ce que signifie ce champ ainsi que la façon dont DerridAI doit le renseigner et le soumettre à la révision.",
            "schemas.filter_fields": "Filtrer les champs",
            "schemas.add_field": "Ajouter un champ",
            "schemas.duplicate": "Dupliquer",
            "schemas.save": "Enregistrer le schéma",
            "schemas.builtin": "Intégré",
            "schemas.builtin_help":
              "Ce schéma intégré est en lecture seule. Dupliquez-le pour le personnaliser.",
            "schemas.locked_core": "Noyau verrouillé",
            "schemas.locked_core_help":
              "Ces champs structurels sont gérés par DerridAI et ne peuvent pas être supprimés.",
            "schemas.col_fields": "Champs",
            "schemas.type_text": "Texte",
            "schemas.type_choice": "Une valeur parmi une liste",
            "schemas.evidence_short": "Preuve",
            "schemas.assess_short": "Confiance",
            "schemas.review_short": "Révision humaine",
          },
        },
      }),
    );
  }
  await page.goto(`${APP}/schemas`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator(".schema-editor")).toBeVisible();
}

async function expectAxeClean(page: Page) {
  const scan = await runAxe(page, (builder) =>
    builder
      .include(".schemas-page")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]),
  );
  expect(
    scan.violations.map((violation) =>
      `${violation.id}: ${violation.nodes.map((node) => node.target).join(" ")}`,
    ),
  ).toEqual([]);
}

test.beforeEach(({}, info) => {
  test.skip(info.project.name !== "chromium-desktop", "Runs once in Chromium.");
});

test("schema authoring is keyboard-operable and announces a save", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openSchemas(page);

  await expect(page.getByText("Editing schema")).toBeVisible();
  await expect(page.getByText("DerridAI scholarly default", { exact: true }).first()).toBeVisible();

  const builtInFields = page.locator("button.field-select");
  await expect(builtInFields).toHaveCount(2);
  await builtInFields.nth(1).focus();
  await page.keyboard.press("Enter");
  await expect(builtInFields.nth(1)).toHaveAttribute("aria-current", "true");
  await expect(page.locator(".field-inspector fieldset")).toBeDisabled();

  await page.getByRole("button", { name: "Duplicate", exact: true }).click();
  await expect(page.getByText("Not saved yet")).toBeVisible();

  const addField = page.getByRole("button", { name: "Add a field", exact: true }).first();
  await addField.click();
  const inspector = page.locator(".field-inspector");
  const fieldName = inspector.getByLabel("Field name", { exact: true });
  await expect(fieldName).toBeFocused();
  await fieldName.fill("new_field");
  await inspector.getByLabel("Label", { exact: true }).fill("New field");

  const selectedItem = page.locator(".field-list-item.selected");
  await expect(selectedItem.getByText("New field", { exact: true })).toBeVisible();

  await page.keyboard.press("Control+S");
  await expect(page.getByRole("status").filter({ hasText: "Schema saved." })).toBeVisible();
  await expect(page).toHaveURL(/schema=scholarly-copy/);

  await page.getByRole("tab", { name: "Prompt groups" }).click();
  await expect(page.getByLabel("Group", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Fields" }).click();

  await page.getByRole("button", { name: "Add a field", exact: true }).first().click();
  const currentItem = page.locator(".field-list-item.selected");
  await currentItem.getByRole("button", { name: "Remove field" }).click();
  await expect(page.locator("button.field-select[aria-current='true']")).toBeFocused();

  await expectAxeClean(page);
});

test("schema workspace reflows at 320px with WCAG text spacing", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 760 });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await openSchemas(page);
  await page.evaluate(() => {
    document.documentElement.dataset.colorScheme = "dark";
    const style = document.createElement("style");
    style.dataset.testTextSpacing = "true";
    style.textContent = `
      .schemas-page * {
        letter-spacing: 0.12em !important;
        word-spacing: 0.16em !important;
        line-height: 1.5 !important;
      }
    `;
    document.head.append(style);
  });

  await page.getByRole("button", { name: "Duplicate", exact: true }).click();
  await page.getByRole("button", { name: "Add a field", exact: true }).first().click();
  await expect(page.locator(".field-inspector")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save schema" })).toBeVisible();

  expect(
    await page.locator(".schemas-page").evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
  ).toBe(true);
  await expectAxeClean(page);
});

test("schema workspace remains structured in forced colors and increased contrast", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.emulateMedia({ forcedColors: "active", reducedMotion: "reduce" });
  await openSchemas(page);
  await page.evaluate(() => {
    document.documentElement.dataset.contrast = "more";
  });

  await page.getByRole("button", { name: "Duplicate", exact: true }).click();
  await page.getByRole("button", { name: "Add a field", exact: true }).first().click();
  const focused = page.locator(".field-inspector").getByLabel("Field name", { exact: true });
  await expect(focused).toBeFocused();

  const focusGeometry = await focused.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      top: rect.top,
      bottom: rect.bottom,
      viewportHeight: window.innerHeight,
    };
  });
  expect(focusGeometry.top).toBeGreaterThanOrEqual(0);
  expect(focusGeometry.bottom).toBeLessThanOrEqual(focusGeometry.viewportHeight);
  await expectAxeClean(page);
});

test("French schema authoring keeps long translated labels usable", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 820 });
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await openSchemas(page, { french: true });

  await expect(page.locator("html")).toHaveAttribute("lang", "fr-CA");
  await expect(page.getByRole("heading", { name: "Schémas de métadonnées" })).toBeVisible();
  await expect(page.getByText("Schéma en cours de modification")).toBeVisible();
  await page.getByRole("button", { name: "Dupliquer", exact: true }).click();
  await page.getByRole("button", { name: "Ajouter un champ", exact: true }).first().click();
  await expect(page.getByText("Configuration du champ")).toBeVisible();

  expect(
    await page.locator(".schemas-page").evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
  ).toBe(true);
  await expectAxeClean(page);
});
