# Canadian French (`fr-CA`) localization standard

DerridAI uses the technical locale code `fr-CA`. Its built-in French linguistic target is **professional Canadian French as written in Québec**.

The interface localization follows these rules:

- Prefer terminology used in Québec and terminology standardized by the Office québécois de la langue française (OQLF) where applicable.
- Prefer natural French software-interface language over literal English calques and avoid France-specific wording when normal Québec usage differs.
- Follow Canadian French typography and punctuation conventions.
- Preserve product names, model identifiers, API names, accepted technical acronyms (for example API, RAG and LLM), and code-level field identifiers where translating them would make the interface less precise.
- Never translate corpus passages, quotations, bibliographic evidence, user-authored annotations, model output, or source metadata merely because the UI locale changes. Localization applies to application chrome and application-authored explanatory text.
- Every canonical built-in key must exist in both `en-US` and `fr-CA`. Placeholders such as `{count}` and `{title}` must remain identical between locales.
- New UI strings must be entered through the i18n dictionary rather than hard-coded into a component. Compatibility views may use the exact-label bridge only for application-owned labels.

Version 0.35.5 keeps the built-in localization revision at `0.35.0` and adds the new Response FAQ and unified Research-result strings by key. Existing administrator edits therefore remain intact while missing English and Québec French keys are filled in automatically.

The translated-dictionary installer also applies the Québec localization brief automatically when `fr-CA` is selected. Other locale codes continue to receive the general locale translation prompt.


## 0.35.10 Record Workspace

Version 0.35.10 adds the Vue-native Record Workspace strings in both `en-US` and professional Québec `fr-CA`, preserving exact key parity. Record-workspace terminology uses *fiche*, *indexation*, *piste d’audit*, *Explorateur PDF*, and Québec-oriented interface phrasing rather than France-specific vocabulary or unnecessary English calques.
