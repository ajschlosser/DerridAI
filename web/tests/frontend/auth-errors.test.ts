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
import { ApiError } from "../../src/api/http";
import { localizedAuthError, localizedLoginError } from "../../src/domain/authErrors";

const translations: Record<string, string> = {
  "auth.account_last_admin": "Il faut conserver un administrateur actif.",
  "auth.bootstrap_already_done": "L’administrateur initial existe. Connectez-vous.",
  "auth.invalid_credentials": "Identifiants incorrects.",
  "auth.network_error": "Serveur inaccessible.",
  "auth.operation_failed": "La demande a échoué.",
};

const translate = (key: string, fallback: string) => translations[key] ?? fallback;

describe("localizedAuthError", () => {
  it("translates known user and role API errors", () => {
    const error = new ApiError("HTTP 400 · English detail", 400, {
      detail: "At least one active administrator is required.",
    });

    expect(localizedAuthError(error, translate)).toBe("Il faut conserver un administrateur actif.");
  });

  it("localizes network failures without exposing technical details", () => {
    const error = new ApiError("Network error · internal-host", 0, null);

    expect(localizedAuthError(error, translate)).toBe("Serveur inaccessible.");
    expect(localizedAuthError(error, translate)).not.toContain("internal-host");
  });

  it("uses a translated safe fallback for unknown server errors", () => {
    const error = new ApiError("HTTP 500 · database path", 500, {
      detail: "database path",
    });

    expect(localizedAuthError(error, translate)).toBe("La demande a échoué.");
  });

  it("translates credential failures without treating them as expired sessions", () => {
    const error = new ApiError("HTTP 401", 401, { detail: "Invalid username or password." });
    expect(localizedLoginError(error, translate)).toBe("Identifiants incorrects.");
  });

  it("translates a bootstrap race into a sign-in instruction", () => {
    const error = new ApiError("HTTP 400", 400, {
      detail: "Initial administrator has already been created.",
    });
    expect(localizedLoginError(error, translate)).toBe(
      "L’administrateur initial existe. Connectez-vous.",
    );
  });
});
