import { apiRequest } from "./http";

export interface PdfAsset {
  asset_id: string;
  sha256: string;
  filename: string;
  created_at: string;
  page_count: number;
  block_count: number;
  ocr_pages: number;
  warnings: string[];
  metadata: Record<string, unknown>;
  pages?: Array<{pdf_page:number;printed_page_label?:string|null;printed_page_label_source?:string|null;width:number;height:number;block_ids?:string[];extraction_method?:string}>;
}

export interface CorpusBuild {
  build_id: string;
  asset_id: string;
  source_filename: string;
  source_sha256: string;
  status: string;
  stage: string;
  progress: number;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  record_count: number;
  needs_review_count: number;
  accepted_count: number;
  rejected_count?: number;
  model?: string | null;
  provider?: string | null;
  profile_id: string;
  schema_version?: string;
  segmentation_prompt_version?: string;
  metadata_prompt_version?: string;
  document_prompt_version?: string;
  validation?: {valid?:boolean;source_valid?:boolean;metadata_valid?:boolean;coverage?:number;missing_block_ids?:string[];duplicate_block_ids?:string[];text_fidelity_errors?:string[];source_order_errors?:string[];page_mapping_errors?:string[];printed_page_label_errors?:string[];metadata_evidence_errors?:Array<{record_id?:string;field?:string;reason?:string}>;metadata_schema_errors?:Array<{record_id?:string;reason?:string}>;citation_errors?:string[]};
  manifest?: Record<string, unknown>;
  manifest_revision?: number;
  manifest_confirmed_at?: string | null;
  manifest_confirmed_revision?: number | null;
  publication?: {publication_id:string;filename:string;sha256:string;record_count:number;created_at:string}|null;
  publication_status?: "unpublished"|"published";
  published_at?: string | null;
  error?: string | null;
  warnings?: string[];
  resumable?: boolean;
  boundary_count?: number;
  boundary_candidate_count?: number;
  segmentation_degraded?: boolean;
  segmentation_failed_windows?: number;
  segmentation_total_windows?: number;
  segmentation_recovered_windows?: number;
  segmentation_blocked?: boolean;
  retrying_segmentation?: boolean;
  segmentation_unresolved_regions?: Array<{after_block_id?:string;next_block_id?:string;left_block_id?:string;right_block_id?:string;start_block_id?:string;end_block_id?:string;reason?:string;kind?:string;[key:string]:unknown}>;
  segmentation_boundary_reviews?: Array<{after_block_id?:string;next_block_id?:string;reason?:string;kind?:string;[key:string]:unknown}>;
  boundary_review_count?: number;
  provisional_boundary_count?: number;
  boundary_deterministic_split_count?: number;
  boundary_deterministic_keep_count?: number;
  boundary_llm_adjudication_count?: number;
  boundary_llm_batch_call_count?: number;
  boundary_llm_split_count?: number;
  boundary_llm_keep_count?: number;
  boundary_budget_skipped_count?: number;
  boundary_classifier_failure_count?: number;
  topology_validation?: {valid?:boolean;issues?:string[];findings?:Array<{code:string;severity:string;record_id?:string|null;auto_repairable?:boolean;params?:Record<string,unknown>}>;record_count?:number;max_record_chars?:number;min_record_chars?:number;median_record_chars?:number;p10_record_chars?:number;p90_record_chars?:number;preferred_record_chars?:number;record_length_tolerance?:number;long_record_chars?:number;absolute_record_chars?:number;records_in_preferred_range?:number;records_over_preferred_range?:number;records_over_long_limit?:number;micro_record_count?:number};
  topology_quality?: {valid?:boolean;source_block_count?:number;used_source_block_count?:number;source_coverage?:number;source_order_valid?:boolean;source_conservation_valid?:boolean;record_count?:number;median_record_chars?:number;p10_record_chars?:number;p90_record_chars?:number;max_record_chars?:number;records_in_preferred_range?:number;records_over_preferred_range?:number;records_over_long_limit?:number;micro_record_count?:number;policy?:Record<string,number>};
  record_sizing_policy?: Record<string,number>;
  size_optimized_boundary_count?: number;
  absolute_safety_boundary_count?: number;
  long_exception_record_count?: number;
  metadata_completed?: number;
  metadata_total?: number;
  metadata_concurrency?: number;
  metadata_issue_summary?: {
    records_incomplete?:number; fields_unresolved?:number; by_field?:Record<string,number>; by_reason?:Record<string,number>; invalid_by_field?:Record<string,number>;
    auto_retry_records?:number; human_review_records?:number; auto_retry_fields?:number; human_review_fields?:number;
    issues?:Array<{record_id?:string;field?:string;issue_type?:string;retryable?:boolean;status?:string;reason?:string;method?:string;confidence?:number|null;current_value?:unknown;page_start?:number|string|null;page_end?:number|string|null}>;
    records?:Array<{record_id?:string;fields?:string[];issues?:Array<Record<string,unknown>>;page_start?:number|string|null;page_end?:number|string|null}>
  };
  metadata_operation?: {operation_id?:string;kind?:string;state?:"queued"|"running"|"completed"|"failed"|string;started_at?:string;finished_at?:string|null;records_total?:number;records_processed?:number;fields_total?:number;fields_resolved?:number;fields_remaining?:number;provider_profile_id?:string|null;provider?:string|null;model?:string|null;target_fields?:Record<string,string[]>;error?:string|null};
  source_quality?: {valid_for_enrichment?:boolean;page_count?:number;blocking_page_count?:number;warning_page_count?:number;blocking_pages?:number[];warning_pages?:number[];issues?:Array<{page?:number;severity?:string;codes?:string[];characters?:number;replacement_characters?:number;control_characters?:number;extraction_methods?:Record<string,number>}>};
  pipeline_state?: {current?:string;stages?:Record<string,{state?:string;[key:string]:unknown}>};
  publication_readiness?: {can_publish?:boolean;next_action?:string;blockers?:Array<{code?:string;count?:number;fields?:string[]}>;required_metadata_fields?:string[];records_total?:number;records_reviewed?:number;records_accepted?:number;records_rejected?:number;records_pending?:number;metadata_records_remaining?:number;metadata_fields_unresolved?:number;source_valid?:boolean;metadata_valid?:boolean;published?:boolean};
  build_events?: Array<{at?:string;stage?:string;status?:string;progress?:number}>;
  request?: Record<string,unknown>;
  llm_metrics?: {calls?:number;retries?:number;structured_output_failures?:number;escalations?:number};
}

export interface CorpusRecord {
  record_id: string;
  text: string;
  text_length: number;
  page_start?: number | string | null;
  page_end?: number | string | null;
  source_block_ids: string[];
  source_spans: Array<{block_id:string;page:number;bbox?:number[];extraction_method?:string}>;
  metadata_evidence?: Record<string,{block_ids?:string[];confidence?:number;reason?:string;reviewed_by?:string;reviewed_at?:string}>;
  metadata_field_status?: Record<string,{status?:"deterministic"|"llm_inferred"|"human_confirmed"|"unresolved"|"invalid"|string;method?:string;confidence?:number;reason?:string}>;
  metadata_incomplete_fields?: string[];
  metadata_stage_status?: Record<string,string>;
  metadata_complete?: boolean;
  metadata_needs_attention?: boolean;
  metadata_attention_reasons?: string[];
  source_quality_issues?: Array<{code?:string;pages?:number[]}>;
  needs_review?: boolean;
  review_reason?: string;
  accepted?: boolean;
  rejected?: boolean;
  review_disposition?: "pending"|"accepted"|"rejected";
  record_revision?: number;
  topology_index?: number;
  topology_count?: number;
  pdf_pages?: number[];
  [key:string]: unknown;
}

export interface SourceBlock {block_id:string;page:number;bbox:number[];type:string;text:string;extraction_method:string;confidence:number}

export const pdfCorpusApi = {
  listAssets: () => apiRequest<{items:PdfAsset[]}>("/api/pdf/assets"),
  async uploadAsset(file: File, ocrMode="auto") {
    const body=new FormData();
    body.append("file", file);
    body.append("ocr_mode", ocrMode);
    body.append("ocr_languages", "eng+fra+deu");
    return apiRequest<PdfAsset>("/api/pdf/assets", {method:"POST", body});
  },
  assetContentUrl: (assetId:string) => `/api/pdf/assets/${encodeURIComponent(assetId)}/content`,
  updatePageLabels: (assetId:string, labels:Record<number,string|null>) => apiRequest<PdfAsset>(`/api/pdf/assets/${encodeURIComponent(assetId)}/page-labels`, {method:"PATCH",body:JSON.stringify({labels})}),
  blocks: (assetId:string, offset=0, limit=200, ids:string[]=[]) => apiRequest<{items:SourceBlock[];total:number}>(`/api/pdf/assets/${encodeURIComponent(assetId)}/blocks?offset=${offset}&limit=${limit}${ids.length?`&ids=${encodeURIComponent(ids.join(","))}`:""}`),
  profiles: () => apiRequest<{items:Array<Record<string,unknown>>}>("/api/pdf/corpus-profiles"),
  listBuilds: (offset=0, limit=50, assetId="") => apiRequest<{items:CorpusBuild[];total:number;offset:number;limit:number}>(`/api/pdf/corpus-builds?offset=${offset}&limit=${limit}${assetId?`&asset_id=${encodeURIComponent(assetId)}`:""}`),
  build: (buildId:string) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}`),
  patchManifest: (buildId:string, changes:Record<string,unknown>, expectedRevision?:number) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/manifest`, {method:"PATCH",body:JSON.stringify({changes,expected_revision:expectedRevision})}),
  createBuild: (payload:Record<string,unknown>) => apiRequest<CorpusBuild>("/api/pdf/corpus-builds", {method:"POST",body:JSON.stringify(payload)}),
  records: (buildId:string, offset=0, limit=50, reviewOnly=false, query="", disposition:"pending"|"accepted"|"rejected"|""="", metadataIncomplete=false) => apiRequest<{items:CorpusRecord[];total:number;offset:number;limit:number}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records?offset=${offset}&limit=${limit}${reviewOnly?"&needs_review=true":""}${disposition?`&disposition=${encodeURIComponent(disposition)}`:""}${metadataIncomplete?"&metadata_incomplete=true":""}${query?`&query=${encodeURIComponent(query)}`:""}`),
  accept: (buildId:string, recordId:string, accepted=true, expectedRevision?:number) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/accept`, {method:"POST",body:JSON.stringify({accepted,expected_revision:expectedRevision})}),
  disposition: (buildId:string, recordId:string, disposition:"pending"|"accepted"|"rejected", reason="", expectedRevision?:number) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/disposition`, {method:"POST",body:JSON.stringify({disposition,reason,expected_revision:expectedRevision})}),
  bulkDisposition: (buildId:string, disposition:"pending"|"accepted"|"rejected", needsReview:boolean|null, query="", reason="", filterDisposition:"pending"|"accepted"|"rejected"|null=null) => apiRequest<{changed:number;disposition:string}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/disposition`, {method:"POST",body:JSON.stringify({disposition,reason,needs_review:needsReview,filter_disposition:filterDisposition,query})}),
  undoReview: (buildId:string) => apiRequest<{restored:boolean;action?:string;selected_record_id?:string;record_count:number}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/review/undo`, {method:"POST"}),
  patchMetadata: (buildId:string, recordId:string, changes:Record<string,unknown>, expectedRevision?:number) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata`, {method:"PATCH",body:JSON.stringify({changes,expected_revision:expectedRevision})}),
  patchEvidence: (buildId:string, recordId:string, field:string, blockIds:string[], confidence=1, reason="", expectedRevision?:number) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/evidence`, {method:"PATCH",body:JSON.stringify({field,block_ids:blockIds,confidence,reason,expected_revision:expectedRevision})}),
  merge: (buildId:string, recordId:string, direction:"previous"|"next", expectedRevision?:number) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/merge`, {method:"POST",body:JSON.stringify({direction,expected_revision:expectedRevision})}),
  split: (buildId:string, recordId:string, afterBlockId:string, expectedRevision?:number) => apiRequest<{records:CorpusRecord[]}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/split`, {method:"POST",body:JSON.stringify({after_block_id:afterBlockId,expected_revision:expectedRevision})}),
  retryMetadata: (buildId:string, payload:Record<string,unknown>) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/metadata/retry`, {method:"POST",body:JSON.stringify(payload)}),
  rerunMetadata: (buildId:string, recordId:string, payload:Record<string,unknown>) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/rerun-metadata`, {method:"POST",body:JSON.stringify(payload)}),
  confirmManifest: (buildId:string, payload:Record<string,unknown>) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/confirm-manifest`, {method:"POST",body:JSON.stringify(payload)}),
  cancel: (buildId:string) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/cancel`, {method:"POST"}),
  resume: (buildId:string, payload:Record<string,unknown>) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/resume`, {method:"POST",body:JSON.stringify(payload)}),
  publish: (buildId:string) => apiRequest<{publication_id:string;filename:string;sha256:string;record_count:number;created_at:string}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/publish`, {method:"POST",body:JSON.stringify({require_acceptance:true})}),
  publicationUrl: (publicationId:string) => `/api/pdf/publications/${encodeURIComponent(publicationId)}/download`,
};
