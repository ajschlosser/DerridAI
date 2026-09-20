// Copyright 2026 Aaron John Schlosser, PhD.
import { apiRequest } from "./http";
import type { Annotation, AnnotationDraft } from "../types/annotations";

export const annotationsApi = {
  list: (store?: string) =>
    apiRequest<{ annotations: Annotation[] }>(
      `/api/annotations${store ? `?store=${encodeURIComponent(store)}` : ""}`,
    ),
  create: (payload: AnnotationDraft) =>
    apiRequest<Annotation>("/api/annotations", { method: "POST", body: JSON.stringify(payload) }),
  remove: (id: string) =>
    apiRequest<{ deleted: string }>(`/api/annotations/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
};
