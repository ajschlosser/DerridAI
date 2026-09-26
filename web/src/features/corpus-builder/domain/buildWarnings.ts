// Copyright 2026 Aaron John Schlosser, PhD.
import type { CorpusBuild } from "../../../api/corpus";

/** The texts of the build warnings someone has acknowledged. */
export function acknowledgedWarningTexts(build: Pick<CorpusBuild, "warning_acknowledgements">) {
  return new Set(
    Object.values(build.warning_acknowledgements || {}).map((item) => String(item.warning)),
  );
}

/** Build warnings nobody has acknowledged yet, in the order the build raised them. */
export function openBuildWarnings(
  build: Pick<CorpusBuild, "warnings" | "warning_acknowledgements">,
): string[] {
  const acknowledged = acknowledgedWarningTexts(build);
  return [...new Set((build.warnings || []).map(String))].filter((text) => !acknowledged.has(text));
}
