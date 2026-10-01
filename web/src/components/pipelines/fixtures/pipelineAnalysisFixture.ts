/* Copyright 2026 Aaron John Schlosser, PhD. */
import type {
  PipelineAnalysis,
  PipelineStageWiring,
  PipelineWiringOption,
} from "../../../types/pipelines";

const runQuery: PipelineWiringOption = {
  kind: "run_input",
  name: "query",
  data_type: "query",
  upstream: true,
  possible: true,
};

/** Analysis of the three-stage draft a → b → c used by the editor tests. */
export function analysisFixture(overrides: Partial<PipelineAnalysis> = {}): PipelineAnalysis {
  const a: PipelineStageWiring = {
    inputs: [
      {
        port: "query",
        data_type: "query",
        required: true,
        multiple: false,
        explicit: false,
        status: "bound",
        sources: [
          {
            kind: "run_input",
            stage: null,
            output: null,
            name: "query",
            data_type: "query",
            via: "run_input",
            explicit: false,
            producer_enabled: true,
          },
        ],
        options: [runQuery],
      },
    ],
    outputs: [
      {
        name: "candidates",
        data_type: "candidate_set",
        consumers: [{ stage: "b", port: "candidates" }],
      },
    ],
  };
  const b: PipelineStageWiring = {
    inputs: [
      {
        port: "candidates",
        data_type: "candidate_set",
        required: true,
        multiple: true,
        explicit: false,
        status: "bound",
        sources: [
          {
            kind: "stage",
            stage: "a",
            output: "candidates",
            name: null,
            data_type: "candidate_set",
            via: "next",
            explicit: false,
            producer_enabled: true,
          },
        ],
        options: [
          {
            kind: "stage",
            stage: "a",
            output: "candidates",
            data_type: "candidate_set",
            upstream: true,
            possible: true,
          },
        ],
      },
    ],
    outputs: [
      {
        name: "candidates",
        data_type: "candidate_set",
        consumers: [{ stage: "c", port: "candidates" }],
      },
    ],
  };
  const c: PipelineStageWiring = {
    inputs: [{ ...b.inputs[0], sources: [{ ...b.inputs[0].sources[0], stage: "b" }] }],
    outputs: [{ name: "context", data_type: "context_packet", consumers: [] }],
  };
  return {
    validation: { valid: true, issues: [] },
    wiring: {
      stages: { a, b, c },
      run_inputs: [
        { name: "query", data_type: "query", consumers: [{ stage: "a", port: "query" }] },
      ],
    },
    complexity: {
      stages: [
        {
          stage_id: "a",
          strategy_id: "retrieve.chroma_similarity",
          time: "O(q + d·log N + k)",
          space: "O(k·d)",
          order: 1,
          order_id: "sublinear",
          driver: "embedding",
          variables: ["q", "d", "N", "k"],
          scales_with_scope: true,
          n_in: null,
          n_in_bounded: false,
          n_out: 500,
          n_out_bounded: true,
          model_calls: { formula: "1", max: 1 },
          conditional: false,
        },
        {
          stage_id: "b",
          strategy_id: "validate.provenance",
          time: "O(n)",
          space: "O(n)",
          order: 2,
          order_id: "linear_in_candidates",
          driver: "storage",
          variables: ["n"],
          scales_with_scope: false,
          n_in: 500,
          n_in_bounded: true,
          n_out: 500,
          n_out_bounded: true,
          model_calls: { formula: "0", max: 0 },
          conditional: false,
        },
        {
          stage_id: "c",
          strategy_id: "pack.evidence_context",
          time: "O(n·L)",
          space: "O(n·L)",
          order: 2,
          order_id: "linear_in_candidates",
          driver: "cpu",
          variables: ["n", "L"],
          scales_with_scope: false,
          n_in: 500,
          n_in_bounded: true,
          n_out: 1,
          n_out_bounded: true,
          model_calls: { formula: "0", max: 0 },
          conditional: false,
        },
      ],
      summary: {
        time_terms: ["O(n·L)", "O(n)"],
        dominant_stage_id: "a",
        dominant_time: "O(q + d·log N + k)",
        dominant_order_id: "sublinear",
        dominant_driver: "embedding",
        scales_with_scope: true,
        scope_stage_ids: ["a"],
        candidate_bound: 500,
        candidates_request_bound: false,
        model_calls: { embedding: { stage_ids: ["a"], max_calls: 1, calls_known: true } },
      },
    },
    latency: {
      stages: [
        {
          stage_id: "a",
          strategy_id: "retrieve.chroma_similarity",
          basis: "this_pipeline",
          conditional: false,
          reach: 1,
          share: 0.8,
          samples: 12,
          p50_ms: 400,
          p90_ms: 700,
          reliable: true,
          median_ms_per_input: null,
          by_model: [],
          observed_scaling: null,
        },
        {
          stage_id: "b",
          strategy_id: "validate.provenance",
          basis: "strategy",
          conditional: false,
          reach: 1,
          share: 0.1,
          samples: 3,
          p50_ms: 50,
          p90_ms: 80,
          reliable: false,
          median_ms_per_input: 0.1,
          by_model: [],
          observed_scaling: null,
        },
        {
          stage_id: "c",
          strategy_id: "pack.evidence_context",
          basis: "none",
          conditional: false,
          reach: 1,
          share: 0,
          samples: 0,
          median_ms_per_input: null,
          by_model: [],
          observed_scaling: null,
        },
      ],
      typical_ms: 450,
      slow_ms: 780,
      critical_path_ms: 450,
      critical_path_slow_ms: 780,
      critical_path: ["a", "b", "c"],
      slowest_stage_id: "a",
      coverage: 0.667,
      reliable: false,
      observed_runs: { samples: 12, p50_ms: 1900, p90_ms: 2600, reliable: true },
      observed_pipeline_runs: { samples: 12, p50_ms: 1900, p90_ms: 2600, reliable: true },
    },
    sample: { runs: 120, pipeline_runs: 12, exact_runs: 12 },
    ...overrides,
  };
}
