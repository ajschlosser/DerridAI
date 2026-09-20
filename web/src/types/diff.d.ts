/* Copyright 2026 Aaron John Schlosser, PhD. */
declare module "diff" {
  export function diffWordsWithSpace(oldStr: string, newStr: string): Array<{value: string; added?: boolean; removed?: boolean}>;
}
