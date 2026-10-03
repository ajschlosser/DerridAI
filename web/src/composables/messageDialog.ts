/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
