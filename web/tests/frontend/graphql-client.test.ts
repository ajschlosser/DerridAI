/* Copyright 2026 Aaron John Schlosser, PhD. */
import { afterEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";
import {
  clearGraphQLReadCache,
  GraphQLRequestError,
  execute,
  isAbortError,
  operationNameOf,
} from "../../src/api/graphql/client";
import {
  CelfModelDocument,
  CorpusReviewQueueDocument,
  type CorpusReviewQueueQueryVariables,
} from "../../src/api/graphql/generated";
import { useQuery } from "../../src/api/graphql/useQuery";

function respond(body: unknown, status = 200) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

function lastBody(fetchMock: ReturnType<typeof vi.fn>) {
  const calls = fetchMock.mock.calls as unknown as Array<[string, RequestInit]>;
  return JSON.parse(String(calls[calls.length - 1][1].body));
}

describe("graphql client", () => {
  afterEach(() => {
    clearGraphQLReadCache();
    vi.unstubAllGlobals();
  });

  it("posts a generated document with its operation name and returns typed data", async () => {
    const fetchMock = respond({ data: { celf_model: { specification_version: "1.0" } } });
    vi.stubGlobal("fetch", fetchMock);
    const data = await execute(CelfModelDocument, {});
    expect(data.celf_model.specification_version).toBe("1.0");
    const [path, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(path).toBe("/api/graphql");
    expect(init.method).toBe("POST");
    expect(lastBody(fetchMock)).toMatchObject({
      operationName: "CelfModel",
      query: CelfModelDocument.toString(),
    });
  });

  it("sends the fragments a document spreads along with it", () => {
    const query = CorpusReviewQueueDocument.toString();
    expect(operationNameOf(query)).toBe("CorpusReviewQueue");
    expect(query).toContain("fragment CorpusQueueRowFields on CorpusQueueRow");
  });

  it("treats GraphQL errors as failures even with HTTP 200 and exposes their codes", async () => {
    vi.stubGlobal(
      "fetch",
      respond({
        data: null,
        errors: [{ message: "Administrator access required.", extensions: { code: "FORBIDDEN" } }],
      }),
    );
    const failure = await execute(CelfModelDocument, {}).catch((error) => error);
    expect(failure).toBeInstanceOf(GraphQLRequestError);
    expect((failure as GraphQLRequestError).hasCode("FORBIDDEN")).toBe(true);
    vi.stubGlobal(
      "fetch",
      respond({ data: { partial: true }, errors: [{ message: "one field failed" }] }),
    );
    await expect(execute(CelfModelDocument, {})).rejects.toThrow("one field failed");
  });

  it("lets a caller cancel a superseded request without recording an HTTP error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_path: string, init: RequestInit) =>
          new Promise((_resolve, reject) =>
            init.signal?.addEventListener("abort", () =>
              reject(new DOMException("aborted", "AbortError")),
            ),
          ),
      ),
    );
    const controller = new AbortController();
    const pending = execute(CelfModelDocument, {}, { signal: controller.signal });
    controller.abort();
    const error = await pending.catch((cause) => cause);
    expect(isAbortError(error)).toBe(true);
  });

  it("cancels only one consumer of a shared read", async () => {
    let respond!: (value: Response) => void;
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => (respond = resolve)));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    const first = execute(CelfModelDocument, {}, { signal: controller.signal });
    const second = execute(CelfModelDocument, {});
    const cancelled = first.catch((error: unknown) => error);
    controller.abort();
    expect(isAbortError(await cancelled)).toBe(true);
    respond(
      new Response(JSON.stringify({ data: { celf_model: { specification_version: "1.0" } } })),
    );
    expect((await second).celf_model.specification_version).toBe("1.0");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("useQuery", () => {
  afterEach(() => {
    clearGraphQLReadCache();
    vi.unstubAllGlobals();
  });

  const page = (rows: string[]) => ({
    corpus_build: {
      review_queue: {
        total: rows.length,
        offset: 0,
        limit: 50,
        queue_counts: {
          all: rows.length,
          ready: 0,
          preparing: 0,
          issues: 0,
          metadata: 0,
          topology: 0,
          source: 0,
          accepted: 0,
          rejected: 0,
          pending: rows.length,
        },
        items: rows.map((record_id) => ({ record_id })),
      },
    },
  });

  it("re-reads when variables change, keeps only the newest answer, and skips null variables", async () => {
    const resolvers: Array<(value: Response) => void> = [];
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => resolvers.push(resolve)));
    vi.stubGlobal("fetch", fetchMock);
    const offset = ref<number | null>(0);
    const scope = effectScope();
    const query = scope.run(() =>
      useQuery(CorpusReviewQueueDocument, {
        variables: () =>
          offset.value == null
            ? null
            : ({
                build_id: "b",
                offset: offset.value,
                limit: 50,
              } satisfies CorpusReviewQueueQueryVariables),
      }),
    )!;
    await nextTick();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    offset.value = 50;
    await nextTick();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    // The newer page answers first; the older, slower answer must not overwrite it.
    resolvers[1](new Response(JSON.stringify({ data: page(["rec-51"]) })));
    await vi.waitFor(() => expect(query.loading.value).toBe(false));
    resolvers[0](new Response(JSON.stringify({ data: page(["rec-1"]) })));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(query.data.value?.corpus_build.review_queue.items[0]?.record_id).toBe("rec-51");
    offset.value = null;
    await nextTick();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    scope.stop();
  });

  it("reports failures on error instead of throwing into the view", async () => {
    vi.stubGlobal(
      "fetch",
      respond({ data: null, errors: [{ message: "no", extensions: { code: "NOT_FOUND" } }] }),
    );
    const scope = effectScope();
    const query = scope.run(() => useQuery(CelfModelDocument, { variables: () => ({}) }))!;
    await vi.waitFor(() => expect(query.error.value).toBeInstanceOf(GraphQLRequestError));
    expect(query.data.value).toBeNull();
    scope.stop();
  });

  it("deduplicates in-flight reads and isolates cached results from callers", async () => {
    const fetchMock = respond({ data: { celf_model: { specification_version: "1.0" } } });
    vi.stubGlobal("fetch", fetchMock);
    const [first] = await Promise.all([
      execute(CelfModelDocument, {}),
      execute(CelfModelDocument, {}),
    ]);
    first.celf_model.specification_version = "mutated";
    const cached = await execute(CelfModelDocument, {});
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(cached.celf_model.specification_version).toBe("1.0");
  });

  it("does not reuse an invalidated in-flight read", async () => {
    const resolvers: Array<(value: Response) => void> = [];
    const fetchMock = vi.fn(
      () =>
        new Promise<Response>((done) => {
          resolvers.push(done);
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const first = execute(CelfModelDocument, {});
    clearGraphQLReadCache();
    const second = execute(CelfModelDocument, {});
    expect(fetchMock).toHaveBeenCalledTimes(2);
    resolvers[0](
      new Response(JSON.stringify({ data: { celf_model: { specification_version: "stale" } } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    resolvers[1](
      new Response(JSON.stringify({ data: { celf_model: { specification_version: "fresh" } } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await expect(first).resolves.toMatchObject({
      celf_model: { specification_version: "stale" },
    });
    await expect(second).resolves.toMatchObject({
      celf_model: { specification_version: "fresh" },
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
