/* Copyright 2026 Aaron John Schlosser, PhD. */
import { useI18nStore } from "../stores/i18n";

/** Translate a `schemas.*` key. Every metadata-schema component reads its copy through this. */
export function useSchemaCopy() {
  const i18n = useI18nStore();
  const t = (key: string, fallback?: string) => i18n.t(`schemas.${key}`, fallback);
  const tf = (key: string, values: Record<string, string | number>) =>
    i18n.tf(`schemas.${key}`, values);
  return { t, tf };
}
