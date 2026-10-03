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
import { firstValidationRecordId } from "../../src/features/corpus-builder/domain/publicationReadiness";

describe("Corpus Builder publication readiness targeting", () => {
  it("prefers explicit validation issues with record ids", () => {
    expect(
      firstValidationRecordId({
        validation: {
          validation_issues: [{ record_id: "record-explicit" }],
          metadata_schema_errors: [{ record_id: "record-schema" }],
        },
      } as any),
    ).toBe("record-explicit");
  });

  it("falls back through structured validation families before citation errors", () => {
    expect(
      firstValidationRecordId({
        validation: {
          relationship_errors: [{ record_id: "record-relationship" }],
          citation_errors: ["record-citation"],
        },
      } as any),
    ).toBe("record-relationship");
  });

  it("uses citation errors as the final record-target fallback", () => {
    expect(
      firstValidationRecordId({
        validation: { citation_errors: ["record-citation"] },
      } as any),
    ).toBe("record-citation");
  });

  it("returns an empty target when validation has no record identity", () => {
    expect(firstValidationRecordId({ validation: {} } as any)).toBe("");
  });
});
