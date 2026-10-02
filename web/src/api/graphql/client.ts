/* Copyright 2026 Aaron John Schlosser, PhD. */
// Typed GraphQL client for the read-only cELF façade (docs/GRAPHQL.md). Commands stay on REST.
// Documents are the generated TypedDocumentStrings in ./generated (npm run codegen), so result and
// variable types always match the server schema. Any `errors` entry fails the request, even with
// HTTP 200: a half-answered provenance read is never shown as complete.
import { apiRequest } from "../http";
import type { TypedDocumentString } from "./generated";

export const GRAPHQL_ENDPOINT = "/api/graphql";

/** Stable codes the server puts in `extensions.code` (app/graphql/errors.py). */
export type GraphQLErrorCode =
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "BAD_REQUEST"
  | "UNAVAILABLE"
  | "STALE_QUEUE_CURSOR";

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
interface ReadScope {
  operationName: string;
  buildId?: string;
  recordIds?: readonly string[];
}
const readCache = new Map<string, { expiresAt: number; value: unknown; scope: ReadScope }>();
interface PendingRead {
  promise: Promise<unknown>;
  controller: AbortController;
  consumers: number;
  scope: ReadScope;
  valid: boolean;
}
const pendingReads = new Map<string, PendingRead>();
let cacheEpoch = 0;

export interface GraphQLReadInvalidation {
  operations?: readonly string[];
  buildId?: string;
  recordIds?: readonly string[];
}

/** Detach matching pending reads too: their late responses cannot repopulate the cache. */
export function invalidateGraphQLReads(filter: GraphQLReadInvalidation): void {
  function matches(scope: ReadScope) {
    return (
      (!filter.operations || filter.operations.includes(scope.operationName)) &&
      (!filter.buildId || filter.buildId === scope.buildId) &&
      (!filter.recordIds || scope.recordIds?.some((id) => filter.recordIds!.includes(id)))
    );
  }
  for (const [key, entry] of readCache) if (matches(entry.scope)) readCache.delete(key);
  for (const [key, entry] of pendingReads) {
    if (!matches(entry.scope)) continue;
    entry.valid = false;
    pendingReads.delete(key);
  }
}

function consume<TResult>(read: PendingRead, signal?: AbortSignal): Promise<TResult> {
  read.consumers += 1;
  return new Promise<TResult>((resolve, reject) => {
    let settled = false;
    function release() {
      if (settled) return false;
      settled = true;
      signal?.removeEventListener("abort", abort);
      read.consumers -= 1;
      return true;
    }
    function abort() {
      if (!release()) return;
      reject(new DOMException("aborted", "AbortError"));
      if (!read.consumers) read.controller.abort();
    }
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) abort();
    read.promise.then(
      (value) => {
        if (release()) resolve(clone(value) as TResult);
      },
      (error: unknown) => {
        if (release()) reject(error);
      },
    );
  });
}

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
  const scopedVariables = variables as { build_id?: string; record_ids?: string[] };
  const scope: ReadScope = {
    operationName,
    buildId: scopedVariables?.build_id,
    recordIds: scopedVariables?.record_ids,
  };
  if (options.signal?.aborted) return Promise.reject(new DOMException("aborted", "AbortError"));
  const cached = readCache.get(key);
  if (cached && cached.expiresAt > Date.now())
    return Promise.resolve(clone(cached.value) as TResult);
  const pending = pendingReads.get(key);
  if (pending && !pending.controller.signal.aborted)
    return consume<TResult>(pending, options.signal);

  const requestEpoch = cacheEpoch;
  const controller = new AbortController();
  const request = apiRequest<GraphQLResponse<TResult>>(GRAPHQL_ENDPOINT, {
    method: "POST",
    body: JSON.stringify({ query, variables, operationName }),
    signal: controller.signal,
  })
    .then((response) => {
      if (response.errors?.length) throw new GraphQLRequestError(operationName, response.errors);
      if (response.data == null) throw new GraphQLRequestError(operationName, []);
      const value = response.data;
      if (requestEpoch === cacheEpoch && read.valid && !controller.signal.aborted) {
        readCache.set(key, {
          expiresAt: Date.now() + READ_CACHE_TTL_MS,
          value: clone(value),
          scope,
        });
        for (const [cachedKey, entry] of readCache)
          if (entry.expiresAt <= Date.now()) readCache.delete(cachedKey);
        while (readCache.size > 128) {
          const oldest = readCache.keys().next().value;
          if (oldest === undefined) break;
          readCache.delete(oldest);
        }
      }
      return value;
    })
    .finally(() => {
      if (pendingReads.get(key)?.promise === request) pendingReads.delete(key);
    });
  const read: PendingRead = { promise: request, controller, consumers: 0, scope, valid: true };
  pendingReads.set(key, read);
  return consume<TResult>(read, options.signal);
}
