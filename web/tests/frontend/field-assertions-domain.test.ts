/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  assertionConflict,
  assertionHistory,
  currentFieldAssertions,
} from "../../src/domain/fieldAssertions";

const record = {
  current_field_assertions: { "derridai.speaker": "a2" },
  field_assertions: {
    "derridai.speaker": [
      {
        assertion_id: "a1",
        record_revision: 1,
        field_id: "derridai.speaker",
        field_name: "speaker",
        value: "Levinas",
        derivation_method: "model",
        evaluation_status: "value_supported",
        authority_status: "unreviewed",
        value_status: "present",
        confidence: 0.61,
        evidence: [{ block_id: "b1" }],
        model: "small-model",
        created_at: "2026-09-25T10:00:00Z",
      },
      {
        assertion_id: "a2",
        record_revision: 2,
        field_id: "derridai.speaker",
        field_name: "speaker",
        value: "Derrida",
        derivation_method: "model",
        evaluation_status: "value_supported",
        authority_status: "human_confirmed",
        value_status: "present",
        confidence: 0.82,
        evidence: [{ block_id: "b2" }],
        actor: "reviewer",
        model: "small-model",
        supersedes_assertion_id: "a1",
        created_at: "2026-09-25T10:05:00Z",
      },
    ],
  },
};

describe("canonical FieldAssertion presentation", () => {
  it("uses the selected canonical assertion and preserves model provenance after confirmation", () => {
    const [current] = currentFieldAssertions(record);
    expect(current.assertion_id).toBe("a2");
    expect(current.derivation_method).toBe("model");
    expect(current.authority_status).toBe("human_confirmed");
    expect(current.confidence).toBe(0.82);
    expect(current.evidence).toEqual([{ block_id: "b2" }]);
    expect(current.actor).toBe("reviewer");
  });

  it("retains the complete field history", () => {
    expect(assertionHistory(record, "speaker").map((item) => item.assertion_id)).toEqual([
      "a1",
      "a2",
    ]);
  });

  it("surfaces distinct retained values as disagreement rather than overwriting history", () => {
    const conflict = assertionConflict(record, "speaker");
    expect(conflict?.current?.value).toBe("Derrida");
    expect(conflict?.alternatives.map((item) => item.value)).toEqual(["Levinas"]);
    expect(conflict?.disputed).toBe(false);
  });

  it("marks authority disputes independently from retained alternatives", () => {
    const disputed = structuredClone(record);
    disputed.field_assertions["derridai.speaker"][1].authority_status = "disputed";
    expect(assertionConflict(disputed, "speaker")?.disputed).toBe(true);
  });

  it("does not treat identical historical values as a semantic conflict", () => {
    const same = structuredClone(record);
    same.field_assertions["derridai.speaker"][0].value = "Derrida";
    expect(assertionConflict(same, "speaker")?.alternatives).toEqual([]);
  });
});
