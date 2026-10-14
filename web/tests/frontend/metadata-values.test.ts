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

import { describe, expect, it } from "vitest";
import {
  isPlaceholderValue,
  usableListOptions,
  usableOptions,
  withoutTransportItems,
} from "../../src/domain/metadataValues";
import { metadataSuggestions } from "../../src/domain/metadataFieldRegistry";

describe("metadata values that are not answers", () => {
  it.each([
    "null",
    "None",
    " N/A ",
    "unknown",
    "",
    "The author of the current record",
    "the speaker",
    "Unknown author",
    "an unnamed speaker",
    "the narrator of this passage",
  ])("treats %j as a placeholder", (value) => expect(isPlaceholderValue(value)).toBe(true));
  it.each([
    "Jacques Derrida",
    "cities of refuge",
    "Anonymous",
    "The Author of Waverley",
    "speaker of the house",
    "hospitality",
  ])("keeps %j", (value) => expect(isPlaceholderValue(value)).toBe(false));
  it("never offers a placeholder as an option", () => {
    expect(
      usableOptions([
        "Derrida",
        "null",
        "the author of the current record",
        " Levinas ",
        "Derrida",
        4,
      ]),
    ).toEqual(["Derrida", "Levinas"]);
    expect(
      metadataSuggestions({ speaker: "null", persons: ["Derrida", "N/A", "the author"] }, [
        "speaker",
        "persons",
      ]),
    ).toEqual(["Derrida"]);
  });
  it("drops runtime JSON and source-block fragments from autocomplete", () => {
    expect(
      usableOptions([
        "Jacques Derrida",
        '"reason": "The quote describes a tension."',
        '["p00014-b0002"]',
        "p00014-b0002",
        '{"needs_review":true}',
      ]),
    ).toEqual(["Jacques Derrida"]);
    expect(
      usableListOptions([
        "hospitality, cosmopolitanism",
        '"block_ids": ["p00014-b0002"]',
        ["Levinas", "p00014-b0002"],
      ]),
    ).toEqual(["hospitality", "cosmopolitanism", "Levinas"]);
  });
});

describe("structured-output residue in list values", () => {
  const leaked = [
    "Balzac",
    "field_evidence_id-12b1b026d14aebb21198d716:p00001-b0001",
    "confidence_score_0.95",
    "The text presents a quote from Balzac's 'Lettres a l'Etrangere'.",
  ];

  it("reads a stored list up to its first residue item, and never offers the residue as an option", () => {
    expect(withoutTransportItems(leaked)).toEqual(["Balzac"]);
    expect(usableListOptions([leaked, ["Honoré de Balzac"]])).toEqual([
      "Balzac",
      "Honoré de Balzac",
    ]);
  });

  it("keeps real values that happen to begin like a key", () => {
    const values = ["Reason and faith", "Confidence", "Evidence"];
    expect(withoutTransportItems(values)).toEqual(values);
  });
});
