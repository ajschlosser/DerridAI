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

import { beforeAll, describe, expect, it } from "vitest";
import "../../src/runtime/runtimeBridge";
import { decorateDisabledControls } from "../../src/domain/disabledControls";
import { setTranslationDictionary } from "../../src/domain/sharedTranslate";

describe("disabled control reasons", () => {
  beforeAll(() => {
    setTranslationDictionary("fr-CA", {
      "runtime.disabled.first_page": "Vous êtes déjà sur la première page.",
      "runtime.disabled.unavailable": "Indisponible pour l'instant.",
    });
  });

  it("explains a disabled control in the active locale", () => {
    document.body.innerHTML = `<div id="root"><button disabled data-page="x:first">«</button><button disabled id="other">x</button></div>`;
    decorateDisabledControls(document.querySelector("#root")!);
    expect(document.querySelector<HTMLButtonElement>("[data-page]")!.title).toBe(
      "Vous êtes déjà sur la première page.",
    );
    expect(document.querySelector<HTMLButtonElement>("#other")!.title).toBe(
      "Indisponible pour l'instant.",
    );
  });
});
