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

import { apiRequest } from "../../src/api/http";

/** A fetch that never settles on its own, only when its signal aborts. */
function hangingFetch() {
  return vi.fn(
    (_path: string, init: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init.signal?.addEventListener("abort", () =>
          reject(new DOMException("aborted", "AbortError")),
        );
      }),
  );
}

describe("apiRequest timeouts", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("lets long source ingestion outlive the 30s default instead of aborting it", async () => {
    vi.useFakeTimers();
    const fetchMock = hangingFetch();
    vi.stubGlobal("fetch", fetchMock);

    const quick = apiRequest<never>("/api/quick").catch((error: Error) => error);
    const slow = apiRequest<never>("/api/slow", { timeoutMs: 120_000 }).catch(
      (error: Error) => error,
    );
    let slowSettled = false;
    void slow.then(() => (slowSettled = true));

    await vi.advanceTimersByTimeAsync(30_000);
    expect((await quick).message).toContain("timed out after 30s");
    expect(slowSettled).toBe(false);
    expect(fetchMock.mock.calls[1][1]).not.toHaveProperty("timeoutMs");

    await vi.advanceTimersByTimeAsync(90_000);
    expect((await slow).message).toContain("timed out after 120s");
  });
});
