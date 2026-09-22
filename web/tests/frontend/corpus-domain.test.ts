import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import type { CorpusBuild, CorpusRecord } from '../../src/api/pdfCorpus';
import type { ReviewQueue } from '../../src/types/corpus';
import { recordIssueKinds, recordState } from '../../src/domain/corpusReview';
import { useCorpusBuildLifecycle } from '../../src/composables/useCorpusBuildLifecycle';

const record = (overrides: Partial<CorpusRecord> = {}): CorpusRecord => ({
  record_id: 'r1', text: 'Source passage', text_length: 14,
  source_block_ids: ['b1'], source_spans: [], ...overrides,
});
const build = (overrides: Partial<CorpusBuild> = {}): CorpusBuild => ({
  build_id: 'build', asset_id: 'asset', source_filename: 'source.pdf', source_sha256: 'sha',
  status: 'awaiting_review', stage: 'review', progress: .9, created_at: '', record_count: 3,
  accepted_count: 0, needs_review_count: 1, profile_id: 'derrida-scholarly-v12', ...overrides,
});

describe('record review domain', () => {
  it('uses explicit server issues over stale local reasons', () => {
    expect(recordIssueKinds(record({review_issue_codes: [], needs_review: true, review_reason: 'boundary'}))).toEqual([]);
    expect(recordIssueKinds(record({review_issue_codes: ['source', 'metadata', 'future-code']}))).toEqual(['source', 'metadata']);
  });
  it('keeps authoritative review state ahead of legacy flags', () => {
    expect(recordState(record({review_state: 'metadata', accepted: true}))).toBe('metadata');
    expect(recordState(record({accepted: true}))).toBe('accepted');
    expect(recordState(record({needs_review: true, review_reason: 'Split boundary requires review'}))).toBe('topology');
  });
});

describe('corpus lifecycle composable', () => {
  it('reacts to the build/review/finish cycle without treating enrichment as structural review', () => {
    const current = ref<CorpusBuild|null>(null), total = ref(0), queue = ref<ReviewQueue>('all');
    const view = useCorpusBuildLifecycle(current, total, queue);
    expect(view.showBuildConfiguration.value).toBe(true);
    current.value = build({status: 'running', stage: 'segmenting'});
    expect(view.reviewLocked.value).toBe(true);
    current.value.stage = 'enriching';
    expect(view.reviewLocked.value).toBe(false);
    expect(view.structuralReviewLocked.value).toBe(true);
    current.value.stage = 'metadata_enrichment_rerun';
    expect(view.reviewLocked.value).toBe(false);
    expect(view.structuralReviewLocked.value).toBe(true);
    current.value = build({accepted_count: 2, rejected_count: 1});
    expect(view.finishPhase.value).toBe(true);
    expect(view.showReviewWorkspace.value).toBe(false);
    queue.value = 'rejected';
    expect(view.showReviewWorkspace.value).toBe(true);
  });
  it('honors manifest review, resume eligibility, and authoritative queue counts', () => {
    const current = ref<CorpusBuild|null>(build({status: 'awaiting_manifest_review'}));
    const view = useCorpusBuildLifecycle(current, ref(3), ref<ReviewQueue>('all'));
    expect(view.hasRecordTopology.value).toBe(false);
    current.value = build({status: 'interrupted', resumable: true, review_queue_counts: {pending: 1, ready: 0, issues: 1}});
    expect(view.canResume.value).toBe(true);
    expect(view.pendingCount.value).toBe(1);
    expect(view.readyCount.value).toBe(0);
    current.value.status = 'running';
    expect(view.canResume.value).toBe(false);
  });
});
