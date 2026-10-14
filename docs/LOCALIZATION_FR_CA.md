<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# French (`fr-CA`) localization standard

DerridAI uses `fr-CA` for its built-in Canadian French interface dictionary. The goal is professional, natural French software copy while preserving scholarly source material exactly.

## Interface rules

- Prefer natural French software-interface language over literal English calques.
- Follow French typography and punctuation conventions.
- Preserve product names, model identifiers, API names, accepted technical acronyms (for example API, RAG and LLM), and code-level field identifiers when translating them would reduce precision.
- Never translate corpus passages, quotations, evidence, bibliographic text, user-authored annotations, model output, or source metadata merely because the UI locale changes. Localization applies to application chrome and application-authored explanatory text.
- Every canonical built-in key must exist in both `en-US` and `fr-CA`. Placeholders such as `{count}` and `{title}` must remain identical.
- New user-facing application strings go through the i18n dictionary; do not hard-code English/French pairs in components.
- Terminology for source/media concepts must match the selected medium. Do not translate an audio time span into PDF/page vocabulary because an older component used PDF terminology.

## Locale identity

Installed locale identities use valid BCP 47 tags, including language-only and script-aware forms where appropriate. The runtime sets the document `lang` and script-aware `dir` attributes from the active locale.

Country flags are optional presentation metadata, not a claim that a language belongs to one country. A neutral globe remains appropriate when country identity would be misleading.

## Translation workflow

The canonical English application dictionary is the source for machine-assisted locale installation.

A translation run must:

- preserve every required key and placeholder;
- validate each returned value before persistence;
- avoid translating research/source content;
- retain resumable validated work when a provider fails partway through;
- make English fallbacks visible as needing review rather than presenting them as completed localization;
- fail installation when the configured completeness/safety threshold is not met.

Provider/model suitability warnings are advisory; they do not replace validation of the returned dictionary.

## UI quality

English and French are first-class acceptance surfaces. New/changed UI must be checked for:

- long strings and label wrapping;
- keyboard operation and focus order;
- accessible names/status announcements;
- narrow/mobile reflow;
- dark/increased-contrast/forced-colors modes where relevant;
- placeholder parity and missing-key fallbacks.

Historical localization milestones belong in [release notes](notes/) rather than this current contract.
