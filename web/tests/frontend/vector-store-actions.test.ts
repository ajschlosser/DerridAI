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
import {
  openCollectionCreationWizard,
  registerVectorStoreActions,
  triggerUpsertQueue,
} from "../../src/domain/vectorStoreActions";

describe("vectorStoreActions facade", () => {
  afterEach(() => registerVectorStoreActions(null));

  it("forwards arguments and results to the registered implementation", () => {
    const wizard = vi.fn().mockReturnValue("opened");
    registerVectorStoreActions({ openCollectionCreationWizard: wizard });
    expect(openCollectionCreationWizard({ defaultProvider: "ollama" })).toBe("opened");
    expect(wizard).toHaveBeenCalledWith({ defaultProvider: "ollama" });
  });

  it("fails loudly when called before registration", () => {
    expect(() => triggerUpsertQueue()).toThrow(/not ready/);
  });
});
