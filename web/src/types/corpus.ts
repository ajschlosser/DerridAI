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

export interface RecordSizingPolicy {
  preferred_record_chars: number;
  record_length_tolerance: number;
  long_record_chars: number;
  absolute_record_chars: number;
}

export type ReviewQueue =
  | "all"
  | "ready"
  | "issues"
  | "metadata"
  | "topology"
  | "source"
  | "accepted"
  | "rejected";
