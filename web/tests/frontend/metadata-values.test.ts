import { describe, expect, it } from "vitest";
import { isPlaceholderValue, usableOptions } from "../../src/domain/metadataValues";
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
});
