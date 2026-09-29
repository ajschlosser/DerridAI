// Copyright 2026 Aaron John Schlosser, PhD.
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

    const quick = apiRequest("/api/quick").catch((error: Error) => error);
    const slow = apiRequest("/api/slow", { timeoutMs: 120_000 }).catch((error: Error) => error);
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
