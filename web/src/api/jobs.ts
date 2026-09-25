import { apiRequest } from "./http";
export interface JobSummary {
  id: string;
  status: string;
  kind?: string;
  type?: string;
  mode?: string;
  tool?: string;
  label?: string;
  provider?: string;
  model?: string | null;
  provider_profile_id?: string | null;
  request?: Record<string, unknown> | null;
  stage?: string;
  stage_detail?: string;
  total?: number;
  completed?: number;
  failed?: number;
  result?: Record<string, unknown> | null;
  error?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
  finished_at?: string | null;
}
export const jobsApi = {
  list: () => apiRequest<{ jobs: JobSummary[] }>("/api/jobs"),
  get: (id: string) => apiRequest<JobSummary>(`/api/jobs/${encodeURIComponent(id)}`),
};
