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
  model?: string | null;
  provider?: string | null;
  profile_id: string;
  schema_version?: string;
  segmentation_prompt_version?: string;
  metadata_prompt_version?: string;
  document_prompt_version?: string;
  validation?: {valid?:boolean;coverage?:number;missing_block_ids?:string[];duplicate_block_ids?:string[];text_fidelity_errors?:string[]};
  manifest?: Record<string, unknown>;
  publication?: {publication_id:string;filename:string;sha256:string;record_count:number;created_at:string}|null;
  error?: string | null;
}

export interface CorpusRecord {
  record_id: string;
  text: string;
  text_length: number;
  page_start?: number | null;
  page_end?: number | null;
  source_block_ids: string[];
  source_spans: Array<{block_id:string;page:number;bbox?:number[];extraction_method?:string}>;
  metadata_evidence?: Record<string,{block_ids?:string[];confidence?:number;reason?:string}>;
  needs_review?: boolean;
  review_reason?: string;
  accepted?: boolean;
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
  blocks: (assetId:string, offset=0, limit=200, ids:string[]=[]) => apiRequest<{items:SourceBlock[];total:number}>(`/api/pdf/assets/${encodeURIComponent(assetId)}/blocks?offset=${offset}&limit=${limit}${ids.length?`&ids=${encodeURIComponent(ids.join(","))}`:""}`),
  profiles: () => apiRequest<{items:Array<Record<string,unknown>>}>("/api/pdf/corpus-profiles"),
  listBuilds: (offset=0, limit=50, assetId="") => apiRequest<{items:CorpusBuild[];total:number;offset:number;limit:number}>(`/api/pdf/corpus-builds?offset=${offset}&limit=${limit}${assetId?`&asset_id=${encodeURIComponent(assetId)}`:""}`),
  build: (buildId:string) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}`),
  createBuild: (payload:Record<string,unknown>) => apiRequest<CorpusBuild>("/api/pdf/corpus-builds", {method:"POST",body:JSON.stringify(payload)}),
  records: (buildId:string, offset=0, limit=50, reviewOnly=false, query="") => apiRequest<{items:CorpusRecord[];total:number;offset:number;limit:number}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records?offset=${offset}&limit=${limit}${reviewOnly?"&needs_review=true":""}${query?`&query=${encodeURIComponent(query)}`:""}`),
  accept: (buildId:string, recordId:string, accepted=true) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/accept`, {method:"POST",body:JSON.stringify({accepted})}),
  patchMetadata: (buildId:string, recordId:string, changes:Record<string,unknown>) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/metadata`, {method:"PATCH",body:JSON.stringify({changes})}),
  merge: (buildId:string, recordId:string, direction:"previous"|"next") => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/merge`, {method:"POST",body:JSON.stringify({direction})}),
  split: (buildId:string, recordId:string, afterBlockId:string) => apiRequest<{records:CorpusRecord[]}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/split`, {method:"POST",body:JSON.stringify({after_block_id:afterBlockId})}),
  rerunMetadata: (buildId:string, recordId:string, payload:Record<string,unknown>) => apiRequest<CorpusRecord>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/records/${encodeURIComponent(recordId)}/rerun-metadata`, {method:"POST",body:JSON.stringify(payload)}),
  cancel: (buildId:string) => apiRequest<CorpusBuild>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/cancel`, {method:"POST"}),
  publish: (buildId:string) => apiRequest<{publication_id:string;filename:string;sha256:string;record_count:number;created_at:string}>(`/api/pdf/corpus-builds/${encodeURIComponent(buildId)}/publish`, {method:"POST",body:JSON.stringify({require_acceptance:true})}),
  publicationUrl: (publicationId:string) => `/api/pdf/publications/${encodeURIComponent(publicationId)}/download`,
};
