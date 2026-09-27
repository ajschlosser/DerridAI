/* Copyright 2026 Aaron John Schlosser, PhD. */
import { afterEach, describe, expect, it, vi } from "vitest";
import { GraphQLRequestError, graphqlRequest, runOperation } from "../../src/api/graphql/client";
import { operations } from "../../src/api/graphql/operations";

function respond(body: unknown, status = 200) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

describe("graphql client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts the named operation and returns its data", async () => {
    const fetchMock = respond({ data: { celf_model: { specification_version: "1.0" } } });
    vi.stubGlobal("fetch", fetchMock);
    const data = await runOperation("CelfModel", {});
    expect(data.celf_model.specification_version).toBe("1.0");
    const [path, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(path).toBe("/api/graphql");
    expect(init.method).toBe("POST");
    const body = JSON.parse(String(init.body));
    expect(body.operationName).toBe("CelfModel");
    expect(body.query).toBe(operations.CelfModel);
  });

  it("treats GraphQL errors as failures even with HTTP 200", async () => {
    vi.stubGlobal(
      "fetch",
      respond({ data: null, errors: [{ message: "Administrator access required." }] }),
    );
    await expect(graphqlRequest("{ x }", {}, "X")).rejects.toBeInstanceOf(GraphQLRequestError);
    vi.stubGlobal(
      "fetch",
      respond({ data: { partial: true }, errors: [{ message: "one field failed" }] }),
    );
    await expect(graphqlRequest("{ x }", {}, "X")).rejects.toThrow("one field failed");
  });
});
