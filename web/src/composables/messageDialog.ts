/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readonly, shallowRef } from "vue";

export interface MessageDialogOptions {
  title?: string;
  message?: string;
  detail?: string;
  /** `"danger"` styles the dialog and its confirm button as destructive. */
  tone?: string;
  confirmLabel?: string;
  /** When set, the dialog offers a cancel button; otherwise it is an acknowledgement. */
  cancelLabel?: string | null;
}
export interface MessageDialogRequest extends MessageDialogOptions {
  id: number;
}

const queue = shallowRef<MessageDialogRequest[]>([]);
const resolvers = new Map<number, (confirmed: boolean) => void>();
let nextId = 1;

/**
 * Show a message or confirmation and resolve with whether the user confirmed. Requests queue and
 * show one at a time, so a second message never replaces a pending confirmation.
 */
export function openMessageDialog(options: MessageDialogOptions = {}): Promise<boolean> {
  const id = nextId++;
  return new Promise((resolve) => {
    resolvers.set(id, resolve);
    queue.value = [...queue.value, { ...options, id }];
  });
}

export function settleMessageDialog(id: number, confirmed: boolean) {
  const resolve = resolvers.get(id);
  resolvers.delete(id);
  queue.value = queue.value.filter((request) => request.id !== id);
  resolve?.(confirmed);
}

export function useMessageDialog() {
  return { queue: readonly(queue), open: openMessageDialog, settle: settleMessageDialog };
}
