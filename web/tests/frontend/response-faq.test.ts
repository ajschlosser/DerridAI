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

import { describe, expect, it, vi } from "vitest";
import { createResponseFaq } from "../../src/domain/responseFaq";
import {
  gradeRagResponse,
  prepareRagRerun,
  registerOperationsPanelHooks,
} from "../../src/domain/operationsPanelHooks";

function build() {
  const deps = {
    api: vi.fn(async () => ({ records: [] })),
    canAccessPage: vi.fn(() => true),
    tr: (key: string) => key,
    gradeRagResponse: vi.fn(),
    prepareRagRerun: vi.fn(),
  };
  return { deps, faq: createResponseFaq(deps) };
}

describe("createResponseFaq", () => {
  it("bounds paging and trims the query", async () => {
    const { deps, faq } = build();
    await faq.getResponseFaqPage({ limit: 5000, offset: -3, query: "  trace " });
    expect(deps.api).toHaveBeenCalledWith(
      "/api/response-cache/records?limit=1000&offset=0&query=trace",
    );
  });

  it("refuses without faq access", async () => {
    const { deps, faq } = build();
    deps.canAccessPage.mockReturnValue(false);
    await expect(faq.getResponseFaqPage()).rejects.toThrow("permissions.faq_denied");
  });

  it("grades with the stored response and reruns with its request", () => {
    const { deps, faq } = build();
    faq.gradeResponseFaqRecord({ record_id: "r1", question: "q", text: "a", provider: "p" });
    expect(deps.gradeRagResponse).toHaveBeenCalledWith(
      expect.objectContaining({ responseRecordId: "r1", question: "q", answer: "a", evidence: [] }),
    );
    faq.rerunResponseFaqRecord({ rag_request: { prompt: "q" } });
    expect(deps.prepareRagRerun).toHaveBeenCalledWith({ prompt: "q" });
  });
});

describe("operationsPanelHooks registration", () => {
  it("merges partial registrations and clears on null", () => {
    const grade = vi.fn(() => "g");
    const rerun = vi.fn(() => "r");
    registerOperationsPanelHooks({ gradeRagResponse: grade });
    registerOperationsPanelHooks({ prepareRagRerun: rerun });
    expect(gradeRagResponse({})).toBe("g");
    expect(prepareRagRerun({})).toBe("r");
    registerOperationsPanelHooks(null);
    expect(gradeRagResponse({})).toBeUndefined();
  });
});
