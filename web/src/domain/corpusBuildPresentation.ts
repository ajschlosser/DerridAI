// Copyright 2026 Aaron John Schlosser, PhD.
import type { CorpusBuild } from "../api/pdfCorpus";

/** Missing or malformed counters must not acquire a fabricated numeric value. */
function count(value: unknown): number | null {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : null;
}

export function metadataTaskProgress(build: Partial<CorpusBuild>) {
  const total = count(build.metadata_tasks_total);
  const complete = count(build.metadata_tasks_completed);
  const failed = count(build.metadata_tasks_failed);
  const skipped = count(build.metadata_tasks_skipped);
  const running = count(build.metadata_tasks_running);
  const queued = count(build.metadata_tasks_queued);
  // The server counts current family states, not attempts. Settlement includes failures.
  const settled = complete !== null && failed !== null && skipped !== null
    ? complete + failed + skipped : null;
  const inconsistent = total !== null && (
    [complete, failed, skipped, running, queued].some(value => value !== null && value > total)
    || (settled !== null && settled + (running ?? 0) + (queued ?? 0) > total)
  );
  const determinate = total !== null && total > 0 && settled !== null && !inconsistent;
  return { total, complete, failed, skipped, running, queued, settled, inconsistent, determinate,
    fraction: determinate ? settled / total : null };
}

/** Independent issue subqueues overlap; expose them without summing them. */
export function corpusRecordCounts(build: Partial<CorpusBuild>) {
  const queues = build.review_queue_counts;
  return {
    total: count(build.record_count), accepted: count(build.accepted_count), rejected: count(build.rejected_count),
    ready: count(queues?.ready), preparing: count(queues?.preparing), issues: count(queues?.issues),
    metadata: count(queues?.metadata), topology: count(queues?.topology), source: count(queues?.source),
  };
}

/** Group a narrow display format; grouping alone never establishes record identity. */
export function groupBuildWarnings(warnings: readonly string[]) {
  const groups = new Map<string, {key:string;label:string;messages:string[]}>();
  for (const message of warnings) {
    const match = /^[A-Za-z0-9][A-Za-z0-9_-]*: ([a-z_]+ metadata failed \([a-z_]+\); review required\.)$/.exec(message);
    const label = match?.[1] ?? message;
    const key = `${match ? "metadata" : "raw"}:${label}`;
    const existing = groups.get(key);
    if (existing) existing.messages.push(message);
    else groups.set(key, {key,label,messages:[message]});
  }
  return [...groups.values()];
}

/** A warning supplies only a candidate ID. Current structured issues establish build membership. */
export function currentWarningRecordIds(messages:readonly string[], summary:CorpusBuild['metadata_issue_summary']):string[]{
  const current=new Set([...(summary?.issues||[]),...(summary?.records||[])].map(issue=>issue.record_id).filter((id):id is string=>typeof id==='string'&&id.length>0));
  const ids=new Set<string>();
  for(const message of messages){
    const match=/^([A-Za-z0-9][A-Za-z0-9_-]*): [a-z_]+ metadata failed \([a-z_]+\); review required\.$/.exec(message);
    if(match&&current.has(match[1]))ids.add(match[1]);
  }
  return [...ids];
}
