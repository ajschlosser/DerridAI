# French (`fr-CA`) localization standard

DerridAI uses the technical locale code `fr-CA` for its built-in French dictionary. The target is professional, natural French for a software interface.

The interface localization follows these rules:

- Prefer natural French software-interface language over literal English calques.
- Follow French typography and punctuation conventions.
- Preserve product names, model identifiers, API names, accepted technical acronyms (for example API, RAG and LLM), and code-level field identifiers where translating them would make the interface less precise.
- Never translate corpus passages, quotations, bibliographic evidence, user-authored annotations, model output, or source metadata merely because the UI locale changes. Localization applies to application chrome and application-authored explanatory text.
- Every canonical built-in key must exist in both `en-US` and `fr-CA`. Placeholders such as `{count}` and `{title}` must remain identical between locales.
- New UI strings must be entered through the i18n dictionary rather than hard-coded into a component. Compatibility views may use the exact-label bridge only for application-owned labels.

Version 0.35.5 keeps the built-in localization revision at `0.35.0` and adds the new Response Library and unified Research-result strings by key. Existing administrator edits therefore remain intact while missing English and French keys are filled in automatically.

The translated-dictionary installer applies no locale-specific brief: every locale receives the same general translation prompt, which names the target language.


## 0.35.10 Record Workspace

Version 0.35.10 adds the Vue-native Record Workspace strings in both `en-US` and `fr-CA`, preserving exact key parity. Record-workspace terminology uses *fiche*, *indexation*, *piste d’audit*, *Explorateur PDF*..

## 0.35.12 — Tongue Twister localization studio

The Languages & internationalization workspace now treats `en-US` as the visible canonical source beside every translated value. Installing a locale translates the complete English interface dictionary before persistence, in bounded batches, and rejects missing keys, empty values, damaged `{placeholders}`, or output that is effectively unchanged English. Installation is atomic: failed or refused translations do not create a partial locale.

Locale identity uses common BCP 47 language tags (including language-only and script-aware tags such as `de`, `pt-BR`, and `zh-Hant-TW`) and a searchable ISO 3166-1 country-flag library. Country flags are presentation metadata, not a claim that a language belongs to one country; the neutral globe remains available. The runtime also sets the document `lang` and script-aware `dir` attributes when the active locale changes.

The LLM translation workflow applies only to DerridAI interface strings. Never translate corpus passages, quotations, evidence, bibliographic titles, or other research content as part of interface localization.French continues to follow the policy above.

## 0.35.16 — Tongue Tied Again

Machine-localized dictionaries are now resumable and failure-tolerant without weakening the canonical-English contract. A translation run validates each returned value and placeholder independently. If **fewer than 10%** of canonical keys cannot be translated safely, the locale may still be installed: those exact keys fall back to the canonical `en-US` value and remain durably recorded in the locale's translation report until an administrator supplies and saves a localized value. If **10% or more** fail, installation stops rather than presenting the dictionary as usable, but validated work is retained server-side so the administrator can resume from only the unfinished or unsafe keys.

Translation-provider selection also presents an advisory warning for model families that are predictably poor choices for multilingual work, such as embedding/reranking models, code-specialized families, and very small models. The warning is not a claim that the provider is categorically incapable: the administrator may explicitly acknowledge the risk and continue. A provider that actually refuses or cannot perform the requested translation still produces a clear failure and retains resumable work where available.

The localization editor keeps the canonical English source visually aligned with each target-language row, exposes tracked English fallbacks as a dedicated **Needs review** state, and preserves the locale identity, `lang`, script-aware `dir`, placeholder, and French requirements documented above. Incomplete translation payloads are kept on the server rather than sent back to the browser; the UI receives only the status and failure information needed to explain and resume the operation.

