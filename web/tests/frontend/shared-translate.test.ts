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

import { afterEach, describe, expect, it, vi } from "vitest";
import { toast } from "../../src/composables/notifications";
import { copyCitation } from "../../src/domain/clipboardCopy";
import { setTranslationDictionary, tr, trf } from "../../src/domain/sharedTranslate";
import { state } from "../../src/domain/sharedUrlState";

vi.mock("../../src/composables/notifications", () => ({ toast: vi.fn() }));

describe("shared translations", () => {
  afterEach(() => {
    state.translations = { locale: "en-US", dictionary: {}, base: {} };
    vi.unstubAllGlobals();
  });

  it("reads the dictionary the runtime writes, and fills placeholders", () => {
    state.translations = { locale: "fr-CA", dictionary: { "x.key": "Copié {label}" }, base: {} };
    expect(trf("x.key", { label: "fiche" })).toBe("Copié fiche");
  });

  it("setTranslationDictionary writes the slice that tr reads, with the locale info", () => {
    setTranslationDictionary(
      "fr-CA",
      { "x.key": "Bonjour" },
      { "x.key": "Hello" },
      { name: "Français" },
    );
    expect(tr("x.key")).toBe("Bonjour");
    expect(state.translations.locale).toBe("fr-CA");
    expect(state.translations.info).toEqual({ name: "Français" });
    expect(state.translations.reverse.get("Hello")).toBe("x.key");
  });

  it("copyCitation reports the exact citation that reached the clipboard", async () => {
    const writeText = vi.fn(async (_text: string) => undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    await copyCitation({ document_author: "Derrida, Jacques", work: "Glas", year: "1974" });
    const text = writeText.mock.calls[0][0] as string;
    expect(text).toBeTruthy();
    expect(vi.mocked(toast).mock.calls.at(-1)?.[0]).toContain(text);
  });

  it("copyCitation surfaces a clipboard failure instead of swallowing it", async () => {
    vi.stubGlobal("navigator", {
      clipboard: {
        writeText: vi.fn(async () => {
          throw new Error("denied");
        }),
      },
    });
    await copyCitation({ work: "Glas" });
    expect(vi.mocked(toast).mock.calls.at(-1)?.[1]).toEqual({ tone: "danger" });
  });
});
