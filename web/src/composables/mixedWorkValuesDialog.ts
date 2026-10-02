/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readonly, shallowRef } from "vue";

export interface MixedWorkValue {
  /** Display-ready value; `null` means the value is unset. */
  text: string | null;
  files: string[];
  count: number;
}
export interface MixedWorkValuesRequest {
  work: string;
  fieldLabel: string;
  recordCount: number;
  values: MixedWorkValue[];
}

const current = shallowRef<MixedWorkValuesRequest | null>(null);

/** Show the variants of one metadata field across a work's records. */
export function openMixedWorkValuesDialog(request: MixedWorkValuesRequest) {
  current.value = request;
}

export function closeMixedWorkValuesDialog() {
  current.value = null;
}

export function useMixedWorkValuesDialog() {
  return { current: readonly(current), close: closeMixedWorkValuesDialog };
}
