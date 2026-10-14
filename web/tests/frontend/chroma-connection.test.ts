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
import { chromaIdentity, parseChromaHttpUrl } from "../../src/domain/chromaConnection";

describe("chroma connection URL parsing", () => {
  it("strips API version suffixes and rejects credentials in the URL", () => {
    expect(parseChromaHttpUrl("https://chroma.example:8000/api/v2").display).toBe(
      "https://chroma.example:8000",
    );
    expect(parseChromaHttpUrl("http://chroma:8000/").ssl).toBe(false);
    expect(() => parseChromaHttpUrl("chroma:8000")).toThrow("url-invalid");
    expect(() => parseChromaHttpUrl("http://user:secret@chroma:8000")).toThrow("url-credentials");
  });

  it("never puts a token into the identity label", () => {
    expect(chromaIdentity("http", undefined, "http://chroma:8000")).toBe(
      "Chroma server · http://chroma:8000",
    );
    expect(chromaIdentity("embedded", "./data/chroma")).toBe("Local Chroma · ./data/chroma");
  });
});
