import { apiRequest } from "./http";
export interface JobSummary { id:string; status:string; kind?:string; created_at?:string; updated_at?:string; }
export const jobsApi = {
  list: () => apiRequest<JobSummary[]>("/api/jobs"),
  get: (id:string) => apiRequest<JobSummary>(`/api/jobs/${encodeURIComponent(id)}`),
};
