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

/**
 * The element in which the user is actively entering a value.
 *
 * Async refreshes and delayed focus work must treat this as a hard focus lock:
 * new data may update around the editor, but it must not move the caret or focus
 * somewhere else while the user is typing/selecting a value.
 */
export function activeValueEditor(): HTMLElement | null {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement)) return null;
  if (
    active.matches(
      [
        "textarea",
        "select",
        "input:not([type='button']):not([type='submit']):not([type='reset'])",
        "[contenteditable='true']",
        "[role='textbox']",
        "[role='combobox']",
      ].join(","),
    )
  )
    return active;
  return null;
}
