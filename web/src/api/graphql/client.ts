/* Copyright 2026 Aaron John Schlosser, PhD. */
// Minimal typed GraphQL client for the read-only cELF façade (docs/GRAPHQL.md). Commands stay
// on REST. Any `errors` entry fails the request, even with HTTP 200: there is no partial-data
// policy yet, so a half-answered provenance read is never shown as complete.
import { apiRequest } from "../http";
import { operations, type OperationName } from "./operations";
import type { OperationResults, OperationVariables } from "./types";

export const GRAPHQL_ENDPOINT = "/api/graphql";

export interface GraphQLErrorEntry {
  message: string;
  path?: Array<string | number>;
  extensions?: Record<string, unknown>;
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
}

interface GraphQLResponse<TData> {
  data?: TData | null;
  errors?: GraphQLErrorEntry[];
}

export async function graphqlRequest<TData, TVariables extends object>(
  query: string,
  variables: TVariables,
  operationName: string,
): Promise<TData> {
  const response = await apiRequest<GraphQLResponse<TData>>(GRAPHQL_ENDPOINT, {
    method: "POST",
    body: JSON.stringify({ query, variables, operationName }),
  });
  if (response.errors?.length) throw new GraphQLRequestError(operationName, response.errors);
  if (response.data == null) throw new GraphQLRequestError(operationName, []);
  return response.data;
}

/** Run one of the checked-in operations by name, with its declared result and variable types. */
export function runOperation<Name extends OperationName>(
  name: Name,
  variables: OperationVariables[Name],
): Promise<OperationResults[Name]> {
  return graphqlRequest<OperationResults[Name], OperationVariables[Name]>(
    operations[name],
    variables,
    name,
  );
}
