/* Copyright 2026 Aaron John Schlosser, PhD. */
// Every GraphQL document the frontend sends lives in a .graphql file beside this one, so
// scripts/check_frontend_graphql_contract.py can validate each against the live schema.
import CelfModel from "./CelfModel.graphql?raw";
import RecordGraph from "./RecordGraph.graphql?raw";
import SimilarValidatedClaims from "./SimilarValidatedClaims.graphql?raw";

export const operations = {
  CelfModel,
  RecordGraph,
  SimilarValidatedClaims,
} as const;

export type OperationName = keyof typeof operations;
