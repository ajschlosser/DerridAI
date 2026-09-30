/* Copyright 2026 Aaron John Schlosser, PhD. */
// Typed access to the served pipeline catalog contract for stories and tests.
// The JSON is exported from the API and a backend test keeps it identical.
import contract from "./pipelineCatalogContract.json";
import type {
  PipelinePurpose,
  PipelineStrategy,
  PipelineWorkflowVocabulary,
} from "../../../types/pipelines";

export const contractPurposes = contract.purposes as unknown as PipelinePurpose[];
export const contractVocabulary = contract.vocabulary as unknown as PipelineWorkflowVocabulary;
export const contractStrategies = contract.strategies as unknown as PipelineStrategy[];

export function contractStrategy(strategyId: string): PipelineStrategy {
  const strategy = contractStrategies.find((item) => item.strategy_id === strategyId);
  if (!strategy) throw new Error(`Unknown strategy in catalog contract: ${strategyId}`);
  return strategy;
}

export function contractPurpose(purposeId: string): PipelinePurpose {
  const purpose = contractPurposes.find((item) => item.purpose_id === purposeId);
  if (!purpose) throw new Error(`Unknown purpose in catalog contract: ${purposeId}`);
  return purpose;
}
