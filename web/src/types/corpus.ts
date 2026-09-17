export interface CorpusSegmentationTelemetry {
  candidateCount?: number;
  deterministicSplits?: number;
  deterministicKeeps?: number;
  llmAdjudications?: number;
  llmBatchCalls?: number;
  llmSplits?: number;
  llmKeeps?: number;
  provisionalSplits?: number;
  sizeOptimizedSplits?: number;
  absoluteSafetySplits?: number;
  budgetSkipped?: number;
  classifierFailures?: number;
  reviewCount?: number;
}
