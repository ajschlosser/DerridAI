/* Copyright 2026 Aaron John Schlosser, PhD. */
// Typed GraphQL client for the read-only cELF façade (docs/GRAPHQL.md). Commands stay on REST.
// Documents are the generated TypedDocumentStrings in ./generated (npm run codegen), so result and
// variable types always match the server schema. Any `errors` entry fails the request, even with
// HTTP 200: a half-answered provenance read is never shown as complete.
import { apiRequest } from "../http";
import type { TypedDocumentString } from "./generated";

export const GRAPHQL_ENDPOINT = "/api/graphql";

/** Stable codes the server puts in `extensions.code` (app/graphql/errors.py). */
export type GraphQLErrorCode = "FORBIDDEN" | "NOT_FOUND" | "BAD_REQUEST" | "UNAVAILABLE";

export interface GraphQLErrorEntry {
  message: string;
  path?: Array<string | number>;
  extensions?: { code?: GraphQLErrorCode | string; [key: string]: unknown };
}

export class GraphQLRequestError extends Error {
  errors: GraphQLErrorEntry[];
  operationName: string;
  constructor(operationName: string, errors: GraphQLErrorEntry[]) {
    super(errors.map((error) => error.message).join("; ") || `${operationName} failed`);
    this.name = "GraphQLRequestError";
    this.errors = errors;
    this.operationName = operationName;
  }
  /** Whether any error carries this code (branch on codes, never on localized messages). */
  hasCode(code: GraphQLErrorCode): boolean {
    return this.errors.some((error) => error.extensions?.code === code);
  }
}

interface GraphQLResponse<TData> {
  data?: TData | null;
  errors?: GraphQLErrorEntry[];
}

export interface ExecuteOptions {
  /** Abort a superseded request (for example when the reviewer moves to another page). */
  signal?: AbortSignal;
}

const OPERATION_NAME = /\b(?:query|mutation|subscription)\s+([_A-Za-z][_0-9A-Za-z]*)/;

export function operationNameOf(document: string): string {
  return OPERATION_NAME.exec(document)?.[1] ?? "";
}

/** Whether an error only means a request was deliberately cancelled. */
export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException
    ? error.name === "AbortError"
    : (error as { name?: string } | null)?.name === "AbortError";
}

const READ_CACHE_TTL_MS = 1500;
const readCache = new Map<string, { expiresAt: number; value: unknown }>();
const pendingReads = new Map<string, Promise<unknown>>();
let cacheEpoch = 0;

function clone<T>(value: T): T {
  if (typeof structuredClone === "function") return structuredClone(value);
  return JSON.parse(JSON.stringify(value)) as T;
}

/** Invalidate read projections after a realtime event or an authenticated mutation. */
export function clearGraphQLReadCache(): void {
  cacheEpoch += 1;
  readCache.clear();
  pendingReads.clear();
}

export function execute<TResult, TVariables>(
  document: TypedDocumentString<TResult, TVariables>,
  variables: TVariables,
  options: ExecuteOptions = {},
): Promise<TResult> {
  const query = document.toString();
  const operationName = operationNameOf(query);
  const key = `${operationName}:${JSON.stringify(variables)}`;
  const cached = readCache.get(key);
  if (cached && cached.expiresAt > Date.now())
    return Promise.resolve(clone(cached.value) as TResult);
  const pending = pendingReads.get(key);
  if (pending) return pending.then((value) => clone(value) as TResult);

  const requestEpoch = cacheEpoch;
  const request = apiRequest<GraphQLResponse<TResult>>(GRAPHQL_ENDPOINT, {
    method: "POST",
    body: JSON.stringify({ query, variables, operationName }),
    signal: options.signal,
  })
    .then((response) => {
      if (response.errors?.length) throw new GraphQLRequestError(operationName, response.errors);
      if (response.data == null) throw new GraphQLRequestError(operationName, []);
      const value = response.data;
      if (requestEpoch === cacheEpoch)
        readCache.set(key, { expiresAt: Date.now() + READ_CACHE_TTL_MS, value: clone(value) });
      return value;
    })
    .finally(() => {
      if (pendingReads.get(key) === request) pendingReads.delete(key);
    });
  pendingReads.set(key, request);
  return request.then((value) => clone(value));
}
