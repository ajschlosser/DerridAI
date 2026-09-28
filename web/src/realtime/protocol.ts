/* Copyright 2026 Aaron John Schlosser, PhD. */
// Realtime wire protocol, mirroring api/app/realtime/protocol.py (docs/REALTIME.md).

export const PROTOCOL_VERSION = 1;

export const CLOSE_CODES = {
  malformed: 4400,
  unauthenticated: 4401,
  forbidden: 4403,
  notFound: 4404,
  policy: 4408,
  internal: 1011,
} as const;

/** Bounded, text-free live-state summary of one background job (see job_realtime_summary). */
export interface JobSummary {
  id: string;
  type?: string;
  tool?: string;
  mode?: string;
  status?: string;
  stage?: string | null;
  stage_detail?: string;
  total?: number;
  completed?: number;
  failed?: number;
  cancel_requested?: boolean;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  store_name?: string;
  build_id?: string;
  warnings_count?: number;
  has_error?: boolean;
  pending_result_count?: number;
  [key: string]: unknown;
}

export interface CorpusBuildSummary {
  id: string;
  status?: string;
  raw_status?: string;
  stage?: string | null;
  stage_detail?: string;
  record_count?: number;
  review_count?: number;
  metadata_tasks_total?: number;
  metadata_tasks_completed?: number;
  metadata_tasks_failed?: number;
  metadata_tasks_skipped?: number;
  metadata_tasks_running?: number;
  metadata_tasks_queued?: number;
  progress?: number;
  [key: string]: unknown;
}

export interface ModelActivitySummary {
  calls_in_flight: number;
  task: string | null;
  provider: string | null;
  model: string | null;
}

/** One streamed Research draft delta (see rag.chat_complete(on_delta=)). */
export interface GenerationDelta {
  seq: number;
  delta: string;
  /** Text was dropped before this delta: stop appending and wait for the final answer. */
  gap: boolean;
  final: boolean;
}

/** Per-record metadata enrichment progress: identifiers and state only, never values or evidence. */
export interface CorpusRecordMetadataNote {
  record_id: string;
  family?: string;
  state?: "complete" | "failed" | "skipped" | "needs_review";
  field_ids?: string[];
  precedents_used?: number;
}

/** Bounded public state for `activity:gutenberg` (see gutenberg_catalogue.realtime_summary). */
export interface GutenbergActivitySummary {
  catalogue_status: string;
  archive_status: string;
  bytes_done: number;
  total_bytes: number | null;
  ready: boolean;
  search_ready: boolean;
  has_error: boolean;
}

interface Envelope<Type extends string, ResourceType extends string, Payload> {
  type: Type;
  event_id: number;
  resource_type: ResourceType;
  resource_id: string;
  revision: number;
  timestamp: string;
  payload: Payload;
}

export type JobEventType =
  | "job.snapshot"
  | "job.created"
  | "job.queued"
  | "job.started"
  | "job.stage_changed"
  | "job.progress"
  | "job.warning"
  | "job.needs_attention"
  | "job.cancelling"
  | "job.cancelled"
  | "job.completed"
  | "job.failed"
  | "job.removed";

export type CorpusEventType =
  | "corpus.build_changed"
  | "corpus.stage_changed"
  | "corpus.progress"
  | "corpus.metadata_progress"
  | "corpus.review_queue_changed";

export type ModelActivityEventType = "llm.started" | "llm.progress" | "llm.completed";

/** Ephemeral: never replayed after a reconnect, and the first dropped under backpressure. */
export type GenerationEventType = "llm.token";
export type CorpusRecordEventType =
  | "corpus.record_started"
  | "corpus.field_checked"
  | "corpus.record_completed";
export type ActivityEventType = "activity.changed";

export type JobEvent = Envelope<
  JobEventType,
  "job",
  { job: JobSummary; previous_status?: string | null }
>;
export type CorpusBuildEvent = Envelope<
  CorpusEventType,
  "corpus_build",
  { build: CorpusBuildSummary }
>;
export type ModelActivityEvent = Envelope<
  ModelActivityEventType,
  "corpus_build",
  { activity: ModelActivitySummary }
>;
/** Streamed Research draft text, delivered on `job:<id>` only (see llm.token). */
export type GenerationEvent = Envelope<GenerationEventType, "job", { generation: GenerationDelta }>;
export type CorpusRecordEvent = Envelope<
  CorpusRecordEventType,
  "corpus_build",
  { metadata: CorpusRecordMetadataNote }
>;
/** Background work that is not a tracked job, delivered on `activity:<kind>` only. */
export type ActivityEvent = Envelope<
  ActivityEventType,
  "activity",
  { activity: GutenbergActivitySummary | Record<string, unknown> }
>;

export type RealtimeEvent =
  | JobEvent
  | CorpusBuildEvent
  | ModelActivityEvent
  | GenerationEvent
  | CorpusRecordEvent
  | ActivityEvent;

export interface ReadyFrame {
  type: "connection.ready";
  payload: {
    protocol_version: number;
    connection_id: string;
    last_event_id: number;
    heartbeat_seconds: number;
    idle_timeout_seconds: number;
  };
}

export type ControlFrame =
  | ReadyFrame
  | { type: "connection.resync_required"; payload: { reason: string; last_event_id: number } }
  | { type: "connection.heartbeat"; payload: { last_event_id: number } }
  | { type: "pong"; payload: { last_event_id: number } }
  | {
      type: "subscription.updated";
      payload: {
        topics: string[];
        rejected: Array<{ topic: string; code: number; reason: string }>;
      };
    }
  | { type: "auth.permissions_changed"; payload: Record<string, never> };

export type ServerFrame = ControlFrame | RealtimeEvent;

export type ClientMessage =
  | { type: "subscribe"; topics: string[]; last_event_id?: number }
  | { type: "unsubscribe"; topics: string[] }
  | { type: "resync"; last_event_id?: number }
  | { type: "ping" };

export const TERMINAL_JOB_STATUSES = new Set(["completed", "failed", "cancelled"]);

export function isResourceEvent(frame: ServerFrame): frame is RealtimeEvent {
  return typeof (frame as RealtimeEvent).event_id === "number";
}

/** The subscription topics an event is delivered for (mirrors the server's topic model). */
export function topicsForEvent(event: RealtimeEvent): string[] {
  if (event.type === "llm.token") return [`job:${event.resource_id}`];
  if (event.resource_type === "job") return ["jobs", `job:${event.resource_id}`];
  if (event.resource_type === "activity") return [`activity:${event.resource_id}`];
  if (
    event.type === "corpus.record_started" ||
    event.type === "corpus.field_checked" ||
    event.type === "corpus.record_completed"
  ) {
    return [`corpus-build:${event.resource_id}`];
  }
  return ["corpus-builds", `corpus-build:${event.resource_id}`];
}
