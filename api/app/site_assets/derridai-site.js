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

(()=>{const style=document.createElement("style");style.dataset.derridaiPublishedSiteVue="";style.textContent="/*\n * This file is part of DerridAI, a cELF-compliant research workspace\n * Copyright © 2026  Aaron John Schlosser, PhD\n *\n * This program is free software: you can redistribute it and/or modify\n * it under the terms of the GNU Affero General Public License as\n * published by the Free Software Foundation, either version 3 of the\n * License, or (at your option) any later version.\n *\n * This program is distributed in the hope that it will be useful,\n * but WITHOUT ANY WARRANTY; without even the implied warranty of\n * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n * GNU Affero General Public License for more details.\n *\n * You should have received a copy of the GNU Affero General Public License\n * along with this program.  If not, see <https://www.gnu.org/licenses/>.\n */\n\n/*\n * Canonical skin for ordinary native form controls.\n *\n * Feature components own layout; these classes own the interaction contract:\n * sizing, padding, border, type, focus, disabled/read-only and invalid states.\n */\n.ui-control {\n  inline-size: 100%;\n  min-block-size: var(--control-height);\n  border: 1px solid var(--border-strong);\n  border-radius: var(--radius-control);\n  background: var(--surface-card);\n  color: var(--text-primary);\n  padding: var(--space-2) var(--space-3);\n  font: inherit;\n  font-size: var(--fs-base);\n  line-height: var(--lh-normal);\n  outline: none;\n  transition:\n    border-color var(--motion-fast) var(--ease-standard),\n    background var(--motion-fast) var(--ease-standard),\n    box-shadow var(--motion-fast) var(--ease-standard);\n}\n\n.ui-control:hover:not(:disabled):not([readonly]) {\n  border-color: var(--border-interactive);\n}\n\n.ui-control:focus-visible {\n  border-color: var(--border-interactive);\n  outline: var(--focus-ring-width) solid var(--focus-ring);\n  outline-offset: var(--focus-ring-offset);\n}\n\n.ui-control[aria-invalid=\"true\"] {\n  border-color: var(--tone-danger-border);\n}\n\n.ui-control:disabled {\n  cursor: not-allowed;\n  border-color: var(--border-subtle);\n  background: var(--surface-disabled);\n  color: var(--text-tertiary);\n}\n\n.ui-control[readonly] {\n  background: var(--surface-inset);\n}\n\ntextarea.ui-control {\n  min-block-size: calc(var(--control-height) * 2.5);\n  resize: vertical;\n}\n\n.ui-checkbox {\n  display: flex;\n  align-items: flex-start;\n  gap: var(--space-2);\n  min-block-size: var(--control-height);\n  padding-block: var(--space-2);\n  color: var(--text-primary);\n  font-size: var(--fs-base);\n  line-height: var(--lh-normal);\n  cursor: pointer;\n}\n\n.ui-checkbox[data-disabled=\"true\"] {\n  cursor: not-allowed;\n  color: var(--text-tertiary);\n}\n\n.ui-checkbox-control {\n  flex: 0 0 auto;\n  inline-size: 1.25rem;\n  block-size: 1.25rem;\n  margin-block-start: 0.08rem;\n  accent-color: var(--ui-accent);\n}\n\n.ui-checkbox-control:focus-visible {\n  outline: var(--focus-ring-width) solid var(--focus-ring);\n  outline-offset: var(--focus-ring-offset);\n}\n\n.ui-checkbox-control[aria-invalid=\"true\"] {\n  outline: 2px solid var(--tone-danger-border);\n  outline-offset: 2px;\n}\n\n.ui-checkbox-copy {\n  display: grid;\n  gap: var(--space-1);\n  min-inline-size: 0;\n}\n\n.ui-checkbox-label {\n  font-weight: var(--fw-semibold);\n}\n\n.ui-checkbox-description {\n  color: var(--text-tertiary);\n  font-size: var(--fs-sm);\n  line-height: var(--lh-normal);\n}\n\n@media (forced-colors: active) {\n  .ui-control,\n  .ui-checkbox-control {\n    forced-color-adjust: auto;\n  }\n}\n\n.ui-tooltip[data-v-894a0d2d] {\n  position: relative;\n  display: inline-flex;\n  align-items: center;\n  vertical-align: middle;\n}\n.ui-tooltip-trigger[data-v-894a0d2d] {\n  display: inline-grid;\n  inline-size: 1.75rem;\n  block-size: 1.75rem;\n  place-items: center;\n  padding: 0;\n  border: 0;\n  border-radius: 999px;\n  background: transparent;\n  color: var(--text-tertiary, var(--muted));\n  font: inherit;\n  cursor: help;\n}\n.ui-tooltip-trigger > span[data-v-894a0d2d] {\n  display: grid;\n  inline-size: 1rem;\n  block-size: 1rem;\n  place-items: center;\n  border: 1px solid currentColor;\n  border-radius: 999px;\n  font-size: 0.75rem;\n  font-weight: 800;\n  line-height: 1;\n}\n.ui-tooltip-trigger[data-v-894a0d2d]:hover {\n  background: var(--surface-hover, var(--soft));\n  color: var(--text, currentColor);\n}\n.ui-tooltip-anchor[data-v-894a0d2d] {\n  display: inline-flex;\n  min-inline-size: 0;\n  border-radius: inherit;\n  cursor: help;\n}\n.ui-tooltip-trigger[data-v-894a0d2d]:focus-visible,\n.ui-tooltip-anchor[data-v-894a0d2d]:focus-visible {\n  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);\n  outline-offset: var(--focus-ring-offset, 2px);\n}\n.ui-tooltip-content[data-v-894a0d2d] {\n  position: fixed;\n  z-index: 10000;\n  inline-size: max-content;\n  max-inline-size: min(22rem, calc(100vw - 2rem));\n  padding: 0.625rem 0.75rem;\n  border: 1px solid var(--border-strong, var(--line-strong));\n  border-radius: var(--radius-overlay, 0.625rem);\n  background: var(--surface-overlay, var(--card));\n  color: var(--text);\n  box-shadow: var(--shadow-overlay, 0 12px 30px rgb(0 0 0 / 20%));\n  font-size: 0.8125rem;\n  font-weight: 500;\n  line-height: 1.45;\n  text-align: start;\n  white-space: normal;\n  pointer-events: none;\n}\n.ui-tooltip-content[hidden][data-v-894a0d2d] {\n  display: none;\n}\n@media (forced-colors: active) {\n.ui-tooltip-trigger[data-v-894a0d2d],\n  .ui-tooltip-content[data-v-894a0d2d] {\n    border-color: CanvasText;\n}\n.ui-tooltip-trigger[data-v-894a0d2d]:focus-visible,\n  .ui-tooltip-anchor[data-v-894a0d2d]:focus-visible {\n    outline-color: Highlight;\n}\n}\n\n.ui-button-wrap[data-v-de735335] {\n  display: inline-flex;\n  position: relative;\n}\n.ui-button[data-v-de735335] {\n  min-height: var(--control-height);\n  display: inline-flex;\n  align-items: center;\n  justify-content: center;\n  gap: 7px;\n  border: 1px solid var(--border-strong);\n  border-radius: var(--radius-control);\n  padding: 8px 13px;\n  background: var(--surface-card);\n  color: var(--text-primary);\n  font-size: 0.875rem;\n  font-weight: 700;\n  line-height: 1.2;\n  box-shadow: var(--shadow-card);\n  transition:\n    background var(--motion-fast) var(--ease-standard),\n    border-color var(--motion-fast) var(--ease-standard),\n    box-shadow var(--motion-fast) var(--ease-standard),\n    transform var(--motion-fast) var(--ease-standard);\n}\n.ui-button[data-v-de735335]:hover:not(:disabled) {\n  background: var(--surface-hover);\n  border-color: var(--border-interactive);\n  box-shadow: var(--elev-2);\n  transform: translateY(-1px);\n}\n.ui-button[data-v-de735335]:active:not(:disabled) {\n  transform: none;\n}\n.ui-button[data-v-de735335]:focus-visible {\n  outline: var(--focus-ring-width) solid var(--focus-ring);\n  outline-offset: var(--focus-ring-offset);\n}\n.ui-button[data-v-de735335]:disabled {\n  background: var(--surface-disabled);\n  opacity: 0.72;\n  cursor: not-allowed;\n  box-shadow: none;\n}\n.ui-button.variant-primary[data-v-de735335] {\n  background: var(--accent);\n  color: var(--accent-on);\n  border-color: var(--accent);\n}\n.ui-button.variant-primary[data-v-de735335]:hover:not(:disabled) {\n  background: var(--accent-2);\n  border-color: var(--accent-2);\n}\n.ui-button.variant-soft[data-v-de735335] {\n  background: var(--surface-selected);\n  color: var(--accent-fg);\n  border-color: var(--border-interactive);\n}\n.ui-button.variant-danger[data-v-de735335] {\n  background: var(--tone-danger-bg);\n  color: var(--tone-danger-fg);\n  border-color: var(--tone-danger-border);\n}\n.ui-button.variant-ghost[data-v-de735335] {\n  background: transparent;\n  border-color: transparent;\n  box-shadow: none;\n}\n.ui-button.variant-ghost[data-v-de735335]:hover:not(:disabled) {\n  background: var(--surface-hover);\n  border-color: var(--border-subtle);\n}\n.ui-button.size-small[data-v-de735335] {\n  min-height: var(--control-height-small);\n  padding: 6px 10px;\n  font-size: 0.8125rem;\n}\n.ui-button.icon-only[data-v-de735335] {\n  width: var(--control-height);\n  padding: 0;\n}\n.ui-button.size-small.icon-only[data-v-de735335] {\n  width: var(--control-height-small);\n  min-width: var(--control-height-small);\n  min-height: var(--control-height-small);\n}\n.ui-button[data-v-de735335] svg {\n  width: 16px;\n  height: 16px;\n}\n.ui-button-count[data-v-de735335] {\n  min-width: 1.55em;\n  padding: 1px 5px;\n  border-radius: var(--radius-pill);\n  background: var(--surface-inset);\n  font-size: 0.75rem;\n  text-align: center;\n}\n@media (prefers-reduced-motion: reduce) {\n.ui-button[data-v-de735335] {\n    transition: none;\n}\n.ui-button[data-v-de735335]:hover:not(:disabled) {\n    transform: none;\n}\n}\n\n.ui-card[data-v-c21b5364] {\n  background: var(--surface-card);\n  border: 1px solid var(--border-subtle);\n  border-radius: var(--radius-card);\n  box-shadow: var(--shadow-card);\n}\n.ui-card.padded[data-v-c21b5364] {\n  padding: var(--space-5);\n}\n\n.ui-dialog-backdrop[data-v-dd8a615b] {\n  position: fixed;\n  inset: 0;\n  z-index: 12000;\n  display: grid;\n  place-items: center;\n  padding: 24px;\n  background: var(--scrim);\n  backdrop-filter: blur(2px);\n}\n.ui-dialog[data-v-dd8a615b] {\n  width: min(760px, calc(100vw - 32px));\n  max-height: min(92vh, 960px);\n  display: grid;\n  grid-template-rows: auto minmax(0, 1fr) auto;\n  overflow: hidden;\n  border: 1px solid var(--border-strong);\n  border-radius: var(--radius-overlay);\n  background: var(--surface-overlay);\n  color: var(--text-primary);\n  box-shadow: var(--shadow-overlay);\n}\n.ui-dialog[data-size=\"large\"][data-v-dd8a615b] {\n  width: min(980px, calc(100vw - 32px));\n}\n.ui-dialog[data-size=\"xlarge\"][data-v-dd8a615b] {\n  width: min(1180px, calc(100vw - 32px));\n}\n.ui-dialog-header[data-v-dd8a615b] {\n  display: flex;\n  justify-content: space-between;\n  align-items: flex-start;\n  gap: 20px;\n  padding: 20px 22px;\n  border-bottom: 1px solid var(--border-subtle);\n  background: var(--surface-overlay);\n}\n.ui-dialog-heading[data-v-dd8a615b] {\n  min-width: 0;\n  display: grid;\n  gap: 6px;\n}\n.ui-dialog-heading h2[data-v-dd8a615b] {\n  margin: 0;\n  font-size: 1.25rem;\n  line-height: 1.25;\n  overflow-wrap: anywhere;\n}\n.ui-dialog-heading p[data-v-dd8a615b] {\n  max-width: 72ch;\n  margin: 0;\n  color: var(--text-tertiary);\n  font-size: 0.875rem;\n  line-height: 1.5;\n}\n.ui-dialog-body[data-v-dd8a615b] {\n  min-height: 0;\n  overflow: auto;\n  padding: 20px 22px;\n  overscroll-behavior: contain;\n  background: var(--surface-overlay);\n}\n.ui-dialog-footer[data-v-dd8a615b] {\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n  gap: 12px;\n  padding: 14px 22px;\n  border-top: 1px solid var(--border-subtle);\n  background: var(--surface-overlay);\n}\n.ui-dialog[data-v-dd8a615b] :focus-visible {\n  outline: var(--focus-ring-width) solid var(--focus-ring, var(--accent));\n  outline-offset: var(--focus-ring-offset);\n}\n@media (max-width: 700px) {\n.ui-dialog-backdrop[data-v-dd8a615b] {\n    padding: 8px;\n    place-items: stretch;\n}\n.ui-dialog[data-v-dd8a615b],\n  .ui-dialog[data-size=\"large\"][data-v-dd8a615b],\n  .ui-dialog[data-size=\"xlarge\"][data-v-dd8a615b] {\n    width: 100%;\n    max-height: calc(100dvh - 16px);\n    align-self: center;\n    border-radius: 12px;\n}\n.ui-dialog-header[data-v-dd8a615b],\n  .ui-dialog-body[data-v-dd8a615b],\n  .ui-dialog-footer[data-v-dd8a615b] {\n    padding-inline: 14px;\n}\n.ui-dialog-footer[data-v-dd8a615b] {\n    align-items: stretch;\n    flex-direction: column;\n}\n}\n@media (prefers-reduced-motion: reduce) {\n.ui-dialog-backdrop[data-v-dd8a615b] {\n    backdrop-filter: none;\n}\n}\n\n.model-list[data-v-aef123e2] {\n  display: grid;\n  gap: 0.5rem;\n  margin: 0;\n  padding: 0;\n  list-style: none;\n}\n[data-v-aef123e2] .model-choice {\n  width: 100%;\n  height: auto;\n  justify-content: flex-start;\n  text-align: start;\n}\n.model-choice-copy[data-v-aef123e2] {\n  display: grid;\n  gap: 0.15rem;\n}\n\n.ui-field[data-v-2760bbcc] {\n  display: grid;\n  gap: var(--space-2);\n  min-width: 0;\n}\n.ui-field.wide[data-v-2760bbcc] {\n  grid-column: 1/-1;\n}\n.ui-field-label[data-v-2760bbcc] {\n  display: flex;\n  flex-wrap: wrap;\n  align-items: baseline;\n  gap: var(--space-2);\n  font-size: var(--fs-sm);\n  font-weight: var(--fw-bold);\n  color: var(--text-primary);\n}\n.ui-field-required[data-v-2760bbcc] {\n  color: var(--tone-danger-fg);\n}\n.ui-field-persist[data-v-2760bbcc] {\n  margin-inline-start: auto;\n  font-weight: var(--fw-semibold);\n  color: var(--text-tertiary);\n  font-size: var(--fs-sm);\n  letter-spacing: 0.02em;\n  text-transform: uppercase;\n}\n.ui-field-hint[data-v-2760bbcc] {\n  font-size: var(--fs-sm);\n  line-height: var(--lh-normal);\n  color: var(--text-tertiary);\n}\n.ui-field-error[data-v-2760bbcc] {\n  font-size: var(--fs-sm);\n  line-height: var(--lh-normal);\n  color: var(--tone-danger-fg);\n  font-weight: var(--fw-bold);\n}\n.ui-field.invalid[data-v-2760bbcc] input,\n.ui-field.invalid[data-v-2760bbcc] select,\n.ui-field.invalid[data-v-2760bbcc] textarea {\n  border-color: var(--tone-danger-border);\n}\n\n.published-research-config[data-v-791c945e] {\n  display: grid;\n  gap: var(--space-5);\n}\n.published-research-config-grid[data-v-791c945e] {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));\n  gap: var(--space-4);\n}\n.published-work-scope[data-v-791c945e] {\n  display: grid;\n  gap: var(--space-3);\n  min-width: 0;\n  margin: 0;\n  padding: var(--space-4);\n  border: 1px solid var(--border-subtle);\n  border-radius: var(--radius-control);\n}\n.published-work-scope legend[data-v-791c945e] {\n  padding-inline: var(--space-2);\n  font-weight: var(--fw-bold);\n}\n.published-work-scope p[data-v-791c945e] {\n  margin: 0;\n}\n.published-work-options[data-v-791c945e] {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));\n  gap: var(--space-2);\n  max-block-size: 16rem;\n  overflow: auto;\n}\n.published-work-option[data-v-791c945e] {\n  min-width: 0;\n}\n\n.record-dialog-content[data-v-33452b27] {\n  display: grid;\n  gap: 1rem;\n}\n.record-dialog-content h3[data-v-33452b27] {\n  margin-block-end: 0;\n}\n\n.published-research-answer[data-v-89110dd1] {\n  white-space: pre-wrap;\n}\n.inline-citation[data-v-89110dd1] {\n  font-family: inherit;\n}\n.published-evidence-card[data-v-89110dd1] {\n  align-content: start;\n}\n.published-evidence-card h3[data-v-89110dd1] {\n  margin-block-start: 0;\n}\n.published-evidence-list[data-v-89110dd1] {\n  display: grid;\n  gap: 0.6rem;\n}\n.evidence-item[data-v-89110dd1] {\n  scroll-margin-top: 6rem;\n}\n.evidence-item[data-v-89110dd1]:target {\n  outline: 3px solid var(--accent);\n  outline-offset: 3px;\n  border-radius: var(--radius-control, 0.55rem);\n}\n[data-v-89110dd1] .published-evidence-button {\n  width: 100%;\n  height: auto;\n  justify-content: flex-start;\n  text-align: start;\n}\n.published-evidence-copy[data-v-89110dd1] {\n  display: grid;\n  gap: 0.18rem;\n  min-width: 0;\n}\n.published-evidence-copy strong[data-v-89110dd1],\n.published-evidence-copy small[data-v-89110dd1] {\n  overflow-wrap: anywhere;\n}\n.published-evidence-copy small[data-v-89110dd1] {\n  color: var(--muted);\n  font-weight: 400;\n}\n\n.research-run-settings[data-v-14d4b029] {\n  border: 1px solid var(--border-subtle);\n  border-radius: var(--radius-control);\n}\n.research-run-settings > summary[data-v-14d4b029] {\n  min-height: var(--control-height);\n  padding: var(--space-3) var(--space-4);\n  cursor: pointer;\n  font-weight: var(--fw-bold);\n}\n.research-run-settings > summary[data-v-14d4b029]:focus-visible {\n  outline: var(--focus-ring-width) solid var(--focus-ring);\n  outline-offset: var(--focus-ring-offset);\n}\n.research-run-settings-body[data-v-14d4b029] {\n  display: grid;\n  gap: var(--space-4);\n  padding: 0 var(--space-4) var(--space-4);\n}\n.research-run-settings-body > p[data-v-14d4b029] {\n  margin: 0;\n}\n.research-run-progress[data-v-14d4b029] {\n  display: grid;\n  gap: var(--space-2);\n}\n.research-run-progress progress[data-v-14d4b029] {\n  width: 100%;\n}\n\n.work-card-copy[data-v-c054ebca] {\n  display: grid;\n  gap: 0.15rem;\n}\n/*\n * This file is part of DerridAI, a cELF-compliant research workspace\n * Copyright © 2026  Aaron John Schlosser, PhD\n *\n * Published-site theme and layout. Shared DerridAI Vue primitives consume the semantic aliases below.\n */\n\n:root {\n  font-family:\n    Inter,\n    ui-sans-serif,\n    system-ui,\n    -apple-system,\n    BlinkMacSystemFont,\n    \"Segoe UI\",\n    sans-serif;\n  color-scheme: light;\n  --bg: #ffffff;\n  --fg: #111827;\n  --muted: #4b5563;\n  --surface: #f7f8fa;\n  --raised: #eef1f4;\n  --border: #697586;\n  --border-subtle: #d7dde4;\n  --accent: #005ea8;\n  --accent-text: #ffffff;\n  --danger: #b42318;\n  --success: #166534;\n  --warning: #7c4a03;\n  --mark-bg: #fde68a;\n  --mark-fg: #111827;\n  --shadow: 0 12px 32px rgba(17, 24, 39, 0.18);\n\n  --card: var(--surface);\n  --soft: var(--raised);\n  --text: var(--fg);\n  --text-2: var(--muted);\n  --line: var(--border-subtle);\n  --line-strong: var(--border);\n  --ui-accent: var(--accent);\n  --ui-accent-dark: var(--accent);\n  --ui-accent-border: var(--border);\n  --accent-2: var(--accent);\n  --accent-on: var(--accent-text);\n  --accent-fg: var(--accent);\n  --focus-ring: var(--accent);\n  --surface-page: var(--bg);\n  --surface-card: var(--surface);\n  --surface-raised: var(--raised);\n  --surface-inset: var(--raised);\n  --surface-overlay: var(--bg);\n  --surface-glass: var(--bg);\n  --surface-hover: var(--raised);\n  --surface-selected: var(--raised);\n  --surface-disabled: var(--raised);\n  --text-primary: var(--fg);\n  --text-secondary: var(--muted);\n  --text-tertiary: var(--muted);\n  --border-strong: var(--border);\n  --border-interactive: var(--border);\n  --tone-danger-bg: var(--surface);\n  --tone-danger-fg: var(--danger);\n  --tone-danger-border: var(--danger);\n  --control-height: 2.75rem;\n  --control-height-small: 2.35rem;\n  --radius-control: 0.55rem;\n  --radius-card: 0.7rem;\n  --radius-overlay: 0.9rem;\n  --radius-pill: 999px;\n  --shadow-card: none;\n  --shadow-overlay: var(--shadow);\n  --scrim: rgba(0, 0, 0, 0.65);\n  --elev-2: var(--shadow);\n  --motion-fast: 120ms;\n  --ease-standard: ease;\n  --focus-ring-width: 3px;\n  --focus-ring-offset: 3px;\n  --space-1: 0.25rem;\n  --space-2: 0.5rem;\n  --space-3: 0.75rem;\n  --space-4: 1rem;\n  --space-5: 1.25rem;\n  --fs-sm: 0.8125rem;\n  --fs-base: 0.875rem;\n  --lh-normal: 1.5;\n  --fw-semibold: 650;\n}\n\n:root[data-theme=\"dark\"] {\n  color-scheme: dark;\n  --bg: #111827;\n  --fg: #f9fafb;\n  --muted: #d1d5db;\n  --surface: #171f2d;\n  --raised: #283446;\n  --border: #a6afbc;\n  --border-subtle: #3d495a;\n  --accent: #8ecbff;\n  --accent-text: #0b1725;\n  --danger: #ffb4ab;\n  --success: #9ee6b1;\n  --warning: #ffd38a;\n  --mark-bg: #facc15;\n  --mark-fg: #111827;\n  --shadow: 0 12px 32px rgba(0, 0, 0, 0.55);\n}\n\n:root[data-contrast=\"high\"] {\n  color-scheme: dark;\n  --bg: #000000;\n  --fg: #ffffff;\n  --muted: #ffffff;\n  --surface: #000000;\n  --raised: #1a1a1a;\n  --border: #ffffff;\n  --border-subtle: #ffffff;\n  --accent: #ffdf00;\n  --accent-text: #000000;\n  --danger: #ff8a80;\n  --success: #9cff9c;\n  --warning: #ffe66d;\n  --mark-bg: #ffdf00;\n  --mark-fg: #000000;\n  --shadow: 0 0 0 2px #ffffff;\n}\n\n* {\n  box-sizing: border-box;\n}\nhtml {\n  background: var(--bg);\n  scroll-behavior: auto;\n}\nbody {\n  margin: 0;\n  background: var(--bg);\n  color: var(--fg);\n  line-height: 1.6;\n  font-size: 1rem;\n}\nbutton,\ninput,\nselect,\ntextarea {\n  font: inherit;\n  color: inherit;\n}\nbutton,\n.control {\n  min-height: 2.75rem;\n}\nbutton {\n  border: 1px solid var(--border);\n  border-radius: 0.55rem;\n  background: var(--surface);\n  padding: 0.5rem 0.85rem;\n  cursor: pointer;\n}\nbutton:hover {\n  background: var(--raised);\n}\nbutton:focus-visible,\ninput:focus-visible,\nselect:focus-visible,\ntextarea:focus-visible,\na:focus-visible,\nsummary:focus-visible {\n  outline: 3px solid var(--accent);\n  outline-offset: 3px;\n}\nbutton.primary {\n  background: var(--accent);\n  color: var(--accent-text);\n  border-color: var(--accent);\n  font-weight: 700;\n}\nbutton.danger {\n  color: var(--danger);\n}\nbutton[disabled] {\n  opacity: 0.58;\n  cursor: not-allowed;\n}\n.skip-link {\n  position: fixed;\n  inset-inline-start: 0.75rem;\n  top: 0.75rem;\n  z-index: 13000;\n  transform: translateY(-180%);\n  background: var(--accent);\n  color: var(--accent-text);\n  padding: 0.65rem 0.85rem;\n  border-radius: 0.4rem;\n  font-weight: 700;\n}\n.skip-link:focus {\n  transform: none;\n}\n.shell,\n.published-site-vue-host {\n  min-height: 100vh;\n}\n.top {\n  border-bottom: 1px solid var(--border-subtle);\n  background: var(--bg);\n  position: sticky;\n  top: 0;\n  z-index: 5;\n}\n.top-inner,\n.main {\n  width: min(1080px, calc(100% - 2rem));\n  margin: auto;\n}\n.top-inner {\n  display: flex;\n  gap: 0.8rem;\n  align-items: center;\n  padding: 0.72rem 0;\n  flex-wrap: wrap;\n}\n.brand {\n  min-width: 13rem;\n  flex: 1;\n}\n.brand strong {\n  display: block;\n  font-size: 1.05rem;\n}\n.brand small,\n.muted,\n.meta {\n  color: var(--muted);\n}\nnav {\n  display: flex;\n  gap: 0.15rem;\n  flex-wrap: wrap;\n}\nnav button {\n  min-height: 2.5rem;\n  border-color: transparent;\n  border-radius: 0.3rem;\n  background: transparent;\n  padding: 0.4rem 0.65rem;\n}\nnav button[aria-current=\"page\"] {\n  background: transparent;\n  color: var(--accent);\n  border-color: transparent;\n  border-bottom: 3px solid var(--accent);\n  font-weight: 800;\n}\n.header-controls {\n  display: flex;\n  gap: 0.45rem;\n  align-items: end;\n  flex-wrap: wrap;\n}\n.compact-field {\n  display: grid;\n  gap: 0.18rem;\n  min-width: 8rem;\n}\n.compact-field > span {\n  font-size: 0.78rem;\n  font-weight: 800;\n  color: var(--muted);\n}\n.control {\n  width: 100%;\n}\n.toggle {\n  display: flex;\n  align-items: center;\n  gap: 0.45rem;\n  min-height: 2.75rem;\n  padding: 0.35rem 0.55rem;\n  border: 1px solid var(--border);\n  border-radius: 0.5rem;\n  background: var(--bg);\n  font-weight: 700;\n}\n.toggle input {\n  width: 1.1rem;\n  height: 1.1rem;\n}\n.main {\n  padding: 1.15rem 0 2.4rem;\n  scroll-margin-top: 6rem;\n}\n.hero {\n  margin-bottom: 1rem;\n}\n.hero h1 {\n  margin: 0.1rem 0;\n  font-size: clamp(1.4rem, 2.8vw, 2.05rem);\n  letter-spacing: -0.015em;\n}\n.hero p {\n  max-width: 68ch;\n  margin: 0.35rem 0 0;\n  color: var(--muted);\n}\n.panel,\n.card {\n  border: 1px solid var(--border-subtle);\n  border-radius: 0.7rem;\n  background: var(--surface);\n  padding: 1rem;\n}\n.stack {\n  display: grid;\n  gap: 0.8rem;\n}\n.grid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));\n  gap: 0.8rem;\n}\n.search-surface {\n  border: 1px solid var(--border-subtle);\n  border-radius: 0.85rem;\n  background: var(--surface);\n  padding: clamp(0.9rem, 2vw, 1.25rem);\n}\n.search-head {\n  display: grid;\n  gap: 0.2rem;\n  margin-bottom: 0.8rem;\n}\n.search-head h2 {\n  margin: 0;\n  font-size: 1.08rem;\n}\n.search-head p {\n  max-width: 68ch;\n  margin: 0;\n  color: var(--muted);\n}\n.search-form {\n  display: grid;\n  gap: 0.65rem;\n}\n.search-row {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) auto;\n  gap: 0.55rem;\n}\n.search-row .control {\n  min-height: 3rem;\n  font-size: 1.04rem;\n  background: var(--bg);\n}\n.search-toolbar {\n  display: flex;\n  gap: 0.75rem;\n  align-items: center;\n  justify-content: space-between;\n  flex-wrap: wrap;\n}\n.search-mode-field {\n  display: flex;\n  gap: 0.45rem;\n  align-items: center;\n  color: var(--muted);\n  font-size: 0.86rem;\n  font-weight: 700;\n}\n.search-mode-field .control {\n  width: auto;\n  min-width: 9rem;\n  min-height: 2.4rem;\n  padding: 0.35rem 0.55rem;\n}\n.search-refine {\n  border-top: 1px solid var(--border-subtle);\n  padding-top: 0.2rem;\n}\n.search-refine summary {\n  width: max-content;\n  max-width: 100%;\n  padding: 0.4rem 0;\n  cursor: pointer;\n  font-weight: 750;\n}\n.filters {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));\n  gap: 0.7rem;\n  margin: 0.45rem 0 0.15rem;\n}\n.search-results {\n  display: grid;\n  gap: 0;\n}\n.results-heading {\n  display: flex;\n  gap: 0.75rem;\n  align-items: end;\n  justify-content: space-between;\n  padding: 0.2rem 0 0.55rem;\n  border-bottom: 1px solid var(--border-subtle);\n}\n.results-heading h2 {\n  margin: 0;\n  font-size: 1rem;\n}\n.results-heading .meta {\n  font-size: 0.85rem;\n}\n.field {\n  display: grid;\n  gap: 0.3rem;\n}\n.field > span {\n  font-size: 0.82rem;\n  font-weight: 800;\n  color: var(--muted);\n}\n.result {\n  display: grid;\n  gap: 0.45rem;\n  padding: 1rem 0;\n  border: 0;\n  border-bottom: 1px solid var(--border-subtle);\n  border-radius: 0;\n  background: transparent;\n}\n.result-head {\n  display: flex;\n  gap: 0.7rem;\n  justify-content: space-between;\n  align-items: start;\n}\n.result .meta {\n  font-size: 0.88rem;\n}\n.result .ui-button-wrap {\n  justify-self: start;\n}\n.result button {\n  min-height: 2.35rem;\n  padding: 0.35rem 0.65rem;\n  background: transparent;\n}\nmark {\n  background: var(--mark-bg);\n  color: var(--mark-fg);\n  border-radius: 0.2em;\n  padding: 0 0.12em;\n  font-weight: 700;\n  text-decoration: underline;\n  text-decoration-thickness: 2px;\n  text-underline-offset: 0.15em;\n}\n.snippet,\n.record-text {\n  white-space: pre-wrap;\n}\n.chips,\n.method-strip {\n  display: flex;\n  flex-wrap: wrap;\n  gap: 0.35rem;\n}\n.chip,\n.method-badge {\n  font-size: 0.78rem;\n  padding: 0.18rem 0.48rem;\n  border-radius: 999px;\n  background: transparent;\n  border: 1px solid var(--border-subtle);\n}\n.method-strip {\n  margin: 0;\n}\n.method-badge[data-active=\"true\"] {\n  border-color: var(--border);\n  font-weight: 750;\n}\n.method-badge[data-active=\"false\"] {\n  opacity: 0.64;\n}\n.method-badge .state {\n  margin-inline-start: 0.25rem;\n  font-weight: 700;\n}\n.status {\n  min-height: 1.5rem;\n  color: var(--muted);\n  margin: 0.6rem 0;\n}\n.status.error {\n  color: var(--danger);\n  font-weight: 700;\n}\n.status.warning {\n  color: var(--warning);\n  font-weight: 700;\n}\n.status.success {\n  color: var(--success);\n  font-weight: 700;\n}\n.empty {\n  text-align: center;\n  padding: 2.3rem;\n  color: var(--muted);\n}\n.record-dialog {\n  width: min(900px, calc(100% - 2rem));\n  max-height: 88vh;\n  border: 2px solid var(--border);\n  border-radius: 0.9rem;\n  background: var(--bg);\n  color: var(--fg);\n  box-shadow: var(--shadow);\n  padding: 0;\n}\n.record-dialog::backdrop {\n  background: rgba(0, 0, 0, 0.65);\n}\n.record-text {\n  font-family: Georgia, serif;\n  font-size: 1.04rem;\n  line-height: 1.75;\n  border-block: 1px solid var(--border);\n  padding: 1rem 0;\n}\n.metadata {\n  display: grid;\n  grid-template-columns: minmax(9rem, auto) 1fr;\n  gap: 0.35rem 1rem;\n  font-size: 0.9rem;\n}\n.metadata dt {\n  font-weight: 800;\n}\n.metadata dd {\n  margin: 0;\n  overflow-wrap: anywhere;\n}\ntextarea {\n  min-height: 7rem;\n  resize: vertical;\n}\n.annotation {\n  border-inline-start: 4px solid var(--accent);\n  padding: 0.8rem 1rem;\n  background: var(--surface);\n}\n.annotation blockquote {\n  margin: 0.35rem 0;\n  font-family: Georgia, serif;\n}\n.research-layout {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) minmax(18rem, 24rem);\n  gap: 1rem;\n}\n.answer {\n  white-space: pre-wrap;\n  font-family: Georgia, serif;\n  font-size: 1.04rem;\n}\n.inline-citation {\n  font-family: inherit;\n}\n.research-evidence-pane {\n  align-self: start;\n  position: sticky;\n  top: 5.5rem;\n  max-height: calc(100vh - 6.5rem);\n  overflow: auto;\n  overscroll-behavior: contain;\n}\n.research-evidence-panel {\n  align-content: start;\n}\n.evidence-item {\n  scroll-margin-top: 6rem;\n}\n.work-button {\n  width: 100%;\n  height: 100%;\n  padding: 1rem;\n  justify-content: flex-start;\n  text-align: start;\n}\n.work-button .work-card-copy {\n  width: 100%;\n}\n.work-title {\n  display: block;\n  font-size: 1.1rem;\n  font-weight: 800;\n}\n.count {\n  font-size: 1.6rem;\n  font-weight: 800;\n}\n.provider-panel {\n  display: grid;\n  gap: 0.7rem;\n}\n.provider-form {\n  display: grid;\n  gap: 0.7rem;\n  padding-top: 0.8rem;\n  border-top: 1px solid var(--border);\n}\n.provider-summary {\n  padding: 0.65rem;\n  border: 1px solid var(--border);\n  border-radius: 0.5rem;\n  background: var(--bg);\n  overflow-wrap: anywhere;\n}\n[data-tour] {\n  scroll-margin: 6rem 0 1rem;\n}\ndialog.tour {\n  position: fixed;\n  inset: 0;\n  width: 100%;\n  height: 100%;\n  max-width: none;\n  max-height: none;\n  margin: 0;\n  border: 0;\n  border-radius: 0;\n  background: transparent;\n  box-shadow: none;\n  overflow: hidden;\n  color: var(--fg);\n}\ndialog.tour::backdrop {\n  background: transparent;\n}\ndialog.tour.tour-centered {\n  background: rgba(0, 0, 0, 0.72);\n}\n.tour-spot {\n  position: fixed;\n  border-radius: 0.65rem;\n  outline: 3px solid var(--accent);\n  box-shadow: 0 0 0 200vmax rgba(0, 0, 0, 0.72);\n  pointer-events: none;\n}\n.tour-centered .tour-spot {\n  display: none;\n}\n@media (prefers-reduced-motion: no-preference) {\n  .tour-spot {\n    transition:\n      left 0.2s,\n      top 0.2s,\n      width 0.2s,\n      height 0.2s;\n  }\n}\n.tour-card {\n  position: fixed;\n  width: min(26rem, calc(100% - 1rem));\n  max-height: calc(100% - 1rem);\n  overflow: auto;\n  background: var(--bg);\n  color: var(--fg);\n  border: 2px solid var(--border);\n  border-radius: 0.9rem;\n  box-shadow: var(--shadow);\n}\n.tour-centered .tour-card {\n  top: 50%;\n  left: 50%;\n  transform: translate(-50%, -50%);\n}\n.tour-dock .tour-card {\n  left: 0.5rem;\n  right: 0.5rem;\n  bottom: 0.5rem;\n  top: auto;\n  width: auto;\n}\n.tour-dock-top .tour-card {\n  left: 0.5rem;\n  right: 0.5rem;\n  top: 0.5rem;\n  bottom: auto;\n  width: auto;\n}\n.dialog-head {\n  position: sticky;\n  top: 0;\n  background: var(--bg);\n  border-bottom: 1px solid var(--border);\n  padding: 1rem;\n  display: flex;\n  justify-content: space-between;\n  gap: 1rem;\n  align-items: start;\n}\n.dialog-body {\n  padding: 1rem;\n  display: grid;\n  gap: 1rem;\n}\n.dialog-actions {\n  display: flex;\n  gap: 0.55rem;\n  justify-content: flex-end;\n  flex-wrap: wrap;\n  padding: 1rem;\n  border-top: 1px solid var(--border);\n}\n.tour-card .dialog-head {\n  position: static;\n  flex-direction: column;\n  gap: 0.15rem;\n}\n.tour-card h2 {\n  margin: 0;\n  font-size: 1.15rem;\n}\n.tour-bar {\n  height: 0.3rem;\n  background: var(--raised);\n}\n.tour-bar span {\n  display: block;\n  height: 100%;\n  background: var(--accent);\n}\n.tour-hint {\n  padding-block: 0;\n  font-size: 0.875rem;\n}\n.tutorial-progress {\n  font-weight: 800;\n  color: var(--muted);\n  font-size: 0.875rem;\n}\n.tutorial-copy {\n  margin: 0;\n  font-size: 1.02rem;\n}\n.footer {\n  margin-top: 3rem;\n  border-top: 1px solid var(--border);\n  padding: 1.2rem 0 2.5rem;\n  color: var(--muted);\n  font-size: 0.875rem;\n}\nprogress {\n  width: 100%;\n  height: 1rem;\n  accent-color: var(--accent);\n}\n.sr-only {\n  position: absolute !important;\n  width: 1px !important;\n  height: 1px !important;\n  padding: 0 !important;\n  margin: -1px !important;\n  overflow: hidden !important;\n  clip: rect(0, 0, 0, 0) !important;\n  white-space: nowrap !important;\n  border: 0 !important;\n}\n\n@media (max-width: 760px) {\n  .research-layout {\n    grid-template-columns: 1fr;\n  }\n  .research-evidence-pane {\n    position: static;\n    max-height: none;\n    overflow: visible;\n  }\n  .search-row {\n    grid-template-columns: 1fr;\n  }\n  .search-toolbar {\n    align-items: flex-start;\n    flex-direction: column;\n  }\n  .top {\n    position: static;\n  }\n  .top-inner,\n  .main {\n    width: min(100% - 1rem, 1080px);\n  }\n  .main {\n    scroll-margin-top: 1rem;\n  }\n  .header-controls {\n    width: 100%;\n  }\n  .metadata {\n    grid-template-columns: 1fr;\n  }\n}\n\n@media (forced-colors: active) {\n  .tour-spot {\n    outline: 4px solid Highlight;\n  }\n  mark {\n    background: Mark;\n    color: MarkText;\n    forced-color-adjust: none;\n  }\n  button,\n  .control,\n  .panel,\n  .card,\n  .method-badge,\n  .toggle {\n    forced-color-adjust: auto;\n  }\n  .method-badge[data-active=\"true\"] {\n    outline: 2px solid CanvasText;\n  }\n}\n";document.head.appendChild(style)})();
(function() {
  "use strict";
  // @__NO_SIDE_EFFECTS__
  function makeMap(str) {
    const map = /* @__PURE__ */ Object.create(null);
    for (const key of str.split(",")) map[key] = 1;
    return (val) => val in map;
  }
  const EMPTY_OBJ = {};
  const EMPTY_ARR = [];
  const NOOP = () => {
  };
  const NO = () => false;
  const isOn = (key) => key.charCodeAt(0) === 111 && key.charCodeAt(1) === 110 && // uppercase letter
  (key.charCodeAt(2) > 122 || key.charCodeAt(2) < 97);
  const isModelListener = (key) => key.startsWith("onUpdate:");
  const extend = Object.assign;
  const remove = (arr, el) => {
    const i = arr.indexOf(el);
    if (i > -1) {
      arr.splice(i, 1);
    }
  };
  const hasOwnProperty$1 = Object.prototype.hasOwnProperty;
  const hasOwn = (val, key) => hasOwnProperty$1.call(val, key);
  const isArray = Array.isArray;
  const isMap = (val) => toTypeString(val) === "[object Map]";
  const isSet = (val) => toTypeString(val) === "[object Set]";
  const isDate = (val) => toTypeString(val) === "[object Date]";
  const isFunction = (val) => typeof val === "function";
  const isString = (val) => typeof val === "string";
  const isSymbol = (val) => typeof val === "symbol";
  const isObject = (val) => val !== null && typeof val === "object";
  const isPromise = (val) => {
    return (isObject(val) || isFunction(val)) && isFunction(val.then) && isFunction(val.catch);
  };
  const objectToString = Object.prototype.toString;
  const toTypeString = (value) => objectToString.call(value);
  const toRawType = (value) => {
    return toTypeString(value).slice(8, -1);
  };
  const isPlainObject = (val) => toTypeString(val) === "[object Object]";
  const isIntegerKey = (key) => isString(key) && key !== "NaN" && key[0] !== "-" && "" + parseInt(key, 10) === key;
  const isReservedProp = /* @__PURE__ */ makeMap(
    // the leading comma is intentional so empty string "" is also included
    ",key,ref,ref_for,ref_key,onVnodeBeforeMount,onVnodeMounted,onVnodeBeforeUpdate,onVnodeUpdated,onVnodeBeforeUnmount,onVnodeUnmounted"
  );
  const cacheStringFunction = (fn) => {
    const cache = /* @__PURE__ */ Object.create(null);
    return ((str) => {
      const hit = cache[str];
      return hit || (cache[str] = fn(str));
    });
  };
  const camelizeRE = /-\w/g;
  const camelize = cacheStringFunction(
    (str) => {
      return str.replace(camelizeRE, (c) => c.slice(1).toUpperCase());
    }
  );
  const hyphenateRE = /\B([A-Z])/g;
  const hyphenate = cacheStringFunction(
    (str) => str.replace(hyphenateRE, "-$1").toLowerCase()
  );
  const capitalize = cacheStringFunction((str) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
  });
  const toHandlerKey = cacheStringFunction(
    (str) => {
      const s = str ? `on${capitalize(str)}` : ``;
      return s;
    }
  );
  const hasChanged = (value, oldValue) => !Object.is(value, oldValue);
  const invokeArrayFns = (fns, ...arg) => {
    for (let i = 0; i < fns.length; i++) {
      fns[i](...arg);
    }
  };
  const def = (obj, key, value, writable = false) => {
    Object.defineProperty(obj, key, {
      configurable: true,
      enumerable: false,
      writable,
      value
    });
  };
  const looseToNumber = (val) => {
    const n = parseFloat(val);
    return isNaN(n) ? val : n;
  };
  let _globalThis;
  const getGlobalThis = () => {
    return _globalThis || (_globalThis = typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : typeof window !== "undefined" ? window : typeof global !== "undefined" ? global : {});
  };
  function normalizeStyle(value) {
    if (isArray(value)) {
      const res = {};
      for (let i = 0; i < value.length; i++) {
        const item = value[i];
        const normalized = isString(item) ? parseStringStyle(item) : normalizeStyle(item);
        if (normalized) {
          for (const key in normalized) {
            res[key] = normalized[key];
          }
        }
      }
      return res;
    } else if (isString(value) || isObject(value)) {
      return value;
    }
  }
  const listDelimiterRE = /;(?![^(]*\))/g;
  const propertyDelimiterRE = /:([^]+)/;
  const styleCommentRE = /"(?:[^"\\]|\\[^])*"|'(?:[^'\\]|\\[^])*'|\\[^]|\/\*[^]*?\*\//g;
  function parseStringStyle(cssText) {
    const ret = {};
    cssText.replace(styleCommentRE, (match) => match.startsWith("/*") ? "" : match).split(listDelimiterRE).forEach((item) => {
      if (item) {
        const tmp = item.split(propertyDelimiterRE);
        tmp.length > 1 && (ret[tmp[0].trim()] = tmp[1].trim());
      }
    });
    return ret;
  }
  function normalizeClass(value) {
    let res = "";
    if (isString(value)) {
      res = value;
    } else if (isArray(value)) {
      for (let i = 0; i < value.length; i++) {
        const normalized = normalizeClass(value[i]);
        if (normalized) {
          res += normalized + " ";
        }
      }
    } else if (isObject(value)) {
      for (const name in value) {
        if (value[name]) {
          res += name + " ";
        }
      }
    }
    return res.trim();
  }
  const specialBooleanAttrs = `itemscope,allowfullscreen,formnovalidate,ismap,nomodule,novalidate,readonly`;
  const isSpecialBooleanAttr = /* @__PURE__ */ makeMap(specialBooleanAttrs);
  function includeBooleanAttr(value) {
    return !!value || value === "";
  }
  function looseCompareArrays(a, b, seen) {
    if (a.length !== b.length) return false;
    let equal = true;
    for (let i = 0; equal && i < a.length; i++) {
      equal = looseEqual(a[i], b[i], seen);
    }
    return equal;
  }
  function looseCompareCollections(a, b, seen) {
    if (a.size !== b.size) return false;
    const candidates = Array.from(b);
    const matched = new Uint8Array(candidates.length);
    for (const item of a) {
      let index = -1;
      for (let i = 0; i < candidates.length; i++) {
        if (!matched[i] && looseEqual(item, candidates[i], seen)) {
          index = i;
          break;
        }
      }
      if (index < 0) return false;
      matched[index] = 1;
    }
    return true;
  }
  function looseCompareObjects(a, b, seen) {
    let aValidType = isMap(a);
    let bValidType = isMap(b);
    if (aValidType || bValidType) {
      return aValidType && bValidType ? looseCompareCollections(a, b, seen) : false;
    }
    aValidType = isSet(a);
    bValidType = isSet(b);
    if (aValidType || bValidType) {
      return aValidType && bValidType ? looseCompareCollections(a, b, seen) : false;
    }
    const aKeysCount = Object.keys(a).length;
    const bKeysCount = Object.keys(b).length;
    if (aKeysCount !== bKeysCount) {
      return false;
    }
    for (const key in a) {
      const aHasKey = a.hasOwnProperty(key);
      const bHasKey = b.hasOwnProperty(key);
      if (aHasKey && !bHasKey || !aHasKey && bHasKey || !looseEqual(a[key], b[key], seen)) {
        return false;
      }
    }
    return String(a) === String(b);
  }
  function looseCompareNested(a, b, seen, compare) {
    if (!seen) {
      seen = [/* @__PURE__ */ new Map(), /* @__PURE__ */ new Map()];
    }
    const [seenA, seenB] = seen;
    if (seenA.has(a) || seenB.has(b)) {
      return seenA.get(a) === b && seenB.get(b) === a;
    }
    seenA.set(a, b);
    seenB.set(b, a);
    const equal = compare(a, b, seen);
    seenA.delete(a);
    seenB.delete(b);
    return equal;
  }
  function looseEqual(a, b, seen) {
    if (a === b) return true;
    let aValidType = isDate(a);
    let bValidType = isDate(b);
    if (aValidType || bValidType) {
      return aValidType && bValidType ? a.getTime() === b.getTime() : false;
    }
    aValidType = isSymbol(a);
    bValidType = isSymbol(b);
    if (aValidType || bValidType) {
      return a === b;
    }
    aValidType = isArray(a);
    bValidType = isArray(b);
    if (aValidType || bValidType) {
      return aValidType && bValidType ? looseCompareNested(a, b, seen, looseCompareArrays) : false;
    }
    aValidType = isObject(a);
    bValidType = isObject(b);
    if (aValidType || bValidType) {
      if (!aValidType || !bValidType) {
        return false;
      }
      return looseCompareNested(a, b, seen, looseCompareObjects);
    }
    return String(a) === String(b);
  }
  function looseIndexOf(arr, val) {
    return arr.findIndex((item) => looseEqual(item, val));
  }
  const isRef$1 = (val) => {
    return !!(val && val["__v_isRef"] === true);
  };
  const toDisplayString = (val) => {
    return isString(val) ? val : val == null ? "" : isArray(val) || isObject(val) && (val.toString === objectToString || !isFunction(val.toString)) ? isRef$1(val) ? toDisplayString(val.value) : JSON.stringify(val, replacer, 2) : String(val);
  };
  const replacer = (_key, val) => {
    if (isRef$1(val)) {
      return replacer(_key, val.value);
    } else if (isMap(val)) {
      return {
        [`Map(${val.size})`]: [...val.entries()].reduce(
          (entries, [key, val2], i) => {
            entries[stringifySymbol(key, i) + " =>"] = val2;
            return entries;
          },
          {}
        )
      };
    } else if (isSet(val)) {
      return {
        [`Set(${val.size})`]: [...val.values()].map((v) => stringifySymbol(v))
      };
    } else if (isSymbol(val)) {
      return stringifySymbol(val);
    } else if (isObject(val) && !isArray(val) && !isPlainObject(val)) {
      return String(val);
    }
    return val;
  };
  const stringifySymbol = (v, i = "") => {
    var _a;
    return (
      // Symbol.description in es2019+ so we need to cast here to pass
      // the lib: es2016 check
      isSymbol(v) ? `Symbol(${(_a = v.description) != null ? _a : i})` : v
    );
  };
  let activeEffectScope;
  class EffectScope {
    // TODO isolatedDeclarations "__v_skip"
    constructor(detached = false) {
      this.detached = detached;
      this._active = true;
      this._on = 0;
      this.effects = [];
      this.cleanups = [];
      this._isPaused = false;
      this._warnOnRun = true;
      this.__v_skip = true;
      if (!detached && activeEffectScope) {
        if (activeEffectScope.active) {
          this.parent = activeEffectScope;
          this.index = (activeEffectScope.scopes || (activeEffectScope.scopes = [])).push(
            this
          ) - 1;
        } else {
          this._active = false;
          this._warnOnRun = false;
        }
      }
    }
    get active() {
      return this._active;
    }
    pause() {
      if (this._active) {
        this._isPaused = true;
        let i, l;
        if (this.scopes) {
          const scopes = this.scopes.slice();
          for (i = 0, l = scopes.length; i < l; i++) {
            scopes[i].pause();
          }
        }
        for (i = 0, l = this.effects.length; i < l; i++) {
          this.effects[i].pause();
        }
      }
    }
    /**
     * Resumes the effect scope, including all child scopes and effects.
     */
    resume() {
      if (this._active) {
        if (this._isPaused) {
          this._isPaused = false;
          let i, l;
          if (this.scopes) {
            const scopes = this.scopes.slice();
            for (i = 0, l = scopes.length; i < l; i++) {
              scopes[i].resume();
            }
          }
          const effects = this.effects.slice();
          for (i = 0, l = effects.length; i < l; i++) {
            effects[i].resume();
          }
        }
      }
    }
    run(fn) {
      if (this._active) {
        const currentEffectScope = activeEffectScope;
        try {
          activeEffectScope = this;
          return fn();
        } finally {
          activeEffectScope = currentEffectScope;
        }
      }
    }
    /**
     * This should only be called on non-detached scopes
     * @internal
     */
    on() {
      if (++this._on === 1) {
        this.prevScope = activeEffectScope;
        activeEffectScope = this;
      }
    }
    /**
     * This should only be called on non-detached scopes
     * @internal
     */
    off() {
      if (this._on > 0 && --this._on === 0) {
        if (activeEffectScope === this) {
          activeEffectScope = this.prevScope;
        } else {
          let current = activeEffectScope;
          while (current) {
            if (current.prevScope === this) {
              current.prevScope = this.prevScope;
              break;
            }
            current = current.prevScope;
          }
        }
        this.prevScope = void 0;
      }
    }
    stop(fromParent) {
      if (this._active) {
        this._active = false;
        let i, l;
        for (i = 0, l = this.effects.length; i < l; i++) {
          this.effects[i].stop();
        }
        this.effects.length = 0;
        for (i = 0, l = this.cleanups.length; i < l; i++) {
          this.cleanups[i]();
        }
        this.cleanups.length = 0;
        if (this.scopes) {
          const scopes = this.scopes.slice();
          for (i = 0, l = scopes.length; i < l; i++) {
            scopes[i].stop(true);
          }
          this.scopes.length = 0;
        }
        if (!this.detached && this.parent && !fromParent) {
          const last = this.parent.scopes.pop();
          if (last && last !== this) {
            this.parent.scopes[this.index] = last;
            last.index = this.index;
          }
        }
        this.parent = void 0;
      }
    }
  }
  function getCurrentScope() {
    return activeEffectScope;
  }
  let activeSub;
  const pausedQueueEffects = /* @__PURE__ */ new WeakSet();
  class ReactiveEffect {
    constructor(fn) {
      this.fn = fn;
      this.deps = void 0;
      this.depsTail = void 0;
      this.flags = 1 | 4;
      this.next = void 0;
      this.cleanup = void 0;
      this.scheduler = void 0;
      if (activeEffectScope) {
        if (activeEffectScope.active) {
          activeEffectScope.effects.push(this);
        } else {
          this.flags &= -2;
        }
      }
    }
    pause() {
      this.flags |= 64;
    }
    resume() {
      if (this.flags & 64) {
        this.flags &= -65;
        if (pausedQueueEffects.has(this)) {
          pausedQueueEffects.delete(this);
          this.trigger();
        }
      }
    }
    /**
     * @internal
     */
    notify() {
      if (this.flags & 2 && !(this.flags & 32)) {
        return;
      }
      if (!(this.flags & 8)) {
        batch(this);
      }
    }
    run() {
      if (!(this.flags & 1)) {
        return this.fn();
      }
      this.flags |= 2;
      cleanupEffect(this);
      prepareDeps(this);
      const prevEffect = activeSub;
      const prevShouldTrack = shouldTrack;
      activeSub = this;
      shouldTrack = true;
      try {
        return this.fn();
      } finally {
        cleanupDeps(this);
        activeSub = prevEffect;
        shouldTrack = prevShouldTrack;
        this.flags &= -3;
      }
    }
    stop() {
      if (this.flags & 1) {
        for (let link = this.deps; link; link = link.nextDep) {
          removeSub(link);
        }
        this.deps = this.depsTail = void 0;
        cleanupEffect(this);
        this.onStop && this.onStop();
        this.flags &= -2;
      }
    }
    trigger() {
      if (this.flags & 64) {
        pausedQueueEffects.add(this);
      } else if (this.scheduler) {
        this.scheduler();
      } else {
        this.runIfDirty();
      }
    }
    /**
     * @internal
     */
    runIfDirty() {
      if (isDirty(this)) {
        this.run();
      }
    }
    get dirty() {
      return isDirty(this);
    }
  }
  let batchDepth = 0;
  let batchedSub;
  let batchedComputed;
  function batch(sub, isComputed = false) {
    sub.flags |= 8;
    if (isComputed) {
      sub.next = batchedComputed;
      batchedComputed = sub;
      return;
    }
    sub.next = batchedSub;
    batchedSub = sub;
  }
  function startBatch() {
    batchDepth++;
  }
  function endBatch() {
    if (--batchDepth > 0) {
      return;
    }
    if (batchedComputed) {
      let e = batchedComputed;
      batchedComputed = void 0;
      while (e) {
        const next = e.next;
        e.next = void 0;
        e.flags &= -9;
        e = next;
      }
    }
    let error;
    while (batchedSub) {
      let e = batchedSub;
      batchedSub = void 0;
      while (e) {
        const next = e.next;
        e.next = void 0;
        e.flags &= -9;
        if (e.flags & 1) {
          try {
            ;
            e.trigger();
          } catch (err) {
            if (!error) error = err;
          }
        }
        e = next;
      }
    }
    if (error) throw error;
  }
  function prepareDeps(sub) {
    for (let link = sub.deps; link; link = link.nextDep) {
      link.version = -1;
      link.prevActiveLink = link.dep.activeLink;
      link.dep.activeLink = link;
    }
  }
  function cleanupDeps(sub) {
    let head;
    let tail = sub.depsTail;
    let link = tail;
    while (link) {
      const prev = link.prevDep;
      if (link.version === -1) {
        if (link === tail) tail = prev;
        removeSub(link);
        removeDep(link);
      } else {
        head = link;
      }
      link.dep.activeLink = link.prevActiveLink;
      link.prevActiveLink = void 0;
      link = prev;
    }
    sub.deps = head;
    sub.depsTail = tail;
  }
  function isDirty(sub) {
    for (let link = sub.deps; link; link = link.nextDep) {
      if (link.dep.version !== link.version || link.dep.computed && (refreshComputed(link.dep.computed) || link.dep.version !== link.version)) {
        return true;
      }
    }
    if (sub._dirty) {
      return true;
    }
    return false;
  }
  function refreshComputed(computed2) {
    if (computed2.flags & 4 && !(computed2.flags & 16)) {
      return;
    }
    computed2.flags &= -17;
    if (computed2.globalVersion === globalVersion) {
      return;
    }
    computed2.globalVersion = globalVersion;
    if (!computed2.isSSR && computed2.flags & 128 && (!computed2.deps && !computed2._dirty || !isDirty(computed2))) {
      return;
    }
    computed2.flags |= 2;
    const dep = computed2.dep;
    const prevSub = activeSub;
    const prevShouldTrack = shouldTrack;
    activeSub = computed2;
    shouldTrack = true;
    try {
      prepareDeps(computed2);
      const value = computed2.fn(computed2._value);
      if (dep.version === 0 || hasChanged(value, computed2._value)) {
        computed2.flags |= 128;
        computed2._value = value;
        dep.version++;
      }
    } catch (err) {
      dep.version++;
      throw err;
    } finally {
      activeSub = prevSub;
      shouldTrack = prevShouldTrack;
      cleanupDeps(computed2);
      computed2.flags &= -3;
    }
  }
  function removeSub(link, soft = false) {
    const { dep, prevSub, nextSub } = link;
    if (prevSub) {
      prevSub.nextSub = nextSub;
      link.prevSub = void 0;
    }
    if (nextSub) {
      nextSub.prevSub = prevSub;
      link.nextSub = void 0;
    }
    if (dep.subs === link) {
      dep.subs = prevSub;
      if (!prevSub && dep.computed) {
        dep.computed.flags &= -5;
        for (let l = dep.computed.deps; l; l = l.nextDep) {
          removeSub(l, true);
        }
      }
    }
    if (!soft && !--dep.sc && dep.map) {
      dep.map.delete(dep.key);
    }
  }
  function removeDep(link) {
    const { prevDep, nextDep } = link;
    if (prevDep) {
      prevDep.nextDep = nextDep;
      link.prevDep = void 0;
    }
    if (nextDep) {
      nextDep.prevDep = prevDep;
      link.nextDep = void 0;
    }
  }
  let shouldTrack = true;
  const trackStack = [];
  function pauseTracking() {
    trackStack.push(shouldTrack);
    shouldTrack = false;
  }
  function resetTracking() {
    const last = trackStack.pop();
    shouldTrack = last === void 0 ? true : last;
  }
  function cleanupEffect(e) {
    const { cleanup } = e;
    e.cleanup = void 0;
    if (cleanup) {
      const prevSub = activeSub;
      activeSub = void 0;
      try {
        cleanup();
      } finally {
        activeSub = prevSub;
      }
    }
  }
  let globalVersion = 0;
  class Link {
    constructor(sub, dep) {
      this.sub = sub;
      this.dep = dep;
      this.version = dep.version;
      this.nextDep = this.prevDep = this.nextSub = this.prevSub = this.prevActiveLink = void 0;
    }
  }
  class Dep {
    // TODO isolatedDeclarations "__v_skip"
    constructor(computed2) {
      this.computed = computed2;
      this.version = 0;
      this.activeLink = void 0;
      this.subs = void 0;
      this.map = void 0;
      this.key = void 0;
      this.sc = 0;
      this.__v_skip = true;
    }
    track(debugInfo) {
      if (!activeSub || !shouldTrack || activeSub === this.computed) {
        return;
      }
      let link = this.activeLink;
      if (link === void 0 || link.sub !== activeSub) {
        link = this.activeLink = new Link(activeSub, this);
        if (!activeSub.deps) {
          activeSub.deps = activeSub.depsTail = link;
        } else {
          link.prevDep = activeSub.depsTail;
          activeSub.depsTail.nextDep = link;
          activeSub.depsTail = link;
        }
        addSub(link);
      } else if (link.version === -1) {
        link.version = this.version;
        if (link.nextDep) {
          const next = link.nextDep;
          next.prevDep = link.prevDep;
          if (link.prevDep) {
            link.prevDep.nextDep = next;
          }
          link.prevDep = activeSub.depsTail;
          link.nextDep = void 0;
          activeSub.depsTail.nextDep = link;
          activeSub.depsTail = link;
          if (activeSub.deps === link) {
            activeSub.deps = next;
          }
        }
      }
      return link;
    }
    trigger(debugInfo) {
      this.version++;
      globalVersion++;
      this.notify(debugInfo);
    }
    notify(debugInfo) {
      startBatch();
      try {
        if (false) ;
        for (let link = this.subs; link; link = link.prevSub) {
          if (link.sub.notify()) {
            ;
            link.sub.dep.notify();
          }
        }
      } finally {
        endBatch();
      }
    }
  }
  function addSub(link) {
    link.dep.sc++;
    if (link.sub.flags & 4) {
      const computed2 = link.dep.computed;
      if (computed2 && !link.dep.subs) {
        computed2.flags |= 4 | 16;
        for (let l = computed2.deps; l; l = l.nextDep) {
          addSub(l);
        }
      }
      const currentTail = link.dep.subs;
      if (currentTail !== link) {
        link.prevSub = currentTail;
        if (currentTail) currentTail.nextSub = link;
      }
      link.dep.subs = link;
    }
  }
  const targetMap = /* @__PURE__ */ new WeakMap();
  const ITERATE_KEY = /* @__PURE__ */ Symbol(
    ""
  );
  const MAP_KEY_ITERATE_KEY = /* @__PURE__ */ Symbol(
    ""
  );
  const ARRAY_ITERATE_KEY = /* @__PURE__ */ Symbol(
    ""
  );
  function track(target, type, key) {
    if (shouldTrack && activeSub) {
      let depsMap = targetMap.get(target);
      if (!depsMap) {
        targetMap.set(target, depsMap = /* @__PURE__ */ new Map());
      }
      let dep = depsMap.get(key);
      if (!dep) {
        depsMap.set(key, dep = new Dep());
        dep.map = depsMap;
        dep.key = key;
      }
      {
        dep.track();
      }
    }
  }
  function trigger(target, type, key, newValue, oldValue, oldTarget) {
    const depsMap = targetMap.get(target);
    if (!depsMap) {
      globalVersion++;
      return;
    }
    const run = (dep) => {
      if (dep) {
        {
          dep.trigger();
        }
      }
    };
    startBatch();
    if (type === "clear") {
      depsMap.forEach(run);
    } else {
      const targetIsArray = isArray(target);
      const isArrayIndex = targetIsArray && isIntegerKey(key);
      if (targetIsArray && key === "length") {
        const newLength = Number(newValue);
        depsMap.forEach((dep, key2) => {
          if (key2 === "length" || key2 === ARRAY_ITERATE_KEY || !isSymbol(key2) && key2 >= newLength) {
            run(dep);
          }
        });
      } else {
        if (key !== void 0 || depsMap.has(void 0)) {
          run(depsMap.get(key));
        }
        if (isArrayIndex) {
          run(depsMap.get(ARRAY_ITERATE_KEY));
        }
        switch (type) {
          case "add":
            if (!targetIsArray) {
              run(depsMap.get(ITERATE_KEY));
              if (isMap(target)) {
                run(depsMap.get(MAP_KEY_ITERATE_KEY));
              }
            } else if (isArrayIndex) {
              run(depsMap.get("length"));
            }
            break;
          case "delete":
            if (!targetIsArray) {
              run(depsMap.get(ITERATE_KEY));
              if (isMap(target)) {
                run(depsMap.get(MAP_KEY_ITERATE_KEY));
              }
            }
            break;
          case "set":
            if (isMap(target)) {
              run(depsMap.get(ITERATE_KEY));
            }
            break;
        }
      }
    }
    endBatch();
  }
  function reactiveReadArray(array) {
    const raw = /* @__PURE__ */ toRaw(array);
    if (raw === array) return raw;
    track(raw, "iterate", ARRAY_ITERATE_KEY);
    if (/* @__PURE__ */ isShallow(array)) return raw;
    if (!/* @__PURE__ */ isReadonly(array)) return raw.map(toReactive);
    return /* @__PURE__ */ isReactive(array) ? raw.map((item) => toReadonly(toReactive(item))) : raw.map(toReadonly);
  }
  function shallowReadArray(arr) {
    track(arr = /* @__PURE__ */ toRaw(arr), "iterate", ARRAY_ITERATE_KEY);
    return arr;
  }
  function toWrapped(target, item) {
    if (/* @__PURE__ */ isReadonly(target)) {
      return /* @__PURE__ */ isReactive(target) ? toReadonly(toReactive(item)) : toReadonly(item);
    }
    return toReactive(item);
  }
  const arrayInstrumentations = {
    __proto__: null,
    [Symbol.iterator]() {
      return iterator(this, Symbol.iterator, (item) => toWrapped(this, item));
    },
    concat(...args) {
      return reactiveReadArray(this).concat(
        ...args.map((x) => isArray(x) ? reactiveReadArray(x) : x)
      );
    },
    entries() {
      return iterator(this, "entries", (value) => {
        value[1] = toWrapped(this, value[1]);
        return value;
      });
    },
    every(fn, thisArg) {
      return apply(this, "every", fn, thisArg, void 0, arguments);
    },
    filter(fn, thisArg) {
      return apply(
        this,
        "filter",
        fn,
        thisArg,
        (v) => v.map((item) => toWrapped(this, item)),
        arguments
      );
    },
    find(fn, thisArg) {
      return apply(
        this,
        "find",
        fn,
        thisArg,
        (item) => toWrapped(this, item),
        arguments
      );
    },
    findIndex(fn, thisArg) {
      return apply(this, "findIndex", fn, thisArg, void 0, arguments);
    },
    findLast(fn, thisArg) {
      return apply(
        this,
        "findLast",
        fn,
        thisArg,
        (item) => toWrapped(this, item),
        arguments
      );
    },
    findLastIndex(fn, thisArg) {
      return apply(this, "findLastIndex", fn, thisArg, void 0, arguments);
    },
    // flat, flatMap could benefit from ARRAY_ITERATE but are not straight-forward to implement
    forEach(fn, thisArg) {
      return apply(this, "forEach", fn, thisArg, void 0, arguments);
    },
    includes(...args) {
      return searchProxy(this, "includes", args);
    },
    indexOf(...args) {
      return searchProxy(this, "indexOf", args);
    },
    join(separator) {
      return reactiveReadArray(this).join(separator);
    },
    // keys() iterator only reads `length`, no optimization required
    lastIndexOf(...args) {
      return searchProxy(this, "lastIndexOf", args);
    },
    map(fn, thisArg) {
      return apply(this, "map", fn, thisArg, void 0, arguments);
    },
    pop() {
      return noTracking(this, "pop");
    },
    push(...args) {
      return noTracking(this, "push", args);
    },
    reduce(fn, ...args) {
      return reduce(this, "reduce", fn, args);
    },
    reduceRight(fn, ...args) {
      return reduce(this, "reduceRight", fn, args);
    },
    shift() {
      return noTracking(this, "shift");
    },
    // slice could use ARRAY_ITERATE but also seems to beg for range tracking
    some(fn, thisArg) {
      return apply(this, "some", fn, thisArg, void 0, arguments);
    },
    splice(...args) {
      return noTracking(this, "splice", args);
    },
    toReversed() {
      return reactiveReadArray(this).toReversed();
    },
    toSorted(comparer) {
      return reactiveReadArray(this).toSorted(comparer);
    },
    toSpliced(...args) {
      return reactiveReadArray(this).toSpliced(...args);
    },
    unshift(...args) {
      return noTracking(this, "unshift", args);
    },
    values() {
      return iterator(this, "values", (item) => toWrapped(this, item));
    }
  };
  function iterator(self2, method, wrapValue) {
    const arr = shallowReadArray(self2);
    const iter = arr[method]();
    if (arr !== self2 && !/* @__PURE__ */ isShallow(self2)) {
      iter._next = iter.next;
      iter.next = () => {
        const result = iter._next();
        if (!result.done) {
          result.value = wrapValue(result.value);
        }
        return result;
      };
    }
    return iter;
  }
  const arrayProto = Array.prototype;
  function apply(self2, method, fn, thisArg, wrappedRetFn, args) {
    const arr = shallowReadArray(self2);
    const needsWrap = arr !== self2 && !/* @__PURE__ */ isShallow(self2);
    const methodFn = arr[method];
    if (methodFn !== arrayProto[method]) {
      const result2 = methodFn.apply(self2, args);
      return needsWrap ? toReactive(result2) : result2;
    }
    let wrappedFn = fn;
    if (arr !== self2) {
      if (needsWrap) {
        wrappedFn = function(item, index) {
          return fn.call(this, toWrapped(self2, item), index, self2);
        };
      } else if (fn.length > 2) {
        wrappedFn = function(item, index) {
          return fn.call(this, item, index, self2);
        };
      }
    }
    const result = methodFn.call(arr, wrappedFn, thisArg);
    return needsWrap && wrappedRetFn ? wrappedRetFn(result) : result;
  }
  function reduce(self2, method, fn, args) {
    const arr = shallowReadArray(self2);
    const needsWrap = arr !== self2 && !/* @__PURE__ */ isShallow(self2);
    let wrappedFn = fn;
    let wrapInitialAccumulator = false;
    if (arr !== self2) {
      if (needsWrap) {
        wrapInitialAccumulator = args.length === 0;
        wrappedFn = function(acc, item, index) {
          if (wrapInitialAccumulator) {
            wrapInitialAccumulator = false;
            acc = toWrapped(self2, acc);
          }
          return fn.call(this, acc, toWrapped(self2, item), index, self2);
        };
      } else if (fn.length > 3) {
        wrappedFn = function(acc, item, index) {
          return fn.call(this, acc, item, index, self2);
        };
      }
    }
    const result = arr[method](wrappedFn, ...args);
    return wrapInitialAccumulator ? toWrapped(self2, result) : result;
  }
  function searchProxy(self2, method, args) {
    const arr = /* @__PURE__ */ toRaw(self2);
    track(arr, "iterate", ARRAY_ITERATE_KEY);
    const res = arr[method](...args);
    if ((res === -1 || res === false) && /* @__PURE__ */ isProxy(args[0])) {
      args[0] = /* @__PURE__ */ toRaw(args[0]);
      return arr[method](...args);
    }
    return res;
  }
  function noTracking(self2, method, args = []) {
    pauseTracking();
    startBatch();
    const res = (/* @__PURE__ */ toRaw(self2))[method].apply(self2, args);
    endBatch();
    resetTracking();
    return res;
  }
  const isNonTrackableKeys = /* @__PURE__ */ makeMap(`__proto__,__v_isRef,__isVue`);
  const builtInSymbols = new Set(
    /* @__PURE__ */ Object.getOwnPropertyNames(Symbol).filter((key) => key !== "arguments" && key !== "caller").map((key) => Symbol[key]).filter(isSymbol)
  );
  function hasOwnProperty(key) {
    if (!isSymbol(key)) key = String(key);
    const obj = /* @__PURE__ */ toRaw(this);
    track(obj, "has", key);
    return obj.hasOwnProperty(key);
  }
  class BaseReactiveHandler {
    constructor(_isReadonly = false, _isShallow = false) {
      this._isReadonly = _isReadonly;
      this._isShallow = _isShallow;
    }
    get(target, key, receiver) {
      if (key === "__v_skip") return target["__v_skip"];
      const isReadonly2 = this._isReadonly, isShallow2 = this._isShallow;
      if (key === "__v_isReactive") {
        return !isReadonly2;
      } else if (key === "__v_isReadonly") {
        return isReadonly2;
      } else if (key === "__v_isShallow") {
        return isShallow2;
      } else if (key === "__v_raw") {
        if (receiver === (isReadonly2 ? isShallow2 ? shallowReadonlyMap : readonlyMap : isShallow2 ? shallowReactiveMap : reactiveMap).get(target) || // receiver is not the reactive proxy, but has the same prototype
        // this means the receiver is a user proxy of the reactive proxy
        Object.getPrototypeOf(target) === Object.getPrototypeOf(receiver)) {
          return target;
        }
        return;
      }
      const targetIsArray = isArray(target);
      if (!isReadonly2) {
        let fn;
        if (targetIsArray && (fn = arrayInstrumentations[key])) {
          return fn;
        }
        if (key === "hasOwnProperty") {
          return hasOwnProperty;
        }
      }
      const res = Reflect.get(
        target,
        key,
        // if this is a proxy wrapping a ref, return methods using the raw ref
        // as receiver so that we don't have to call `toRaw` on the ref in all
        // its class methods
        /* @__PURE__ */ isRef(target) ? target : receiver
      );
      if (isSymbol(key) ? builtInSymbols.has(key) : isNonTrackableKeys(key)) {
        return res;
      }
      if (!isReadonly2) {
        track(target, "get", key);
      }
      if (isShallow2) {
        return res;
      }
      if (/* @__PURE__ */ isRef(res)) {
        const value = targetIsArray && isIntegerKey(key) ? res : res.value;
        return isReadonly2 && isObject(value) ? /* @__PURE__ */ readonly(value) : value;
      }
      if (isObject(res)) {
        return isReadonly2 ? /* @__PURE__ */ readonly(res) : /* @__PURE__ */ reactive(res);
      }
      return res;
    }
  }
  class MutableReactiveHandler extends BaseReactiveHandler {
    constructor(isShallow2 = false) {
      super(false, isShallow2);
    }
    set(target, key, value, receiver) {
      let oldValue = target[key];
      const isArrayWithIntegerKey = isArray(target) && isIntegerKey(key);
      if (!this._isShallow) {
        const isOldValueReadonly = /* @__PURE__ */ isReadonly(oldValue);
        if (!/* @__PURE__ */ isShallow(value) && !/* @__PURE__ */ isReadonly(value)) {
          oldValue = /* @__PURE__ */ toRaw(oldValue);
          value = /* @__PURE__ */ toRaw(value);
        }
        if (!isArrayWithIntegerKey && /* @__PURE__ */ isRef(oldValue) && !/* @__PURE__ */ isRef(value)) {
          if (isOldValueReadonly) {
            return true;
          } else {
            oldValue.value = value;
            return true;
          }
        }
      }
      const hadKey = isArrayWithIntegerKey ? Number(key) < target.length : hasOwn(target, key);
      const result = Reflect.set(
        target,
        key,
        value,
        /* @__PURE__ */ isRef(target) ? target : receiver
      );
      if (target === /* @__PURE__ */ toRaw(receiver) && result) {
        if (!hadKey) {
          trigger(target, "add", key, value);
        } else if (hasChanged(value, oldValue)) {
          trigger(target, "set", key, value);
        }
      }
      return result;
    }
    deleteProperty(target, key) {
      const hadKey = hasOwn(target, key);
      target[key];
      const result = Reflect.deleteProperty(target, key);
      if (result && hadKey) {
        trigger(target, "delete", key, void 0);
      }
      return result;
    }
    has(target, key) {
      const result = Reflect.has(target, key);
      if (!isSymbol(key) || !builtInSymbols.has(key)) {
        track(target, "has", key);
      }
      return result;
    }
    ownKeys(target) {
      track(
        target,
        "iterate",
        isArray(target) ? "length" : ITERATE_KEY
      );
      return Reflect.ownKeys(target);
    }
  }
  class ReadonlyReactiveHandler extends BaseReactiveHandler {
    constructor(isShallow2 = false) {
      super(true, isShallow2);
    }
    set(target, key) {
      return true;
    }
    deleteProperty(target, key) {
      return true;
    }
  }
  const mutableHandlers = /* @__PURE__ */ new MutableReactiveHandler();
  const readonlyHandlers = /* @__PURE__ */ new ReadonlyReactiveHandler();
  const shallowReactiveHandlers = /* @__PURE__ */ new MutableReactiveHandler(true);
  const shallowReadonlyHandlers = /* @__PURE__ */ new ReadonlyReactiveHandler(true);
  const toShallow = (value) => value;
  const getProto = (v) => Reflect.getPrototypeOf(v);
  function createIterableMethod(method, isReadonly2, isShallow2) {
    return function(...args) {
      const target = this["__v_raw"];
      const rawTarget = /* @__PURE__ */ toRaw(target);
      const targetIsMap = isMap(rawTarget);
      const isPair = method === "entries" || method === Symbol.iterator && targetIsMap;
      const isKeyOnly = method === "keys" && targetIsMap;
      const innerIterator = target[method](...args);
      const wrap = isShallow2 ? toShallow : isReadonly2 ? toReadonly : toReactive;
      !isReadonly2 && track(
        rawTarget,
        "iterate",
        isKeyOnly ? MAP_KEY_ITERATE_KEY : ITERATE_KEY
      );
      return extend(
        // inheriting all iterator properties
        Object.create(innerIterator),
        {
          // iterator protocol
          next() {
            const { value, done } = innerIterator.next();
            return done ? { value, done } : {
              value: isPair ? [wrap(value[0]), wrap(value[1])] : wrap(value),
              done
            };
          }
        }
      );
    };
  }
  function createReadonlyMethod(type) {
    return function(...args) {
      return type === "delete" ? false : type === "clear" ? void 0 : this;
    };
  }
  function createInstrumentations(readonly2, shallow) {
    const instrumentations = {
      get(key) {
        const target = this["__v_raw"];
        const rawTarget = /* @__PURE__ */ toRaw(target);
        const rawKey = /* @__PURE__ */ toRaw(key);
        if (!readonly2) {
          if (hasChanged(key, rawKey)) {
            track(rawTarget, "get", key);
          }
          track(rawTarget, "get", rawKey);
        }
        const { has } = getProto(rawTarget);
        const wrap = shallow ? toShallow : readonly2 ? toReadonly : toReactive;
        if (has.call(rawTarget, key)) {
          return wrap(target.get(key));
        } else if (has.call(rawTarget, rawKey)) {
          return wrap(target.get(rawKey));
        } else if (target !== rawTarget) {
          target.get(key);
        }
      },
      get size() {
        const target = this["__v_raw"];
        !readonly2 && track(/* @__PURE__ */ toRaw(target), "iterate", ITERATE_KEY);
        return target.size;
      },
      has(key) {
        const target = this["__v_raw"];
        const rawTarget = /* @__PURE__ */ toRaw(target);
        const rawKey = /* @__PURE__ */ toRaw(key);
        if (!readonly2) {
          if (hasChanged(key, rawKey)) {
            track(rawTarget, "has", key);
          }
          track(rawTarget, "has", rawKey);
        }
        return key === rawKey ? target.has(key) : target.has(key) || target.has(rawKey);
      },
      forEach(callback, thisArg) {
        const observed = this;
        const target = observed["__v_raw"];
        const rawTarget = /* @__PURE__ */ toRaw(target);
        const wrap = shallow ? toShallow : readonly2 ? toReadonly : toReactive;
        !readonly2 && track(rawTarget, "iterate", ITERATE_KEY);
        return target.forEach((value, key) => {
          return callback.call(thisArg, wrap(value), wrap(key), observed);
        });
      }
    };
    extend(
      instrumentations,
      readonly2 ? {
        add: createReadonlyMethod("add"),
        set: createReadonlyMethod("set"),
        delete: createReadonlyMethod("delete"),
        clear: createReadonlyMethod("clear")
      } : {
        add(value) {
          const target = /* @__PURE__ */ toRaw(this);
          const proto = getProto(target);
          const rawValue = /* @__PURE__ */ toRaw(value);
          const valueToAdd = !shallow && !/* @__PURE__ */ isShallow(value) && !/* @__PURE__ */ isReadonly(value) ? rawValue : value;
          const hadKey = proto.has.call(target, valueToAdd) || hasChanged(value, valueToAdd) && proto.has.call(target, value) || hasChanged(rawValue, valueToAdd) && proto.has.call(target, rawValue);
          if (!hadKey) {
            target.add(valueToAdd);
            trigger(target, "add", valueToAdd, valueToAdd);
          }
          return this;
        },
        set(key, value) {
          if (!shallow && !/* @__PURE__ */ isShallow(value) && !/* @__PURE__ */ isReadonly(value)) {
            value = /* @__PURE__ */ toRaw(value);
          }
          const target = /* @__PURE__ */ toRaw(this);
          const { has, get } = getProto(target);
          let hadKey = has.call(target, key);
          if (!hadKey) {
            key = /* @__PURE__ */ toRaw(key);
            hadKey = has.call(target, key);
          }
          const oldValue = get.call(target, key);
          target.set(key, value);
          if (!hadKey) {
            trigger(target, "add", key, value);
          } else if (hasChanged(value, oldValue)) {
            trigger(target, "set", key, value);
          }
          return this;
        },
        delete(key) {
          const target = /* @__PURE__ */ toRaw(this);
          const { has, get } = getProto(target);
          let hadKey = has.call(target, key);
          if (!hadKey) {
            key = /* @__PURE__ */ toRaw(key);
            hadKey = has.call(target, key);
          }
          get ? get.call(target, key) : void 0;
          const result = target.delete(key);
          if (hadKey) {
            trigger(target, "delete", key, void 0);
          }
          return result;
        },
        clear() {
          const target = /* @__PURE__ */ toRaw(this);
          const hadItems = target.size !== 0;
          const result = target.clear();
          if (hadItems) {
            trigger(
              target,
              "clear",
              void 0,
              void 0
            );
          }
          return result;
        }
      }
    );
    const iteratorMethods = [
      "keys",
      "values",
      "entries",
      Symbol.iterator
    ];
    iteratorMethods.forEach((method) => {
      instrumentations[method] = createIterableMethod(method, readonly2, shallow);
    });
    return instrumentations;
  }
  function createInstrumentationGetter(isReadonly2, shallow) {
    const instrumentations = createInstrumentations(isReadonly2, shallow);
    return (target, key, receiver) => {
      if (key === "__v_isReactive") {
        return !isReadonly2;
      } else if (key === "__v_isReadonly") {
        return isReadonly2;
      } else if (key === "__v_raw") {
        return target;
      }
      return Reflect.get(
        hasOwn(instrumentations, key) && key in target ? instrumentations : target,
        key,
        receiver
      );
    };
  }
  const mutableCollectionHandlers = {
    get: /* @__PURE__ */ createInstrumentationGetter(false, false)
  };
  const shallowCollectionHandlers = {
    get: /* @__PURE__ */ createInstrumentationGetter(false, true)
  };
  const readonlyCollectionHandlers = {
    get: /* @__PURE__ */ createInstrumentationGetter(true, false)
  };
  const shallowReadonlyCollectionHandlers = {
    get: /* @__PURE__ */ createInstrumentationGetter(true, true)
  };
  const reactiveMap = /* @__PURE__ */ new WeakMap();
  const shallowReactiveMap = /* @__PURE__ */ new WeakMap();
  const readonlyMap = /* @__PURE__ */ new WeakMap();
  const shallowReadonlyMap = /* @__PURE__ */ new WeakMap();
  function targetTypeMap(rawType) {
    switch (rawType) {
      case "Object":
      case "Array":
        return 1;
      case "Map":
      case "Set":
      case "WeakMap":
      case "WeakSet":
        return 2;
      default:
        return 0;
    }
  }
  // @__NO_SIDE_EFFECTS__
  function reactive(target) {
    if (/* @__PURE__ */ isReadonly(target)) {
      return target;
    }
    return createReactiveObject(
      target,
      false,
      mutableHandlers,
      mutableCollectionHandlers,
      reactiveMap
    );
  }
  // @__NO_SIDE_EFFECTS__
  function shallowReactive(target) {
    return createReactiveObject(
      target,
      false,
      shallowReactiveHandlers,
      shallowCollectionHandlers,
      shallowReactiveMap
    );
  }
  // @__NO_SIDE_EFFECTS__
  function readonly(target) {
    return createReactiveObject(
      target,
      true,
      readonlyHandlers,
      readonlyCollectionHandlers,
      readonlyMap
    );
  }
  // @__NO_SIDE_EFFECTS__
  function shallowReadonly(target) {
    return createReactiveObject(
      target,
      true,
      shallowReadonlyHandlers,
      shallowReadonlyCollectionHandlers,
      shallowReadonlyMap
    );
  }
  function createReactiveObject(target, isReadonly2, baseHandlers, collectionHandlers, proxyMap) {
    if (!isObject(target)) {
      return target;
    }
    if (target["__v_raw"] && !(isReadonly2 && target["__v_isReactive"])) {
      return target;
    }
    if (target["__v_skip"] || !Object.isExtensible(target)) {
      return target;
    }
    const existingProxy = proxyMap.get(target);
    if (existingProxy) {
      return existingProxy;
    }
    const targetType = targetTypeMap(toRawType(target));
    if (targetType === 0) {
      return target;
    }
    const proxy = new Proxy(
      target,
      targetType === 2 ? collectionHandlers : baseHandlers
    );
    proxyMap.set(target, proxy);
    return proxy;
  }
  // @__NO_SIDE_EFFECTS__
  function isReactive(value) {
    if (/* @__PURE__ */ isReadonly(value)) {
      return /* @__PURE__ */ isReactive(value["__v_raw"]);
    }
    return !!(value && value["__v_isReactive"]);
  }
  // @__NO_SIDE_EFFECTS__
  function isReadonly(value) {
    return !!(value && value["__v_isReadonly"]);
  }
  // @__NO_SIDE_EFFECTS__
  function isShallow(value) {
    return !!(value && value["__v_isShallow"]);
  }
  // @__NO_SIDE_EFFECTS__
  function isProxy(value) {
    return value ? !!value["__v_raw"] : false;
  }
  // @__NO_SIDE_EFFECTS__
  function toRaw(observed) {
    const raw = observed && observed["__v_raw"];
    return raw ? /* @__PURE__ */ toRaw(raw) : observed;
  }
  function markRaw(value) {
    if (!hasOwn(value, "__v_skip") && Object.isExtensible(value)) {
      def(value, "__v_skip", true);
    }
    return value;
  }
  const toReactive = (value) => isObject(value) ? /* @__PURE__ */ reactive(value) : value;
  const toReadonly = (value) => isObject(value) ? /* @__PURE__ */ readonly(value) : value;
  // @__NO_SIDE_EFFECTS__
  function isRef(r) {
    return r ? r["__v_isRef"] === true : false;
  }
  // @__NO_SIDE_EFFECTS__
  function ref(value) {
    return createRef(value, false);
  }
  function createRef(rawValue, shallow) {
    if (/* @__PURE__ */ isRef(rawValue)) {
      return rawValue;
    }
    return new RefImpl(rawValue, shallow);
  }
  class RefImpl {
    constructor(value, isShallow2) {
      this.dep = new Dep();
      this["__v_isRef"] = true;
      this["__v_isShallow"] = false;
      this._rawValue = isShallow2 ? value : /* @__PURE__ */ toRaw(value);
      this._value = isShallow2 ? value : toReactive(value);
      this["__v_isShallow"] = isShallow2;
    }
    get value() {
      {
        this.dep.track();
      }
      return this._value;
    }
    set value(newValue) {
      const oldValue = this._rawValue;
      const useDirectValue = this["__v_isShallow"] || /* @__PURE__ */ isShallow(newValue) || /* @__PURE__ */ isReadonly(newValue);
      newValue = useDirectValue ? newValue : /* @__PURE__ */ toRaw(newValue);
      if (hasChanged(newValue, oldValue)) {
        this._rawValue = newValue;
        this._value = useDirectValue ? newValue : toReactive(newValue);
        {
          this.dep.trigger();
        }
      }
    }
  }
  function unref(ref2) {
    return /* @__PURE__ */ isRef(ref2) ? ref2.value : ref2;
  }
  const shallowUnwrapHandlers = {
    get: (target, key, receiver) => key === "__v_raw" ? target : unref(Reflect.get(target, key, receiver)),
    set: (target, key, value, receiver) => {
      const oldValue = target[key];
      if (/* @__PURE__ */ isRef(oldValue) && !/* @__PURE__ */ isRef(value)) {
        oldValue.value = value;
        return true;
      } else {
        return Reflect.set(target, key, value, receiver);
      }
    }
  };
  function proxyRefs(objectWithRefs) {
    return /* @__PURE__ */ isReactive(objectWithRefs) ? objectWithRefs : new Proxy(objectWithRefs, shallowUnwrapHandlers);
  }
  class ComputedRefImpl {
    constructor(fn, setter, isSSR) {
      this.fn = fn;
      this.setter = setter;
      this._value = void 0;
      this.dep = new Dep(this);
      this.__v_isRef = true;
      this.deps = void 0;
      this.depsTail = void 0;
      this.flags = 16;
      this.globalVersion = globalVersion - 1;
      this.next = void 0;
      this.effect = this;
      this["__v_isReadonly"] = !setter;
      this.isSSR = isSSR;
    }
    /**
     * @internal
     */
    notify() {
      this.flags |= 16;
      if (!(this.flags & 8) && // avoid infinite self recursion
      activeSub !== this) {
        batch(this, true);
        return true;
      }
    }
    get value() {
      const link = this.dep.track();
      refreshComputed(this);
      if (link) {
        link.version = this.dep.version;
      }
      return this._value;
    }
    set value(newValue) {
      if (this.setter) {
        this.setter(newValue);
      }
    }
  }
  // @__NO_SIDE_EFFECTS__
  function computed$1(getterOrOptions, debugOptions, isSSR = false) {
    let getter;
    let setter;
    if (isFunction(getterOrOptions)) {
      getter = getterOrOptions;
    } else {
      getter = getterOrOptions.get;
      setter = getterOrOptions.set;
    }
    const cRef = new ComputedRefImpl(getter, setter, isSSR);
    return cRef;
  }
  const INITIAL_WATCHER_VALUE = {};
  const cleanupMap = /* @__PURE__ */ new WeakMap();
  let activeWatcher = void 0;
  function onWatcherCleanup(cleanupFn, failSilently = false, owner = activeWatcher) {
    if (owner) {
      let cleanups = cleanupMap.get(owner);
      if (!cleanups) cleanupMap.set(owner, cleanups = []);
      cleanups.push(cleanupFn);
    }
  }
  function watch$1(source, cb, options = EMPTY_OBJ) {
    const { immediate, deep, once, scheduler, augmentJob, call } = options;
    const reactiveGetter = (source2) => {
      if (deep) return source2;
      if (/* @__PURE__ */ isShallow(source2) || deep === false || deep === 0)
        return traverse(source2, 1);
      return traverse(source2);
    };
    let effect2;
    let getter;
    let cleanup;
    let boundCleanup;
    let forceTrigger = false;
    let isMultiSource = false;
    if (/* @__PURE__ */ isRef(source)) {
      getter = () => source.value;
      forceTrigger = /* @__PURE__ */ isShallow(source);
    } else if (/* @__PURE__ */ isReactive(source)) {
      getter = () => reactiveGetter(source);
      forceTrigger = true;
    } else if (isArray(source)) {
      isMultiSource = true;
      forceTrigger = source.some((s) => /* @__PURE__ */ isReactive(s) || /* @__PURE__ */ isShallow(s));
      getter = () => source.map((s) => {
        if (/* @__PURE__ */ isRef(s)) {
          return s.value;
        } else if (/* @__PURE__ */ isReactive(s)) {
          return reactiveGetter(s);
        } else if (isFunction(s)) {
          return call ? call(s, 2) : s();
        } else ;
      });
    } else if (isFunction(source)) {
      if (cb) {
        getter = call ? () => call(source, 2) : source;
      } else {
        getter = () => {
          if (cleanup) {
            pauseTracking();
            try {
              cleanup();
            } finally {
              resetTracking();
            }
          }
          const currentEffect = activeWatcher;
          activeWatcher = effect2;
          try {
            return call ? call(source, 3, [boundCleanup]) : source(boundCleanup);
          } finally {
            activeWatcher = currentEffect;
          }
        };
      }
    } else {
      getter = NOOP;
    }
    if (cb && deep) {
      const baseGetter = getter;
      const depth = deep === true ? Infinity : deep;
      getter = () => traverse(baseGetter(), depth);
    }
    const scope = getCurrentScope();
    const watchHandle = () => {
      effect2.stop();
      if (scope && scope.active) {
        remove(scope.effects, effect2);
      }
    };
    if (once && cb) {
      const _cb = cb;
      cb = (...args) => {
        const res = _cb(...args);
        watchHandle();
        return res;
      };
    }
    let oldValue = isMultiSource ? new Array(source.length).fill(INITIAL_WATCHER_VALUE) : INITIAL_WATCHER_VALUE;
    const job = (immediateFirstRun) => {
      if (!(effect2.flags & 1) || !effect2.dirty && !immediateFirstRun) {
        return;
      }
      if (cb) {
        const newValue = effect2.run();
        if (immediateFirstRun || deep || forceTrigger || (isMultiSource ? newValue.some((v, i) => hasChanged(v, oldValue[i])) : hasChanged(newValue, oldValue))) {
          if (cleanup) {
            cleanup();
          }
          const currentWatcher = activeWatcher;
          activeWatcher = effect2;
          try {
            const args = [
              newValue,
              // pass undefined as the old value when it's changed for the first time
              oldValue === INITIAL_WATCHER_VALUE ? void 0 : isMultiSource && oldValue[0] === INITIAL_WATCHER_VALUE ? [] : oldValue,
              boundCleanup
            ];
            oldValue = newValue;
            call ? call(cb, 3, args) : (
              // @ts-expect-error
              cb(...args)
            );
          } finally {
            activeWatcher = currentWatcher;
          }
        }
      } else {
        effect2.run();
      }
    };
    if (augmentJob) {
      augmentJob(job);
    }
    effect2 = new ReactiveEffect(getter);
    effect2.scheduler = scheduler ? () => scheduler(job, false) : job;
    boundCleanup = (fn) => onWatcherCleanup(fn, false, effect2);
    cleanup = effect2.onStop = () => {
      const cleanups = cleanupMap.get(effect2);
      if (cleanups) {
        if (call) {
          call(cleanups, 4);
        } else {
          for (const cleanup2 of cleanups) cleanup2();
        }
        cleanupMap.delete(effect2);
      }
    };
    if (cb) {
      if (immediate) {
        job(true);
      } else {
        oldValue = effect2.run();
      }
    } else if (scheduler) {
      scheduler(job.bind(null, true), true);
    } else {
      effect2.run();
    }
    watchHandle.pause = effect2.pause.bind(effect2);
    watchHandle.resume = effect2.resume.bind(effect2);
    watchHandle.stop = watchHandle;
    return watchHandle;
  }
  function traverse(value, depth = Infinity, seen) {
    if (depth <= 0 || !isObject(value) || value["__v_skip"]) {
      return value;
    }
    seen = seen || /* @__PURE__ */ new Map();
    if ((seen.get(value) || 0) >= depth) {
      return value;
    }
    seen.set(value, depth);
    depth--;
    if (/* @__PURE__ */ isRef(value)) {
      traverse(value.value, depth, seen);
    } else if (isArray(value)) {
      for (let i = 0; i < value.length; i++) {
        traverse(value[i], depth, seen);
      }
    } else if (isSet(value) || isMap(value)) {
      value.forEach((v) => {
        traverse(v, depth, seen);
      });
    } else if (isPlainObject(value)) {
      for (const key in value) {
        traverse(value[key], depth, seen);
      }
      for (const key of Object.getOwnPropertySymbols(value)) {
        if (Object.prototype.propertyIsEnumerable.call(value, key)) {
          traverse(value[key], depth, seen);
        }
      }
    }
    return value;
  }
  const stack = [];
  let isWarning = false;
  function warn$1(msg, ...args) {
    if (isWarning) return;
    isWarning = true;
    pauseTracking();
    const instance = stack.length ? stack[stack.length - 1].component : null;
    const appWarnHandler = instance && instance.appContext.config.warnHandler;
    const trace = getComponentTrace();
    if (appWarnHandler) {
      callWithErrorHandling(
        appWarnHandler,
        instance,
        11,
        [
          // eslint-disable-next-line no-restricted-syntax
          msg + args.map((a) => {
            var _a, _b;
            return (_b = (_a = a.toString) == null ? void 0 : _a.call(a)) != null ? _b : JSON.stringify(a);
          }).join(""),
          instance && instance.proxy,
          trace.map(
            ({ vnode }) => `at <${formatComponentName(instance, vnode.type)}>`
          ).join("\n"),
          trace
        ]
      );
    } else {
      const warnArgs = [`[Vue warn]: ${msg}`, ...args];
      if (trace.length && // avoid spamming console during tests
      true) {
        warnArgs.push(`
`, ...formatTrace(trace));
      }
      console.warn(...warnArgs);
    }
    resetTracking();
    isWarning = false;
  }
  function getComponentTrace() {
    let currentVNode = stack[stack.length - 1];
    if (!currentVNode) {
      return [];
    }
    const normalizedStack = [];
    while (currentVNode) {
      const last = normalizedStack[0];
      if (last && last.vnode === currentVNode) {
        last.recurseCount++;
      } else {
        normalizedStack.push({
          vnode: currentVNode,
          recurseCount: 0
        });
      }
      const parentInstance = currentVNode.component && currentVNode.component.parent;
      currentVNode = parentInstance && parentInstance.vnode;
    }
    return normalizedStack;
  }
  function formatTrace(trace) {
    const logs = [];
    trace.forEach((entry, i) => {
      logs.push(...i === 0 ? [] : [`
`], ...formatTraceEntry(entry));
    });
    return logs;
  }
  function formatTraceEntry({ vnode, recurseCount }) {
    const postfix = recurseCount > 0 ? `... (${recurseCount} recursive calls)` : ``;
    const isRoot = vnode.component ? vnode.component.parent == null : false;
    const open = ` at <${formatComponentName(
      vnode.component,
      vnode.type,
      isRoot
    )}`;
    const close = `>` + postfix;
    return vnode.props ? [open, ...formatProps(vnode.props), close] : [open + close];
  }
  function formatProps(props) {
    const res = [];
    const keys = Object.keys(props);
    keys.slice(0, 3).forEach((key) => {
      res.push(...formatProp(key, props[key]));
    });
    if (keys.length > 3) {
      res.push(` ...`);
    }
    return res;
  }
  function formatProp(key, value, raw) {
    if (isString(value)) {
      value = JSON.stringify(value);
      return raw ? value : [`${key}=${value}`];
    } else if (typeof value === "number" || typeof value === "boolean" || value == null) {
      return raw ? value : [`${key}=${value}`];
    } else if (/* @__PURE__ */ isRef(value)) {
      value = formatProp(key, /* @__PURE__ */ toRaw(value.value), true);
      return raw ? value : [`${key}=Ref<`, value, `>`];
    } else if (isFunction(value)) {
      return [`${key}=fn${value.name ? `<${value.name}>` : ``}`];
    } else {
      value = /* @__PURE__ */ toRaw(value);
      return raw ? value : [`${key}=`, value];
    }
  }
  function callWithErrorHandling(fn, instance, type, args) {
    try {
      return args ? fn(...args) : fn();
    } catch (err) {
      handleError(err, instance, type);
    }
  }
  function callWithAsyncErrorHandling(fn, instance, type, args) {
    if (isFunction(fn)) {
      const res = callWithErrorHandling(fn, instance, type, args);
      if (res && isPromise(res)) {
        res.catch((err) => {
          handleError(err, instance, type);
        });
      }
      return res;
    }
    if (isArray(fn)) {
      const values = [];
      for (let i = 0; i < fn.length; i++) {
        values.push(callWithAsyncErrorHandling(fn[i], instance, type, args));
      }
      return values;
    }
  }
  function handleError(err, instance, type, throwInDev = true) {
    const contextVNode = instance ? instance.vnode : null;
    const { errorHandler, throwUnhandledErrorInProduction } = instance && instance.appContext.config || EMPTY_OBJ;
    if (instance) {
      let cur = instance.parent;
      const exposedInstance = instance.proxy;
      const errorInfo = `https://vuejs.org/error-reference/#runtime-${type}`;
      while (cur) {
        const errorCapturedHooks = cur.ec;
        if (errorCapturedHooks) {
          for (let i = 0; i < errorCapturedHooks.length; i++) {
            if (errorCapturedHooks[i](err, exposedInstance, errorInfo) === false) {
              return;
            }
          }
        }
        cur = cur.parent;
      }
      if (errorHandler) {
        pauseTracking();
        callWithErrorHandling(errorHandler, null, 10, [
          err,
          exposedInstance,
          errorInfo
        ]);
        resetTracking();
        return;
      }
    }
    logError(err, type, contextVNode, throwInDev, throwUnhandledErrorInProduction);
  }
  function logError(err, type, contextVNode, throwInDev = true, throwInProd = false) {
    if (throwInProd) {
      throw err;
    } else {
      console.error(err);
    }
  }
  const queue = [];
  let flushIndex = -1;
  const pendingPostFlushCbs = [];
  let activePostFlushCbs = null;
  let postFlushIndex = 0;
  const resolvedPromise = /* @__PURE__ */ Promise.resolve();
  let currentFlushPromise = null;
  function nextTick(fn) {
    const p2 = currentFlushPromise || resolvedPromise;
    return fn ? p2.then(this ? fn.bind(this) : fn) : p2;
  }
  function findInsertionIndex(id) {
    let start = flushIndex + 1;
    let end = queue.length;
    while (start < end) {
      const middle = start + end >>> 1;
      const middleJob = queue[middle];
      const middleJobId = getId(middleJob);
      if (middleJobId < id || middleJobId === id && middleJob.flags & 2) {
        start = middle + 1;
      } else {
        end = middle;
      }
    }
    return start;
  }
  function queueJob(job) {
    if (!(job.flags & 1)) {
      const jobId = getId(job);
      const lastJob = queue[queue.length - 1];
      if (!lastJob || // fast path when the job id is larger than the tail
      !(job.flags & 2) && jobId >= getId(lastJob)) {
        queue.push(job);
      } else {
        queue.splice(findInsertionIndex(jobId), 0, job);
      }
      job.flags |= 1;
      queueFlush();
    }
  }
  function queueFlush() {
    if (!currentFlushPromise) {
      currentFlushPromise = resolvedPromise.then(flushJobs);
    }
  }
  function queuePostFlushCb(cb) {
    if (!isArray(cb)) {
      if (activePostFlushCbs && cb.id === -1) {
        activePostFlushCbs.splice(postFlushIndex + 1, 0, cb);
      } else if (!(cb.flags & 1)) {
        pendingPostFlushCbs.push(cb);
        cb.flags |= 1;
      }
    } else {
      for (let i = 0; i < cb.length; i++) {
        pendingPostFlushCbs.push(cb[i]);
      }
    }
    queueFlush();
  }
  function flushPreFlushCbs(instance, seen, i = flushIndex + 1) {
    for (; i < queue.length; i++) {
      const cb = queue[i];
      if (cb && cb.flags & 2) {
        if (instance && cb.id !== instance.uid) {
          continue;
        }
        queue.splice(i, 1);
        i--;
        if (cb.flags & 4) {
          cb.flags &= -2;
        }
        cb();
        if (!(cb.flags & 4)) {
          cb.flags &= -2;
        }
      }
    }
  }
  function flushPostFlushCbs(seen) {
    if (pendingPostFlushCbs.length) {
      const deduped = [...new Set(pendingPostFlushCbs)].sort(
        (a, b) => getId(a) - getId(b)
      );
      pendingPostFlushCbs.length = 0;
      if (activePostFlushCbs) {
        for (let i = 0; i < deduped.length; i++) {
          activePostFlushCbs.push(deduped[i]);
        }
        return;
      }
      activePostFlushCbs = deduped;
      for (postFlushIndex = 0; postFlushIndex < activePostFlushCbs.length; postFlushIndex++) {
        const cb = activePostFlushCbs[postFlushIndex];
        if (cb.flags & 4) {
          cb.flags &= -2;
        }
        if (!(cb.flags & 8)) cb();
        cb.flags &= -2;
      }
      activePostFlushCbs = null;
      postFlushIndex = 0;
    }
  }
  const getId = (job) => job.id == null ? job.flags & 2 ? -1 : Infinity : job.id;
  function flushJobs(seen) {
    try {
      for (flushIndex = 0; flushIndex < queue.length; flushIndex++) {
        const job = queue[flushIndex];
        if (job && !(job.flags & 8)) {
          if (false) ;
          if (job.flags & 4) {
            job.flags &= ~1;
          }
          callWithErrorHandling(
            job,
            job.i,
            job.i ? 15 : 14
          );
          if (!(job.flags & 4)) {
            job.flags &= ~1;
          }
        }
      }
    } finally {
      for (; flushIndex < queue.length; flushIndex++) {
        const job = queue[flushIndex];
        if (job) {
          job.flags &= -2;
        }
      }
      flushIndex = -1;
      queue.length = 0;
      flushPostFlushCbs();
      currentFlushPromise = null;
      if (queue.length || pendingPostFlushCbs.length) {
        flushJobs();
      }
    }
  }
  let currentRenderingInstance = null;
  let currentScopeId = null;
  function setCurrentRenderingInstance(instance) {
    const prev = currentRenderingInstance;
    currentRenderingInstance = instance;
    currentScopeId = instance && instance.type.__scopeId || null;
    return prev;
  }
  function withCtx(fn, ctx = currentRenderingInstance, isNonScopedSlot) {
    if (!ctx) return fn;
    if (fn._n) {
      return fn;
    }
    const renderFnWithContext = (...args) => {
      if (renderFnWithContext._d) {
        setBlockTracking(-1);
      }
      const prevInstance = setCurrentRenderingInstance(ctx);
      const prevStackSize = blockStack.length;
      let res;
      try {
        res = fn(...args);
      } finally {
        for (let i = blockStack.length; i > prevStackSize; i--) closeBlock();
        setCurrentRenderingInstance(prevInstance);
        if (renderFnWithContext._d) {
          setBlockTracking(1);
        }
      }
      return res;
    };
    renderFnWithContext._n = true;
    renderFnWithContext._c = true;
    renderFnWithContext._d = true;
    return renderFnWithContext;
  }
  function withDirectives(vnode, directives) {
    if (currentRenderingInstance === null) {
      return vnode;
    }
    const instance = getComponentPublicInstance(currentRenderingInstance);
    const bindings = vnode.dirs || (vnode.dirs = []);
    for (let i = 0; i < directives.length; i++) {
      let [dir, value, arg, modifiers = EMPTY_OBJ] = directives[i];
      if (dir) {
        if (isFunction(dir)) {
          dir = {
            mounted: dir,
            updated: dir
          };
        }
        if (dir.deep) {
          traverse(value);
        }
        bindings.push({
          dir,
          instance,
          value,
          oldValue: void 0,
          arg,
          modifiers
        });
      }
    }
    return vnode;
  }
  function invokeDirectiveHook(vnode, prevVNode, instance, name) {
    const bindings = vnode.dirs;
    const oldBindings = prevVNode && prevVNode.dirs;
    for (let i = 0; i < bindings.length; i++) {
      const binding = bindings[i];
      if (oldBindings) {
        binding.oldValue = oldBindings[i].value;
      }
      let hook = binding.dir[name];
      if (hook) {
        pauseTracking();
        callWithAsyncErrorHandling(hook, instance, 8, [
          vnode.el,
          binding,
          vnode,
          prevVNode
        ]);
        resetTracking();
      }
    }
  }
  function provide(key, value) {
    if (currentInstance) {
      let provides = currentInstance.provides;
      const parentProvides = currentInstance.parent && currentInstance.parent.provides;
      if (parentProvides === provides) {
        provides = currentInstance.provides = Object.create(parentProvides);
      }
      provides[key] = value;
    }
  }
  function inject(key, defaultValue, treatDefaultAsFactory = false) {
    const instance = getCurrentInstance();
    if (instance || currentApp) {
      let provides = currentApp ? currentApp._context.provides : instance ? instance.parent == null || instance.ce ? instance.vnode.appContext && instance.vnode.appContext.provides : instance.parent.provides : void 0;
      if (provides && key in provides) {
        return provides[key];
      } else if (arguments.length > 1) {
        return treatDefaultAsFactory && isFunction(defaultValue) ? defaultValue.call(instance && instance.proxy) : defaultValue;
      } else ;
    }
  }
  const ssrContextKey = /* @__PURE__ */ Symbol.for("v-scx");
  const useSSRContext = () => {
    {
      const ctx = inject(ssrContextKey);
      return ctx;
    }
  };
  function watch(source, cb, options) {
    return doWatch(source, cb, options);
  }
  function doWatch(source, cb, options = EMPTY_OBJ) {
    const { immediate, deep, flush, once } = options;
    const baseWatchOptions = extend({}, options);
    const runsImmediately = cb && immediate || !cb && flush !== "post";
    let ssrCleanup;
    if (isInSSRComponentSetup) {
      if (flush === "sync") {
        const ctx = useSSRContext();
        ssrCleanup = ctx.__watcherHandles || (ctx.__watcherHandles = []);
      } else if (!runsImmediately) {
        const watchStopHandle = () => {
        };
        watchStopHandle.stop = NOOP;
        watchStopHandle.resume = NOOP;
        watchStopHandle.pause = NOOP;
        return watchStopHandle;
      }
    }
    const instance = currentInstance;
    baseWatchOptions.call = (fn, type, args) => callWithAsyncErrorHandling(fn, instance, type, args);
    let isPre = false;
    if (flush === "post") {
      baseWatchOptions.scheduler = (job) => {
        queuePostRenderEffect(job, instance && instance.suspense);
      };
    } else if (flush !== "sync") {
      isPre = true;
      baseWatchOptions.scheduler = (job, isFirstRun) => {
        if (isFirstRun) {
          job();
        } else {
          queueJob(job);
        }
      };
    }
    baseWatchOptions.augmentJob = (job) => {
      if (cb) {
        job.flags |= 4;
      }
      if (isPre) {
        job.flags |= 2;
        if (instance) {
          job.id = instance.uid;
          job.i = instance;
        }
      }
    };
    const watchHandle = watch$1(source, cb, baseWatchOptions);
    if (isInSSRComponentSetup) {
      if (ssrCleanup) {
        ssrCleanup.push(watchHandle);
      } else if (runsImmediately) {
        watchHandle();
      }
    }
    return watchHandle;
  }
  function instanceWatch(source, value, options) {
    const publicThis = this.proxy;
    const getter = isString(source) ? source.includes(".") ? createPathGetter(publicThis, source) : () => publicThis[source] : source.bind(publicThis, publicThis);
    let cb;
    if (isFunction(value)) {
      cb = value;
    } else {
      cb = value.handler;
      options = value;
    }
    const reset = setCurrentInstance(this);
    const res = doWatch(getter, cb.bind(publicThis), options);
    reset();
    return res;
  }
  function createPathGetter(ctx, path) {
    const segments = path.split(".");
    return () => {
      let cur = ctx;
      for (let i = 0; i < segments.length && cur; i++) {
        cur = cur[segments[i]];
      }
      return cur;
    };
  }
  const pendingMounts = /* @__PURE__ */ new WeakMap();
  const TeleportEndKey = /* @__PURE__ */ Symbol("_vte");
  const isTeleport = (type) => type.__isTeleport;
  const isTeleportDisabled = (props) => props && (props.disabled || props.disabled === "");
  const isTeleportDeferred = (props) => props && (props.defer || props.defer === "");
  const isTargetSVG = (target) => typeof SVGElement !== "undefined" && target instanceof SVGElement;
  const isTargetMathML = (target) => typeof MathMLElement === "function" && target instanceof MathMLElement;
  const resolveTarget = (props, select) => {
    const targetSelector = props && props.to;
    if (isString(targetSelector)) {
      if (!select) {
        return null;
      } else {
        const target = select(targetSelector);
        return target;
      }
    } else {
      return targetSelector;
    }
  };
  const TeleportImpl = {
    name: "Teleport",
    __isTeleport: true,
    process(n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized, internals) {
      const {
        mc: mountChildren,
        pc: patchChildren,
        pbc: patchBlockChildren,
        o: { insert, querySelector, createText, createComment, parentNode }
      } = internals;
      const disabled = isTeleportDisabled(n2.props);
      let { dynamicChildren } = n2;
      const mount = (vnode, container2, anchor2) => {
        if (vnode.shapeFlag & 16) {
          mountChildren(
            vnode.children,
            container2,
            anchor2,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
        }
      };
      const mountToTarget = (vnode = n2) => {
        const disabled2 = isTeleportDisabled(vnode.props);
        const target = vnode.target = resolveTarget(vnode.props, querySelector);
        const targetAnchor = prepareAnchor(target, vnode, createText, insert);
        if (target) {
          if (namespace !== "svg" && isTargetSVG(target)) {
            namespace = "svg";
          } else if (namespace !== "mathml" && isTargetMathML(target)) {
            namespace = "mathml";
          }
          if (parentComponent && parentComponent.isCE) {
            (parentComponent.ce._teleportTargets || (parentComponent.ce._teleportTargets = /* @__PURE__ */ new Set())).add(target);
          }
          if (!disabled2) {
            mount(vnode, target, targetAnchor);
            updateCssVars(vnode, false);
          }
        }
      };
      const queuePendingMount = (vnode) => {
        const mountJob = () => {
          if (pendingMounts.get(vnode) !== mountJob) return;
          pendingMounts.delete(vnode);
          if (isTeleportDisabled(vnode.props)) {
            const mountContainer = parentNode(vnode.el) || container;
            mount(vnode, mountContainer, vnode.anchor);
            updateCssVars(vnode, true);
          }
          mountToTarget(vnode);
        };
        pendingMounts.set(vnode, mountJob);
        queuePostRenderEffect(mountJob, parentSuspense);
      };
      if (n1 == null) {
        const placeholder = n2.el = createText("");
        const mainAnchor = n2.anchor = createText("");
        insert(placeholder, container, anchor);
        insert(mainAnchor, container, anchor);
        if (isTeleportDeferred(n2.props) || parentSuspense && parentSuspense.pendingBranch) {
          queuePendingMount(n2);
          return;
        }
        if (disabled) {
          mount(n2, container, mainAnchor);
          updateCssVars(n2, true);
        }
        mountToTarget();
      } else {
        n2.el = n1.el;
        const mainAnchor = n2.anchor = n1.anchor;
        const pendingMount = pendingMounts.get(n1);
        if (pendingMount) {
          pendingMount.flags |= 8;
          pendingMounts.delete(n1);
          queuePendingMount(n2);
          return;
        }
        n2.targetStart = n1.targetStart;
        const target = n2.target = n1.target;
        const targetAnchor = n2.targetAnchor = n1.targetAnchor;
        const wasDisabled = isTeleportDisabled(n1.props);
        const currentContainer = wasDisabled ? container : target;
        const currentAnchor = wasDisabled ? mainAnchor : targetAnchor;
        if (namespace === "svg" || isTargetSVG(target)) {
          namespace = "svg";
        } else if (namespace === "mathml" || isTargetMathML(target)) {
          namespace = "mathml";
        }
        if (dynamicChildren) {
          patchBlockChildren(
            n1.dynamicChildren,
            dynamicChildren,
            currentContainer,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds
          );
          traverseStaticChildren(n1, n2, true);
        } else if (!optimized) {
          patchChildren(
            n1,
            n2,
            currentContainer,
            currentAnchor,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            false
          );
        }
        if (disabled) {
          if (!wasDisabled) {
            moveTeleport(
              n2,
              container,
              mainAnchor,
              internals,
              1
            );
          } else {
            if (n2.props && n1.props && n2.props.to !== n1.props.to) {
              n2.props.to = n1.props.to;
            }
          }
        } else {
          if ((n2.props && n2.props.to) !== (n1.props && n1.props.to)) {
            const nextTarget = resolveTarget(n2.props, querySelector);
            if (nextTarget) {
              n2.target = nextTarget;
              moveTeleport(
                n2,
                nextTarget,
                null,
                internals,
                0
              );
            }
          } else if (wasDisabled) {
            moveTeleport(
              n2,
              target,
              targetAnchor,
              internals,
              1
            );
          }
        }
        updateCssVars(n2, disabled);
      }
    },
    remove(vnode, parentComponent, parentSuspense, { um: unmount, o: { remove: hostRemove } }, doRemove) {
      const {
        shapeFlag,
        children,
        anchor,
        targetStart,
        targetAnchor,
        target,
        props
      } = vnode;
      const disabled = isTeleportDisabled(props);
      const shouldRemove = doRemove || !disabled;
      const pendingMount = pendingMounts.get(vnode);
      if (pendingMount) {
        pendingMount.flags |= 8;
        pendingMounts.delete(vnode);
      }
      if (target) {
        hostRemove(targetStart);
        hostRemove(targetAnchor);
      }
      doRemove && hostRemove(anchor);
      if (!pendingMount && (disabled || target) && shapeFlag & 16) {
        for (let i = 0; i < children.length; i++) {
          const child = children[i];
          unmount(
            child,
            parentComponent,
            parentSuspense,
            shouldRemove,
            !!child.dynamicChildren
          );
        }
      }
    },
    move: moveTeleport,
    hydrate: hydrateTeleport
  };
  function moveTeleport(vnode, container, parentAnchor, { o: { insert }, m: move }, moveType = 2) {
    if (moveType === 0) {
      insert(vnode.targetAnchor, container, parentAnchor);
    }
    const { el, anchor, shapeFlag, children, props } = vnode;
    const isReorder = moveType === 2;
    if (isReorder) {
      insert(el, container, parentAnchor);
    }
    if (!pendingMounts.has(vnode) && (!isReorder || isTeleportDisabled(props))) {
      if (shapeFlag & 16) {
        for (let i = 0; i < children.length; i++) {
          move(
            children[i],
            container,
            parentAnchor,
            2
          );
        }
      }
    }
    if (isReorder) {
      insert(anchor, container, parentAnchor);
    }
  }
  function hydrateTeleport(node, vnode, parentComponent, parentSuspense, slotScopeIds, optimized, {
    o: { nextSibling, parentNode, querySelector, insert, createText }
  }, hydrateChildren) {
    function hydrateAnchor(target2, targetNode) {
      let targetAnchor = targetNode;
      while (targetAnchor) {
        if (targetAnchor && targetAnchor.nodeType === 8) {
          if (targetAnchor.data === "teleport start anchor") {
            vnode.targetStart = targetAnchor;
          } else if (targetAnchor.data === "teleport anchor") {
            vnode.targetAnchor = targetAnchor;
            target2._lpa = vnode.targetAnchor && nextSibling(vnode.targetAnchor);
            break;
          }
        }
        targetAnchor = nextSibling(targetAnchor);
      }
    }
    function hydrateDisabledTeleport(node2, vnode2) {
      vnode2.anchor = hydrateChildren(
        nextSibling(node2),
        vnode2,
        parentNode(node2),
        parentComponent,
        parentSuspense,
        slotScopeIds,
        optimized
      );
    }
    const target = vnode.target = resolveTarget(
      vnode.props,
      querySelector
    );
    const disabled = isTeleportDisabled(vnode.props);
    if (target) {
      const targetNode = target._lpa || target.firstChild;
      if (vnode.shapeFlag & 16) {
        if (disabled) {
          hydrateDisabledTeleport(node, vnode);
          hydrateAnchor(target, targetNode);
          if (!vnode.targetAnchor) {
            prepareAnchor(
              target,
              vnode,
              createText,
              insert,
              // if target is the same as the main view, insert anchors before current node
              // to avoid hydrating mismatch
              parentNode(node) === target ? node : null
            );
          }
        } else {
          vnode.anchor = nextSibling(node);
          hydrateAnchor(target, targetNode);
          if (!vnode.targetAnchor) {
            prepareAnchor(target, vnode, createText, insert);
          }
          hydrateChildren(
            targetNode && nextSibling(targetNode),
            vnode,
            target,
            parentComponent,
            parentSuspense,
            slotScopeIds,
            optimized
          );
        }
      }
      updateCssVars(vnode, disabled);
    } else if (disabled) {
      if (vnode.shapeFlag & 16) {
        hydrateDisabledTeleport(node, vnode);
        vnode.targetStart = node;
        vnode.targetAnchor = nextSibling(node);
      }
    }
    return vnode.anchor && nextSibling(vnode.anchor);
  }
  const Teleport = TeleportImpl;
  function updateCssVars(vnode, isDisabled) {
    const ctx = vnode.ctx;
    if (ctx && ctx.ut) {
      let node, anchor;
      if (isDisabled) {
        node = vnode.el;
        anchor = vnode.anchor;
      } else {
        node = vnode.targetStart;
        anchor = vnode.targetAnchor;
      }
      while (node && node !== anchor) {
        if (node.nodeType === 1) node.setAttribute("data-v-owner", ctx.uid);
        node = node.nextSibling;
      }
      ctx.ut();
    }
  }
  function prepareAnchor(target, vnode, createText, insert, anchor = null) {
    const targetStart = vnode.targetStart = createText("");
    const targetAnchor = vnode.targetAnchor = createText("");
    targetStart[TeleportEndKey] = targetAnchor;
    if (target) {
      insert(targetStart, target, anchor);
      insert(targetAnchor, target, anchor);
    }
    return targetAnchor;
  }
  const leaveCbKey = /* @__PURE__ */ Symbol("_leaveCb");
  function findNonCommentChild(children) {
    let child = children[0];
    if (children.length > 1) {
      for (const c of children) {
        if (c.type !== Comment) {
          child = c;
          break;
        }
      }
    }
    return child;
  }
  function getInnerChild$1(vnode) {
    if (!isKeepAlive(vnode)) {
      if (isTeleport(vnode.type) && vnode.children) {
        return findNonCommentChild(vnode.children);
      }
      return vnode;
    }
    if (vnode.component) {
      return vnode.component.subTree;
    }
    const { shapeFlag, children } = vnode;
    if (children) {
      if (shapeFlag & 16) {
        return children[0];
      }
      if (shapeFlag & 32 && isFunction(children.default)) {
        return children.default();
      }
    }
  }
  function setTransitionHooks(vnode, hooks) {
    if (vnode.shapeFlag & 6 && vnode.component) {
      vnode.transition = hooks;
      const subTree = vnode.component.subTree;
      setTransitionHooks(
        isTeleport(subTree.type) ? getInnerChild$1(subTree) || subTree : subTree,
        hooks
      );
    } else if (vnode.shapeFlag & 128) {
      vnode.ssContent.transition = hooks.clone(vnode.ssContent);
      vnode.ssFallback.transition = hooks.clone(vnode.ssFallback);
    } else {
      vnode.transition = hooks;
    }
  }
  // @__NO_SIDE_EFFECTS__
  function defineComponent(options, extraOptions) {
    return isFunction(options) ? (
      // #8236: extend call and options.name access are considered side-effects
      // by Rollup, so we have to wrap it in a pure-annotated IIFE.
      /* @__PURE__ */ (() => extend({ name: options.name }, extraOptions, { setup: options }))()
    ) : options;
  }
  function useId() {
    const i = getCurrentInstance();
    if (i) {
      return (i.appContext.config.idPrefix || "v") + "-" + i.ids[0] + i.ids[1]++;
    }
    return "";
  }
  function markAsyncBoundary(instance) {
    instance.ids = [instance.ids[0] + instance.ids[2]++ + "-", 0, 0];
  }
  function isTemplateRefKey(refs, key) {
    let desc;
    return !!((desc = Object.getOwnPropertyDescriptor(refs, key)) && !desc.configurable);
  }
  const pendingSetRefMap = /* @__PURE__ */ new WeakMap();
  function setRef(rawRef, oldRawRef, parentSuspense, vnode, isUnmount = false) {
    if (isArray(rawRef)) {
      rawRef.forEach(
        (r, i) => setRef(
          r,
          oldRawRef && (isArray(oldRawRef) ? oldRawRef[i] : oldRawRef),
          parentSuspense,
          vnode,
          isUnmount
        )
      );
      return;
    }
    if (isAsyncWrapper(vnode) && !isUnmount) {
      if (vnode.shapeFlag & 512 && vnode.type.__asyncResolved && vnode.component.subTree.component) {
        setRef(rawRef, oldRawRef, parentSuspense, vnode.component.subTree);
      }
      return;
    }
    const refValue = vnode.shapeFlag & 4 ? getComponentPublicInstance(vnode.component) : vnode.el;
    const value = isUnmount ? null : refValue;
    const { i: owner, r: ref3 } = rawRef;
    const oldRef = oldRawRef && oldRawRef.r;
    const refs = owner.refs === EMPTY_OBJ ? owner.refs = {} : owner.refs;
    const setupState = owner.setupState;
    const rawSetupState = /* @__PURE__ */ toRaw(setupState);
    const canSetSetupRef = setupState === EMPTY_OBJ ? NO : (key) => {
      if (isTemplateRefKey(refs, key)) {
        return false;
      }
      return hasOwn(rawSetupState, key);
    };
    const canSetRef = (ref22, key) => {
      if (key && isTemplateRefKey(refs, key)) {
        return false;
      }
      return true;
    };
    if (oldRef != null && oldRef !== ref3) {
      invalidatePendingSetRef(oldRawRef);
      if (isString(oldRef)) {
        refs[oldRef] = null;
        if (canSetSetupRef(oldRef)) {
          setupState[oldRef] = null;
        }
      } else if (/* @__PURE__ */ isRef(oldRef)) {
        const oldRawRefAtom = oldRawRef;
        if (canSetRef(oldRef, oldRawRefAtom.k)) {
          oldRef.value = null;
        }
        if (oldRawRefAtom.k) refs[oldRawRefAtom.k] = null;
      }
    }
    if (isFunction(ref3)) {
      callWithErrorHandling(ref3, owner, 12, [value, refs]);
    } else {
      const _isString = isString(ref3);
      const _isRef = /* @__PURE__ */ isRef(ref3);
      if (_isString || _isRef) {
        const doSet = () => {
          if (rawRef.f) {
            const existing = _isString ? canSetSetupRef(ref3) ? setupState[ref3] : refs[ref3] : canSetRef() || !rawRef.k ? ref3.value : refs[rawRef.k];
            if (isUnmount) {
              isArray(existing) && remove(existing, refValue);
            } else {
              if (!isArray(existing)) {
                if (_isString) {
                  refs[ref3] = [refValue];
                  if (canSetSetupRef(ref3)) {
                    setupState[ref3] = refs[ref3];
                  }
                } else {
                  const newVal = [refValue];
                  if (canSetRef(ref3, rawRef.k)) {
                    ref3.value = newVal;
                  }
                  if (rawRef.k) refs[rawRef.k] = newVal;
                }
              } else if (!existing.includes(refValue)) {
                existing.push(refValue);
              }
            }
          } else if (_isString) {
            refs[ref3] = value;
            if (canSetSetupRef(ref3)) {
              setupState[ref3] = value;
            }
          } else if (_isRef) {
            if (canSetRef(ref3, rawRef.k)) {
              ref3.value = value;
            }
            if (rawRef.k) refs[rawRef.k] = value;
          } else ;
        };
        if (value) {
          const job = () => {
            doSet();
            pendingSetRefMap.delete(rawRef);
          };
          job.id = -1;
          pendingSetRefMap.set(rawRef, job);
          queuePostRenderEffect(job, parentSuspense);
        } else {
          invalidatePendingSetRef(rawRef);
          doSet();
        }
      }
    }
  }
  function invalidatePendingSetRef(rawRef) {
    const pendingSetRef = pendingSetRefMap.get(rawRef);
    if (pendingSetRef) {
      pendingSetRef.flags |= 8;
      pendingSetRefMap.delete(rawRef);
    }
  }
  getGlobalThis().requestIdleCallback || ((cb) => setTimeout(cb, 1));
  getGlobalThis().cancelIdleCallback || ((id) => clearTimeout(id));
  const isAsyncWrapper = (i) => !!i.type.__asyncLoader;
  const isKeepAlive = (vnode) => vnode.type.__isKeepAlive;
  function onActivated(hook, target) {
    registerKeepAliveHook(hook, "a", target);
  }
  function onDeactivated(hook, target) {
    registerKeepAliveHook(hook, "da", target);
  }
  function registerKeepAliveHook(hook, type, target = currentInstance) {
    const wrappedHook = hook.__wdc || (hook.__wdc = () => {
      let current = target;
      while (current) {
        if (current.isDeactivated) {
          return;
        }
        current = current.parent;
      }
      return hook();
    });
    injectHook(type, wrappedHook, target);
    if (target) {
      let current = target.parent;
      while (current && current.parent) {
        if (isKeepAlive(current.parent.vnode)) {
          injectToKeepAliveRoot(wrappedHook, type, target, current);
        }
        current = current.parent;
      }
    }
  }
  function injectToKeepAliveRoot(hook, type, target, keepAliveRoot) {
    const injected = injectHook(
      type,
      hook,
      keepAliveRoot,
      true
      /* prepend */
    );
    onUnmounted(() => {
      remove(keepAliveRoot[type], injected);
    }, target);
  }
  function injectHook(type, hook, target = currentInstance, prepend = false) {
    if (target) {
      const hooks = target[type] || (target[type] = []);
      const wrappedHook = hook.__weh || (hook.__weh = (...args) => {
        pauseTracking();
        const reset = setCurrentInstance(target);
        const res = callWithAsyncErrorHandling(hook, target, type, args);
        reset();
        resetTracking();
        return res;
      });
      if (prepend) {
        hooks.unshift(wrappedHook);
      } else {
        hooks.push(wrappedHook);
      }
      return wrappedHook;
    }
  }
  const createHook = (lifecycle) => (hook, target = currentInstance) => {
    if (!isInSSRComponentSetup || lifecycle === "sp") {
      injectHook(lifecycle, (...args) => hook(...args), target);
    }
  };
  const onBeforeMount = createHook("bm");
  const onMounted = createHook("m");
  const onBeforeUpdate = createHook(
    "bu"
  );
  const onUpdated = createHook("u");
  const onBeforeUnmount = createHook(
    "bum"
  );
  const onUnmounted = createHook("um");
  const onServerPrefetch = createHook(
    "sp"
  );
  const onRenderTriggered = createHook("rtg");
  const onRenderTracked = createHook("rtc");
  function onErrorCaptured(hook, target = currentInstance) {
    injectHook("ec", hook, target);
  }
  const COMPONENTS = "components";
  const NULL_DYNAMIC_COMPONENT = /* @__PURE__ */ Symbol.for("v-ndc");
  function resolveDynamicComponent(component) {
    if (isString(component)) {
      return resolveAsset(COMPONENTS, component, false) || component;
    } else {
      return component || NULL_DYNAMIC_COMPONENT;
    }
  }
  function resolveAsset(type, name, warnMissing = true, maybeSelfReference = false) {
    const instance = currentRenderingInstance || currentInstance;
    if (instance) {
      const Component = instance.type;
      {
        const selfName = getComponentName(
          Component,
          false
        );
        if (selfName && (selfName === name || selfName === camelize(name) || selfName === capitalize(camelize(name)))) {
          return Component;
        }
      }
      const res = (
        // local registration
        // check instance[type] first which is resolved for options API
        resolve(instance[type] || Component[type], name) || // global registration
        resolve(instance.appContext[type], name)
      );
      if (!res && maybeSelfReference) {
        return Component;
      }
      return res;
    }
  }
  function resolve(registry, name) {
    return registry && (registry[name] || registry[camelize(name)] || registry[capitalize(camelize(name))]);
  }
  function renderList(source, renderItem, cache, index) {
    let ret;
    const cached = cache;
    const sourceIsArray = isArray(source);
    if (sourceIsArray || isString(source)) {
      const sourceIsReactiveArray = sourceIsArray && /* @__PURE__ */ isReactive(source);
      let needsWrap = false;
      let isReadonlySource = false;
      if (sourceIsReactiveArray) {
        needsWrap = !/* @__PURE__ */ isShallow(source);
        isReadonlySource = /* @__PURE__ */ isReadonly(source);
        source = shallowReadArray(source);
      }
      ret = new Array(source.length);
      for (let i = 0, l = source.length; i < l; i++) {
        ret[i] = renderItem(
          needsWrap ? isReadonlySource ? toReadonly(toReactive(source[i])) : toReactive(source[i]) : source[i],
          i,
          void 0,
          cached
        );
      }
    } else if (typeof source === "number") {
      {
        ret = new Array(source);
        for (let i = 0; i < source; i++) {
          ret[i] = renderItem(i + 1, i, void 0, cached);
        }
      }
    } else if (isObject(source)) {
      if (source[Symbol.iterator]) {
        ret = Array.from(
          source,
          (item, i) => renderItem(item, i, void 0, cached)
        );
      } else {
        const keys = Object.keys(source);
        ret = new Array(keys.length);
        for (let i = 0, l = keys.length; i < l; i++) {
          const key = keys[i];
          ret[i] = renderItem(source[key], key, i, cached);
        }
      }
    } else {
      ret = [];
    }
    return ret;
  }
  function renderSlot(slots, name, props, fallback, noSlotted, branchKey) {
    if (props == null) props = {};
    if (currentRenderingInstance.ce || currentRenderingInstance.parent && isAsyncWrapper(currentRenderingInstance.parent) && currentRenderingInstance.parent.ce) {
      const slotProps = branchKey != null && props.key == null ? extend({}, props, { key: branchKey }) : props;
      const hasProps = Object.keys(slotProps).length > 0;
      if (name !== "default") slotProps.name = name;
      return openBlock(), createBlock(
        Fragment,
        null,
        [createVNode("slot", slotProps, fallback && fallback())],
        hasProps ? -2 : 64
      );
    }
    let slot = slots[name];
    if (slot && slot._c) {
      slot._d = false;
    }
    const prevStackSize = blockStack.length;
    openBlock();
    let rendered;
    try {
      const validSlotContent = slot && ensureValidVNode(slot(props));
      const slotKey = props.key || branchKey || // slot content array of a dynamic conditional slot may have a branch
      // key attached in the `createSlots` helper, respect that
      validSlotContent && validSlotContent.key;
      rendered = createBlock(
        Fragment,
        {
          key: (slotKey && !isSymbol(slotKey) ? slotKey : `_${name}`) + // #7256 force differentiate fallback content from actual content
          (!validSlotContent && fallback ? "_fb" : "")
        },
        validSlotContent || (fallback ? fallback() : []),
        validSlotContent && slots._ === 1 ? 64 : -2
      );
    } catch (err) {
      for (let i = blockStack.length; i > prevStackSize; i--) closeBlock();
      throw err;
    } finally {
      if (slot && slot._c) {
        slot._d = true;
      }
    }
    if (!noSlotted && rendered.scopeId) {
      rendered.slotScopeIds = [rendered.scopeId + "-s"];
    }
    return rendered;
  }
  function ensureValidVNode(vnodes) {
    return vnodes.some((child) => {
      if (!isVNode(child)) return true;
      if (child.type === Comment) return false;
      if (child.type === Fragment && !ensureValidVNode(child.children))
        return false;
      return true;
    }) ? vnodes : null;
  }
  const getPublicInstance = (i) => {
    if (!i) return null;
    if (isStatefulComponent(i)) return getComponentPublicInstance(i);
    return getPublicInstance(i.parent);
  };
  const publicPropertiesMap = (
    // Move PURE marker to new line to workaround compiler discarding it
    // due to type annotation
    /* @__PURE__ */ extend(/* @__PURE__ */ Object.create(null), {
      $: (i) => i,
      $el: (i) => i.vnode.el,
      $data: (i) => i.data,
      $props: (i) => i.props,
      $attrs: (i) => i.attrs,
      $slots: (i) => i.slots,
      $refs: (i) => i.refs,
      $parent: (i) => getPublicInstance(i.parent),
      $root: (i) => getPublicInstance(i.root),
      $host: (i) => i.ce,
      $emit: (i) => i.emit,
      $options: (i) => resolveMergedOptions(i),
      $forceUpdate: (i) => i.f || (i.f = () => {
        queueJob(i.update);
      }),
      $nextTick: (i) => i.n || (i.n = nextTick.bind(i.proxy)),
      $watch: (i) => instanceWatch.bind(i)
    })
  );
  const hasSetupBinding = (state, key) => state !== EMPTY_OBJ && !state.__isScriptSetup && hasOwn(state, key);
  const PublicInstanceProxyHandlers = {
    get({ _: instance }, key) {
      if (key === "__v_skip") {
        return true;
      }
      const { ctx, setupState, data, props, accessCache, type, appContext } = instance;
      if (key[0] !== "$") {
        const n = accessCache[key];
        if (n !== void 0) {
          switch (n) {
            case 1:
              return setupState[key];
            case 2:
              return data[key];
            case 4:
              return ctx[key];
            case 3:
              return props[key];
          }
        } else if (hasSetupBinding(setupState, key)) {
          accessCache[key] = 1;
          return setupState[key];
        } else if (data !== EMPTY_OBJ && hasOwn(data, key)) {
          accessCache[key] = 2;
          return data[key];
        } else if (hasOwn(props, key)) {
          accessCache[key] = 3;
          return props[key];
        } else if (ctx !== EMPTY_OBJ && hasOwn(ctx, key)) {
          accessCache[key] = 4;
          return ctx[key];
        } else if (shouldCacheAccess) {
          accessCache[key] = 0;
        }
      }
      const publicGetter = publicPropertiesMap[key];
      let cssModule, globalProperties;
      if (publicGetter) {
        if (key === "$attrs") {
          track(instance.attrs, "get", "");
        }
        return publicGetter(instance);
      } else if (
        // css module (injected by vue-loader)
        (cssModule = type.__cssModules) && (cssModule = cssModule[key])
      ) {
        return cssModule;
      } else if (ctx !== EMPTY_OBJ && hasOwn(ctx, key)) {
        accessCache[key] = 4;
        return ctx[key];
      } else if (
        // global properties
        globalProperties = appContext.config.globalProperties, hasOwn(globalProperties, key)
      ) {
        {
          return globalProperties[key];
        }
      } else ;
    },
    set({ _: instance }, key, value) {
      const { data, setupState, ctx } = instance;
      if (hasSetupBinding(setupState, key)) {
        setupState[key] = value;
        return true;
      } else if (data !== EMPTY_OBJ && hasOwn(data, key)) {
        data[key] = value;
        return true;
      } else if (hasOwn(instance.props, key)) {
        return false;
      }
      if (key[0] === "$" && key.slice(1) in instance) {
        return false;
      } else {
        {
          ctx[key] = value;
        }
      }
      return true;
    },
    has({
      _: { data, setupState, accessCache, ctx, appContext, props, type }
    }, key) {
      let cssModules;
      return !!(accessCache[key] || data !== EMPTY_OBJ && key[0] !== "$" && hasOwn(data, key) || hasSetupBinding(setupState, key) || hasOwn(props, key) || hasOwn(ctx, key) || hasOwn(publicPropertiesMap, key) || hasOwn(appContext.config.globalProperties, key) || (cssModules = type.__cssModules) && cssModules[key]);
    },
    defineProperty(target, key, descriptor) {
      if (descriptor.get != null) {
        target._.accessCache[key] = 0;
      } else if (hasOwn(descriptor, "value")) {
        this.set(target, key, descriptor.value, null);
      }
      return Reflect.defineProperty(target, key, descriptor);
    }
  };
  function normalizePropsOrEmits(props) {
    return isArray(props) ? props.reduce(
      (normalized, p2) => (normalized[p2] = null, normalized),
      {}
    ) : props;
  }
  let shouldCacheAccess = true;
  function applyOptions(instance) {
    const options = resolveMergedOptions(instance);
    const publicThis = instance.proxy;
    const ctx = instance.ctx;
    shouldCacheAccess = false;
    if (options.beforeCreate) {
      callHook(options.beforeCreate, instance, "bc");
    }
    const {
      // state
      data: dataOptions,
      computed: computedOptions,
      methods,
      watch: watchOptions,
      provide: provideOptions,
      inject: injectOptions,
      // lifecycle
      created,
      beforeMount,
      mounted,
      beforeUpdate,
      updated,
      activated,
      deactivated,
      beforeDestroy,
      beforeUnmount,
      destroyed,
      unmounted,
      render,
      renderTracked,
      renderTriggered,
      errorCaptured,
      serverPrefetch,
      // public API
      expose,
      inheritAttrs,
      // assets
      components,
      directives,
      filters
    } = options;
    const checkDuplicateProperties = null;
    if (injectOptions) {
      resolveInjections(injectOptions, ctx, checkDuplicateProperties);
    }
    if (methods) {
      for (const key in methods) {
        const methodHandler = methods[key];
        if (isFunction(methodHandler)) {
          {
            ctx[key] = methodHandler.bind(publicThis);
          }
        }
      }
    }
    if (dataOptions) {
      const data = dataOptions.call(publicThis, publicThis);
      if (!isObject(data)) ;
      else {
        instance.data = /* @__PURE__ */ reactive(data);
      }
    }
    shouldCacheAccess = true;
    if (computedOptions) {
      for (const key in computedOptions) {
        const opt = computedOptions[key];
        const get = isFunction(opt) ? opt.bind(publicThis, publicThis) : isFunction(opt.get) ? opt.get.bind(publicThis, publicThis) : NOOP;
        const set = !isFunction(opt) && isFunction(opt.set) ? opt.set.bind(publicThis) : NOOP;
        const c = computed({
          get,
          set
        });
        Object.defineProperty(ctx, key, {
          enumerable: true,
          configurable: true,
          get: () => c.value,
          set: (v) => c.value = v
        });
      }
    }
    if (watchOptions) {
      for (const key in watchOptions) {
        createWatcher(watchOptions[key], ctx, publicThis, key);
      }
    }
    if (provideOptions) {
      const provides = isFunction(provideOptions) ? provideOptions.call(publicThis) : provideOptions;
      Reflect.ownKeys(provides).forEach((key) => {
        provide(key, provides[key]);
      });
    }
    if (created) {
      callHook(created, instance, "c");
    }
    function registerLifecycleHook(register, hook) {
      if (isArray(hook)) {
        hook.forEach((_hook) => register(_hook.bind(publicThis)));
      } else if (hook) {
        register(hook.bind(publicThis));
      }
    }
    registerLifecycleHook(onBeforeMount, beforeMount);
    registerLifecycleHook(onMounted, mounted);
    registerLifecycleHook(onBeforeUpdate, beforeUpdate);
    registerLifecycleHook(onUpdated, updated);
    registerLifecycleHook(onActivated, activated);
    registerLifecycleHook(onDeactivated, deactivated);
    registerLifecycleHook(onErrorCaptured, errorCaptured);
    registerLifecycleHook(onRenderTracked, renderTracked);
    registerLifecycleHook(onRenderTriggered, renderTriggered);
    registerLifecycleHook(onBeforeUnmount, beforeUnmount);
    registerLifecycleHook(onUnmounted, unmounted);
    registerLifecycleHook(onServerPrefetch, serverPrefetch);
    if (isArray(expose)) {
      if (expose.length) {
        const exposed = instance.exposed || (instance.exposed = {});
        expose.forEach((key) => {
          Object.defineProperty(exposed, key, {
            get: () => publicThis[key],
            set: (val) => publicThis[key] = val,
            enumerable: true
          });
        });
      } else if (!instance.exposed) {
        instance.exposed = {};
      }
    }
    if (render && instance.render === NOOP) {
      instance.render = render;
    }
    if (inheritAttrs != null) {
      instance.inheritAttrs = inheritAttrs;
    }
    if (components) instance.components = components;
    if (directives) instance.directives = directives;
    if (serverPrefetch) {
      markAsyncBoundary(instance);
    }
  }
  function resolveInjections(injectOptions, ctx, checkDuplicateProperties = NOOP) {
    if (isArray(injectOptions)) {
      injectOptions = normalizeInject(injectOptions);
    }
    for (const key in injectOptions) {
      const opt = injectOptions[key];
      let injected;
      if (isObject(opt)) {
        if ("default" in opt) {
          injected = inject(
            opt.from || key,
            opt.default,
            true
          );
        } else {
          injected = inject(opt.from || key);
        }
      } else {
        injected = inject(opt);
      }
      if (/* @__PURE__ */ isRef(injected)) {
        Object.defineProperty(ctx, key, {
          enumerable: true,
          configurable: true,
          get: () => injected.value,
          set: (v) => injected.value = v
        });
      } else {
        ctx[key] = injected;
      }
    }
  }
  function callHook(hook, instance, type) {
    callWithAsyncErrorHandling(
      isArray(hook) ? hook.map((h2) => h2.bind(instance.proxy)) : hook.bind(instance.proxy),
      instance,
      type
    );
  }
  function createWatcher(raw, ctx, publicThis, key) {
    let getter = key.includes(".") ? createPathGetter(publicThis, key) : () => publicThis[key];
    if (isString(raw)) {
      const handler = ctx[raw];
      if (isFunction(handler)) {
        {
          watch(getter, handler);
        }
      }
    } else if (isFunction(raw)) {
      {
        watch(getter, raw.bind(publicThis));
      }
    } else if (isObject(raw)) {
      if (isArray(raw)) {
        raw.forEach((r) => createWatcher(r, ctx, publicThis, key));
      } else {
        const handler = isFunction(raw.handler) ? raw.handler.bind(publicThis) : ctx[raw.handler];
        if (isFunction(handler)) {
          watch(getter, handler, raw);
        }
      }
    } else ;
  }
  function resolveMergedOptions(instance) {
    const base = instance.type;
    const { mixins, extends: extendsOptions } = base;
    const {
      mixins: globalMixins,
      optionsCache: cache,
      config: { optionMergeStrategies }
    } = instance.appContext;
    const cached = cache.get(base);
    let resolved;
    if (cached) {
      resolved = cached;
    } else if (!globalMixins.length && !mixins && !extendsOptions) {
      {
        resolved = base;
      }
    } else {
      resolved = {};
      if (globalMixins.length) {
        globalMixins.forEach(
          (m) => mergeOptions(resolved, m, optionMergeStrategies, true)
        );
      }
      mergeOptions(resolved, base, optionMergeStrategies);
    }
    if (isObject(base)) {
      cache.set(base, resolved);
    }
    return resolved;
  }
  function mergeOptions(to, from, strats, asMixin = false) {
    const { mixins, extends: extendsOptions } = from;
    if (extendsOptions) {
      mergeOptions(to, extendsOptions, strats, true);
    }
    if (mixins) {
      mixins.forEach(
        (m) => mergeOptions(to, m, strats, true)
      );
    }
    for (const key in from) {
      if (asMixin && key === "expose") ;
      else {
        const strat = internalOptionMergeStrats[key] || strats && strats[key];
        to[key] = strat ? strat(to[key], from[key]) : from[key];
      }
    }
    return to;
  }
  const internalOptionMergeStrats = {
    data: mergeDataFn,
    props: mergeEmitsOrPropsOptions,
    emits: mergeEmitsOrPropsOptions,
    // objects
    methods: mergeObjectOptions,
    computed: mergeObjectOptions,
    // lifecycle
    beforeCreate: mergeAsArray,
    created: mergeAsArray,
    beforeMount: mergeAsArray,
    mounted: mergeAsArray,
    beforeUpdate: mergeAsArray,
    updated: mergeAsArray,
    beforeDestroy: mergeAsArray,
    beforeUnmount: mergeAsArray,
    destroyed: mergeAsArray,
    unmounted: mergeAsArray,
    activated: mergeAsArray,
    deactivated: mergeAsArray,
    errorCaptured: mergeAsArray,
    serverPrefetch: mergeAsArray,
    // assets
    components: mergeObjectOptions,
    directives: mergeObjectOptions,
    // watch
    watch: mergeWatchOptions,
    // provide / inject
    provide: mergeDataFn,
    inject: mergeInject
  };
  function mergeDataFn(to, from) {
    if (!from) {
      return to;
    }
    if (!to) {
      return from;
    }
    return function mergedDataFn() {
      return extend(
        isFunction(to) ? to.call(this, this) : to,
        isFunction(from) ? from.call(this, this) : from
      );
    };
  }
  function mergeInject(to, from) {
    return mergeObjectOptions(normalizeInject(to), normalizeInject(from));
  }
  function normalizeInject(raw) {
    if (isArray(raw)) {
      const res = {};
      for (let i = 0; i < raw.length; i++) {
        res[raw[i]] = raw[i];
      }
      return res;
    }
    return raw;
  }
  function mergeAsArray(to, from) {
    return to ? [...new Set([].concat(to, from))] : from;
  }
  function mergeObjectOptions(to, from) {
    return to ? extend(/* @__PURE__ */ Object.create(null), to, from) : from;
  }
  function mergeEmitsOrPropsOptions(to, from) {
    if (to) {
      if (isArray(to) && isArray(from)) {
        return [.../* @__PURE__ */ new Set([...to, ...from])];
      }
      return extend(
        /* @__PURE__ */ Object.create(null),
        normalizePropsOrEmits(to),
        normalizePropsOrEmits(from != null ? from : {})
      );
    } else {
      return from;
    }
  }
  function mergeWatchOptions(to, from) {
    if (!to) return from;
    if (!from) return to;
    const merged = extend(/* @__PURE__ */ Object.create(null), to);
    for (const key in from) {
      merged[key] = mergeAsArray(to[key], from[key]);
    }
    return merged;
  }
  function createAppContext() {
    return {
      app: null,
      config: {
        isNativeTag: NO,
        performance: false,
        globalProperties: {},
        optionMergeStrategies: {},
        errorHandler: void 0,
        warnHandler: void 0,
        compilerOptions: {}
      },
      mixins: [],
      components: {},
      directives: {},
      provides: /* @__PURE__ */ Object.create(null),
      optionsCache: /* @__PURE__ */ new WeakMap(),
      propsCache: /* @__PURE__ */ new WeakMap(),
      emitsCache: /* @__PURE__ */ new WeakMap()
    };
  }
  let uid$1 = 0;
  function createAppAPI(render, hydrate) {
    return function createApp2(rootComponent, rootProps = null) {
      if (!isFunction(rootComponent)) {
        rootComponent = extend({}, rootComponent);
      }
      if (rootProps != null && !isObject(rootProps)) {
        rootProps = null;
      }
      const context = createAppContext();
      const installedPlugins = /* @__PURE__ */ new WeakSet();
      const pluginCleanupFns = [];
      let isMounted = false;
      const app = context.app = {
        _uid: uid$1++,
        _component: rootComponent,
        _props: rootProps,
        _container: null,
        _context: context,
        _instance: null,
        version,
        get config() {
          return context.config;
        },
        set config(v) {
        },
        use(plugin, ...options) {
          if (installedPlugins.has(plugin)) ;
          else if (plugin && isFunction(plugin.install)) {
            installedPlugins.add(plugin);
            plugin.install(app, ...options);
          } else if (isFunction(plugin)) {
            installedPlugins.add(plugin);
            plugin(app, ...options);
          } else ;
          return app;
        },
        mixin(mixin) {
          {
            if (!context.mixins.includes(mixin)) {
              context.mixins.push(mixin);
            }
          }
          return app;
        },
        component(name, component) {
          if (!component) {
            return context.components[name];
          }
          context.components[name] = component;
          return app;
        },
        directive(name, directive) {
          if (!directive) {
            return context.directives[name];
          }
          context.directives[name] = directive;
          return app;
        },
        mount(rootContainer, isHydrate, namespace) {
          if (!isMounted) {
            const vnode = app._ceVNode || createVNode(rootComponent, rootProps);
            vnode.appContext = context;
            if (namespace === true) {
              namespace = "svg";
            } else if (namespace === false) {
              namespace = void 0;
            }
            {
              render(vnode, rootContainer, namespace);
            }
            isMounted = true;
            app._container = rootContainer;
            rootContainer.__vue_app__ = app;
            return getComponentPublicInstance(vnode.component);
          }
        },
        onUnmount(cleanupFn) {
          pluginCleanupFns.push(cleanupFn);
        },
        unmount() {
          if (isMounted) {
            callWithAsyncErrorHandling(
              pluginCleanupFns,
              app._instance,
              16
            );
            render(null, app._container);
            delete app._container.__vue_app__;
          }
        },
        provide(key, value) {
          context.provides[key] = value;
          return app;
        },
        runWithContext(fn) {
          const lastApp = currentApp;
          currentApp = app;
          try {
            return fn();
          } finally {
            currentApp = lastApp;
          }
        }
      };
      return app;
    };
  }
  let currentApp = null;
  const getModelModifiers = (props, modelName) => {
    return modelName === "modelValue" || modelName === "model-value" ? props.modelModifiers : props[`${modelName}Modifiers`] || props[`${camelize(modelName)}Modifiers`] || props[`${hyphenate(modelName)}Modifiers`];
  };
  function emit(instance, event, ...rawArgs) {
    if (instance.isUnmounted) return;
    const props = instance.vnode.props || EMPTY_OBJ;
    let args = rawArgs;
    const isModelListener2 = event.startsWith("update:");
    const modifiers = isModelListener2 && getModelModifiers(props, event.slice(7));
    if (modifiers) {
      if (modifiers.trim) {
        args = rawArgs.map((a) => isString(a) ? a.trim() : a);
      }
      if (modifiers.number) {
        args = args.map(looseToNumber);
      }
    }
    let handlerName;
    let handler = props[handlerName = toHandlerKey(event)] || // also try camelCase event handler (#2249)
    props[handlerName = toHandlerKey(camelize(event))];
    if (!handler && isModelListener2) {
      handler = props[handlerName = toHandlerKey(hyphenate(event))];
    }
    if (handler) {
      callWithAsyncErrorHandling(
        handler,
        instance,
        6,
        args
      );
    }
    const onceHandler = props[handlerName + `Once`];
    if (onceHandler) {
      if (!instance.emitted) {
        instance.emitted = {};
      } else if (instance.emitted[handlerName]) {
        return;
      }
      instance.emitted[handlerName] = true;
      callWithAsyncErrorHandling(
        onceHandler,
        instance,
        6,
        args
      );
    }
  }
  const mixinEmitsCache = /* @__PURE__ */ new WeakMap();
  function normalizeEmitsOptions(comp, appContext, asMixin = false) {
    const cache = asMixin ? mixinEmitsCache : appContext.emitsCache;
    const cached = cache.get(comp);
    if (cached !== void 0) {
      return cached;
    }
    const raw = comp.emits;
    let normalized = {};
    let hasExtends = false;
    if (!isFunction(comp)) {
      const extendEmits = (raw2) => {
        const normalizedFromExtend = normalizeEmitsOptions(raw2, appContext, true);
        if (normalizedFromExtend) {
          hasExtends = true;
          extend(normalized, normalizedFromExtend);
        }
      };
      if (!asMixin && appContext.mixins.length) {
        appContext.mixins.forEach(extendEmits);
      }
      if (comp.extends) {
        extendEmits(comp.extends);
      }
      if (comp.mixins) {
        comp.mixins.forEach(extendEmits);
      }
    }
    if (!raw && !hasExtends) {
      if (isObject(comp)) {
        cache.set(comp, null);
      }
      return null;
    }
    if (isArray(raw)) {
      raw.forEach((key) => normalized[key] = null);
    } else {
      extend(normalized, raw);
    }
    if (isObject(comp)) {
      cache.set(comp, normalized);
    }
    return normalized;
  }
  function isEmitListener(options, key) {
    if (!options || !isOn(key)) {
      return false;
    }
    key = key.slice(2);
    key = key === "Once" ? key : key.replace(/Once$/, "");
    return hasOwn(options, key[0].toLowerCase() + key.slice(1)) || hasOwn(options, hyphenate(key)) || hasOwn(options, key);
  }
  function markAttrsAccessed() {
  }
  function renderComponentRoot(instance) {
    const {
      type: Component,
      vnode,
      proxy,
      withProxy,
      propsOptions: [propsOptions],
      slots,
      attrs,
      emit: emit2,
      render,
      renderCache,
      props,
      data,
      setupState,
      ctx,
      inheritAttrs
    } = instance;
    const prev = setCurrentRenderingInstance(instance);
    let result;
    let fallthroughAttrs;
    try {
      if (vnode.shapeFlag & 4) {
        const proxyToUse = withProxy || proxy;
        const thisProxy = false ? new Proxy(proxyToUse, {
          get(target, key, receiver) {
            warn$1(
              `Property '${String(
                key
              )}' was accessed via 'this'. Avoid using 'this' in templates.`
            );
            return Reflect.get(target, key, receiver);
          }
        }) : proxyToUse;
        result = normalizeVNode(
          render.call(
            thisProxy,
            proxyToUse,
            renderCache,
            false ? /* @__PURE__ */ shallowReadonly(props) : props,
            setupState,
            data,
            ctx
          )
        );
        fallthroughAttrs = attrs;
      } else {
        const render2 = Component;
        if (false) ;
        result = normalizeVNode(
          render2.length > 1 ? render2(
            false ? /* @__PURE__ */ shallowReadonly(props) : props,
            false ? {
              get attrs() {
                markAttrsAccessed();
                return /* @__PURE__ */ shallowReadonly(attrs);
              },
              slots,
              emit: emit2
            } : { attrs, slots, emit: emit2 }
          ) : render2(
            false ? /* @__PURE__ */ shallowReadonly(props) : props,
            null
          )
        );
        fallthroughAttrs = Component.props ? attrs : getFunctionalFallthrough(attrs);
      }
    } catch (err) {
      blockStack.length = 0;
      handleError(err, instance, 1);
      result = createVNode(Comment);
    }
    let root2 = result;
    if (fallthroughAttrs && inheritAttrs !== false) {
      const keys = Object.keys(fallthroughAttrs);
      const { shapeFlag } = root2;
      if (keys.length) {
        if (shapeFlag & (1 | 6)) {
          if (propsOptions && keys.some(isModelListener)) {
            fallthroughAttrs = filterModelListeners(
              fallthroughAttrs,
              propsOptions
            );
          }
          root2 = cloneVNode(root2, fallthroughAttrs, false, true);
        }
      }
    }
    if (vnode.dirs) {
      root2 = cloneVNode(root2, null, false, true);
      root2.dirs = root2.dirs ? root2.dirs.concat(vnode.dirs) : vnode.dirs;
    }
    if (vnode.transition) {
      const child = isTeleport(root2.type) ? getInnerChild$1(root2) || root2 : root2;
      setTransitionHooks(child, vnode.transition);
    }
    {
      result = root2;
    }
    setCurrentRenderingInstance(prev);
    return result;
  }
  const getFunctionalFallthrough = (attrs) => {
    let res;
    for (const key in attrs) {
      if (key === "class" || key === "style" || isOn(key)) {
        (res || (res = {}))[key] = attrs[key];
      }
    }
    return res;
  };
  const filterModelListeners = (attrs, props) => {
    const res = {};
    for (const key in attrs) {
      if (!isModelListener(key) || !(key.slice(9) in props)) {
        res[key] = attrs[key];
      }
    }
    return res;
  };
  function shouldUpdateComponent(prevVNode, nextVNode, optimized) {
    const { props: prevProps, children: prevChildren, component } = prevVNode;
    const { props: nextProps, children: nextChildren, patchFlag } = nextVNode;
    const emits = component.emitsOptions;
    if (nextVNode.dirs || nextVNode.transition) {
      return true;
    }
    if (optimized && patchFlag >= 0) {
      if (patchFlag & 1024) {
        return true;
      }
      if (patchFlag & 16) {
        if (!prevProps) {
          return !!nextProps;
        }
        return hasPropsChanged(prevProps, nextProps, emits);
      } else if (patchFlag & 8) {
        const dynamicProps = nextVNode.dynamicProps;
        for (let i = 0; i < dynamicProps.length; i++) {
          const key = dynamicProps[i];
          if (hasPropValueChanged(nextProps, prevProps, key) && !isEmitListener(emits, key)) {
            return true;
          }
        }
      }
    } else {
      if (prevChildren || nextChildren) {
        if (!nextChildren || !nextChildren.$stable) {
          return true;
        }
      }
      if (prevProps === nextProps) {
        return false;
      }
      if (!prevProps) {
        return !!nextProps;
      }
      if (!nextProps) {
        return true;
      }
      return hasPropsChanged(prevProps, nextProps, emits);
    }
    return false;
  }
  function hasPropsChanged(prevProps, nextProps, emitsOptions) {
    const nextKeys = Object.keys(nextProps);
    if (nextKeys.length !== Object.keys(prevProps).length) {
      return true;
    }
    for (let i = 0; i < nextKeys.length; i++) {
      const key = nextKeys[i];
      if (hasPropValueChanged(nextProps, prevProps, key) && !isEmitListener(emitsOptions, key)) {
        return true;
      }
    }
    return false;
  }
  function hasPropValueChanged(nextProps, prevProps, key) {
    const nextProp = nextProps[key];
    const prevProp = prevProps[key];
    if (key === "style" && isObject(nextProp) && isObject(prevProp)) {
      return !looseEqual(nextProp, prevProp);
    }
    return nextProp !== prevProp;
  }
  function updateHOCHostEl({ vnode, parent, suspense }, el) {
    while (parent) {
      const root2 = parent.subTree;
      if (root2.suspense && root2.suspense.activeBranch === vnode) {
        root2.suspense.vnode.el = root2.el = el;
        vnode = root2;
      }
      if (root2 === vnode) {
        (vnode = parent.vnode).el = el;
        parent = parent.parent;
      } else {
        break;
      }
    }
    if (suspense && suspense.activeBranch === vnode) {
      suspense.vnode.el = el;
    }
  }
  const internalObjectProto = {};
  const createInternalObject = () => Object.create(internalObjectProto);
  const isInternalObject = (obj) => Object.getPrototypeOf(obj) === internalObjectProto;
  function initProps(instance, rawProps, isStateful, isSSR = false) {
    const props = {};
    const attrs = createInternalObject();
    instance.propsDefaults = /* @__PURE__ */ Object.create(null);
    setFullProps(instance, rawProps, props, attrs);
    for (const key in instance.propsOptions[0]) {
      if (!(key in props)) {
        props[key] = void 0;
      }
    }
    if (isStateful) {
      instance.props = isSSR ? props : /* @__PURE__ */ shallowReactive(props);
    } else {
      if (!instance.type.props) {
        instance.props = attrs;
      } else {
        instance.props = props;
      }
    }
    instance.attrs = attrs;
  }
  function updateProps(instance, rawProps, rawPrevProps, optimized) {
    const {
      props,
      attrs,
      vnode: { patchFlag }
    } = instance;
    const rawCurrentProps = /* @__PURE__ */ toRaw(props);
    const [options] = instance.propsOptions;
    let hasAttrsChanged = false;
    if (
      // always force full diff in dev
      // - #1942 if hmr is enabled with sfc component
      // - vite#872 non-sfc component used by sfc component
      (optimized || patchFlag > 0) && !(patchFlag & 16)
    ) {
      if (patchFlag & 8) {
        const propsToUpdate = instance.vnode.dynamicProps;
        for (let i = 0; i < propsToUpdate.length; i++) {
          let key = propsToUpdate[i];
          if (isEmitListener(instance.emitsOptions, key)) {
            continue;
          }
          const value = rawProps[key];
          if (options) {
            if (hasOwn(attrs, key)) {
              if (value !== attrs[key]) {
                attrs[key] = value;
                hasAttrsChanged = true;
              }
            } else {
              const camelizedKey = camelize(key);
              props[camelizedKey] = resolvePropValue(
                options,
                rawCurrentProps,
                camelizedKey,
                value,
                instance,
                false
              );
            }
          } else {
            if (value !== attrs[key]) {
              attrs[key] = value;
              hasAttrsChanged = true;
            }
          }
        }
      }
    } else {
      if (setFullProps(instance, rawProps, props, attrs)) {
        hasAttrsChanged = true;
      }
      let kebabKey;
      for (const key in rawCurrentProps) {
        if (!rawProps || // for camelCase
        !hasOwn(rawProps, key) && // it's possible the original props was passed in as kebab-case
        // and converted to camelCase (#955)
        ((kebabKey = hyphenate(key)) === key || !hasOwn(rawProps, kebabKey))) {
          if (options) {
            if (rawPrevProps && // for camelCase
            (rawPrevProps[key] !== void 0 || // for kebab-case
            rawPrevProps[kebabKey] !== void 0)) {
              props[key] = resolvePropValue(
                options,
                rawCurrentProps,
                key,
                void 0,
                instance,
                true
              );
            }
          } else {
            delete props[key];
          }
        }
      }
      if (attrs !== rawCurrentProps) {
        for (const key in attrs) {
          if (!rawProps || !hasOwn(rawProps, key) && true) {
            delete attrs[key];
            hasAttrsChanged = true;
          }
        }
      }
    }
    if (hasAttrsChanged) {
      trigger(instance.attrs, "set", "");
    }
  }
  function setFullProps(instance, rawProps, props, attrs) {
    const [options, needCastKeys] = instance.propsOptions;
    let hasAttrsChanged = false;
    let rawCastValues;
    if (rawProps) {
      for (let key in rawProps) {
        if (isReservedProp(key)) {
          continue;
        }
        const value = rawProps[key];
        let camelKey;
        if (options && hasOwn(options, camelKey = camelize(key))) {
          if (!needCastKeys || !needCastKeys.includes(camelKey)) {
            props[camelKey] = value;
          } else {
            (rawCastValues || (rawCastValues = {}))[camelKey] = value;
          }
        } else if (!isEmitListener(instance.emitsOptions, key)) {
          if (!(key in attrs) || value !== attrs[key]) {
            attrs[key] = value;
            hasAttrsChanged = true;
          }
        }
      }
    }
    if (needCastKeys) {
      const rawCurrentProps = /* @__PURE__ */ toRaw(props);
      const castValues = rawCastValues || EMPTY_OBJ;
      for (let i = 0; i < needCastKeys.length; i++) {
        const key = needCastKeys[i];
        props[key] = resolvePropValue(
          options,
          rawCurrentProps,
          key,
          castValues[key],
          instance,
          !hasOwn(castValues, key)
        );
      }
    }
    return hasAttrsChanged;
  }
  function resolvePropValue(options, props, key, value, instance, isAbsent) {
    const opt = options[key];
    if (opt != null) {
      const hasDefault = hasOwn(opt, "default");
      if (hasDefault && value === void 0) {
        const defaultValue = opt.default;
        if (opt.type !== Function && !opt.skipFactory && isFunction(defaultValue)) {
          const { propsDefaults } = instance;
          if (key in propsDefaults) {
            value = propsDefaults[key];
          } else {
            const reset = setCurrentInstance(instance);
            value = propsDefaults[key] = defaultValue.call(
              null,
              props
            );
            reset();
          }
        } else {
          value = defaultValue;
        }
        if (instance.ce) {
          instance.ce._setProp(key, value);
        }
      }
      if (opt[
        0
        /* shouldCast */
      ]) {
        if (isAbsent && !hasDefault) {
          value = false;
        } else if (opt[
          1
          /* shouldCastTrue */
        ] && (value === "" || value === hyphenate(key))) {
          value = true;
        }
      }
    }
    return value;
  }
  const mixinPropsCache = /* @__PURE__ */ new WeakMap();
  function normalizePropsOptions(comp, appContext, asMixin = false) {
    const cache = asMixin ? mixinPropsCache : appContext.propsCache;
    const cached = cache.get(comp);
    if (cached) {
      return cached;
    }
    const raw = comp.props;
    const normalized = {};
    const needCastKeys = [];
    let hasExtends = false;
    if (!isFunction(comp)) {
      const extendProps = (raw2) => {
        hasExtends = true;
        const [props, keys] = normalizePropsOptions(raw2, appContext, true);
        extend(normalized, props);
        if (keys) needCastKeys.push(...keys);
      };
      if (!asMixin && appContext.mixins.length) {
        appContext.mixins.forEach(extendProps);
      }
      if (comp.extends) {
        extendProps(comp.extends);
      }
      if (comp.mixins) {
        comp.mixins.forEach(extendProps);
      }
    }
    if (!raw && !hasExtends) {
      if (isObject(comp)) {
        cache.set(comp, EMPTY_ARR);
      }
      return EMPTY_ARR;
    }
    if (isArray(raw)) {
      for (let i = 0; i < raw.length; i++) {
        const normalizedKey = camelize(raw[i]);
        if (validatePropName(normalizedKey)) {
          normalized[normalizedKey] = EMPTY_OBJ;
        }
      }
    } else if (raw) {
      for (const key in raw) {
        const normalizedKey = camelize(key);
        if (validatePropName(normalizedKey)) {
          const opt = raw[key];
          const prop = normalized[normalizedKey] = isArray(opt) || isFunction(opt) ? { type: opt } : extend({}, opt);
          const propType = prop.type;
          let shouldCast = false;
          let shouldCastTrue = true;
          if (isArray(propType)) {
            for (let index = 0; index < propType.length; ++index) {
              const type = propType[index];
              const typeName = isFunction(type) && type.name;
              if (typeName === "Boolean") {
                shouldCast = true;
                break;
              } else if (typeName === "String") {
                shouldCastTrue = false;
              }
            }
          } else {
            shouldCast = isFunction(propType) && propType.name === "Boolean";
          }
          prop[
            0
            /* shouldCast */
          ] = shouldCast;
          prop[
            1
            /* shouldCastTrue */
          ] = shouldCastTrue;
          if (shouldCast || hasOwn(prop, "default")) {
            needCastKeys.push(normalizedKey);
          }
        }
      }
    }
    const res = [normalized, needCastKeys];
    if (isObject(comp)) {
      cache.set(comp, res);
    }
    return res;
  }
  function validatePropName(key) {
    if (key[0] !== "$" && !isReservedProp(key)) {
      return true;
    }
    return false;
  }
  const isInternalKey = (key) => key === "_" || key === "_ctx" || key === "$stable";
  const normalizeSlotValue = (value) => isArray(value) ? value.map(normalizeVNode) : [normalizeVNode(value)];
  const normalizeSlot = (key, rawSlot, ctx) => {
    if (rawSlot._n) {
      return rawSlot;
    }
    const normalized = withCtx((...args) => {
      if (false) ;
      return normalizeSlotValue(rawSlot(...args));
    }, ctx);
    normalized._c = false;
    return normalized;
  };
  const normalizeObjectSlots = (rawSlots, slots, instance) => {
    const ctx = rawSlots._ctx;
    for (const key in rawSlots) {
      if (isInternalKey(key)) continue;
      const value = rawSlots[key];
      if (isFunction(value)) {
        slots[key] = normalizeSlot(key, value, ctx);
      } else if (value != null) {
        const normalized = normalizeSlotValue(value);
        slots[key] = () => normalized;
      }
    }
  };
  const normalizeVNodeSlots = (instance, children) => {
    const normalized = normalizeSlotValue(children);
    instance.slots.default = () => normalized;
  };
  const assignSlots = (slots, children, optimized) => {
    for (const key in children) {
      if (optimized || !isInternalKey(key)) {
        slots[key] = children[key];
      }
    }
  };
  const initSlots = (instance, children, optimized) => {
    const slots = instance.slots = createInternalObject();
    if (instance.vnode.shapeFlag & 32) {
      const type = children._;
      if (type) {
        assignSlots(slots, children, optimized);
        if (optimized) {
          def(slots, "_", type, true);
        }
      } else {
        normalizeObjectSlots(children, slots);
      }
    } else if (children) {
      normalizeVNodeSlots(instance, children);
    }
  };
  const updateSlots = (instance, children, optimized) => {
    const { vnode, slots } = instance;
    let needDeletionCheck = true;
    let deletionComparisonTarget = EMPTY_OBJ;
    if (vnode.shapeFlag & 32) {
      const type = children._;
      if (type) {
        if (optimized && type === 1) {
          needDeletionCheck = false;
        } else {
          assignSlots(slots, children, optimized);
        }
      } else {
        needDeletionCheck = !children.$stable;
        normalizeObjectSlots(children, slots);
      }
      deletionComparisonTarget = children;
    } else if (children) {
      normalizeVNodeSlots(instance, children);
      deletionComparisonTarget = { default: 1 };
    }
    if (needDeletionCheck) {
      for (const key in slots) {
        if (!isInternalKey(key) && deletionComparisonTarget[key] == null) {
          delete slots[key];
        }
      }
    }
  };
  const queuePostRenderEffect = queueEffectWithSuspense;
  function createRenderer(options) {
    return baseCreateRenderer(options);
  }
  function baseCreateRenderer(options, createHydrationFns) {
    const target = getGlobalThis();
    target.__VUE__ = true;
    const {
      insert: hostInsert,
      remove: hostRemove,
      patchProp: hostPatchProp,
      createElement: hostCreateElement,
      createText: hostCreateText,
      createComment: hostCreateComment,
      setText: hostSetText,
      setElementText: hostSetElementText,
      parentNode: hostParentNode,
      nextSibling: hostNextSibling,
      setScopeId: hostSetScopeId = NOOP,
      insertStaticContent: hostInsertStaticContent
    } = options;
    const patch = (n1, n2, container, anchor = null, parentComponent = null, parentSuspense = null, namespace = void 0, slotScopeIds = null, optimized = !!n2.dynamicChildren) => {
      if (n1 === n2) {
        return;
      }
      if (n1 && !isSameVNodeType(n1, n2)) {
        anchor = getNextHostNode(n1);
        unmount(n1, parentComponent, parentSuspense, true);
        n1 = null;
      }
      if (n2.patchFlag === -2) {
        optimized = false;
        n2.dynamicChildren = null;
      }
      if (n2.dynamicChildren && n1 && n1.dynamicChildren && n1.dynamicChildren.hasOnce) {
        if (n2.dynamicChildren === EMPTY_ARR) {
          n2.dynamicChildren = [];
        }
        n2.dynamicChildren.hasOnce = true;
      }
      const { type, ref: ref3, shapeFlag } = n2;
      switch (type) {
        case Text:
          processText(n1, n2, container, anchor);
          break;
        case Comment:
          processCommentNode(n1, n2, container, anchor);
          break;
        case Static:
          if (n1 == null) {
            mountStaticNode(n2, container, anchor, namespace);
          }
          break;
        case Fragment:
          processFragment(
            n1,
            n2,
            container,
            anchor,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
          break;
        default:
          if (shapeFlag & 1) {
            processElement(
              n1,
              n2,
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized
            );
          } else if (shapeFlag & 6) {
            processComponent(
              n1,
              n2,
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized
            );
          } else if (shapeFlag & 64) {
            type.process(
              n1,
              n2,
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized,
              internals
            );
          } else if (shapeFlag & 128) {
            type.process(
              n1,
              n2,
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized,
              internals
            );
          } else ;
      }
      if (ref3 != null && parentComponent) {
        setRef(ref3, n1 && n1.ref, parentSuspense, n2 || n1, !n2);
      } else if (ref3 == null && n1 && n1.ref != null) {
        setRef(n1.ref, null, parentSuspense, n1, true);
      }
    };
    const processText = (n1, n2, container, anchor) => {
      if (n1 == null) {
        hostInsert(
          n2.el = hostCreateText(n2.children),
          container,
          anchor
        );
      } else {
        const el = n2.el = n1.el;
        if (n2.children !== n1.children) {
          hostSetText(el, n2.children);
        }
      }
    };
    const processCommentNode = (n1, n2, container, anchor) => {
      if (n1 == null) {
        hostInsert(
          n2.el = hostCreateComment(n2.children || ""),
          container,
          anchor
        );
      } else {
        n2.el = n1.el;
      }
    };
    const mountStaticNode = (n2, container, anchor, namespace) => {
      [n2.el, n2.anchor] = hostInsertStaticContent(
        n2.children,
        container,
        anchor,
        namespace,
        n2.el,
        n2.anchor
      );
    };
    const moveStaticNode = ({ el, anchor }, container, nextSibling) => {
      let next;
      while (el && el !== anchor) {
        next = hostNextSibling(el);
        hostInsert(el, container, nextSibling);
        el = next;
      }
      hostInsert(anchor, container, nextSibling);
    };
    const removeStaticNode = ({ el, anchor }) => {
      let next;
      while (el && el !== anchor) {
        next = hostNextSibling(el);
        hostRemove(el);
        el = next;
      }
      hostRemove(anchor);
    };
    const processElement = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
      if (n2.type === "svg") {
        namespace = "svg";
      } else if (n2.type === "math") {
        namespace = "mathml";
      }
      if (n1 == null) {
        mountElement(
          n2,
          container,
          anchor,
          parentComponent,
          parentSuspense,
          namespace,
          slotScopeIds,
          optimized
        );
      } else {
        const customElement = n1.el && n1.el._isVueCE ? n1.el : null;
        try {
          if (customElement) {
            customElement._beginPatch();
          }
          patchElement(
            n1,
            n2,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
        } finally {
          if (customElement) {
            customElement._endPatch();
          }
        }
      }
    };
    const mountElement = (vnode, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
      let el;
      let vnodeHook;
      const { props, shapeFlag, transition, dirs } = vnode;
      el = vnode.el = hostCreateElement(
        vnode.type,
        namespace,
        props && props.is,
        props
      );
      if (shapeFlag & 8) {
        hostSetElementText(el, vnode.children);
      } else if (shapeFlag & 16) {
        mountChildren(
          vnode.children,
          el,
          null,
          parentComponent,
          parentSuspense,
          resolveChildrenNamespace(vnode, namespace),
          slotScopeIds,
          optimized
        );
      }
      if (dirs) {
        invokeDirectiveHook(vnode, null, parentComponent, "created");
      }
      setScopeId(el, vnode, vnode.scopeId, slotScopeIds, parentComponent);
      if (props) {
        for (const key in props) {
          if (key !== "value" && !isReservedProp(key)) {
            hostPatchProp(el, key, null, props[key], namespace, parentComponent);
          }
        }
        if ("value" in props) {
          hostPatchProp(el, "value", null, props.value, namespace);
        }
        if (vnodeHook = props.onVnodeBeforeMount) {
          invokeVNodeHook(vnodeHook, parentComponent, vnode);
        }
      }
      if (dirs) {
        invokeDirectiveHook(vnode, null, parentComponent, "beforeMount");
      }
      const needCallTransitionHooks = needTransition(parentSuspense, transition);
      if (needCallTransitionHooks) {
        transition.beforeEnter(el);
      }
      hostInsert(el, container, anchor);
      if ((vnodeHook = props && props.onVnodeMounted) || needCallTransitionHooks || dirs) {
        queuePostRenderEffect(() => {
          try {
            vnodeHook && invokeVNodeHook(vnodeHook, parentComponent, vnode);
            needCallTransitionHooks && transition.enter(el);
            dirs && invokeDirectiveHook(vnode, null, parentComponent, "mounted");
          } finally {
          }
        }, parentSuspense);
      }
    };
    const setScopeId = (el, vnode, scopeId, slotScopeIds, parentComponent) => {
      if (scopeId) {
        hostSetScopeId(el, scopeId);
      }
      if (slotScopeIds) {
        for (let i = 0; i < slotScopeIds.length; i++) {
          hostSetScopeId(el, slotScopeIds[i]);
        }
      }
      if (parentComponent) {
        let subTree = parentComponent.subTree;
        if (vnode === subTree || isSuspense(subTree.type) && (subTree.ssContent === vnode || subTree.ssFallback === vnode)) {
          const parentVNode = parentComponent.vnode;
          setScopeId(
            el,
            parentVNode,
            parentVNode.scopeId,
            parentVNode.slotScopeIds,
            parentComponent.parent
          );
        }
      }
    };
    const mountChildren = (children, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized, start = 0) => {
      for (let i = start; i < children.length; i++) {
        const child = children[i] = optimized ? cloneIfMounted(children[i]) : normalizeVNode(children[i]);
        patch(
          null,
          child,
          container,
          anchor,
          parentComponent,
          parentSuspense,
          namespace,
          slotScopeIds,
          optimized
        );
      }
    };
    const patchElement = (n1, n2, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
      const el = n2.el = n1.el;
      let { patchFlag, dynamicChildren, dirs } = n2;
      patchFlag |= n1.patchFlag & 16;
      const oldProps = n1.props || EMPTY_OBJ;
      const newProps = n2.props || EMPTY_OBJ;
      let vnodeHook;
      parentComponent && toggleRecurse(parentComponent, false);
      if (vnodeHook = newProps.onVnodeBeforeUpdate) {
        invokeVNodeHook(vnodeHook, parentComponent, n2, n1);
      }
      if (dirs) {
        invokeDirectiveHook(n2, n1, parentComponent, "beforeUpdate");
      }
      parentComponent && toggleRecurse(parentComponent, true);
      if (
        // #6385 the old vnode may be a user-wrapped non-isomorphic block
        // Force full diff when block metadata is unstable.
        dynamicChildren && (!n1.dynamicChildren || n1.dynamicChildren.length !== dynamicChildren.length)
      ) {
        patchFlag = 0;
        optimized = false;
        dynamicChildren = null;
      }
      if (oldProps.innerHTML && newProps.innerHTML == null || oldProps.textContent && newProps.textContent == null) {
        hostSetElementText(el, "");
      }
      if (dynamicChildren) {
        patchBlockChildren(
          n1.dynamicChildren,
          dynamicChildren,
          el,
          parentComponent,
          parentSuspense,
          resolveChildrenNamespace(n2, namespace),
          slotScopeIds
        );
      } else if (!optimized) {
        patchChildren(
          n1,
          n2,
          el,
          null,
          parentComponent,
          parentSuspense,
          resolveChildrenNamespace(n2, namespace),
          slotScopeIds,
          false
        );
      }
      if (patchFlag > 0) {
        if (patchFlag & 16) {
          patchProps(el, oldProps, newProps, parentComponent, namespace);
        } else {
          if (patchFlag & 2) {
            if (oldProps.class !== newProps.class) {
              hostPatchProp(el, "class", null, newProps.class, namespace);
            }
          }
          if (patchFlag & 4) {
            hostPatchProp(el, "style", oldProps.style, newProps.style, namespace);
          }
          if (patchFlag & 8) {
            const propsToUpdate = n2.dynamicProps;
            for (let i = 0; i < propsToUpdate.length; i++) {
              const key = propsToUpdate[i];
              const prev = oldProps[key];
              const next = newProps[key];
              if (next !== prev || key === "value") {
                hostPatchProp(el, key, prev, next, namespace, parentComponent);
              }
            }
          }
        }
        if (patchFlag & 1) {
          if (n1.children !== n2.children) {
            hostSetElementText(el, n2.children);
          }
        }
      } else if (!optimized && dynamicChildren == null) {
        patchProps(el, oldProps, newProps, parentComponent, namespace);
      }
      if ((vnodeHook = newProps.onVnodeUpdated) || dirs) {
        queuePostRenderEffect(() => {
          vnodeHook && invokeVNodeHook(vnodeHook, parentComponent, n2, n1);
          dirs && invokeDirectiveHook(n2, n1, parentComponent, "updated");
        }, parentSuspense);
      }
    };
    const patchBlockChildren = (oldChildren, newChildren, fallbackContainer, parentComponent, parentSuspense, namespace, slotScopeIds) => {
      for (let i = 0; i < newChildren.length; i++) {
        const oldVNode = oldChildren[i];
        const newVNode = newChildren[i];
        const container = (
          // oldVNode may be an errored async setup() component inside Suspense
          // which will not have a mounted element
          oldVNode.el && // - In the case of a Fragment, we need to provide the actual parent
          // of the Fragment itself so it can move its children.
          (oldVNode.type === Fragment || // - In the case of different nodes, there is going to be a replacement
          // which also requires the correct parent container
          !isSameVNodeType(oldVNode, newVNode) || // - In the case of a component, it could contain anything.
          oldVNode.shapeFlag & (6 | 64 | 128)) ? hostParentNode(oldVNode.el) : (
            // In other cases, the parent container is not actually used so we
            // just pass the block element here to avoid a DOM parentNode call.
            fallbackContainer
          )
        );
        patch(
          oldVNode,
          newVNode,
          container,
          null,
          parentComponent,
          parentSuspense,
          namespace,
          slotScopeIds,
          true
        );
      }
    };
    const patchProps = (el, oldProps, newProps, parentComponent, namespace) => {
      if (oldProps !== newProps) {
        if (oldProps !== EMPTY_OBJ) {
          for (const key in oldProps) {
            if (!isReservedProp(key) && !(key in newProps)) {
              hostPatchProp(
                el,
                key,
                oldProps[key],
                null,
                namespace,
                parentComponent
              );
            }
          }
        }
        for (const key in newProps) {
          if (isReservedProp(key)) continue;
          const next = newProps[key];
          const prev = oldProps[key];
          if (next !== prev && key !== "value") {
            hostPatchProp(el, key, prev, next, namespace, parentComponent);
          }
        }
        if ("value" in newProps) {
          hostPatchProp(el, "value", oldProps.value, newProps.value, namespace);
        }
      }
    };
    const processFragment = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
      const fragmentStartAnchor = n2.el = n1 ? n1.el : hostCreateText("");
      const fragmentEndAnchor = n2.anchor = n1 ? n1.anchor : hostCreateText("");
      let { patchFlag, dynamicChildren, slotScopeIds: fragmentSlotScopeIds } = n2;
      if (fragmentSlotScopeIds) {
        slotScopeIds = slotScopeIds ? slotScopeIds.concat(fragmentSlotScopeIds) : fragmentSlotScopeIds;
      }
      if (n1 == null) {
        hostInsert(fragmentStartAnchor, container, anchor);
        hostInsert(fragmentEndAnchor, container, anchor);
        mountChildren(
          // #10007
          // such fragment like `<></>` will be compiled into
          // a fragment which doesn't have a children.
          // In this case fallback to an empty array
          n2.children || [],
          container,
          fragmentEndAnchor,
          parentComponent,
          parentSuspense,
          namespace,
          slotScopeIds,
          optimized
        );
      } else {
        if (patchFlag > 0 && patchFlag & 64 && dynamicChildren && // #2715 the previous fragment could've been a BAILed one as a result
        // of renderSlot() with no valid children
        n1.dynamicChildren && n1.dynamicChildren.length === dynamicChildren.length) {
          patchBlockChildren(
            n1.dynamicChildren,
            dynamicChildren,
            container,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds
          );
          if (
            // #2080 if the stable fragment has a key, it's a <template v-for> that may
            //  get moved around. Make sure all root level vnodes inherit el.
            // #2134 or if it's a component root, it may also get moved around
            // as the component is being moved.
            n2.key != null || parentComponent && n2 === parentComponent.subTree
          ) {
            traverseStaticChildren(
              n1,
              n2,
              true
              /* shallow */
            );
          }
        } else {
          patchChildren(
            n1,
            n2,
            container,
            fragmentEndAnchor,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
        }
      }
    };
    const processComponent = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
      n2.slotScopeIds = slotScopeIds;
      if (n1 == null) {
        if (n2.shapeFlag & 512) {
          parentComponent.ctx.activate(
            n2,
            container,
            anchor,
            namespace,
            optimized
          );
        } else {
          mountComponent(
            n2,
            container,
            anchor,
            parentComponent,
            parentSuspense,
            namespace,
            optimized
          );
        }
      } else {
        updateComponent(n1, n2, optimized);
      }
    };
    const mountComponent = (initialVNode, container, anchor, parentComponent, parentSuspense, namespace, optimized) => {
      const instance = initialVNode.component = createComponentInstance(
        initialVNode,
        parentComponent,
        parentSuspense
      );
      if (isKeepAlive(initialVNode)) {
        instance.ctx.renderer = internals;
      }
      {
        setupComponent(instance, false, optimized);
      }
      if (instance.asyncDep) {
        parentSuspense && parentSuspense.registerDep(instance, setupRenderEffect, optimized);
        if (!initialVNode.el) {
          const placeholder = instance.subTree = createVNode(Comment);
          processCommentNode(null, placeholder, container, anchor);
          initialVNode.placeholder = placeholder.el;
        }
      } else {
        setupRenderEffect(
          instance,
          initialVNode,
          container,
          anchor,
          parentSuspense,
          namespace,
          optimized
        );
      }
    };
    const updateComponent = (n1, n2, optimized) => {
      const instance = n2.component = n1.component;
      if (shouldUpdateComponent(n1, n2, optimized)) {
        if (instance.asyncDep && !instance.asyncResolved) {
          n2.el = n1.el;
          updateComponentPreRender(instance, n2, optimized);
          return;
        } else {
          instance.next = n2;
          instance.update();
        }
      } else {
        n2.el = n1.el;
        instance.vnode = n2;
      }
    };
    const setupRenderEffect = (instance, initialVNode, container, anchor, parentSuspense, namespace, optimized) => {
      const componentUpdateFn = () => {
        if (!instance.isMounted) {
          let vnodeHook;
          const { el, props } = initialVNode;
          const { bm, m, parent, root: root2, type } = instance;
          const isAsyncWrapperVNode = isAsyncWrapper(initialVNode);
          toggleRecurse(instance, false);
          if (bm) {
            invokeArrayFns(bm);
          }
          if (!isAsyncWrapperVNode && (vnodeHook = props && props.onVnodeBeforeMount)) {
            invokeVNodeHook(vnodeHook, parent, initialVNode);
          }
          toggleRecurse(instance, true);
          {
            if (root2.ce && root2.ce._hasShadowRoot()) {
              root2.ce._injectChildStyle(
                type,
                instance.parent ? instance.parent.type : void 0
              );
            }
            const subTree = instance.subTree = renderComponentRoot(instance);
            patch(
              null,
              subTree,
              container,
              anchor,
              instance,
              parentSuspense,
              namespace
            );
            initialVNode.el = subTree.el;
          }
          if (m) {
            queuePostRenderEffect(m, parentSuspense);
          }
          if (!isAsyncWrapperVNode && (vnodeHook = props && props.onVnodeMounted)) {
            const scopedInitialVNode = initialVNode;
            queuePostRenderEffect(
              () => invokeVNodeHook(vnodeHook, parent, scopedInitialVNode),
              parentSuspense
            );
          }
          if (initialVNode.shapeFlag & 256 || parent && isAsyncWrapper(parent.vnode) && parent.vnode.shapeFlag & 256) {
            instance.a && queuePostRenderEffect(instance.a, parentSuspense);
          }
          instance.isMounted = true;
          initialVNode = container = anchor = null;
        } else {
          let { next, bu, u, parent, vnode } = instance;
          {
            const nonHydratedAsyncRoot = locateNonHydratedAsyncRoot(instance);
            if (nonHydratedAsyncRoot) {
              if (next) {
                next.el = vnode.el;
                updateComponentPreRender(instance, next, optimized);
              }
              nonHydratedAsyncRoot.asyncDep.then(() => {
                queuePostRenderEffect(() => {
                  if (!instance.isUnmounted) update();
                }, parentSuspense);
              });
              return;
            }
          }
          let originNext = next;
          let vnodeHook;
          toggleRecurse(instance, false);
          if (next) {
            next.el = vnode.el;
            updateComponentPreRender(instance, next, optimized);
          } else {
            next = vnode;
          }
          if (bu) {
            invokeArrayFns(bu);
          }
          if (vnodeHook = next.props && next.props.onVnodeBeforeUpdate) {
            invokeVNodeHook(vnodeHook, parent, next, vnode);
          }
          toggleRecurse(instance, true);
          const nextTree = renderComponentRoot(instance);
          const prevTree = instance.subTree;
          instance.subTree = nextTree;
          patch(
            prevTree,
            nextTree,
            // parent may have changed if it's in a teleport
            hostParentNode(prevTree.el),
            // anchor may have changed if it's in a fragment
            getNextHostNode(prevTree),
            instance,
            parentSuspense,
            namespace
          );
          next.el = nextTree.el;
          if (originNext === null) {
            updateHOCHostEl(instance, nextTree.el);
          }
          if (u) {
            queuePostRenderEffect(u, parentSuspense);
          }
          if (vnodeHook = next.props && next.props.onVnodeUpdated) {
            queuePostRenderEffect(
              () => invokeVNodeHook(vnodeHook, parent, next, vnode),
              parentSuspense
            );
          }
        }
      };
      instance.scope.on();
      const effect2 = instance.effect = new ReactiveEffect(componentUpdateFn);
      instance.scope.off();
      const update = instance.update = effect2.run.bind(effect2);
      const job = instance.job = effect2.runIfDirty.bind(effect2);
      job.i = instance;
      job.id = instance.uid;
      effect2.scheduler = () => queueJob(job);
      toggleRecurse(instance, true);
      update();
    };
    const updateComponentPreRender = (instance, nextVNode, optimized) => {
      nextVNode.component = instance;
      const prevProps = instance.vnode.props;
      instance.vnode = nextVNode;
      instance.next = null;
      updateProps(instance, nextVNode.props, prevProps, optimized);
      updateSlots(instance, nextVNode.children, optimized);
      pauseTracking();
      flushPreFlushCbs(instance);
      resetTracking();
    };
    const patchChildren = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized = false) => {
      const c1 = n1 && n1.children;
      const prevShapeFlag = n1 ? n1.shapeFlag : 0;
      const c2 = n2.children;
      const { patchFlag, shapeFlag } = n2;
      if (patchFlag > 0) {
        if (patchFlag & 128) {
          patchKeyedChildren(
            c1,
            c2,
            container,
            anchor,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
          return;
        } else if (patchFlag & 256) {
          patchUnkeyedChildren(
            c1,
            c2,
            container,
            anchor,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
          return;
        }
      }
      if (shapeFlag & 8) {
        if (prevShapeFlag & 16) {
          unmountChildren(c1, parentComponent, parentSuspense);
        }
        if (c2 !== c1) {
          hostSetElementText(container, c2);
        }
      } else {
        if (prevShapeFlag & 16) {
          if (shapeFlag & 16) {
            patchKeyedChildren(
              c1,
              c2,
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized
            );
          } else {
            unmountChildren(c1, parentComponent, parentSuspense, true);
          }
        } else {
          if (prevShapeFlag & 8) {
            hostSetElementText(container, "");
          }
          if (shapeFlag & 16) {
            mountChildren(
              c2,
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized
            );
          }
        }
      }
    };
    const patchUnkeyedChildren = (c1, c2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
      c1 = c1 || EMPTY_ARR;
      c2 = c2 || EMPTY_ARR;
      const oldLength = c1.length;
      const newLength = c2.length;
      const commonLength = Math.min(oldLength, newLength);
      let i;
      for (i = 0; i < commonLength; i++) {
        const nextChild = c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]);
        patch(
          c1[i],
          nextChild,
          container,
          null,
          parentComponent,
          parentSuspense,
          namespace,
          slotScopeIds,
          optimized
        );
      }
      if (oldLength > newLength) {
        unmountChildren(
          c1,
          parentComponent,
          parentSuspense,
          true,
          false,
          commonLength
        );
      } else {
        mountChildren(
          c2,
          container,
          anchor,
          parentComponent,
          parentSuspense,
          namespace,
          slotScopeIds,
          optimized,
          commonLength
        );
      }
    };
    const patchKeyedChildren = (c1, c2, container, parentAnchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
      let i = 0;
      const l2 = c2.length;
      let e1 = c1.length - 1;
      let e2 = l2 - 1;
      while (i <= e1 && i <= e2) {
        const n1 = c1[i];
        const n2 = c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]);
        if (isSameVNodeType(n1, n2)) {
          patch(
            n1,
            n2,
            container,
            null,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
        } else {
          break;
        }
        i++;
      }
      while (i <= e1 && i <= e2) {
        const n1 = c1[e1];
        const n2 = c2[e2] = optimized ? cloneIfMounted(c2[e2]) : normalizeVNode(c2[e2]);
        if (isSameVNodeType(n1, n2)) {
          patch(
            n1,
            n2,
            container,
            null,
            parentComponent,
            parentSuspense,
            namespace,
            slotScopeIds,
            optimized
          );
        } else {
          break;
        }
        e1--;
        e2--;
      }
      if (i > e1) {
        if (i <= e2) {
          const nextPos = e2 + 1;
          const anchor = nextPos < l2 ? c2[nextPos].el : parentAnchor;
          while (i <= e2) {
            patch(
              null,
              c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]),
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized
            );
            i++;
          }
        }
      } else if (i > e2) {
        while (i <= e1) {
          unmount(c1[i], parentComponent, parentSuspense, true);
          i++;
        }
      } else {
        const s1 = i;
        const s2 = i;
        const keyToNewIndexMap = /* @__PURE__ */ new Map();
        for (i = s2; i <= e2; i++) {
          const nextChild = c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]);
          if (nextChild.key != null) {
            keyToNewIndexMap.set(nextChild.key, i);
          }
        }
        let j;
        let patched = 0;
        const toBePatched = e2 - s2 + 1;
        let moved = false;
        let maxNewIndexSoFar = 0;
        const newIndexToOldIndexMap = new Array(toBePatched);
        for (i = 0; i < toBePatched; i++) newIndexToOldIndexMap[i] = 0;
        for (i = s1; i <= e1; i++) {
          const prevChild = c1[i];
          if (patched >= toBePatched) {
            unmount(prevChild, parentComponent, parentSuspense, true);
            continue;
          }
          let newIndex;
          if (prevChild.key != null) {
            newIndex = keyToNewIndexMap.get(prevChild.key);
          } else {
            for (j = s2; j <= e2; j++) {
              if (newIndexToOldIndexMap[j - s2] === 0 && isSameVNodeType(prevChild, c2[j])) {
                newIndex = j;
                break;
              }
            }
          }
          if (newIndex === void 0) {
            unmount(prevChild, parentComponent, parentSuspense, true);
          } else {
            newIndexToOldIndexMap[newIndex - s2] = i + 1;
            if (newIndex >= maxNewIndexSoFar) {
              maxNewIndexSoFar = newIndex;
            } else {
              moved = true;
            }
            patch(
              prevChild,
              c2[newIndex],
              container,
              null,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized
            );
            patched++;
          }
        }
        const increasingNewIndexSequence = moved ? getSequence(newIndexToOldIndexMap) : EMPTY_ARR;
        j = increasingNewIndexSequence.length - 1;
        for (i = toBePatched - 1; i >= 0; i--) {
          const nextIndex = s2 + i;
          const nextChild = c2[nextIndex];
          const anchorVNode = c2[nextIndex + 1];
          const anchor = nextIndex + 1 < l2 ? (
            // #13559, #14173 fallback to el placeholder for unresolved async component
            anchorVNode.el || resolveAsyncComponentPlaceholder(anchorVNode)
          ) : parentAnchor;
          if (newIndexToOldIndexMap[i] === 0) {
            patch(
              null,
              nextChild,
              container,
              anchor,
              parentComponent,
              parentSuspense,
              namespace,
              slotScopeIds,
              optimized
            );
          } else if (moved) {
            if (j < 0 || i !== increasingNewIndexSequence[j]) {
              move(nextChild, container, anchor, 2);
            } else {
              j--;
            }
          }
        }
      }
    };
    const move = (vnode, container, anchor, moveType, parentSuspense = null) => {
      const { el, type, transition, children, shapeFlag } = vnode;
      if (shapeFlag & 6) {
        move(vnode.component.subTree, container, anchor, moveType);
        return;
      }
      if (shapeFlag & 128) {
        vnode.suspense.move(container, anchor, moveType);
        return;
      }
      if (shapeFlag & 64) {
        type.move(vnode, container, anchor, internals);
        return;
      }
      if (type === Fragment) {
        hostInsert(el, container, anchor);
        for (let i = 0; i < children.length; i++) {
          move(children[i], container, anchor, moveType);
        }
        hostInsert(vnode.anchor, container, anchor);
        return;
      }
      if (type === Static) {
        moveStaticNode(vnode, container, anchor);
        return;
      }
      const needTransition2 = moveType !== 2 && shapeFlag & 1 && transition;
      if (needTransition2) {
        if (moveType === 0) {
          if (transition.persisted && !el[leaveCbKey]) {
            hostInsert(el, container, anchor);
          } else {
            transition.beforeEnter(el);
            hostInsert(el, container, anchor);
            queuePostRenderEffect(() => transition.enter(el), parentSuspense);
          }
        } else {
          const { leave, delayLeave, afterLeave } = transition;
          const remove22 = () => {
            if (vnode.ctx.isUnmounted) {
              hostRemove(el);
            } else {
              hostInsert(el, container, anchor);
            }
          };
          const performLeave = () => {
            const wasLeaving = el._isLeaving || !!el[leaveCbKey];
            if (el._isLeaving) {
              el[leaveCbKey](
                true
                /* cancelled */
              );
            }
            if (transition.persisted && !wasLeaving) {
              remove22();
            } else {
              leave(el, () => {
                remove22();
                afterLeave && afterLeave();
              });
            }
          };
          if (delayLeave) {
            delayLeave(el, remove22, performLeave);
          } else {
            performLeave();
          }
        }
      } else {
        hostInsert(el, container, anchor);
      }
    };
    const unmount = (vnode, parentComponent, parentSuspense, doRemove = false, optimized = false) => {
      const {
        type,
        props,
        ref: ref3,
        children,
        dynamicChildren,
        shapeFlag,
        patchFlag,
        dirs,
        cacheIndex,
        memo
      } = vnode;
      if (patchFlag === -2 || dynamicChildren && dynamicChildren.hasOnce) {
        optimized = false;
      }
      if (ref3 != null) {
        pauseTracking();
        setRef(ref3, null, parentSuspense, vnode, true);
        resetTracking();
      }
      if (cacheIndex != null && (!vnode.ctx || vnode.ctx === parentComponent)) {
        parentComponent.renderCache[cacheIndex] = void 0;
      }
      if (shapeFlag & 256) {
        parentComponent.ctx.deactivate(vnode);
        return;
      }
      const shouldInvokeDirs = shapeFlag & 1 && dirs;
      const shouldInvokeVnodeHook = !isAsyncWrapper(vnode);
      let vnodeHook;
      if (shouldInvokeVnodeHook && (vnodeHook = props && props.onVnodeBeforeUnmount)) {
        invokeVNodeHook(vnodeHook, parentComponent, vnode);
      }
      if (shapeFlag & 6) {
        unmountComponent(vnode.component, parentSuspense, doRemove);
      } else {
        if (shapeFlag & 128) {
          vnode.suspense.unmount(parentSuspense, doRemove);
          return;
        }
        if (shouldInvokeDirs) {
          invokeDirectiveHook(vnode, null, parentComponent, "beforeUnmount");
        }
        if (shapeFlag & 64) {
          vnode.type.remove(
            vnode,
            parentComponent,
            parentSuspense,
            internals,
            doRemove
          );
        } else if (dynamicChildren && // #5154
        // when v-once is used inside a block, setBlockTracking(-1) marks the
        // parent block with hasOnce: true
        // so that it doesn't take the fast path during unmount - otherwise
        // components nested in v-once are never unmounted.
        !dynamicChildren.hasOnce && // #1153: fast path should not be taken for non-stable (v-for) fragments
        (type !== Fragment || patchFlag > 0 && patchFlag & 64)) {
          unmountChildren(
            dynamicChildren,
            parentComponent,
            parentSuspense,
            false,
            true
          );
        } else if (type === Fragment && patchFlag & (128 | 256) || !optimized && shapeFlag & 16) {
          unmountChildren(children, parentComponent, parentSuspense);
        }
        if (doRemove) {
          remove2(vnode);
        }
      }
      const shouldInvalidateMemo = memo != null && cacheIndex == null;
      if (shouldInvokeVnodeHook && (vnodeHook = props && props.onVnodeUnmounted) || shouldInvokeDirs || shouldInvalidateMemo) {
        queuePostRenderEffect(() => {
          vnodeHook && invokeVNodeHook(vnodeHook, parentComponent, vnode);
          shouldInvokeDirs && invokeDirectiveHook(vnode, null, parentComponent, "unmounted");
          if (shouldInvalidateMemo) {
            vnode.el = null;
          }
        }, parentSuspense);
      }
    };
    const remove2 = (vnode) => {
      const { type, el, anchor, transition } = vnode;
      if (type === Fragment) {
        {
          removeFragment(el, anchor);
        }
        return;
      }
      if (type === Static) {
        removeStaticNode(vnode);
        if (transition && !transition.persisted && transition.afterLeave) {
          transition.afterLeave();
        }
        return;
      }
      const performRemove = () => {
        hostRemove(el);
        if (transition && !transition.persisted && transition.afterLeave) {
          transition.afterLeave();
        }
      };
      if (vnode.shapeFlag & 1 && transition && !transition.persisted) {
        const { leave, delayLeave } = transition;
        const performLeave = () => leave(el, performRemove);
        if (delayLeave) {
          delayLeave(vnode.el, performRemove, performLeave);
        } else {
          performLeave();
        }
      } else {
        performRemove();
      }
    };
    const removeFragment = (cur, end) => {
      let next;
      while (cur !== end) {
        next = hostNextSibling(cur);
        hostRemove(cur);
        cur = next;
      }
      hostRemove(end);
    };
    const unmountComponent = (instance, parentSuspense, doRemove) => {
      const { bum, scope, job, subTree, um, m, a } = instance;
      invalidateMount(m);
      invalidateMount(a);
      if (bum) {
        invokeArrayFns(bum);
      }
      scope.stop();
      if (job) {
        job.flags |= 8;
        unmount(subTree, instance, parentSuspense, doRemove);
      } else if (instance.vnode.el && subTree) {
        subTree.transition = instance.vnode.transition;
        unmount(subTree, instance, parentSuspense, doRemove);
      }
      if (um) {
        queuePostRenderEffect(um, parentSuspense);
      }
      queuePostRenderEffect(() => {
        instance.isUnmounted = true;
      }, parentSuspense);
    };
    const unmountChildren = (children, parentComponent, parentSuspense, doRemove = false, optimized = false, start = 0) => {
      for (let i = start; i < children.length; i++) {
        unmount(children[i], parentComponent, parentSuspense, doRemove, optimized);
      }
    };
    const getNextHostNode = (vnode) => {
      if (vnode.shapeFlag & 6) {
        return getNextHostNode(vnode.component.subTree);
      }
      if (vnode.shapeFlag & 128) {
        return vnode.suspense.next();
      }
      const el = hostNextSibling(vnode.anchor || vnode.el);
      const teleportEnd = el && el[TeleportEndKey];
      return teleportEnd ? hostNextSibling(teleportEnd) : el;
    };
    let isFlushing = false;
    const render = (vnode, container, namespace) => {
      let instance;
      if (vnode == null) {
        if (container._vnode) {
          unmount(container._vnode, null, null, true);
          instance = container._vnode.component;
        }
      } else {
        patch(
          container._vnode || null,
          vnode,
          container,
          null,
          null,
          null,
          namespace
        );
      }
      container._vnode = vnode;
      if (!isFlushing) {
        isFlushing = true;
        flushPreFlushCbs(instance);
        flushPostFlushCbs();
        isFlushing = false;
      }
    };
    const internals = {
      p: patch,
      um: unmount,
      m: move,
      r: remove2,
      mt: mountComponent,
      mc: mountChildren,
      pc: patchChildren,
      pbc: patchBlockChildren,
      n: getNextHostNode,
      o: options
    };
    let hydrate;
    return {
      render,
      hydrate,
      createApp: createAppAPI(render)
    };
  }
  function resolveChildrenNamespace({ type, props }, currentNamespace) {
    return currentNamespace === "svg" && type === "foreignObject" || currentNamespace === "mathml" && type === "annotation-xml" && props && props.encoding && props.encoding.includes("html") ? void 0 : currentNamespace;
  }
  function toggleRecurse({ effect: effect2, job }, allowed) {
    if (allowed) {
      effect2.flags |= 32;
      job.flags |= 4;
    } else {
      effect2.flags &= -33;
      job.flags &= -5;
    }
  }
  function needTransition(parentSuspense, transition) {
    return (!parentSuspense || parentSuspense && !parentSuspense.pendingBranch) && transition && !transition.persisted;
  }
  function traverseStaticChildren(n1, n2, shallow = false) {
    const ch1 = n1.children;
    const ch2 = n2.children;
    if (isArray(ch1) && isArray(ch2)) {
      for (let i = 0; i < ch1.length; i++) {
        const c1 = ch1[i];
        let c2 = ch2[i];
        if (c2.shapeFlag & 1 && !c2.dynamicChildren) {
          if (c2.patchFlag <= 0 || c2.patchFlag === 32) {
            c2 = ch2[i] = cloneIfMounted(ch2[i]);
            c2.el = c1.el;
          }
          if (!shallow && c2.patchFlag !== -2)
            traverseStaticChildren(c1, c2);
        }
        if (c2.type === Text) {
          if (c2.patchFlag === -1) {
            c2 = ch2[i] = cloneIfMounted(c2);
          }
          c2.el = c1.el;
        }
        if (c2.type === Comment && !c2.el) {
          c2.el = c1.el;
        }
      }
    }
  }
  function getSequence(arr) {
    const p2 = arr.slice();
    const result = [0];
    let i, j, u, v, c;
    const len = arr.length;
    for (i = 0; i < len; i++) {
      const arrI = arr[i];
      if (arrI !== 0) {
        j = result[result.length - 1];
        if (arr[j] < arrI) {
          p2[i] = j;
          result.push(i);
          continue;
        }
        u = 0;
        v = result.length - 1;
        while (u < v) {
          c = u + v >> 1;
          if (arr[result[c]] < arrI) {
            u = c + 1;
          } else {
            v = c;
          }
        }
        if (arrI < arr[result[u]]) {
          if (u > 0) {
            p2[i] = result[u - 1];
          }
          result[u] = i;
        }
      }
    }
    u = result.length;
    v = result[u - 1];
    while (u-- > 0) {
      result[u] = v;
      v = p2[v];
    }
    return result;
  }
  function locateNonHydratedAsyncRoot(instance) {
    const subComponent = instance.subTree.component;
    if (subComponent) {
      if (subComponent.asyncDep && !subComponent.asyncResolved) {
        return subComponent;
      } else {
        return locateNonHydratedAsyncRoot(subComponent);
      }
    }
  }
  function invalidateMount(hooks) {
    if (hooks) {
      for (let i = 0; i < hooks.length; i++)
        hooks[i].flags |= 8;
    }
  }
  function resolveAsyncComponentPlaceholder(anchorVnode) {
    if (anchorVnode.placeholder) {
      return anchorVnode.placeholder;
    }
    const instance = anchorVnode.component;
    if (instance) {
      return resolveAsyncComponentPlaceholder(instance.subTree);
    }
    return null;
  }
  const isSuspense = (type) => type.__isSuspense;
  function queueEffectWithSuspense(fn, suspense) {
    if (suspense && suspense.pendingBranch) {
      if (isArray(fn)) {
        suspense.effects.push(...fn);
      } else {
        suspense.effects.push(fn);
      }
    } else {
      queuePostFlushCb(fn);
    }
  }
  const Fragment = /* @__PURE__ */ Symbol.for("v-fgt");
  const Text = /* @__PURE__ */ Symbol.for("v-txt");
  const Comment = /* @__PURE__ */ Symbol.for("v-cmt");
  const Static = /* @__PURE__ */ Symbol.for("v-stc");
  const blockStack = [];
  let currentBlock = null;
  function openBlock(disableTracking = false) {
    blockStack.push(currentBlock = disableTracking ? null : []);
  }
  function closeBlock() {
    blockStack.pop();
    currentBlock = blockStack[blockStack.length - 1] || null;
  }
  let isBlockTreeEnabled = 1;
  function setBlockTracking(value, inVOnce = false) {
    isBlockTreeEnabled += value;
    if (value < 0 && currentBlock && inVOnce) {
      currentBlock.hasOnce = true;
    }
  }
  function setupBlock(vnode) {
    vnode.dynamicChildren = isBlockTreeEnabled > 0 ? currentBlock || EMPTY_ARR : null;
    closeBlock();
    if (isBlockTreeEnabled > 0 && currentBlock) {
      currentBlock.push(vnode);
    }
    return vnode;
  }
  function createElementBlock(type, props, children, patchFlag, dynamicProps, shapeFlag) {
    return setupBlock(
      createBaseVNode(
        type,
        props,
        children,
        patchFlag,
        dynamicProps,
        shapeFlag,
        true
      )
    );
  }
  function createBlock(type, props, children, patchFlag, dynamicProps) {
    return setupBlock(
      createVNode(
        type,
        props,
        children,
        patchFlag,
        dynamicProps,
        true
      )
    );
  }
  function isVNode(value) {
    return value ? value.__v_isVNode === true : false;
  }
  function isSameVNodeType(n1, n2) {
    return n1.type === n2.type && n1.key === n2.key;
  }
  const normalizeKey = ({ key }) => key != null ? key : null;
  const normalizeRef = ({
    ref: ref3,
    ref_key,
    ref_for
  }) => {
    if (typeof ref3 === "number") {
      ref3 = "" + ref3;
    }
    return ref3 != null ? isString(ref3) || /* @__PURE__ */ isRef(ref3) || isFunction(ref3) ? { i: currentRenderingInstance, r: ref3, k: ref_key, f: !!ref_for } : ref3 : null;
  };
  function createBaseVNode(type, props = null, children = null, patchFlag = 0, dynamicProps = null, shapeFlag = type === Fragment ? 0 : 1, isBlockNode = false, needFullChildrenNormalization = false) {
    const vnode = {
      __v_isVNode: true,
      __v_skip: true,
      type,
      props,
      key: props && normalizeKey(props),
      ref: props && normalizeRef(props),
      scopeId: currentScopeId,
      slotScopeIds: null,
      children,
      component: null,
      suspense: null,
      ssContent: null,
      ssFallback: null,
      dirs: null,
      transition: null,
      el: null,
      anchor: null,
      target: null,
      targetStart: null,
      targetAnchor: null,
      staticCount: 0,
      shapeFlag,
      patchFlag,
      dynamicProps,
      dynamicChildren: null,
      appContext: null,
      ctx: currentRenderingInstance
    };
    if (needFullChildrenNormalization) {
      normalizeChildren(vnode, children);
      if (shapeFlag & 128) {
        type.normalize(vnode);
      }
    } else if (children) {
      vnode.shapeFlag |= isString(children) ? 8 : 16;
    }
    if (isBlockTreeEnabled > 0 && // avoid a block node from tracking itself
    !isBlockNode && // has current parent block
    currentBlock && // presence of a patch flag indicates this node needs patching on updates.
    // component nodes also should always be patched, because even if the
    // component doesn't need to update, it needs to persist the instance on to
    // the next vnode so that it can be properly unmounted later.
    (vnode.patchFlag > 0 || shapeFlag & 6) && // the EVENTS flag is only for hydration and if it is the only flag, the
    // vnode should not be considered dynamic due to handler caching.
    vnode.patchFlag !== 32) {
      currentBlock.push(vnode);
    }
    return vnode;
  }
  const createVNode = _createVNode;
  function _createVNode(type, props = null, children = null, patchFlag = 0, dynamicProps = null, isBlockNode = false) {
    if (!type || type === NULL_DYNAMIC_COMPONENT) {
      type = Comment;
    }
    if (isVNode(type)) {
      const cloned = cloneVNode(
        type,
        props,
        true
        /* mergeRef: true */
      );
      if (children) {
        normalizeChildren(cloned, children);
      }
      if (isBlockTreeEnabled > 0 && !isBlockNode && currentBlock) {
        if (cloned.shapeFlag & 6) {
          currentBlock[currentBlock.indexOf(type)] = cloned;
        } else {
          currentBlock.push(cloned);
        }
      }
      cloned.patchFlag = -2;
      return cloned;
    }
    if (isClassComponent(type)) {
      type = type.__vccOpts;
    }
    if (props) {
      props = guardReactiveProps(props);
      let { class: klass, style } = props;
      if (klass && !isString(klass)) {
        props.class = normalizeClass(klass);
      }
      if (isObject(style)) {
        if (/* @__PURE__ */ isProxy(style) && !isArray(style)) {
          style = extend({}, style);
        }
        props.style = normalizeStyle(style);
      }
    }
    const shapeFlag = isString(type) ? 1 : isSuspense(type) ? 128 : isTeleport(type) ? 64 : isObject(type) ? 4 : isFunction(type) ? 2 : 0;
    return createBaseVNode(
      type,
      props,
      children,
      patchFlag,
      dynamicProps,
      shapeFlag,
      isBlockNode,
      true
    );
  }
  function guardReactiveProps(props) {
    if (!props) return null;
    return /* @__PURE__ */ isProxy(props) || isInternalObject(props) ? extend({}, props) : props;
  }
  function cloneVNode(vnode, extraProps, mergeRef = false, cloneTransition = false) {
    const { props, ref: ref3, patchFlag, children, transition } = vnode;
    const mergedProps = extraProps ? mergeProps(props || {}, extraProps) : props;
    const cloned = {
      __v_isVNode: true,
      __v_skip: true,
      type: vnode.type,
      props: mergedProps,
      key: mergedProps && normalizeKey(mergedProps),
      ref: extraProps && extraProps.ref ? (
        // #2078 in the case of <component :is="vnode" ref="extra"/>
        // if the vnode itself already has a ref, cloneVNode will need to merge
        // the refs so the single vnode can be set on multiple refs
        mergeRef && ref3 ? isArray(ref3) ? ref3.concat(normalizeRef(extraProps)) : [ref3, normalizeRef(extraProps)] : normalizeRef(extraProps)
      ) : ref3,
      scopeId: vnode.scopeId,
      slotScopeIds: vnode.slotScopeIds,
      children,
      target: vnode.target,
      targetStart: vnode.targetStart,
      targetAnchor: vnode.targetAnchor,
      staticCount: vnode.staticCount,
      shapeFlag: vnode.shapeFlag,
      // if the vnode is cloned with extra props, we can no longer assume its
      // existing patch flag to be reliable and need to add the FULL_PROPS flag.
      // note: preserve flag for fragments since they use the flag for children
      // fast paths only.
      patchFlag: extraProps && vnode.type !== Fragment ? patchFlag === -1 ? 16 : patchFlag | 16 : patchFlag,
      dynamicProps: vnode.dynamicProps,
      dynamicChildren: vnode.dynamicChildren,
      appContext: vnode.appContext,
      dirs: vnode.dirs,
      transition,
      // These should technically only be non-null on mounted VNodes. However,
      // they *should* be copied for kept-alive vnodes. So we just always copy
      // them since them being non-null during a mount doesn't affect the logic as
      // they will simply be overwritten.
      component: vnode.component,
      suspense: vnode.suspense,
      ssContent: vnode.ssContent && cloneVNode(vnode.ssContent),
      ssFallback: vnode.ssFallback && cloneVNode(vnode.ssFallback),
      placeholder: vnode.placeholder,
      el: vnode.el,
      anchor: vnode.anchor,
      ctx: vnode.ctx,
      ce: vnode.ce,
      cacheIndex: vnode.cacheIndex
    };
    if (transition && cloneTransition) {
      setTransitionHooks(
        cloned,
        transition.clone(cloned)
      );
    }
    return cloned;
  }
  function createTextVNode(text = " ", flag = 0) {
    return createVNode(Text, null, text, flag);
  }
  function createCommentVNode(text = "", asBlock = false) {
    return asBlock ? (openBlock(), createBlock(Comment, null, text)) : createVNode(Comment, null, text);
  }
  function normalizeVNode(child) {
    if (child == null || typeof child === "boolean") {
      return createVNode(Comment);
    } else if (isArray(child)) {
      return createVNode(
        Fragment,
        null,
        // #3666, avoid reference pollution when reusing vnode
        child.slice()
      );
    } else if (isVNode(child)) {
      return cloneIfMounted(child);
    } else {
      return createVNode(Text, null, String(child));
    }
  }
  function cloneIfMounted(child) {
    return child.el === null && child.patchFlag !== -1 || child.memo ? child : cloneVNode(child);
  }
  function normalizeChildren(vnode, children) {
    let type = 0;
    const { shapeFlag } = vnode;
    if (children == null) {
      children = null;
    } else if (isArray(children)) {
      type = 16;
    } else if (typeof children === "object") {
      if (shapeFlag & (1 | 64)) {
        const slot = children.default;
        if (slot) {
          slot._c && (slot._d = false);
          normalizeChildren(vnode, slot());
          slot._c && (slot._d = true);
        }
        return;
      } else {
        type = 32;
        const slotFlag = children._;
        if (!slotFlag && !isInternalObject(children)) {
          children._ctx = currentRenderingInstance;
        } else if (slotFlag === 3 && currentRenderingInstance) {
          if (currentRenderingInstance.slots._ === 1) {
            children._ = 1;
          } else {
            children._ = 2;
            vnode.patchFlag |= 1024;
          }
        }
      }
    } else if (isFunction(children)) {
      if (shapeFlag & (1 | 64)) {
        normalizeChildren(vnode, { default: children });
        return;
      }
      children = { default: children, _ctx: currentRenderingInstance };
      type = 32;
    } else {
      children = String(children);
      if (shapeFlag & 64) {
        type = 16;
        children = [createTextVNode(children)];
      } else {
        type = 8;
      }
    }
    vnode.children = children;
    vnode.shapeFlag |= type;
  }
  function mergeProps(...args) {
    const ret = {};
    for (let i = 0; i < args.length; i++) {
      const toMerge = args[i];
      for (const key in toMerge) {
        if (key === "class") {
          if (ret.class !== toMerge.class) {
            ret.class = normalizeClass([ret.class, toMerge.class]);
          }
        } else if (key === "style") {
          ret.style = normalizeStyle([ret.style, toMerge.style]);
        } else if (isOn(key)) {
          const existing = ret[key];
          const incoming = toMerge[key];
          if (incoming && existing !== incoming && !(isArray(existing) && existing.includes(incoming))) {
            ret[key] = existing ? [].concat(existing, incoming) : incoming;
          } else if (incoming == null && existing == null && // mergeProps({ 'onUpdate:modelValue': undefined }) should not retain
          // the model listener.
          !isModelListener(key)) {
            ret[key] = incoming;
          }
        } else if (key !== "") {
          ret[key] = toMerge[key];
        }
      }
    }
    return ret;
  }
  function invokeVNodeHook(hook, instance, vnode, prevVNode = null) {
    callWithAsyncErrorHandling(hook, instance, 7, [
      vnode,
      prevVNode
    ]);
  }
  const emptyAppContext = createAppContext();
  let uid = 0;
  function createComponentInstance(vnode, parent, suspense) {
    const type = vnode.type;
    const appContext = (parent ? parent.appContext : vnode.appContext) || emptyAppContext;
    const instance = {
      uid: uid++,
      vnode,
      type,
      parent,
      appContext,
      root: null,
      // to be immediately set
      next: null,
      subTree: null,
      // will be set synchronously right after creation
      effect: null,
      update: null,
      // will be set synchronously right after creation
      job: null,
      scope: new EffectScope(
        true
        /* detached */
      ),
      render: null,
      proxy: null,
      exposed: null,
      exposeProxy: null,
      withProxy: null,
      provides: parent ? parent.provides : Object.create(appContext.provides),
      ids: parent ? parent.ids : ["", 0, 0],
      accessCache: null,
      renderCache: [],
      // local resolved assets
      components: null,
      directives: null,
      // resolved props and emits options
      propsOptions: normalizePropsOptions(type, appContext),
      emitsOptions: normalizeEmitsOptions(type, appContext),
      // emit
      emit: null,
      // to be set immediately
      emitted: null,
      // props default value
      propsDefaults: EMPTY_OBJ,
      // inheritAttrs
      inheritAttrs: type.inheritAttrs,
      // state
      ctx: EMPTY_OBJ,
      data: EMPTY_OBJ,
      props: EMPTY_OBJ,
      attrs: EMPTY_OBJ,
      slots: EMPTY_OBJ,
      refs: EMPTY_OBJ,
      setupState: EMPTY_OBJ,
      setupContext: null,
      // suspense related
      suspense,
      suspenseId: suspense ? suspense.pendingId : 0,
      asyncDep: null,
      asyncResolved: false,
      // lifecycle hooks
      // not using enums here because it results in computed properties
      isMounted: false,
      isUnmounted: false,
      isDeactivated: false,
      bc: null,
      c: null,
      bm: null,
      m: null,
      bu: null,
      u: null,
      um: null,
      bum: null,
      da: null,
      a: null,
      rtg: null,
      rtc: null,
      ec: null,
      sp: null
    };
    {
      instance.ctx = { _: instance };
    }
    instance.root = parent ? parent.root : instance;
    instance.emit = emit.bind(null, instance);
    if (vnode.ce) {
      vnode.ce(instance);
    }
    return instance;
  }
  let currentInstance = null;
  const getCurrentInstance = () => currentInstance || currentRenderingInstance;
  let internalSetCurrentInstance;
  let setInSSRSetupState;
  {
    const g = getGlobalThis();
    const registerGlobalSetter = (key, setter) => {
      let setters;
      if (!(setters = g[key])) setters = g[key] = [];
      setters.push(setter);
      return (v) => {
        if (setters.length > 1) setters.forEach((set) => set(v));
        else setters[0](v);
      };
    };
    internalSetCurrentInstance = registerGlobalSetter(
      `__VUE_INSTANCE_SETTERS__`,
      (v) => currentInstance = v
    );
    setInSSRSetupState = registerGlobalSetter(
      `__VUE_SSR_SETTERS__`,
      (v) => isInSSRComponentSetup = v
    );
  }
  const setCurrentInstance = (instance) => {
    const prev = currentInstance;
    internalSetCurrentInstance(instance);
    instance.scope.on();
    return () => {
      instance.scope.off();
      internalSetCurrentInstance(prev);
    };
  };
  const unsetCurrentInstance = () => {
    currentInstance && currentInstance.scope.off();
    internalSetCurrentInstance(null);
  };
  function isStatefulComponent(instance) {
    return instance.vnode.shapeFlag & 4;
  }
  let isInSSRComponentSetup = false;
  function setupComponent(instance, isSSR = false, optimized = false) {
    isSSR && setInSSRSetupState(isSSR);
    const { props, children } = instance.vnode;
    const isStateful = isStatefulComponent(instance);
    initProps(instance, props, isStateful, isSSR);
    initSlots(instance, children, optimized || isSSR);
    const setupResult = isStateful ? setupStatefulComponent(instance, isSSR) : void 0;
    isSSR && setInSSRSetupState(false);
    return setupResult;
  }
  function setupStatefulComponent(instance, isSSR) {
    const Component = instance.type;
    instance.accessCache = /* @__PURE__ */ Object.create(null);
    instance.proxy = new Proxy(instance.ctx, PublicInstanceProxyHandlers);
    const { setup } = Component;
    if (setup) {
      pauseTracking();
      const setupContext = instance.setupContext = setup.length > 1 ? createSetupContext(instance) : null;
      const reset = setCurrentInstance(instance);
      const setupResult = callWithErrorHandling(
        setup,
        instance,
        0,
        [
          instance.props,
          setupContext
        ]
      );
      const isAsyncSetup = isPromise(setupResult);
      resetTracking();
      reset();
      if ((isAsyncSetup || instance.sp) && !isAsyncWrapper(instance)) {
        markAsyncBoundary(instance);
      }
      if (isAsyncSetup) {
        setupResult.then(unsetCurrentInstance, unsetCurrentInstance);
        if (isSSR) {
          return setupResult.then((resolvedResult) => {
            setInSSRSetupState(true);
            try {
              handleSetupResult(instance, resolvedResult, isSSR);
            } finally {
              setInSSRSetupState(false);
            }
          }).catch((e) => {
            handleError(e, instance, 0);
          });
        } else {
          instance.asyncDep = setupResult;
        }
      } else {
        handleSetupResult(instance, setupResult);
      }
    } else {
      finishComponentSetup(instance);
    }
  }
  function handleSetupResult(instance, setupResult, isSSR) {
    if (isFunction(setupResult)) {
      if (instance.type.__ssrInlineRender) {
        instance.ssrRender = setupResult;
      } else {
        instance.render = setupResult;
      }
    } else if (isObject(setupResult)) {
      instance.setupState = proxyRefs(setupResult);
    } else ;
    finishComponentSetup(instance);
  }
  function finishComponentSetup(instance, isSSR, skipOptions) {
    const Component = instance.type;
    if (!instance.render) {
      instance.render = Component.render || NOOP;
    }
    {
      const reset = setCurrentInstance(instance);
      pauseTracking();
      try {
        applyOptions(instance);
      } finally {
        resetTracking();
        reset();
      }
    }
  }
  const attrsProxyHandlers = {
    get(target, key) {
      track(target, "get", "");
      return target[key];
    }
  };
  function createSetupContext(instance) {
    const expose = (exposed) => {
      instance.exposed = exposed || {};
    };
    {
      return {
        attrs: new Proxy(instance.attrs, attrsProxyHandlers),
        slots: instance.slots,
        emit: instance.emit,
        expose
      };
    }
  }
  function getComponentPublicInstance(instance) {
    if (instance.exposed) {
      return instance.exposeProxy || (instance.exposeProxy = new Proxy(proxyRefs(markRaw(instance.exposed)), {
        get(target, key) {
          if (key in target) {
            return target[key];
          } else if (key in publicPropertiesMap) {
            return publicPropertiesMap[key](instance);
          }
        },
        has(target, key) {
          return key in target || key in publicPropertiesMap;
        }
      }));
    } else {
      return instance.proxy;
    }
  }
  const classifyRE = /(?:^|[-_])\w/g;
  const classify = (str) => str.replace(classifyRE, (c) => c.toUpperCase()).replace(/[-_]/g, "");
  function getComponentName(Component, includeInferred = true) {
    return isFunction(Component) ? Component.displayName || Component.name : Component.name || includeInferred && Component.__name;
  }
  function formatComponentName(instance, Component, isRoot = false) {
    let name = getComponentName(Component);
    if (!name && Component.__file) {
      const match = Component.__file.match(/([^/\\]+)\.\w+$/);
      if (match) {
        name = match[1];
      }
    }
    if (!name && instance) {
      const inferFromRegistry = (registry) => {
        for (const key in registry) {
          if (registry[key] === Component) {
            return key;
          }
        }
      };
      name = inferFromRegistry(instance.components) || instance.parent && inferFromRegistry(
        instance.parent.type.components
      ) || inferFromRegistry(instance.appContext.components);
    }
    return name ? classify(name) : isRoot ? `App` : `Anonymous`;
  }
  function isClassComponent(value) {
    return isFunction(value) && "__vccOpts" in value;
  }
  const computed = (getterOrOptions, debugOptions) => {
    const c = /* @__PURE__ */ computed$1(getterOrOptions, debugOptions, isInSSRComponentSetup);
    return c;
  };
  const version = "3.5.43";
  let policy = void 0;
  const tt = typeof window !== "undefined" && window.trustedTypes;
  if (tt) {
    try {
      policy = /* @__PURE__ */ tt.createPolicy("vue", {
        createHTML: (val) => val
      });
    } catch (e) {
    }
  }
  const unsafeToTrustedHTML = policy ? (val) => policy.createHTML(val) : (val) => val;
  const svgNS = "http://www.w3.org/2000/svg";
  const mathmlNS = "http://www.w3.org/1998/Math/MathML";
  const doc = typeof document !== "undefined" ? document : null;
  const templateContainer = doc && /* @__PURE__ */ doc.createElement("template");
  const nodeOps = {
    insert: (child, parent, anchor) => {
      parent.insertBefore(child, anchor || null);
    },
    remove: (child) => {
      const parent = child.parentNode;
      if (parent) {
        parent.removeChild(child);
      }
    },
    createElement: (tag, namespace, is, props) => {
      const el = namespace === "svg" ? doc.createElementNS(svgNS, tag) : namespace === "mathml" ? doc.createElementNS(mathmlNS, tag) : is ? doc.createElement(tag, { is }) : doc.createElement(tag);
      if (tag === "select" && props && props.multiple != null) {
        el.setAttribute("multiple", props.multiple);
      }
      return el;
    },
    createText: (text) => doc.createTextNode(text),
    createComment: (text) => doc.createComment(text),
    setText: (node, text) => {
      node.nodeValue = text;
    },
    setElementText: (el, text) => {
      el.textContent = text;
    },
    parentNode: (node) => node.parentNode,
    nextSibling: (node) => node.nextSibling,
    querySelector: (selector) => doc.querySelector(selector),
    setScopeId(el, id) {
      el.setAttribute(id, "");
    },
    // __UNSAFE__
    // Reason: innerHTML.
    // Static content here can only come from compiled templates.
    // As long as the user only uses trusted templates, this is safe.
    insertStaticContent(content, parent, anchor, namespace, start, end) {
      const before = anchor ? anchor.previousSibling : parent.lastChild;
      if (start && (start === end || start.nextSibling)) {
        while (true) {
          parent.insertBefore(start.cloneNode(true), anchor);
          if (start === end || !(start = start.nextSibling)) break;
        }
      } else {
        templateContainer.innerHTML = unsafeToTrustedHTML(
          namespace === "svg" ? `<svg>${content}</svg>` : namespace === "mathml" ? `<math>${content}</math>` : content
        );
        const template = templateContainer.content;
        if (namespace === "svg" || namespace === "mathml") {
          const wrapper = template.firstChild;
          while (wrapper.firstChild) {
            template.appendChild(wrapper.firstChild);
          }
          template.removeChild(wrapper);
        }
        parent.insertBefore(template, anchor);
      }
      return [
        // first
        before ? before.nextSibling : parent.firstChild,
        // last
        anchor ? anchor.previousSibling : parent.lastChild
      ];
    }
  };
  const vtcKey = /* @__PURE__ */ Symbol("_vtc");
  function patchClass(el, value, isSVG) {
    const transitionClasses = el[vtcKey];
    if (transitionClasses) {
      value = (value ? [value, ...transitionClasses] : [...transitionClasses]).join(" ");
    }
    if (value == null) {
      el.removeAttribute("class");
    } else if (isSVG) {
      el.setAttribute("class", value);
    } else {
      el.className = value;
    }
  }
  const vShowOriginalDisplay = /* @__PURE__ */ Symbol("_vod");
  const vShowHidden = /* @__PURE__ */ Symbol("_vsh");
  const CSS_VAR_TEXT = /* @__PURE__ */ Symbol("");
  const displayRE = /(?:^|;)\s*display\s*:/;
  function patchStyle(el, prev, next) {
    const style = el.style;
    const isCssString = isString(next);
    let hasControlledDisplay = false;
    if (next && !isCssString) {
      if (prev) {
        if (!isString(prev)) {
          for (const key in prev) {
            if (next[key] == null) {
              setStyle(style, key, "");
            }
          }
        } else {
          for (const prevStyle of prev.split(";")) {
            const key = prevStyle.slice(0, prevStyle.indexOf(":")).trim();
            if (next[key] == null) {
              setStyle(style, key, "");
            }
          }
        }
      }
      for (const key in next) {
        if (key === "display") {
          hasControlledDisplay = true;
        }
        const value = next[key];
        if (value != null) {
          if (!shouldPreserveTextareaResizeStyle(
            el,
            key,
            !isString(prev) && prev ? prev[key] : void 0,
            value
          )) {
            setStyle(style, key, value);
          }
        } else {
          setStyle(style, key, "");
        }
      }
    } else {
      if (isCssString) {
        if (prev !== next) {
          const cssVarText = style[CSS_VAR_TEXT];
          if (cssVarText) {
            next += ";" + cssVarText;
          }
          style.cssText = next;
          hasControlledDisplay = displayRE.test(next);
        }
      } else if (prev) {
        el.removeAttribute("style");
      }
    }
    if (vShowOriginalDisplay in el) {
      el[vShowOriginalDisplay] = hasControlledDisplay ? style.display : "";
      if (el[vShowHidden]) {
        style.display = "none";
      }
    }
  }
  const importantRE = /\s*!important$/;
  function setStyle(style, name, val) {
    if (isArray(val)) {
      val.forEach((v) => setStyle(style, name, v));
    } else {
      if (val == null) val = "";
      if (name.startsWith("--")) {
        if (importantRE.test(val)) {
          style.setProperty(name, val.replace(importantRE, ""), "important");
        } else {
          style.setProperty(name, val);
        }
      } else {
        const prefixed = autoPrefix(style, name);
        if (importantRE.test(val)) {
          style.setProperty(
            hyphenate(prefixed),
            val.replace(importantRE, ""),
            "important"
          );
        } else {
          style[prefixed] = val;
        }
      }
    }
  }
  const prefixes = ["Webkit", "Moz", "ms"];
  const prefixCache = {};
  function autoPrefix(style, rawName) {
    const cached = prefixCache[rawName];
    if (cached) {
      return cached;
    }
    let name = camelize(rawName);
    if (name !== "filter" && name in style) {
      return prefixCache[rawName] = name;
    }
    name = capitalize(name);
    for (let i = 0; i < prefixes.length; i++) {
      const prefixed = prefixes[i] + name;
      if (prefixed in style) {
        return prefixCache[rawName] = prefixed;
      }
    }
    return rawName;
  }
  function shouldPreserveTextareaResizeStyle(el, key, prev, next) {
    return el.tagName === "TEXTAREA" && (key === "width" || key === "height") && isString(next) && prev === next;
  }
  const xlinkNS = "http://www.w3.org/1999/xlink";
  function patchAttr(el, key, value, isSVG, instance, isBoolean = isSpecialBooleanAttr(key)) {
    if (isSVG && key.startsWith("xlink:")) {
      if (value == null) {
        el.removeAttributeNS(xlinkNS, key.slice(6, key.length));
      } else {
        el.setAttributeNS(xlinkNS, key, value);
      }
    } else {
      if (value == null || isBoolean && !includeBooleanAttr(value)) {
        el.removeAttribute(key);
      } else {
        el.setAttribute(
          key,
          isBoolean ? "" : isSymbol(value) ? String(value) : value
        );
      }
    }
  }
  function patchDOMProp(el, key, value, parentComponent, attrName) {
    if (key === "innerHTML" || key === "textContent") {
      if (value != null) {
        el[key] = key === "innerHTML" ? unsafeToTrustedHTML(value) : value;
      }
      return;
    }
    const tag = el.tagName;
    if (key === "value" && tag !== "PROGRESS" && // custom elements may use _value internally
    !tag.includes("-")) {
      const oldValue = tag === "OPTION" ? el.getAttribute("value") || "" : el.value;
      const newValue = value == null ? (
        // #11647: value should be set as empty string for null and undefined,
        // but <input type="checkbox"> should be set as 'on'.
        el.type === "checkbox" ? "on" : ""
      ) : String(value);
      if (oldValue !== newValue || !("_value" in el)) {
        el.value = newValue;
      }
      if (value == null) {
        el.removeAttribute(key);
      }
      el._value = value;
      return;
    }
    let needRemove = false;
    if (value === "" || value == null) {
      const type = typeof el[key];
      if (type === "boolean") {
        value = includeBooleanAttr(value);
      } else if (value == null && type === "string") {
        value = "";
        needRemove = true;
      } else if (type === "number") {
        value = 0;
        needRemove = true;
      }
    }
    try {
      el[key] = value;
    } catch (e) {
    }
    needRemove && el.removeAttribute(attrName || key);
  }
  function addEventListener(el, event, handler, options) {
    el.addEventListener(event, handler, options);
  }
  function removeEventListener(el, event, handler, options) {
    el.removeEventListener(event, handler, options);
  }
  const veiKey = /* @__PURE__ */ Symbol("_vei");
  function patchEvent(el, rawName, prevValue, nextValue, instance = null) {
    const invokers = el[veiKey] || (el[veiKey] = {});
    const existingInvoker = invokers[rawName];
    if (nextValue && existingInvoker) {
      existingInvoker.value = nextValue;
    } else {
      const [name, options] = parseName(rawName);
      if (nextValue) {
        const invoker = invokers[rawName] = createInvoker(
          nextValue,
          instance
        );
        addEventListener(el, name, invoker, options);
      } else if (existingInvoker) {
        removeEventListener(el, name, existingInvoker, options);
        invokers[rawName] = void 0;
      }
    }
  }
  const optionsModifierRE = /(Once|Passive|Capture)$/;
  const optionsModifierEventRE = /^on:?(?:Once|Passive|Capture)$/;
  function parseName(name) {
    let options;
    let m;
    while ((m = name.match(optionsModifierRE)) && !optionsModifierEventRE.test(name)) {
      if (!options) options = {};
      name = name.slice(0, name.length - m[1].length);
      options[m[1].toLowerCase()] = true;
    }
    const event = name[2] === ":" ? name.slice(3) : hyphenate(name.slice(2));
    return [event, options];
  }
  let cachedNow = 0;
  const p = /* @__PURE__ */ Promise.resolve();
  const getNow = () => cachedNow || (p.then(() => cachedNow = 0), cachedNow = Date.now());
  function createInvoker(initialValue, instance) {
    const invoker = (e) => {
      if (!e._vts) {
        e._vts = Date.now();
      } else if (e._vts <= invoker.attached) {
        return;
      }
      const value = invoker.value;
      if (isArray(value)) {
        const originalStop = e.stopImmediatePropagation;
        e.stopImmediatePropagation = () => {
          originalStop.call(e);
          e._stopped = true;
        };
        const handlers = value.slice();
        const args = [e];
        for (let i = 0; i < handlers.length; i++) {
          if (e._stopped) {
            break;
          }
          const handler = handlers[i];
          if (handler) {
            callWithAsyncErrorHandling(
              handler,
              instance,
              5,
              args
            );
          }
        }
      } else {
        callWithAsyncErrorHandling(
          value,
          instance,
          5,
          [e]
        );
      }
    };
    invoker.value = initialValue;
    invoker.attached = getNow();
    return invoker;
  }
  const isNativeOn = (key) => key.charCodeAt(0) === 111 && key.charCodeAt(1) === 110 && // lowercase letter
  key.charCodeAt(2) > 96 && key.charCodeAt(2) < 123;
  const patchProp = (el, key, prevValue, nextValue, namespace, parentComponent) => {
    const isSVG = namespace === "svg";
    if (key === "class") {
      patchClass(el, nextValue, isSVG);
    } else if (key === "style") {
      patchStyle(el, prevValue, nextValue);
    } else if (isOn(key)) {
      if (!isModelListener(key)) {
        patchEvent(el, key, prevValue, nextValue, parentComponent);
      }
    } else if (key[0] === "." ? (key = key.slice(1), true) : key[0] === "^" ? (key = key.slice(1), false) : shouldSetAsProp(el, key, nextValue, isSVG)) {
      patchDOMProp(el, key, nextValue);
      if (!el.tagName.includes("-") && (key === "value" || key === "checked" || key === "selected")) {
        patchAttr(el, key, nextValue, isSVG, parentComponent, key !== "value");
      }
    } else if (
      // #11081 force set props for possible async custom element
      el._isVueCE && // #12408 check if it's declared prop or it's async custom element
      (shouldSetAsPropForVueCE(el, key) || // @ts-expect-error _def is private
      el._def.__asyncLoader && (/[A-Z]/.test(key) || !isString(nextValue)))
    ) {
      patchDOMProp(el, camelize(key), nextValue, parentComponent, key);
    } else {
      if (key === "true-value") {
        el._trueValue = nextValue;
      } else if (key === "false-value") {
        el._falseValue = nextValue;
      }
      patchAttr(el, key, nextValue, isSVG);
    }
  };
  function shouldSetAsProp(el, key, value, isSVG) {
    if (isSVG) {
      if (key === "innerHTML" || key === "textContent") {
        return true;
      }
      if (key in el && isNativeOn(key) && isFunction(value)) {
        return true;
      }
      return false;
    }
    if (key === "spellcheck" || key === "draggable" || key === "translate" || key === "autocorrect") {
      return false;
    }
    if (key === "sandbox" && el.tagName === "IFRAME") {
      return false;
    }
    if (key === "form") {
      return false;
    }
    if (key === "list" && el.tagName === "INPUT") {
      return false;
    }
    if (key === "type" && el.tagName === "TEXTAREA") {
      return false;
    }
    if (key === "width" || key === "height") {
      const tag = el.tagName;
      if (tag === "IMG" || tag === "VIDEO" || tag === "CANVAS" || tag === "SOURCE") {
        return false;
      }
    }
    if (isNativeOn(key) && isString(value)) {
      return false;
    }
    return key in el;
  }
  function shouldSetAsPropForVueCE(el, key) {
    const props = (
      // @ts-expect-error _def is private
      el._def.props
    );
    if (!props) {
      return false;
    }
    const camelKey = camelize(key);
    return Array.isArray(props) ? props.some((prop) => camelize(prop) === camelKey) : Object.keys(props).some((prop) => camelize(prop) === camelKey);
  }
  const getModelAssigner = (vnode) => {
    const fn = vnode.props["onUpdate:modelValue"] || false;
    return isArray(fn) ? (value) => invokeArrayFns(fn, value) : fn;
  };
  const assignKey = /* @__PURE__ */ Symbol("_assign");
  const vModelCheckbox = {
    // #4096 array checkboxes need to be deep traversed
    deep: true,
    created(el, _, vnode) {
      el[assignKey] = getModelAssigner(vnode);
      addEventListener(el, "change", () => {
        const modelValue = el._modelValue;
        const elementValue = getValue(el);
        const checked = el.checked;
        const assign = el[assignKey];
        if (isArray(modelValue)) {
          const index = looseIndexOf(modelValue, elementValue);
          const found = index !== -1;
          if (checked && !found) {
            assign(modelValue.concat(elementValue));
          } else if (!checked && found) {
            const filtered = [...modelValue];
            filtered.splice(index, 1);
            assign(filtered);
          }
        } else if (isSet(modelValue)) {
          const cloned = new Set(modelValue);
          if (checked) {
            cloned.add(elementValue);
          } else {
            cloned.delete(elementValue);
          }
          assign(cloned);
        } else {
          assign(getCheckboxValue(el, checked));
        }
      });
    },
    // set initial checked on mount to wait for true-value/false-value
    mounted: setChecked,
    beforeUpdate(el, binding, vnode) {
      el[assignKey] = getModelAssigner(vnode);
      setChecked(el, binding, vnode);
    }
  };
  function setChecked(el, { value, oldValue }, vnode) {
    el._modelValue = value;
    let checked;
    if (isArray(value)) {
      checked = looseIndexOf(value, vnode.props.value) > -1;
    } else if (isSet(value)) {
      checked = value.has(vnode.props.value);
    } else {
      if (value === oldValue) return;
      checked = looseEqual(value, getCheckboxValue(el, true));
    }
    if (el.checked !== checked) {
      el.checked = checked;
    }
  }
  function getValue(el) {
    return "_value" in el ? el._value : el.value;
  }
  function getCheckboxValue(el, checked) {
    const key = checked ? "_trueValue" : "_falseValue";
    return key in el ? el[key] : checked;
  }
  const systemModifiers = ["ctrl", "shift", "alt", "meta"];
  const modifierGuards = {
    stop: (e) => e.stopPropagation(),
    prevent: (e) => e.preventDefault(),
    self: (e) => e.target !== e.currentTarget,
    ctrl: (e) => !e.ctrlKey,
    shift: (e) => !e.shiftKey,
    alt: (e) => !e.altKey,
    meta: (e) => !e.metaKey,
    left: (e) => "button" in e && e.button !== 0,
    middle: (e) => "button" in e && e.button !== 1,
    right: (e) => "button" in e && e.button !== 2,
    exact: (e, modifiers) => systemModifiers.some((m) => e[`${m}Key`] && !modifiers.includes(m))
  };
  const withModifiers = (fn, modifiers) => {
    if (!fn) return fn;
    const cache = fn._withMods || (fn._withMods = {});
    const cacheKey = modifiers.join(".");
    return cache[cacheKey] || (cache[cacheKey] = ((event, ...args) => {
      for (let i = 0; i < modifiers.length; i++) {
        const guard = modifierGuards[modifiers[i]];
        if (guard && guard(event, modifiers)) return;
      }
      return fn(event, ...args);
    }));
  };
  const rendererOptions = /* @__PURE__ */ extend({ patchProp }, nodeOps);
  let renderer;
  function ensureRenderer() {
    return renderer || (renderer = createRenderer(rendererOptions));
  }
  const createApp = ((...args) => {
    const app = ensureRenderer().createApp(...args);
    const { mount } = app;
    app.mount = (containerOrSelector) => {
      const container = normalizeContainer(containerOrSelector);
      if (!container) return;
      const component = app._component;
      if (!isFunction(component) && !component.render && !component.template) {
        component.template = container.innerHTML;
      }
      if (container.nodeType === 1) {
        container.textContent = "";
      }
      const proxy = mount(container, false, resolveRootNamespace(container));
      if (container instanceof Element) {
        container.removeAttribute("v-cloak");
        container.setAttribute("data-v-app", "");
      }
      return proxy;
    };
    return app;
  });
  function resolveRootNamespace(container) {
    if (container instanceof SVGElement) {
      return "svg";
    }
    if (typeof MathMLElement === "function" && container instanceof MathMLElement) {
      return "mathml";
    }
  }
  function normalizeContainer(container) {
    if (isString(container)) {
      const res = document.querySelector(container);
      return res;
    }
    return container;
  }
  const _hoisted_1$l = ["value", "aria-invalid"];
  const _sfc_main$m = /* @__PURE__ */ defineComponent({
    __name: "UiSelect",
    props: {
      modelValue: { default: "" },
      invalid: { type: Boolean, default: false }
    },
    emits: ["update:modelValue"],
    setup(__props, { emit: __emit }) {
      const emit2 = __emit;
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("select", {
          class: "ui-control ui-select",
          value: __props.modelValue ?? "",
          "aria-invalid": __props.invalid ? "true" : void 0,
          onChange: _cache[0] || (_cache[0] = ($event) => emit2("update:modelValue", $event.target.value))
        }, [
          renderSlot(_ctx.$slots, "default")
        ], 40, _hoisted_1$l);
      };
    }
  });
  const _hoisted_1$k = ["innerHTML"];
  const _sfc_main$l = /* @__PURE__ */ defineComponent({
    __name: "AppIcon",
    props: {
      name: {}
    },
    setup(__props) {
      const props = __props;
      const paths = {
        dashboard: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
        list: '<path d="M5 7h14M5 12h14M5 17h14"/><path d="M3 7h.01M3 12h.01M3 17h.01"/>',
        record: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
        chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20v-11"/><path d="M2 20h21"/>',
        books: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
        search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
        map: '<circle cx="6" cy="8" r="2.2"/><circle cx="16" cy="7" r="2.2"/><circle cx="12" cy="16" r="2.2"/><path d="M8 9.2 10.4 14M14.2 8.8 13 14"/>',
        pdf: '<path d="M6 2h9l5 5v15H6z"/><path d="M14 2v6h6M8.5 15h7M8.5 18h5"/>',
        compare: '<path d="M8 7h11M16 4l3 3-3 3M16 17H5M8 14l-3 3 3 3"/>',
        database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
        upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 20h14"/>',
        download: '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M5 20h14"/>',
        edit: '<path d="M4 20h4l11-11-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
        filter: '<path d="M3 5h18l-7 8v5l-4 2v-7z"/>',
        spark: '<path d="m12 3 1.2 4.1L17 9l-3.8 1.9L12 15l-1.2-4.1L7 9l3.8-1.9L12 3Z"/><path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15Z"/>',
        star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z"/>',
        broom: '<path d="m15 3 6 6-8 8-6-6z"/><path d="M7 11 3 15l6 6 4-4M5 17l2 2M8 14l4 4"/>',
        plus: '<path d="M12 5v14M5 12h14"/>',
        history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
        refresh: '<path d="M20 11a8 8 0 0 0-14.8-4L3 10"/><path d="M3 4v6h6"/><path d="M4 13a8 8 0 0 0 14.8 4L21 14"/><path d="M21 20v-6h-6"/>',
        copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
        roles: '<path d="M12 2 20 5v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5z"/><path d="M9 12l2 2 4-5"/>',
        users: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3.5 20c.5-4 2.4-6 5.5-6s5 2 5.5 6M14 15c3.4-.8 5.6.9 6.5 4"/>',
        language: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.4 2.5 3.6 5.5 3.6 9s-1.2 6.5-3.6 9M12 3C9.6 5.5 8.4 8.5 8.4 12s1.2 6.5 3.6 9"/>',
        gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21h-4v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1-.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1L7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.1v4H21a1.7 1.7 0 0 0-1.6 1Z"/>',
        help: '<circle cx="12" cy="12" r="9"/><path d="M9.4 9.4a2.6 2.6 0 1 1 3.7 2.35c-.8.4-1.3.9-1.3 1.75V14"/><path d="M12 17.2h.01"/>',
        warning: '<path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5M12 17h.01"/>',
        check: '<path d="m5 12 4 4L19 6"/>',
        lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
        unlock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M16 10V7a4 4 0 0 0-8 0"/>',
        trash: '<path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/>',
        close: '<path d="M6 6l12 12M18 6 6 18"/>',
        "chevron-left": '<path d="m14.5 6-6 6 6 6"/>',
        "chevron-right": '<path d="m9.5 6 6 6-6 6"/>',
        "chevron-down": '<path d="m6 9.5 6 6 6-6"/>'
      };
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("svg", {
          viewBox: "0 0 24 24",
          fill: "none",
          stroke: "currentColor",
          "stroke-width": "1.8",
          "stroke-linecap": "round",
          "stroke-linejoin": "round",
          "aria-hidden": "true",
          innerHTML: paths[props.name] || paths.record
        }, null, 8, _hoisted_1$k);
      };
    }
  });
  const _hoisted_1$j = ["data-trigger-mode"];
  const _hoisted_2$h = ["aria-label", "aria-expanded"];
  const _hoisted_3$h = ["tabindex", "aria-label"];
  const _hoisted_4$g = ["data-side", "hidden"];
  let tooltipSequence = 0;
  const _sfc_main$k = /* @__PURE__ */ defineComponent({
    __name: "UiTooltip",
    props: {
      text: {},
      label: { default: "" },
      placement: { default: "top" },
      triggerMode: { default: "icon" },
      contentFocusable: { type: Boolean, default: true }
    },
    setup(__props) {
      const id = `ui-tooltip-${++tooltipSequence}`;
      const open = /* @__PURE__ */ ref(false);
      const trigger2 = /* @__PURE__ */ ref(null);
      const bubble = /* @__PURE__ */ ref(null);
      const target = /* @__PURE__ */ ref("body");
      const side = /* @__PURE__ */ ref(__props.placement);
      const position = /* @__PURE__ */ ref({});
      const GAP = 6;
      const MARGIN = 8;
      function place() {
        const anchorElement = trigger2.value;
        const content = bubble.value;
        if (!anchorElement || !content) return;
        const anchor = anchorElement.getBoundingClientRect();
        const box = content.getBoundingClientRect();
        const above = anchor.top - GAP - box.height;
        const below = anchor.bottom + GAP;
        const fitsAbove = above >= MARGIN;
        const fitsBelow = below + box.height <= window.innerHeight - MARGIN;
        side.value = __props.placement === "top" ? fitsAbove || !fitsBelow ? "top" : "bottom" : fitsBelow || !fitsAbove ? "bottom" : "top";
        const top = side.value === "top" ? Math.max(MARGIN, above) : below;
        const centre = anchor.left + anchor.width / 2 - box.width / 2;
        const left = Math.min(Math.max(MARGIN, centre), window.innerWidth - box.width - MARGIN);
        position.value = { top: `${Math.round(top)}px`, left: `${Math.round(left)}px` };
      }
      function show() {
        target.value = trigger2.value?.closest("dialog[open]") || "body";
        open.value = true;
        void nextTick(place);
        window.addEventListener("scroll", hide, true);
        window.addEventListener("resize", hide);
      }
      function hide() {
        open.value = false;
        window.removeEventListener("scroll", hide, true);
        window.removeEventListener("resize", hide);
      }
      function toggle() {
        if (open.value) hide();
        else show();
      }
      function onKeydown(event) {
        if (event.key === "Escape" && open.value) {
          event.preventDefault();
          event.stopPropagation();
          hide();
        }
      }
      onBeforeUnmount(hide);
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("span", {
          class: "ui-tooltip",
          "data-trigger-mode": __props.triggerMode,
          onMouseenter: show,
          onMouseleave: hide,
          onKeydown
        }, [
          __props.triggerMode === "icon" ? (openBlock(), createElementBlock("button", {
            key: 0,
            ref_key: "trigger",
            ref: trigger2,
            type: "button",
            class: "ui-tooltip-trigger",
            "aria-label": __props.label || __props.text,
            "aria-describedby": id,
            "aria-expanded": open.value ? "true" : void 0,
            onFocus: show,
            onBlur: hide,
            onClick: toggle
          }, [..._cache[0] || (_cache[0] = [
            createBaseVNode("span", { "aria-hidden": "true" }, "i", -1)
          ])], 40, _hoisted_2$h)) : (openBlock(), createElementBlock("span", {
            key: 1,
            ref_key: "trigger",
            ref: trigger2,
            class: "ui-tooltip-anchor",
            tabindex: __props.contentFocusable ? 0 : void 0,
            "aria-label": __props.label || void 0,
            "aria-describedby": id,
            onFocusCapture: show,
            onBlurCapture: hide,
            onClick: toggle
          }, [
            renderSlot(_ctx.$slots, "default", {}, void 0, true)
          ], 40, _hoisted_3$h)),
          (openBlock(), createBlock(Teleport, { to: target.value }, [
            createBaseVNode("span", {
              id,
              ref_key: "bubble",
              ref: bubble,
              class: "ui-tooltip-content",
              role: "tooltip",
              "data-side": side.value,
              hidden: !open.value,
              style: normalizeStyle(position.value)
            }, toDisplayString(__props.text), 13, _hoisted_4$g)
          ], 8, ["to"]))
        ], 40, _hoisted_1$j);
      };
    }
  });
  const _export_sfc = (sfc, props) => {
    const target = sfc.__vccOpts || sfc;
    for (const [key, val] of props) {
      target[key] = val;
    }
    return target;
  };
  const UiTooltip = /* @__PURE__ */ _export_sfc(_sfc_main$k, [["__scopeId", "data-v-894a0d2d"]]);
  const _hoisted_1$i = { class: "ui-button-wrap" };
  const _hoisted_2$g = ["type", "disabled", "aria-disabled", "aria-pressed", "aria-expanded", "aria-label"];
  const _hoisted_3$g = { key: 1 };
  const _hoisted_4$f = {
    key: 3,
    class: "ui-button-count",
    "aria-hidden": "true"
  };
  const _hoisted_5$f = {
    key: 4,
    class: "sr-only"
  };
  const _hoisted_6$d = {
    key: 1,
    class: "ui-button-wrap"
  };
  const _hoisted_7$b = ["type", "disabled", "aria-disabled", "aria-pressed", "aria-expanded", "aria-label"];
  const _hoisted_8$9 = { key: 1 };
  const _hoisted_9$7 = {
    key: 3,
    class: "ui-button-count",
    "aria-hidden": "true"
  };
  const _hoisted_10$5 = {
    key: 4,
    class: "sr-only"
  };
  const _sfc_main$j = /* @__PURE__ */ defineComponent({
    __name: "UiButton",
    props: {
      label: { default: "" },
      icon: { default: "" },
      variant: { default: "default" },
      size: { default: "default" },
      disabled: { type: Boolean, default: false },
      disabledReason: { default: "" },
      count: { default: 0 },
      type: { default: "button" },
      iconOnly: { type: Boolean, default: false },
      pressed: { type: Boolean, default: void 0 },
      expanded: { type: Boolean, default: void 0 },
      buttonClass: { default: "" }
    },
    emits: ["click"],
    setup(__props, { emit: __emit }) {
      const props = __props;
      const emit2 = __emit;
      const tooltipText = computed(
        () => props.disabled && props.disabledReason ? props.disabledReason : props.iconOnly && props.label ? props.label : ""
      );
      const tooltipLabel = computed(
        () => props.disabled && props.disabledReason && props.label ? `${props.label}: ${props.disabledReason}` : ""
      );
      return (_ctx, _cache) => {
        return tooltipText.value ? (openBlock(), createBlock(UiTooltip, {
          key: 0,
          text: tooltipText.value,
          label: tooltipLabel.value || void 0,
          placement: "bottom",
          "trigger-mode": "content",
          "content-focusable": props.disabled
        }, {
          default: withCtx(() => [
            createBaseVNode("span", _hoisted_1$i, [
              createBaseVNode("button", {
                class: normalizeClass(["ui-button", [
                  `variant-${props.variant}`,
                  `size-${props.size}`,
                  props.buttonClass,
                  { "icon-only": props.iconOnly }
                ]]),
                type: props.type,
                disabled: props.disabled,
                "aria-disabled": props.disabled || void 0,
                "aria-pressed": props.pressed,
                "aria-expanded": props.expanded,
                "aria-label": props.iconOnly ? props.label : void 0,
                onClick: _cache[0] || (_cache[0] = ($event) => emit2("click", $event))
              }, [
                props.icon ? (openBlock(), createBlock(_sfc_main$l, {
                  key: 0,
                  name: props.icon,
                  "aria-hidden": "true"
                }, null, 8, ["name"])) : createCommentVNode("", true),
                !props.iconOnly ? (openBlock(), createElementBlock("span", _hoisted_3$g, [
                  renderSlot(_ctx.$slots, "default", {}, () => [
                    createTextVNode(toDisplayString(props.label), 1)
                  ], true)
                ])) : renderSlot(_ctx.$slots, "icon-label", {}, void 0, true, 2),
                props.count ? (openBlock(), createElementBlock("span", _hoisted_4$f, toDisplayString(props.count), 1)) : createCommentVNode("", true),
                props.count ? (openBlock(), createElementBlock("span", _hoisted_5$f, toDisplayString(props.count), 1)) : createCommentVNode("", true)
              ], 10, _hoisted_2$g)
            ])
          ]),
          _: 3
        }, 8, ["text", "label", "content-focusable"])) : (openBlock(), createElementBlock("span", _hoisted_6$d, [
          createBaseVNode("button", {
            class: normalizeClass(["ui-button", [
              `variant-${props.variant}`,
              `size-${props.size}`,
              props.buttonClass,
              { "icon-only": props.iconOnly }
            ]]),
            type: props.type,
            disabled: props.disabled,
            "aria-disabled": props.disabled || void 0,
            "aria-pressed": props.pressed,
            "aria-expanded": props.expanded,
            "aria-label": props.iconOnly ? props.label : void 0,
            onClick: _cache[1] || (_cache[1] = ($event) => emit2("click", $event))
          }, [
            props.icon ? (openBlock(), createBlock(_sfc_main$l, {
              key: 0,
              name: props.icon,
              "aria-hidden": "true"
            }, null, 8, ["name"])) : createCommentVNode("", true),
            !props.iconOnly ? (openBlock(), createElementBlock("span", _hoisted_8$9, [
              renderSlot(_ctx.$slots, "default", {}, () => [
                createTextVNode(toDisplayString(props.label), 1)
              ], true)
            ])) : renderSlot(_ctx.$slots, "icon-label", {}, void 0, true, 2),
            props.count ? (openBlock(), createElementBlock("span", _hoisted_9$7, toDisplayString(props.count), 1)) : createCommentVNode("", true),
            props.count ? (openBlock(), createElementBlock("span", _hoisted_10$5, toDisplayString(props.count), 1)) : createCommentVNode("", true)
          ], 10, _hoisted_7$b)
        ]));
      };
    }
  });
  const UiButton = /* @__PURE__ */ _export_sfc(_sfc_main$j, [["__scopeId", "data-v-de735335"]]);
  const PUBLISHED_RESEARCH_DEFAULTS = {
    mode: "auto",
    k: 24,
    fetchK: 500,
    topN: 10,
    mmrLambda: 0.72,
    works: []
  };
  const memoryStorage = /* @__PURE__ */ new Map();
  function readLocal(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return memoryStorage.get(key) || null;
    }
  }
  function writeLocal(key, value) {
    const text = String(value);
    memoryStorage.set(key, text);
    try {
      localStorage.setItem(key, text);
    } catch {
    }
  }
  function providerError(message, code, status = 0) {
    const error = new Error(message);
    error.code = code;
    error.status = status;
    return error;
  }
  function isLoopbackHost(hostname) {
    return ["localhost", "127.0.0.1", "::1", "[::1]"].includes(
      String(hostname || "").toLocaleLowerCase()
    );
  }
  function base64Bytes(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  }
  async function gunzip(bytes, unsupportedMessage) {
    if (typeof DecompressionStream !== "function") {
      throw providerError(unsupportedMessage, "unsupported");
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
  function blobUrl(bytes, type) {
    return URL.createObjectURL(new Blob([bytes], { type }));
  }
  function directionForLocale(code) {
    try {
      const script = new Intl.Locale(code).maximize().script || "";
      return (/* @__PURE__ */ new Set(["Arab", "Hebr", "Syrc", "Thaa", "Nkoo", "Adlm", "Rohg", "Mand"])).has(script) ? "rtl" : "ltr";
    } catch {
      return "ltr";
    }
  }
  function createPublishedSiteContext() {
    const publicationPackageCandidate = window.__DERRIDAI_SITE_PACKAGE__;
    const sdkCandidate = window.DerridAI;
    if (!publicationPackageCandidate?.manifest || !Array.isArray(publicationPackageCandidate.chunks)) {
      throw new Error("This DerridAI publication package is incomplete.");
    }
    if (!sdkCandidate?.createClient || !sdkCandidate?.dataSources?.inline) {
      throw new Error("The DerridAI SDK could not be loaded.");
    }
    const publicationPackage = publicationPackageCandidate;
    const sdk = sdkCandidate;
    const publication = publicationPackage.manifest;
    const publicationId = String(publication.publication_id || "publication");
    const localeKey = `derridai.site.locale.${publicationId}`;
    const themeKey = `derridai.site.theme.${publicationId}`;
    const contrastKey = `derridai.site.contrast.${publicationId}`;
    const tutorialKey = `derridai.site.tutorial.${publicationId}`;
    const legacyProviderKey = `derridai.site.provider.${publicationId}`;
    const embeddingSelectionKey = `derridai.site.provider.embedding.${publicationId}`;
    const generationSelectionKey = `derridai.site.provider.generation.${publicationId}`;
    const providersKey = `derridai.site.providers.${publicationId}`;
    const localModelKey = `derridai.site.local-model.${publicationId}`;
    const endpointsKey = `derridai.site.endpoints.${publicationId}`;
    const researchDefaultsKey = `derridai.site.research-defaults.${publicationId}`;
    const availableLocales = Object.keys(publication.strings || {});
    const languageMetadata = Array.isArray(publication.languages) ? publication.languages : [];
    const initialLocale = readLocal(localeKey) || publication.locale || availableLocales[0] || "en-US";
    const locale = /* @__PURE__ */ ref(
      availableLocales.includes(initialLocale) ? initialLocale : availableLocales[0] || "en-US"
    );
    const theme = /* @__PURE__ */ ref(readLocal(themeKey) === "dark" ? "dark" : "light");
    const highContrast = /* @__PURE__ */ ref(readLocal(contrastKey) === "high");
    const view = /* @__PURE__ */ ref("search");
    const tutorialSeen = /* @__PURE__ */ ref(Boolean(readLocal(tutorialKey)));
    const searchWork = /* @__PURE__ */ ref("");
    const recordDialog = /* @__PURE__ */ ref(null);
    const activeDevice = /* @__PURE__ */ ref("");
    const client = /* @__PURE__ */ ref(null);
    const capabilities = /* @__PURE__ */ ref(null);
    function normalizeResearchSettings(raw) {
      const mode = ["auto", "keyword", "semantic", "hybrid"].includes(
        String(raw?.mode || "")
      ) ? raw?.mode : PUBLISHED_RESEARCH_DEFAULTS.mode;
      const integer = (value, fallback, minimum, maximum) => {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? Math.max(minimum, Math.min(maximum, Math.round(parsed))) : fallback;
      };
      const k = integer(raw?.k, PUBLISHED_RESEARCH_DEFAULTS.k, 1, 500);
      const fetchK = Math.max(k, integer(raw?.fetchK, PUBLISHED_RESEARCH_DEFAULTS.fetchK, 1, 5e3));
      const topN = Math.min(k, integer(raw?.topN, PUBLISHED_RESEARCH_DEFAULTS.topN, 1, 100));
      const lambda = Number(raw?.mmrLambda);
      const mmrLambda = Number.isFinite(lambda) ? Math.max(0, Math.min(1, lambda)) : PUBLISHED_RESEARCH_DEFAULTS.mmrLambda;
      const availableWorks = new Set(
        (publication.works || []).map((item) => String(item.work || "").trim()).filter(Boolean)
      );
      const works = Array.isArray(raw?.works) ? [
        ...new Set(
          raw.works.map(String).map((value) => value.trim()).filter((value) => availableWorks.has(value))
        )
      ] : [];
      return { mode, k, fetchK, topN, mmrLambda, works };
    }
    function loadResearchDefaults() {
      try {
        return normalizeResearchSettings(
          JSON.parse(readLocal(researchDefaultsKey) || "{}")
        );
      } catch {
        return normalizeResearchSettings(PUBLISHED_RESEARCH_DEFAULTS);
      }
    }
    const researchDefaults = /* @__PURE__ */ ref(loadResearchDefaults());
    function updateResearchDefaults(value) {
      const next = normalizeResearchSettings(value);
      researchDefaults.value = next;
      writeLocal(researchDefaultsKey, JSON.stringify(next));
      return next;
    }
    function resetResearchDefaults() {
      return updateResearchDefaults(PUBLISHED_RESEARCH_DEFAULTS);
    }
    const publishedBrowserProfile = {
      model: "Xenova/multilingual-e5-small",
      revision: "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
      dtype: "q8",
      pooling: "mean",
      normalize: true,
      query_prefix: "query: ",
      document_prefix: "passage: ",
      ...publication.browser_embedding_profile || {}
    };
    const transformerSuggestions = [
      {
        id: String(publishedBrowserProfile.model),
        revision: String(publishedBrowserProfile.revision || ""),
        dtype: String(publishedBrowserProfile.dtype || ""),
        pooling: String(publishedBrowserProfile.pooling || "mean"),
        normalize: publishedBrowserProfile.normalize !== false,
        note: "site.runtime.transformers_model_multilingual_small",
        query_prefix: String(publishedBrowserProfile.query_prefix || ""),
        document_prefix: String(publishedBrowserProfile.document_prefix || "")
      },
      {
        id: "Xenova/all-MiniLM-L6-v2",
        revision: "",
        dtype: "",
        pooling: "mean",
        normalize: true,
        note: "site.runtime.transformers_model_english_small",
        query_prefix: "",
        document_prefix: ""
      },
      {
        id: "Xenova/bge-m3",
        aliases: ["bge-m3", "bge-m3:latest", "BAAI/bge-m3", "Xenova/bge-m3"],
        revision: "",
        dtype: "q8",
        pooling: "cls",
        normalize: true,
        note: "site.runtime.transformers_model_bge_m3",
        query_prefix: "",
        document_prefix: ""
      }
    ];
    const defaultTransformersModel = String(publishedBrowserProfile.model);
    const defaultTransformersDevice = "wasm";
    const modelCacheName = "transformers-cache";
    function t(key, vars = {}) {
      const dictionary = (publication.strings || {})[locale.value] || {};
      let value = String(dictionary[key] || key);
      for (const [name, replacement] of Object.entries(vars)) {
        value = value.replaceAll(`{${name}}`, String(replacement));
      }
      return value;
    }
    function sourceEmbeddingModel() {
      return String(
        publication.vector_index?.model || publication.source_collection?.embedding_model || ""
      ).trim();
    }
    function suggestedProfileForModel(model) {
      const normalized = String(model || "").trim().toLocaleLowerCase();
      return transformerSuggestions.find(
        (item) => item.id.toLocaleLowerCase() === normalized || "aliases" in item && (item.aliases || []).some((alias) => alias.toLocaleLowerCase() === normalized)
      );
    }
    function settingsForModel(model) {
      const match = suggestedProfileForModel(model);
      return {
        revision: match?.revision || "",
        dtype: match?.dtype || "",
        pooling: match?.pooling || "mean",
        normalize: match?.normalize !== false,
        query_prefix: match?.query_prefix || "",
        document_prefix: match?.document_prefix || ""
      };
    }
    function loadLocalModel() {
      try {
        const raw = JSON.parse(readLocal(localModelKey) || "{}");
        const model = String(raw.model || defaultTransformersModel);
        const defaults = settingsForModel(model);
        const device = raw.device === "webgpu" || raw.device === "wasm" ? raw.device : defaultTransformersDevice;
        return {
          model,
          device,
          revision: raw.revision == null ? defaults.revision : String(raw.revision),
          dtype: raw.dtype == null ? defaults.dtype : String(raw.dtype),
          pooling: raw.pooling == null ? defaults.pooling : String(raw.pooling),
          normalize: raw.normalize == null ? defaults.normalize : Boolean(raw.normalize),
          query_prefix: raw.query_prefix == null ? defaults.query_prefix : String(raw.query_prefix),
          document_prefix: raw.document_prefix == null ? defaults.document_prefix : String(raw.document_prefix)
        };
      } catch {
        const defaults = settingsForModel(defaultTransformersModel);
        return {
          model: defaultTransformersModel,
          device: defaultTransformersDevice,
          ...defaults
        };
      }
    }
    function normalizeEndpoint(raw) {
      if (!raw || !raw.id || !raw.name || !raw.base_url) return null;
      return {
        id: String(raw.id),
        name: String(raw.name),
        base_url: String(raw.base_url),
        model: String(raw.model || ""),
        remember_key: Boolean(raw.remember_key ?? raw.api_key),
        api_key: String(raw.api_key || ""),
        query_prefix: String(raw.query_prefix || ""),
        document_prefix: String(raw.document_prefix || "")
      };
    }
    function loadEndpoints() {
      try {
        const saved = JSON.parse(readLocal(endpointsKey) || "null");
        if (Array.isArray(saved)) {
          return saved.map((item) => normalizeEndpoint(item)).filter(Boolean);
        }
      } catch {
      }
      try {
        const older = JSON.parse(readLocal(providersKey) || "[]");
        return Array.isArray(older) ? older.map((item) => normalizeEndpoint(item)).filter(Boolean) : [];
      } catch {
        return [];
      }
    }
    const localModel = /* @__PURE__ */ ref(loadLocalModel());
    const endpoints = /* @__PURE__ */ ref(loadEndpoints());
    const sessionApiKeys = /* @__PURE__ */ new Map();
    for (const endpoint of endpoints.value) {
      if (endpoint.remember_key && endpoint.api_key) {
        sessionApiKeys.set(endpoint.id, endpoint.api_key);
      }
    }
    const initialEmbedding = readLocal(embeddingSelectionKey) || "";
    const selectedEmbeddingId = /* @__PURE__ */ ref(
      endpoints.value.some((endpoint) => endpoint.id === initialEmbedding) ? initialEmbedding : ""
    );
    const initialGeneration = readLocal(generationSelectionKey) || readLocal(legacyProviderKey) || "";
    const selectedGenerationId = /* @__PURE__ */ ref(
      endpoints.value.some((endpoint) => endpoint.id === initialGeneration) ? initialGeneration : ""
    );
    function saveLocalModel() {
      writeLocal(localModelKey, JSON.stringify(localModel.value));
    }
    function saveEndpoints() {
      writeLocal(
        endpointsKey,
        JSON.stringify(
          endpoints.value.map((endpoint) => ({
            ...endpoint,
            api_key: endpoint.remember_key ? sessionApiKeys.get(endpoint.id) || "" : ""
          }))
        )
      );
      writeLocal(embeddingSelectionKey, selectedEmbeddingId.value);
      writeLocal(generationSelectionKey, selectedGenerationId.value);
    }
    function applyAppearance() {
      document.documentElement.dataset.theme = theme.value;
      document.documentElement.dataset.contrast = highContrast.value ? "high" : "normal";
      document.documentElement.lang = locale.value;
      document.documentElement.dir = directionForLocale(locale.value);
      document.title = publication.title || t("site.runtime.site_title");
    }
    function setLocale(value) {
      locale.value = availableLocales.includes(value) ? value : locale.value;
      writeLocal(localeKey, locale.value);
      applyAppearance();
    }
    function setTheme(value) {
      theme.value = value === "dark" ? "dark" : "light";
      writeLocal(themeKey, theme.value);
      applyAppearance();
    }
    function setHighContrast(value) {
      highContrast.value = Boolean(value);
      writeLocal(contrastKey, highContrast.value ? "high" : "normal");
      applyAppearance();
    }
    function markTutorial(outcome) {
      writeLocal(tutorialKey, outcome);
      tutorialSeen.value = true;
    }
    function languageLabel(code) {
      const metadata = languageMetadata.find((item) => item.code === code);
      return metadata ? `${metadata.flag || ""} ${metadata.name || code}`.trim() : code;
    }
    function formatDate(value) {
      try {
        return new Intl.DateTimeFormat(locale.value, { dateStyle: "medium" }).format(
          new Date(String(value))
        );
      } catch {
        return String(value || "");
      }
    }
    function filterFields() {
      const excluded = /* @__PURE__ */ new Set(["text", "record_id", "source_spans", "field_assertions", "updates"]);
      const sourceCollection = publication.source_collection;
      const declared = Array.isArray(sourceCollection?.filter_fields) ? sourceCollection.filter_fields : [];
      const common = [
        "document_author",
        "publication_year",
        "year",
        "language",
        "speaker",
        "position_holder",
        "stance",
        "discourse_role",
        "topics",
        "concepts",
        "persons"
      ];
      return [...new Set([...declared, ...common].map(String))].filter((key) => key && !excluded.has(key) && key !== "work").sort((left, right) => left.localeCompare(right));
    }
    function localizedWarning(warning) {
      if (!warning) return "";
      if (warning.code === "semantic_unavailable") {
        return t("site.runtime.semantic_unavailable_keyword_fallback");
      }
      if (warning.code === "embedding_provider_unavailable") {
        return t("site.runtime.sdk_embedding_unavailable");
      }
      if (warning.code === "local_index_required") {
        return t("site.runtime.local_index_required", {
          indexed: warning.details?.indexed ?? 0,
          total: warning.details?.total ?? 0
        });
      }
      if (warning.code === "embedding_contract_mismatch") {
        return t("site.runtime.sdk_embedding_contract_mismatch");
      }
      if (warning.code === "embedding_dimension_mismatch") {
        return t("site.runtime.sdk_embedding_dimension_mismatch");
      }
      return String(warning.message || "");
    }
    function warningText(warnings) {
      return (warnings || []).map(localizedWarning).filter(Boolean).join(" ");
    }
    function providerBase(profile) {
      const raw = String(profile?.base_url || "").trim().replace(/\/$/, "");
      if (!raw) {
        throw providerError(t("site.runtime.provider_endpoint_missing"), "invalid_endpoint");
      }
      if (raw.startsWith("/")) {
        if (!["http:", "https:"].includes(location.protocol)) {
          throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
        }
        const sameOrigin = new URL(raw, location.origin);
        if (sameOrigin.origin !== location.origin) {
          throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
        }
        return sameOrigin.href.replace(/\/$/, "");
      }
      let parsed;
      try {
        parsed = new URL(raw);
      } catch {
        throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
      }
      if (!["http:", "https:"].includes(parsed.protocol)) {
        throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
      }
      if (location.protocol === "https:" && parsed.protocol === "http:" && !isLoopbackHost(parsed.hostname)) {
        throw providerError(
          t("site.runtime.provider_mixed_content", { endpoint: parsed.origin }),
          "mixed_content"
        );
      }
      return raw;
    }
    function providerHeaders(apiKey) {
      const headers = { "Content-Type": "application/json" };
      if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
      return headers;
    }
    async function providerJson(url, init) {
      let response;
      try {
        response = await fetch(url, init);
      } catch {
        throw providerError(
          t("site.runtime.provider_browser_blocked", {
            endpoint: url,
            origin: location.origin === "null" ? t("site.runtime.file_origin") : location.origin
          }),
          "network"
        );
      }
      const text = await response.text();
      let body = {};
      try {
        body = text ? JSON.parse(text) : {};
      } catch {
        body = {};
      }
      if (!response.ok) {
        const code = response.status === 401 || response.status === 403 ? "authentication" : response.status === 404 ? "not_found" : "provider_error";
        throw providerError(
          String(
            body?.error?.message || body?.detail || text || `${response.status} ${response.statusText}`
          ),
          code,
          response.status
        );
      }
      return body;
    }
    async function noCorsReachabilityProbe(url) {
      try {
        await fetch(url, { method: "GET", mode: "no-cors", cache: "no-store" });
        return true;
      } catch {
        return false;
      }
    }
    function embeddingVariant(profile) {
      return [
        profile.query_prefix ? `query-prefix=${profile.query_prefix}` : "",
        profile.document_prefix ? `document-prefix=${profile.document_prefix}` : ""
      ].filter(Boolean).join(";");
    }
    function prefixed(profile, input, purpose) {
      const prefix = purpose === "query" ? profile.query_prefix : profile.document_prefix;
      return prefix ? input.map((text) => `${prefix}${text}`) : input;
    }
    async function yieldAfterEmbeddingBatch(signal) {
      if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
      const scheduler = globalThis.scheduler;
      if (scheduler?.yield) {
        await scheduler.yield();
      } else {
        await new Promise((resolve2) => {
          if (typeof globalThis.requestAnimationFrame === "function") {
            globalThis.requestAnimationFrame(() => setTimeout(resolve2, 0));
          } else {
            setTimeout(resolve2, 0);
          }
        });
      }
      if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
    }
    function embeddingFailure() {
      return providerError(t("site.runtime.embedding_failed"), "embedding_failed");
    }
    function objectValue(value) {
      return value && typeof value === "object" ? value : {};
    }
    function normalizedModelProgress(value) {
      const source = objectValue(value);
      return {
        status: source.status == null ? void 0 : String(source.status),
        file: source.file == null ? void 0 : String(source.file),
        progress: source.progress == null ? void 0 : Number(source.progress)
      };
    }
    function directEmbeddingProvider(profile, apiKey) {
      const model = String(profile.model || "").trim();
      if (!model) return void 0;
      const descriptor = () => ({
        id: profile.id,
        type: "openai",
        model,
        variant: embeddingVariant(profile)
      });
      return {
        descriptor,
        async embed(input, options = {}) {
          const base = providerBase(profile);
          const texts = prefixed(profile, input, options.purpose);
          const body = await providerJson(`${base}/embeddings`, {
            method: "POST",
            headers: providerHeaders(apiKey),
            body: JSON.stringify({ model, input: texts }),
            signal: options.signal
          });
          const entries = Array.isArray(body.data) ? body.data.map(objectValue).sort((left, right) => Number(left.index ?? 0) - Number(right.index ?? 0)) : [];
          const vectors = [];
          for (const entry of entries) {
            const embedding = entry.embedding;
            if (!Array.isArray(embedding) || !embedding.every((value) => typeof value === "number")) {
              throw embeddingFailure();
            }
            vectors.push(embedding);
          }
          if (vectors.length !== texts.length) {
            throw embeddingFailure();
          }
          return { vectors, provider: descriptor() };
        }
      };
    }
    let transformersRuntime = null;
    let modelProgressListener = null;
    const transformersExtractors = /* @__PURE__ */ new Map();
    async function loadTransformersRuntime() {
      if (transformersRuntime) return transformersRuntime;
      transformersRuntime = (async () => {
        const delivery = publication.features?.transformers_runtime || "inline";
        let engineUrl;
        let wasmPaths;
        if (delivery === "files") {
          const base = new URL("./vendor/transformers/", location.href).href;
          engineUrl = `${base}transformers.min.js`;
          wasmPaths = {
            mjs: `${base}ort-wasm-simd-threaded.mjs`,
            wasm: `${base}ort-wasm-simd-threaded.wasm`
          };
        } else {
          const bundle = window.__DERRIDAI_TRANSFORMERS_RUNTIME__;
          if (!bundle) {
            throw providerError(t("site.runtime.transformers_not_included"), "runtime_missing");
          }
          engineUrl = blobUrl(base64Bytes(bundle.engine_b64), "text/javascript");
          wasmPaths = {
            mjs: blobUrl(base64Bytes(bundle.wasm_factory_b64), "text/javascript"),
            wasm: blobUrl(
              await gunzip(
                base64Bytes(bundle.wasm_gzip_b64),
                t("site.runtime.transformers_unsupported_browser")
              ),
              "application/wasm"
            )
          };
        }
        const runtime = await import(
          /* @vite-ignore */
          engineUrl
        );
        runtime.env.allowRemoteModels = true;
        runtime.env.allowLocalModels = false;
        runtime.env.useBrowserCache = true;
        if (runtime.env.backends?.onnx?.wasm) {
          runtime.env.backends.onnx.wasm.wasmPaths = wasmPaths;
          runtime.env.backends.onnx.wasm.numThreads = 1;
        }
        return runtime;
      })();
      transformersRuntime.catch(() => {
        transformersRuntime = null;
      });
      return transformersRuntime;
    }
    async function resolveDevice(preference) {
      if (preference !== "webgpu") return "wasm";
      const gpu = navigator.gpu;
      if (!gpu) return "wasm";
      try {
        if (await gpu.requestAdapter()) return "webgpu";
      } catch {
      }
      return "wasm";
    }
    function transformersExtractor(profile) {
      const key = [
        profile.model,
        profile.revision || "",
        profile.dtype || "",
        profile.device || defaultTransformersDevice
      ].join("|");
      const cached = transformersExtractors.get(key);
      if (cached) return cached;
      const loading = (async () => {
        const runtime = await loadTransformersRuntime();
        const device = await resolveDevice(profile.device || defaultTransformersDevice);
        activeDevice.value = device;
        try {
          return await runtime.pipeline("feature-extraction", profile.model, {
            device,
            ...profile.revision ? { revision: profile.revision } : {},
            ...profile.dtype ? { dtype: profile.dtype } : {},
            progress_callback: (progress) => modelProgressListener?.(normalizedModelProgress(progress))
          });
        } catch (error) {
          if (device === "wasm") throw error;
          activeDevice.value = "wasm";
          return runtime.pipeline("feature-extraction", profile.model, {
            device: "wasm",
            ...profile.revision ? { revision: profile.revision } : {},
            ...profile.dtype ? { dtype: profile.dtype } : {},
            progress_callback: (progress) => modelProgressListener?.(normalizedModelProgress(progress))
          });
        }
      })();
      loading.catch(() => transformersExtractors.delete(key));
      transformersExtractors.set(key, loading);
      return loading;
    }
    async function deleteModelCache() {
      transformersExtractors.clear();
      activeDevice.value = "";
      if (typeof caches === "undefined") return;
      const names = await caches.keys();
      await Promise.all(
        names.filter((name) => name === modelCacheName || name.toLowerCase().includes("transformers")).map((name) => caches.delete(name))
      );
    }
    function transformersEmbeddingProvider(profile) {
      const model = String(profile.model || "").trim();
      if (!model) return void 0;
      const descriptor = () => ({
        id: "transformers-local",
        type: "transformers",
        model,
        revision: profile.revision || void 0,
        variant: [
          embeddingVariant(profile),
          profile.dtype ? `dtype=${profile.dtype}` : "",
          `pooling=${profile.pooling || "mean"}`,
          `normalize=${profile.normalize !== false}`
        ].filter(Boolean).join(";")
      });
      return {
        descriptor,
        async embed(input, options = {}) {
          const extractor = await transformersExtractor(profile);
          const texts = prefixed(profile, input, options.purpose);
          const vectors = [];
          const microBatchSize = /bge-m3$/i.test(model) ? 1 : 4;
          for (let start = 0; start < texts.length; start += microBatchSize) {
            if (options.signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
            const tensor = await extractor(texts.slice(start, start + microBatchSize), {
              pooling: profile.pooling || "mean",
              normalize: profile.normalize !== false
            });
            try {
              vectors.push(...tensor.tolist());
            } finally {
              tensor.dispose?.();
            }
            if (start + microBatchSize < texts.length) {
              await yieldAfterEmbeddingBatch(options.signal);
            }
          }
          if (vectors.length !== texts.length) throw embeddingFailure();
          return { vectors, provider: descriptor() };
        }
      };
    }
    function directGenerationProvider(profile, apiKey) {
      const model = String(profile.model || "").trim();
      if (!model) return void 0;
      const descriptor = () => ({ id: profile.id, type: "openai", model });
      return {
        descriptor,
        async generate(request, options = {}) {
          const base = providerBase(profile);
          const body = await providerJson(`${base}/chat/completions`, {
            method: "POST",
            headers: providerHeaders(apiKey),
            body: JSON.stringify({
              model,
              temperature: 0,
              messages: [{ role: "user", content: request.prompt }]
            }),
            signal: options.signal
          });
          return {
            text: String(body.choices?.[0]?.message?.content || ""),
            provider: descriptor()
          };
        }
      };
    }
    function endpointById(id) {
      return endpoints.value.find((endpoint) => endpoint.id === id) || null;
    }
    function embeddingProviderFor(profile) {
      if (!profile) return transformersEmbeddingProvider(localModel.value);
      return directEmbeddingProvider(profile, sessionApiKeys.get(profile.id) || "");
    }
    async function rebuildClient() {
      const host = window.__DERRIDAI_HOST_CAPABILITIES__ || {};
      const embeddingProfile = endpointById(selectedEmbeddingId.value);
      const generationProfile = endpointById(selectedGenerationId.value);
      const embeddings = embeddingProviderFor(embeddingProfile);
      const generation = generationProfile ? directGenerationProvider(generationProfile, sessionApiKeys.get(generationProfile.id) || "") : host.generation;
      client.value = await sdk.createClient({
        dataSource: sdk.dataSources.inline(publicationPackage),
        storage: host.storage,
        embeddings,
        generation,
        locale: locale.value
      });
      capabilities.value = await client.value.capabilities();
    }
    async function setLocaleAndRebuild(value) {
      setLocale(value);
      await rebuildClient();
    }
    function semanticReady() {
      return Boolean(
        capabilities.value?.provider?.embeddings && capabilities.value?.localIndex?.complete
      );
    }
    function subscribeProgress(setStatus) {
      if (!client.value) return () => void 0;
      return client.value.events.subscribe((event) => {
        if (event.type === "embedding-start") {
          setStatus(t("site.runtime.activity_vector_embedding"));
          return;
        }
        if (event.type === "generation-start") {
          setStatus(
            t("site.runtime.activity_llm_generation", {
              count: event.evidenceCount ?? ""
            })
          );
          return;
        }
        if (event.type !== "load-progress") return;
        setStatus(
          t("site.runtime.loading_progress", {
            stage: event.stage === "vectors" ? t("site.runtime.loading_vectors") : t("site.runtime.loading_records"),
            current: event.completed,
            total: event.total,
            work: event.work || ""
          })
        );
      });
    }
    function subscribeResearchProgress(setProgress) {
      if (!client.value) return () => void 0;
      return client.value.events.subscribe((event) => {
        if (event.type === "search-start") {
          setProgress({ message: t("site.runtime.activity_research_retrieving"), stage: 1 });
          return;
        }
        if (event.type === "embedding-start") {
          setProgress({ message: t("site.runtime.activity_vector_embedding"), stage: 1 });
          return;
        }
        if (event.type === "retrieval-complete") {
          setProgress({
            message: t("site.runtime.activity_research_retrieved", { count: event.resultCount }),
            stage: 2
          });
          return;
        }
        if (event.type === "evidence-selected") {
          setProgress({
            message: t("site.runtime.activity_research_evidence_selected", {
              count: event.evidenceCount
            }),
            stage: 2
          });
          return;
        }
        if (event.type === "generation-start") {
          setProgress({
            message: t("site.runtime.activity_llm_generation", {
              count: event.evidenceCount ?? ""
            }),
            stage: 3
          });
          return;
        }
        if (event.type === "generation-complete") {
          setProgress({ message: t("site.runtime.activity_research_finalizing"), stage: 3 });
          return;
        }
        if (event.type !== "load-progress") return;
        setProgress({
          message: t("site.runtime.loading_progress", {
            stage: event.stage === "vectors" ? t("site.runtime.loading_vectors") : t("site.runtime.loading_records"),
            current: event.completed,
            total: event.total,
            work: event.work || ""
          }),
          stage: 1
        });
      });
    }
    async function refreshCapabilities() {
      if (client.value) capabilities.value = await client.value.capabilities();
    }
    function updateLocalModel(model, device) {
      const nextModel = String(model || "").trim();
      const defaults = settingsForModel(nextModel);
      localModel.value = {
        model: nextModel,
        device,
        ...defaults
      };
      saveLocalModel();
    }
    async function testLocalModel(onProgress) {
      const profile = localModel.value;
      if (!profile.model) {
        return { ok: false, message: t("site.runtime.provider_model_required") };
      }
      modelProgressListener = onProgress || null;
      try {
        const provider = transformersEmbeddingProvider(profile);
        if (!provider) {
          return { ok: false, message: t("site.runtime.provider_model_required") };
        }
        const result = await provider.embed([t("site.runtime.transformers_probe")], {
          purpose: "query"
        });
        return {
          ok: true,
          message: t("site.runtime.transformers_ready", {
            dimension: result.vectors[0]?.length || 0
          })
        };
      } catch (error) {
        return {
          ok: false,
          message: t("site.runtime.provider_test_failed", {
            error: error instanceof Error ? error.message : String(error)
          })
        };
      } finally {
        modelProgressListener = null;
      }
    }
    const embeddingNameHint = /embed|bge|e5|minilm|gte|nomic|mxbai|arctic|snowflake|sentence/i;
    async function discoverModels(profile, apiKey, role = "generation") {
      let base;
      try {
        base = providerBase(profile);
      } catch (error) {
        return {
          ok: false,
          message: error instanceof Error ? error.message : String(error),
          models: []
        };
      }
      const endpoint = `${base}/models`;
      try {
        const body = await providerJson(endpoint, {
          method: "GET",
          headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
          cache: "no-store"
        });
        const models = (body.data || []).map((item) => {
          const model = item && typeof item === "object" ? item : {};
          return {
            name: String(model.id || ""),
            detail: [model.owned_by].filter(Boolean).join(" · ")
          };
        }).filter((item) => item.name);
        const unique = [];
        const seen = /* @__PURE__ */ new Set();
        for (const model of models.sort((left, right) => left.name.localeCompare(right.name))) {
          if (seen.has(model.name)) continue;
          seen.add(model.name);
          unique.push(model);
        }
        const wantsEmbedding = role === "embedding";
        unique.sort(
          (left, right) => Number(embeddingNameHint.test(right.name) === wantsEmbedding) - Number(embeddingNameHint.test(left.name) === wantsEmbedding)
        );
        return {
          ok: true,
          message: t("site.runtime.provider_ready"),
          models: unique
        };
      } catch (error) {
        const providerFailure = error;
        if (providerFailure.code === "network" && await noCorsReachabilityProbe(endpoint)) {
          const origin = location.origin === "null" ? t("site.runtime.file_origin") : location.origin;
          return {
            ok: false,
            message: t("site.runtime.provider_cors_blocked", { origin }),
            models: []
          };
        }
        return {
          ok: false,
          message: t("site.runtime.provider_test_failed", {
            error: error instanceof Error ? error.message : String(error)
          }),
          models: []
        };
      }
    }
    async function applySelections(embeddingId, generationId) {
      selectedEmbeddingId.value = embeddingId;
      selectedGenerationId.value = generationId;
      saveLocalModel();
      saveEndpoints();
      await rebuildClient();
    }
    async function addEndpoint(input) {
      let base = String(input.baseUrl || "").trim();
      try {
        base = new URL(base).href.replace(/\/$/, "");
      } catch {
        base = base.replace(/\/$/, "");
      }
      const raw = {
        id: `endpoint-${globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : Date.now()}`,
        name: String(input.name || "").trim(),
        base_url: base,
        model: String(input.model || "").trim(),
        remember_key: input.rememberKey && Boolean(input.apiKey)
      };
      const profile = normalizeEndpoint(raw);
      if (!profile || !profile.model) {
        throw new Error(
          profile ? t("site.runtime.provider_model_required") : t("site.runtime.provider_endpoint_invalid")
        );
      }
      providerBase(profile);
      sessionApiKeys.set(profile.id, input.apiKey);
      endpoints.value = [...endpoints.value, profile];
      if (input.useForEmbeddings) selectedEmbeddingId.value = profile.id;
      if (input.useForAnswers) selectedGenerationId.value = profile.id;
      saveEndpoints();
      await rebuildClient();
      return profile;
    }
    async function removeEndpoint(id) {
      const profile = endpointById(id);
      if (!profile) return;
      endpoints.value = endpoints.value.filter((endpoint) => endpoint.id !== profile.id);
      sessionApiKeys.delete(profile.id);
      if (selectedEmbeddingId.value === profile.id) selectedEmbeddingId.value = "";
      if (selectedGenerationId.value === profile.id) selectedGenerationId.value = "";
      saveEndpoints();
      await rebuildClient();
    }
    async function buildIndex(options = {}) {
      if (options.prepareLocalModel) {
        saveLocalModel();
        await rebuildClient();
      }
      if (!client.value) throw new Error(t("site.runtime.index_no_provider"));
      const stop = client.value.events.subscribe((event) => {
        if (event.type === "index-progress") {
          options.onIndexProgress?.(Number(event.indexed || 0), Number(event.total || 0));
        }
      });
      modelProgressListener = options.onModelProgress || null;
      try {
        const result = await client.value.index.build({ signal: options.signal });
        await refreshCapabilities();
        return result;
      } finally {
        stop();
        modelProgressListener = null;
      }
    }
    async function clearIndex() {
      if (!client.value) return;
      await client.value.index.clear();
      await refreshCapabilities();
    }
    function openRecord(record, searchedQuery = "") {
      recordDialog.value = { record, searchedQuery };
    }
    function closeRecord() {
      recordDialog.value = null;
    }
    const recordCount = computed(
      () => (publication.works || []).reduce((sum, item) => sum + Number(item.record_count || 0), 0)
    );
    async function initialize() {
      applyAppearance();
      await rebuildClient();
    }
    return {
      publication,
      publicationPackage,
      locale,
      theme,
      highContrast,
      availableLocales,
      view,
      tutorialSeen,
      searchWork,
      recordDialog,
      client,
      capabilities,
      endpoints,
      selectedEmbeddingId,
      selectedGenerationId,
      localModel,
      activeDevice,
      transformerSuggestions,
      researchDefaults,
      recordCount,
      t,
      languageLabel,
      formatDate,
      filterFields,
      warningText,
      sourceEmbeddingModel,
      semanticReady,
      normalizeResearchSettings,
      updateResearchDefaults,
      resetResearchDefaults,
      setLocaleAndRebuild,
      setTheme,
      setHighContrast,
      markTutorial,
      subscribeProgress,
      subscribeResearchProgress,
      refreshCapabilities,
      updateLocalModel,
      testLocalModel,
      deleteModelCache,
      discoverModels,
      endpointById,
      applySelections,
      addEndpoint,
      removeEndpoint,
      buildIndex,
      clearIndex,
      openRecord,
      closeRecord,
      initialize
    };
  }
  const contextKey = /* @__PURE__ */ Symbol("published-site-context");
  function providePublishedSiteContext(context) {
    provide(contextKey, context);
  }
  function usePublishedSite() {
    const context = inject(contextKey);
    if (!context) throw new Error("Published site context is unavailable.");
    return context;
  }
  const _hoisted_1$h = {
    key: 0,
    class: "panel empty",
    "data-tour": "notes"
  };
  const _hoisted_2$f = ["aria-label"];
  const _hoisted_3$f = { class: "meta" };
  const _hoisted_4$e = { key: 0 };
  const _hoisted_5$e = { key: 1 };
  const _hoisted_6$c = { class: "chips" };
  const _hoisted_7$a = { class: "chips" };
  const _hoisted_8$8 = {
    class: "status",
    role: "status",
    "aria-live": "polite"
  };
  const _sfc_main$i = /* @__PURE__ */ defineComponent({
    __name: "PublishedNotesView",
    setup(__props) {
      const site = usePublishedSite();
      const items = /* @__PURE__ */ ref([]);
      const statusById = /* @__PURE__ */ ref({});
      async function refresh() {
        items.value = site.client.value ? await site.client.value.annotations.list() : [];
      }
      async function openRecord(recordId, annotationId) {
        if (!site.client.value) return;
        try {
          const record = await site.client.value.records.get(recordId);
          if (record) site.openRecord(record);
          else {
            statusById.value = {
              ...statusById.value,
              [annotationId]: site.t("site.runtime.record_not_found")
            };
          }
        } catch (error) {
          statusById.value = {
            ...statusById.value,
            [annotationId]: site.t("site.runtime.record_load_failed", {
              error: error instanceof Error ? error.message : String(error)
            })
          };
        }
      }
      async function remove2(id) {
        if (!site.client.value) return;
        await site.client.value.annotations.remove(id);
        await refresh();
      }
      onMounted(refresh);
      return (_ctx, _cache) => {
        return !items.value.length ? (openBlock(), createElementBlock("div", _hoisted_1$h, toDisplayString(unref(site).t("site.runtime.no_annotations")), 1)) : (openBlock(), createElementBlock("section", {
          key: 1,
          class: "stack",
          "data-tour": "notes",
          "aria-label": unref(site).t("site.runtime.annotations")
        }, [
          (openBlock(true), createElementBlock(Fragment, null, renderList(items.value, (item) => {
            return openBlock(), createElementBlock("article", {
              key: item.id,
              class: "annotation"
            }, [
              createBaseVNode("strong", null, toDisplayString(item.work || item.record_id), 1),
              createBaseVNode("div", _hoisted_3$f, toDisplayString(unref(site).formatDate(item.created_at)), 1),
              item.quote ? (openBlock(), createElementBlock("blockquote", _hoisted_4$e, toDisplayString(item.quote), 1)) : createCommentVNode("", true),
              item.note ? (openBlock(), createElementBlock("p", _hoisted_5$e, toDisplayString(item.note), 1)) : createCommentVNode("", true),
              createBaseVNode("div", _hoisted_6$c, [
                (openBlock(true), createElementBlock(Fragment, null, renderList(item.tags || [], (tag) => {
                  return openBlock(), createElementBlock("span", {
                    key: tag,
                    class: "chip"
                  }, toDisplayString(tag), 1);
                }), 128))
              ]),
              createBaseVNode("div", _hoisted_7$a, [
                createVNode(UiButton, {
                  label: unref(site).t("site.runtime.view_record"),
                  onClick: ($event) => openRecord(item.record_id, item.id)
                }, null, 8, ["label", "onClick"]),
                createVNode(UiButton, {
                  variant: "danger",
                  label: unref(site).t("site.runtime.delete"),
                  onClick: ($event) => remove2(item.id)
                }, null, 8, ["label", "onClick"])
              ]),
              createBaseVNode("span", _hoisted_8$8, toDisplayString(statusById.value[item.id] || ""), 1)
            ]);
          }), 128))
        ], 8, _hoisted_2$f));
      };
    }
  });
  const _sfc_main$h = /* @__PURE__ */ defineComponent({
    __name: "UiCard",
    props: {
      as: { default: "section" },
      padded: { type: Boolean, default: true },
      headingId: { default: "" }
    },
    setup(__props) {
      return (_ctx, _cache) => {
        return openBlock(), createBlock(resolveDynamicComponent(__props.as), {
          class: normalizeClass(["ui-card", { padded: __props.padded }]),
          "aria-labelledby": __props.headingId || void 0
        }, {
          default: withCtx(() => [
            renderSlot(_ctx.$slots, "default", {}, void 0, true)
          ]),
          _: 3
        }, 8, ["class", "aria-labelledby"]);
      };
    }
  });
  const UiCard = /* @__PURE__ */ _export_sfc(_sfc_main$h, [["__scopeId", "data-v-c21b5364"]]);
  const _hoisted_1$g = ["type", "value", "aria-invalid"];
  const _sfc_main$g = /* @__PURE__ */ defineComponent({
    __name: "UiInput",
    props: {
      modelValue: { default: "" },
      type: { default: "text" },
      invalid: { type: Boolean, default: false }
    },
    emits: ["update:modelValue"],
    setup(__props, { emit: __emit }) {
      const props = __props;
      const emit2 = __emit;
      function onInput(event) {
        const input = event.target;
        if (props.type === "number") {
          emit2("update:modelValue", input.value === "" ? null : input.valueAsNumber);
          return;
        }
        emit2("update:modelValue", input.value);
      }
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("input", {
          class: "ui-control ui-input",
          type: __props.type,
          value: __props.modelValue ?? "",
          "aria-invalid": __props.invalid ? "true" : void 0,
          onInput
        }, null, 40, _hoisted_1$g);
      };
    }
  });
  const _hoisted_1$f = ["data-index"];
  const _hoisted_2$e = {
    class: "meta",
    role: "status",
    "aria-live": "polite"
  };
  const _hoisted_3$e = ["value", "max", "aria-label"];
  const _hoisted_4$d = {
    key: 1,
    class: "chips"
  };
  const _hoisted_5$d = {
    class: "status",
    role: "status",
    "aria-live": "polite"
  };
  const _sfc_main$f = /* @__PURE__ */ defineComponent({
    __name: "PublishedIndexStatus",
    props: {
      prepareLocalModel: { type: Boolean, default: false },
      initialBuildLabelKey: { default: "" }
    },
    setup(__props) {
      const props = __props;
      const site = usePublishedSite();
      const controller = /* @__PURE__ */ ref(null);
      const building = /* @__PURE__ */ ref(false);
      const progressVisible = /* @__PURE__ */ ref(false);
      const progressValue = /* @__PURE__ */ ref(0);
      const progressMax = /* @__PURE__ */ ref(1);
      const liveDetail = /* @__PURE__ */ ref("");
      const outcome = /* @__PURE__ */ ref("");
      const index = computed(() => site.capabilities.value?.localIndex || null);
      const storageLabel = computed(
        () => index.value?.persistent ? site.t("site.runtime.index_storage_indexeddb") : site.t("site.runtime.index_storage_memory")
      );
      const detail = computed(() => {
        if (building.value && liveDetail.value) return liveDetail.value;
        const current = index.value;
        if (!current) return site.t("site.runtime.index_no_provider");
        if (current.usesPublishedVectors) {
          return site.t("site.runtime.index_published", { model: current.model || "" });
        }
        if (current.complete) {
          return site.t("site.runtime.index_ready", {
            count: current.indexed,
            storage: storageLabel.value
          });
        }
        return site.t(
          site.capabilities.value?.publicationVectors?.available ? "site.runtime.index_needed" : "site.runtime.index_needed_no_published",
          {
            published: site.sourceEmbeddingModel() || site.t("site.runtime.not_configured"),
            model: current.model || site.localModel.value.model || site.t("site.runtime.not_configured"),
            indexed: current.indexed,
            total: current.total,
            storage: storageLabel.value
          }
        );
      });
      const buildLabel = computed(() => {
        const current = index.value;
        if (!current) return site.t("site.runtime.index_build");
        if (current.complete) return site.t("site.runtime.index_rebuild");
        if (current.indexed) return site.t("site.runtime.index_resume");
        return site.t(
          props.initialBuildLabelKey || (props.prepareLocalModel ? "site.runtime.index_build_browser" : "site.runtime.index_build")
        );
      });
      async function build() {
        const current = index.value;
        if (!current) return;
        outcome.value = "";
        controller.value = new AbortController();
        building.value = true;
        progressVisible.value = true;
        progressMax.value = Math.max(1, current.total);
        progressValue.value = current.indexed;
        liveDetail.value = site.t("site.runtime.index_preparing", {
          model: current.model || site.localModel.value.model || "",
          total: current.total
        });
        try {
          await site.buildIndex({
            prepareLocalModel: props.prepareLocalModel,
            signal: controller.value.signal,
            onIndexProgress(indexed, total) {
              progressMax.value = Math.max(1, total);
              progressValue.value = indexed;
              liveDetail.value = site.t("site.runtime.index_progress", { indexed, total });
            },
            onModelProgress(info) {
              if (info?.status === "progress" && info.file) {
                liveDetail.value = site.t("site.runtime.model_download", {
                  file: String(info.file).split("/").pop(),
                  percent: Math.round(Number(info.progress) || 0)
                });
              }
            }
          });
          outcome.value = site.t("site.runtime.index_done");
        } catch (error) {
          outcome.value = error instanceof DOMException && error.name === "AbortError" ? site.t("site.runtime.index_cancelled") : site.t("site.runtime.index_failed", {
            error: error instanceof Error ? error.message : String(error)
          });
        } finally {
          building.value = false;
          progressVisible.value = false;
          liveDetail.value = "";
          controller.value = null;
        }
      }
      function cancel() {
        controller.value?.abort();
      }
      async function clear() {
        if (!window.confirm(site.t("site.runtime.index_clear_confirm"))) return;
        await site.clearIndex();
        outcome.value = "";
      }
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("div", {
          class: "provider-summary stack",
          "data-index": index.value ? "ready" : "none"
        }, [
          createBaseVNode("strong", null, toDisplayString(unref(site).t("site.runtime.index_heading")), 1),
          createBaseVNode("div", _hoisted_2$e, toDisplayString(detail.value), 1),
          progressVisible.value ? (openBlock(), createElementBlock("progress", {
            key: 0,
            value: progressValue.value,
            max: progressMax.value,
            "aria-label": unref(site).t("site.runtime.index_progress_label")
          }, null, 8, _hoisted_3$e)) : createCommentVNode("", true),
          index.value && !index.value.usesPublishedVectors ? (openBlock(), createElementBlock("div", _hoisted_4$d, [
            createVNode(UiButton, {
              variant: index.value.complete ? "default" : "primary",
              label: buildLabel.value,
              disabled: building.value,
              onClick: build
            }, null, 8, ["variant", "label", "disabled"]),
            building.value ? (openBlock(), createBlock(UiButton, {
              key: 0,
              label: unref(site).t("site.runtime.index_cancel"),
              onClick: cancel
            }, null, 8, ["label"])) : createCommentVNode("", true),
            createVNode(UiButton, {
              variant: "danger",
              label: unref(site).t("site.runtime.index_clear"),
              disabled: building.value || !index.value.indexed,
              onClick: clear
            }, null, 8, ["label", "disabled"])
          ])) : createCommentVNode("", true),
          createBaseVNode("div", _hoisted_5$d, toDisplayString(outcome.value), 1)
        ], 8, _hoisted_1$f);
      };
    }
  });
  const _hoisted_1$e = ["data-size", "aria-describedby"];
  const _hoisted_2$d = { class: "ui-dialog-header" };
  const _hoisted_3$d = { class: "ui-dialog-heading" };
  const _hoisted_4$c = ["tabindex", "role", "aria-labelledby"];
  const _hoisted_5$c = {
    key: 0,
    class: "ui-dialog-footer"
  };
  const _sfc_main$e = /* @__PURE__ */ defineComponent({
    __name: "UiDialog",
    props: {
      open: { type: Boolean, default: true },
      title: {},
      description: { default: "" },
      closeLabel: { default: "Close" },
      size: { default: "large" },
      dismissible: { type: Boolean, default: true }
    },
    emits: ["close"],
    setup(__props, { emit: __emit }) {
      const props = __props;
      const emit2 = __emit;
      const panel = /* @__PURE__ */ ref(null);
      const dialogId = useId();
      const titleId = `${dialogId}-title`;
      const descriptionId = `${dialogId}-description`;
      const heading = /* @__PURE__ */ ref(null);
      const body = /* @__PURE__ */ ref(null);
      const scrollable = /* @__PURE__ */ ref(false);
      let bodyObserver;
      let priorActive = null;
      function measureBody() {
        const node = body.value;
        scrollable.value = !!node && node.scrollHeight > node.clientHeight + 1;
      }
      function focusable() {
        if (!panel.value) return [];
        return Array.from(
          panel.value.querySelectorAll(
            'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,audio[controls],video[controls],[tabindex]:not([tabindex="-1"])'
          )
        ).filter((node) => node.offsetParent !== null);
      }
      function requestClose() {
        if (props.dismissible) emit2("close");
      }
      function onKeydown(event) {
        if (!props.open) return;
        if (event.key === "Escape" && props.dismissible) {
          event.preventDefault();
          emit2("close");
          return;
        }
        if (event.key !== "Tab") return;
        const nodes = focusable();
        if (!nodes.length) {
          event.preventDefault();
          heading.value?.focus();
          return;
        }
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (!panel.value?.contains(document.activeElement)) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
      async function focusDialog() {
        await nextTick();
        const first = focusable()[0];
        (first || heading.value)?.focus({ preventScroll: true });
      }
      watch(
        () => props.open,
        async (value) => {
          if (value) {
            priorActive = document.activeElement;
            await focusDialog();
          } else priorActive?.focus?.({ preventScroll: true });
        }
      );
      onUpdated(measureBody);
      onMounted(async () => {
        if (typeof ResizeObserver !== "undefined" && body.value) {
          bodyObserver = new ResizeObserver(measureBody);
          bodyObserver.observe(body.value);
        }
        measureBody();
        priorActive = document.activeElement;
        document.addEventListener("keydown", onKeydown);
        if (props.open) await focusDialog();
      });
      onBeforeUnmount(() => {
        bodyObserver?.disconnect();
        document.removeEventListener("keydown", onKeydown);
        priorActive?.focus?.({ preventScroll: true });
      });
      return (_ctx, _cache) => {
        return openBlock(), createBlock(Teleport, { to: "body" }, [
          props.open ? (openBlock(), createElementBlock("div", {
            key: 0,
            class: "ui-dialog-backdrop",
            onMousedown: withModifiers(requestClose, ["self"])
          }, [
            createBaseVNode("section", {
              ref_key: "panel",
              ref: panel,
              class: "ui-dialog",
              "data-size": props.size,
              role: "dialog",
              "aria-modal": "true",
              "aria-labelledby": titleId,
              "aria-describedby": props.description ? descriptionId : void 0
            }, [
              createBaseVNode("header", _hoisted_2$d, [
                createBaseVNode("div", _hoisted_3$d, [
                  createBaseVNode("h2", {
                    id: titleId,
                    ref_key: "heading",
                    ref: heading,
                    tabindex: "-1"
                  }, toDisplayString(props.title), 513),
                  props.description ? (openBlock(), createElementBlock("p", {
                    key: 0,
                    id: descriptionId
                  }, toDisplayString(props.description), 1)) : createCommentVNode("", true)
                ]),
                props.dismissible ? (openBlock(), createBlock(UiButton, {
                  key: 0,
                  variant: "ghost",
                  size: "small",
                  icon: "close",
                  "icon-only": "",
                  label: props.closeLabel,
                  onClick: _cache[0] || (_cache[0] = ($event) => emit2("close"))
                }, null, 8, ["label"])) : createCommentVNode("", true)
              ]),
              createBaseVNode("div", {
                ref_key: "body",
                ref: body,
                class: "ui-dialog-body",
                tabindex: scrollable.value ? 0 : void 0,
                role: scrollable.value ? "region" : void 0,
                "aria-labelledby": scrollable.value ? titleId : void 0
              }, [
                renderSlot(_ctx.$slots, "default", {}, void 0, true)
              ], 8, _hoisted_4$c),
              _ctx.$slots.footer ? (openBlock(), createElementBlock("footer", _hoisted_5$c, [
                renderSlot(_ctx.$slots, "footer", {}, void 0, true)
              ])) : createCommentVNode("", true)
            ], 8, _hoisted_1$e)
          ], 32)) : createCommentVNode("", true)
        ]);
      };
    }
  });
  const UiDialog = /* @__PURE__ */ _export_sfc(_sfc_main$e, [["__scopeId", "data-v-dd8a615b"]]);
  const _hoisted_1$d = { class: "stack" };
  const _hoisted_2$c = { class: "field" };
  const _hoisted_3$c = {
    class: "meta",
    role: "status",
    "aria-live": "polite"
  };
  const _hoisted_4$b = {
    key: 0,
    class: "model-list"
  };
  const _hoisted_5$b = { class: "model-choice-copy" };
  const _hoisted_6$b = {
    key: 0,
    class: "muted"
  };
  const _hoisted_7$9 = { key: 1 };
  const _sfc_main$d = /* @__PURE__ */ defineComponent({
    __name: "PublishedModelDialog",
    props: {
      open: { type: Boolean },
      models: {},
      current: {}
    },
    emits: ["close", "select"],
    setup(__props, { emit: __emit }) {
      const props = __props;
      const emit2 = __emit;
      const site = usePublishedSite();
      const query = /* @__PURE__ */ ref("");
      watch(
        () => props.open,
        (open) => {
          if (open) query.value = "";
        }
      );
      const shown = computed(() => {
        const needle = query.value.trim().toLocaleLowerCase();
        return props.models.filter((item) => item.name.toLocaleLowerCase().includes(needle));
      });
      function select(model) {
        emit2("select", model);
        emit2("close");
      }
      return (_ctx, _cache) => {
        return openBlock(), createBlock(UiDialog, {
          open: __props.open,
          title: unref(site).t("site.runtime.models_dialog_title"),
          "close-label": unref(site).t("site.runtime.close"),
          onClose: _cache[1] || (_cache[1] = ($event) => emit2("close"))
        }, {
          default: withCtx(() => [
            createBaseVNode("div", _hoisted_1$d, [
              createBaseVNode("label", _hoisted_2$c, [
                createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.filter_models")), 1),
                createVNode(_sfc_main$g, {
                  modelValue: query.value,
                  "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => query.value = $event),
                  class: "control",
                  type: "search",
                  autocomplete: "off",
                  "aria-label": unref(site).t("site.runtime.filter_models")
                }, null, 8, ["modelValue", "aria-label"])
              ]),
              createBaseVNode("p", _hoisted_3$c, toDisplayString(unref(site).t("site.runtime.models_match", { count: shown.value.length })), 1),
              shown.value.length ? (openBlock(), createElementBlock("ul", _hoisted_4$b, [
                (openBlock(true), createElementBlock(Fragment, null, renderList(shown.value, (item) => {
                  return openBlock(), createElementBlock("li", {
                    key: item.name
                  }, [
                    createVNode(UiButton, {
                      pressed: item.name === __props.current,
                      "button-class": "model-choice",
                      onClick: ($event) => select(item.name)
                    }, {
                      default: withCtx(() => [
                        createBaseVNode("span", _hoisted_5$b, [
                          createBaseVNode("strong", null, toDisplayString(item.name), 1),
                          item.detail ? (openBlock(), createElementBlock("small", _hoisted_6$b, toDisplayString(item.detail), 1)) : createCommentVNode("", true),
                          createBaseVNode("span", null, toDisplayString(unref(site).t(
                            item.name === __props.current ? "site.runtime.model_in_use" : "site.runtime.use_model"
                          )), 1)
                        ])
                      ]),
                      _: 2
                    }, 1032, ["pressed", "onClick"])
                  ]);
                }), 128))
              ])) : (openBlock(), createElementBlock("p", _hoisted_7$9, toDisplayString(unref(site).t("site.runtime.no_models_match")), 1))
            ])
          ]),
          _: 1
        }, 8, ["open", "title", "close-label"]);
      };
    }
  });
  const PublishedModelDialog = /* @__PURE__ */ _export_sfc(_sfc_main$d, [["__scopeId", "data-v-aef123e2"]]);
  const _hoisted_1$c = ["for", "data-disabled"];
  const _hoisted_2$b = ["id", "checked", "disabled", "name", "required", "value", "aria-invalid", "aria-describedby"];
  const _hoisted_3$b = ["id"];
  const _sfc_main$c = /* @__PURE__ */ defineComponent({
    __name: "UiCheckbox",
    props: {
      modelValue: { type: Boolean, default: false },
      label: {},
      description: { default: "" },
      disabled: { type: Boolean, default: false },
      invalid: { type: Boolean, default: false },
      inputId: { default: "" },
      hideLabel: { type: Boolean, default: false },
      name: { default: "" },
      required: { type: Boolean, default: false },
      value: { default: "" }
    },
    emits: ["update:modelValue"],
    setup(__props, { emit: __emit }) {
      const props = __props;
      const emit2 = __emit;
      const generatedId = useId();
      const id = computed(() => props.inputId || generatedId);
      const descriptionId = computed(() => props.description ? `${id.value}-description` : void 0);
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("label", {
          class: "ui-checkbox",
          for: id.value,
          "data-disabled": __props.disabled ? "true" : void 0
        }, [
          createBaseVNode("input", {
            id: id.value,
            class: "ui-checkbox-control",
            type: "checkbox",
            checked: __props.modelValue,
            disabled: __props.disabled,
            name: __props.name || void 0,
            required: __props.required,
            value: __props.value || void 0,
            "aria-invalid": __props.invalid ? "true" : void 0,
            "aria-describedby": descriptionId.value,
            onChange: _cache[0] || (_cache[0] = ($event) => emit2("update:modelValue", $event.target.checked))
          }, null, 40, _hoisted_2$b),
          createBaseVNode("span", {
            class: normalizeClass(["ui-checkbox-copy", { "sr-only": __props.hideLabel && !__props.description }])
          }, [
            createBaseVNode("span", {
              class: normalizeClass(["ui-checkbox-label", { "sr-only": __props.hideLabel && __props.description }])
            }, toDisplayString(__props.label), 3),
            __props.description ? (openBlock(), createElementBlock("span", {
              key: 0,
              id: descriptionId.value,
              class: "ui-checkbox-description"
            }, toDisplayString(__props.description), 9, _hoisted_3$b)) : createCommentVNode("", true)
          ], 2)
        ], 8, _hoisted_1$c);
      };
    }
  });
  const _hoisted_1$b = ["for"];
  const _hoisted_2$a = {
    key: 1,
    class: "ui-field-required",
    "aria-hidden": "true"
  };
  const _hoisted_3$a = {
    key: 2,
    class: "ui-field-persist"
  };
  const _hoisted_4$a = {
    key: 1,
    class: "ui-field-label"
  };
  const _hoisted_5$a = {
    key: 1,
    class: "ui-field-required",
    "aria-hidden": "true"
  };
  const _hoisted_6$a = {
    key: 2,
    class: "ui-field-persist"
  };
  const _hoisted_7$8 = ["id"];
  const _hoisted_8$7 = ["id"];
  const _sfc_main$b = /* @__PURE__ */ defineComponent({
    __name: "UiField",
    props: {
      label: {},
      hint: { default: "" },
      tooltip: { default: "" },
      tooltipLabel: { default: "" },
      error: { default: "" },
      wide: { type: Boolean, default: false },
      required: { type: Boolean, default: false },
      persistence: { default: "" },
      controlId: { default: "" }
    },
    setup(__props) {
      const props = __props;
      const generatedId = useId();
      const hintId = computed(() => `${generatedId}-hint`);
      const errorId = computed(() => `${generatedId}-error`);
      const describedby = computed(
        () => [props.hint ? hintId.value : "", props.error ? errorId.value : ""].filter(Boolean).join(" ") || void 0
      );
      return (_ctx, _cache) => {
        return openBlock(), createBlock(resolveDynamicComponent(__props.controlId ? "div" : "label"), {
          class: normalizeClass(["ui-field", { wide: __props.wide, invalid: Boolean(__props.error) }])
        }, {
          default: withCtx(() => [
            __props.controlId ? (openBlock(), createElementBlock("label", {
              key: 0,
              class: "ui-field-label",
              for: __props.controlId
            }, [
              createTextVNode(toDisplayString(__props.label) + " ", 1),
              __props.tooltip ? (openBlock(), createBlock(UiTooltip, {
                key: 0,
                text: __props.tooltip,
                label: __props.tooltipLabel || `${__props.label}: ${__props.tooltip}`,
                placement: "bottom"
              }, null, 8, ["text", "label"])) : createCommentVNode("", true),
              __props.required ? (openBlock(), createElementBlock("span", _hoisted_2$a, " *")) : createCommentVNode("", true),
              __props.persistence ? (openBlock(), createElementBlock("span", _hoisted_3$a, toDisplayString(__props.persistence), 1)) : createCommentVNode("", true)
            ], 8, _hoisted_1$b)) : (openBlock(), createElementBlock("span", _hoisted_4$a, [
              createTextVNode(toDisplayString(__props.label) + " ", 1),
              __props.tooltip ? (openBlock(), createBlock(UiTooltip, {
                key: 0,
                text: __props.tooltip,
                label: __props.tooltipLabel || `${__props.label}: ${__props.tooltip}`,
                placement: "bottom"
              }, null, 8, ["text", "label"])) : createCommentVNode("", true),
              __props.required ? (openBlock(), createElementBlock("span", _hoisted_5$a, " *")) : createCommentVNode("", true),
              __props.persistence ? (openBlock(), createElementBlock("span", _hoisted_6$a, toDisplayString(__props.persistence), 1)) : createCommentVNode("", true)
            ])),
            renderSlot(_ctx.$slots, "default", {
              describedby: describedby.value,
              invalid: Boolean(__props.error),
              controlId: __props.controlId || void 0
            }, void 0, true),
            __props.hint ? (openBlock(), createElementBlock("span", {
              key: 2,
              id: hintId.value,
              class: "ui-field-hint"
            }, toDisplayString(__props.hint), 9, _hoisted_7$8)) : createCommentVNode("", true),
            __props.error ? (openBlock(), createElementBlock("span", {
              key: 3,
              id: errorId.value,
              class: "ui-field-error",
              role: "alert"
            }, toDisplayString(__props.error), 9, _hoisted_8$7)) : createCommentVNode("", true)
          ]),
          _: 3
        }, 8, ["class"]);
      };
    }
  });
  const UiField = /* @__PURE__ */ _export_sfc(_sfc_main$b, [["__scopeId", "data-v-2760bbcc"]]);
  const _hoisted_1$a = { class: "published-research-config" };
  const _hoisted_2$9 = { class: "published-research-config-grid" };
  const _hoisted_3$9 = { value: "auto" };
  const _hoisted_4$9 = { value: "keyword" };
  const _hoisted_5$9 = { value: "semantic" };
  const _hoisted_6$9 = { value: "hybrid" };
  const _hoisted_7$7 = { class: "published-work-scope" };
  const _hoisted_8$6 = { class: "muted" };
  const _hoisted_9$6 = {
    class: "meta",
    role: "status",
    "aria-live": "polite"
  };
  const _hoisted_10$4 = { class: "published-work-options" };
  const _sfc_main$a = /* @__PURE__ */ defineComponent({
    __name: "PublishedResearchConfig",
    props: {
      modelValue: {},
      idPrefix: { default: "published-research-config" },
      disabled: { type: Boolean, default: false }
    },
    emits: ["update:modelValue"],
    setup(__props, { emit: __emit }) {
      const props = __props;
      const emit2 = __emit;
      const site = usePublishedSite();
      function update(patch) {
        emit2("update:modelValue", {
          ...props.modelValue,
          ...patch,
          works: patch.works ? [...patch.works] : [...props.modelValue.works]
        });
      }
      function numberValue(value, fallback) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
      }
      function toggleWork(work, checked) {
        const next = new Set(props.modelValue.works);
        if (checked) next.add(work);
        else next.delete(work);
        update({ works: [...next] });
      }
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("div", _hoisted_1$a, [
          createBaseVNode("div", _hoisted_2$9, [
            createVNode(UiField, {
              label: unref(site).t("site.runtime.research_mode"),
              hint: unref(site).t("site.runtime.research_mode_help"),
              "control-id": `${__props.idPrefix}-mode`
            }, {
              default: withCtx(({ describedby, controlId }) => [
                createVNode(_sfc_main$m, {
                  id: controlId,
                  "model-value": __props.modelValue.mode,
                  "aria-describedby": describedby,
                  disabled: __props.disabled,
                  "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => update({ mode: $event }))
                }, {
                  default: withCtx(() => [
                    createBaseVNode("option", _hoisted_3$9, toDisplayString(unref(site).t("site.runtime.research_mode_auto")), 1),
                    createBaseVNode("option", _hoisted_4$9, toDisplayString(unref(site).t("site.runtime.research_mode_keyword")), 1),
                    createBaseVNode("option", _hoisted_5$9, toDisplayString(unref(site).t("site.runtime.research_mode_semantic")), 1),
                    createBaseVNode("option", _hoisted_6$9, toDisplayString(unref(site).t("site.runtime.research_mode_hybrid")), 1)
                  ]),
                  _: 1
                }, 8, ["id", "model-value", "aria-describedby", "disabled"])
              ]),
              _: 1
            }, 8, ["label", "hint", "control-id"]),
            createVNode(UiField, {
              label: unref(site).t("site.runtime.research_k"),
              hint: unref(site).t("site.runtime.research_k_help"),
              "control-id": `${__props.idPrefix}-k`
            }, {
              default: withCtx(({ describedby, controlId }) => [
                createVNode(_sfc_main$g, {
                  id: controlId,
                  type: "number",
                  "model-value": __props.modelValue.k,
                  min: "1",
                  max: "500",
                  "aria-describedby": describedby,
                  disabled: __props.disabled,
                  "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => update({ k: numberValue($event, __props.modelValue.k) }))
                }, null, 8, ["id", "model-value", "aria-describedby", "disabled"])
              ]),
              _: 1
            }, 8, ["label", "hint", "control-id"]),
            createVNode(UiField, {
              label: unref(site).t("site.runtime.research_fetch_k"),
              hint: unref(site).t("site.runtime.research_fetch_k_help"),
              "control-id": `${__props.idPrefix}-fetch-k`
            }, {
              default: withCtx(({ describedby, controlId }) => [
                createVNode(_sfc_main$g, {
                  id: controlId,
                  type: "number",
                  "model-value": __props.modelValue.fetchK,
                  min: "1",
                  max: "5000",
                  "aria-describedby": describedby,
                  disabled: __props.disabled,
                  "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => update({ fetchK: numberValue($event, __props.modelValue.fetchK) }))
                }, null, 8, ["id", "model-value", "aria-describedby", "disabled"])
              ]),
              _: 1
            }, 8, ["label", "hint", "control-id"]),
            createVNode(UiField, {
              label: unref(site).t("site.runtime.research_top_n"),
              hint: unref(site).t("site.runtime.research_top_n_help"),
              "control-id": `${__props.idPrefix}-top-n`
            }, {
              default: withCtx(({ describedby, controlId }) => [
                createVNode(_sfc_main$g, {
                  id: controlId,
                  type: "number",
                  "model-value": __props.modelValue.topN,
                  min: "1",
                  max: "100",
                  "aria-describedby": describedby,
                  disabled: __props.disabled,
                  "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => update({ topN: numberValue($event, __props.modelValue.topN) }))
                }, null, 8, ["id", "model-value", "aria-describedby", "disabled"])
              ]),
              _: 1
            }, 8, ["label", "hint", "control-id"]),
            createVNode(UiField, {
              label: unref(site).t("site.runtime.research_mmr_lambda"),
              hint: unref(site).t("site.runtime.research_mmr_lambda_help"),
              "control-id": `${__props.idPrefix}-mmr-lambda`
            }, {
              default: withCtx(({ describedby, controlId }) => [
                createVNode(_sfc_main$g, {
                  id: controlId,
                  type: "number",
                  "model-value": __props.modelValue.mmrLambda,
                  min: "0",
                  max: "1",
                  step: "0.01",
                  "aria-describedby": describedby,
                  disabled: __props.disabled,
                  "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => update({ mmrLambda: numberValue($event, __props.modelValue.mmrLambda) }))
                }, null, 8, ["id", "model-value", "aria-describedby", "disabled"])
              ]),
              _: 1
            }, 8, ["label", "hint", "control-id"])
          ]),
          createBaseVNode("fieldset", _hoisted_7$7, [
            createBaseVNode("legend", null, toDisplayString(unref(site).t("site.runtime.research_work_scope")), 1),
            createBaseVNode("p", _hoisted_8$6, toDisplayString(unref(site).t("site.runtime.research_work_scope_help")), 1),
            createBaseVNode("p", _hoisted_9$6, toDisplayString(__props.modelValue.works.length ? unref(site).t("site.runtime.research_selected_works_count", {
              count: __props.modelValue.works.length
            }) : unref(site).t("site.runtime.research_all_works")), 1),
            createBaseVNode("div", _hoisted_10$4, [
              (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).publication.works, (item, index) => {
                return openBlock(), createBlock(_sfc_main$c, {
                  key: item.work,
                  class: "published-work-option",
                  "input-id": `${__props.idPrefix}-work-${index}`,
                  label: String(item.work),
                  "model-value": __props.modelValue.works.includes(String(item.work)),
                  disabled: __props.disabled,
                  "onUpdate:modelValue": ($event) => toggleWork(String(item.work), $event)
                }, null, 8, ["input-id", "label", "model-value", "disabled", "onUpdate:modelValue"]);
              }), 128))
            ])
          ])
        ]);
      };
    }
  });
  const PublishedResearchConfig = /* @__PURE__ */ _export_sfc(_sfc_main$a, [["__scopeId", "data-v-791c945e"]]);
  const _hoisted_1$9 = {
    class: "panel stack provider-panel",
    "data-tour": "provider",
    "aria-labelledby": "provider-heading"
  };
  const _hoisted_2$8 = { id: "provider-heading" };
  const _hoisted_3$8 = { class: "muted" };
  const _hoisted_4$8 = { id: "research-defaults-heading" };
  const _hoisted_5$8 = { class: "muted" };
  const _hoisted_6$8 = { class: "chips" };
  const _hoisted_7$6 = {
    class: "status",
    role: "status",
    "aria-live": "polite"
  };
  const _hoisted_8$5 = { id: "local-model-heading" };
  const _hoisted_9$5 = { class: "muted" };
  const _hoisted_10$3 = { class: "field" };
  const _hoisted_11$3 = { id: "local-model-options" };
  const _hoisted_12$3 = ["value", "label"];
  const _hoisted_13$2 = { class: "field" };
  const _hoisted_14$2 = { value: "wasm" };
  const _hoisted_15$2 = { value: "webgpu" };
  const _hoisted_16$2 = { class: "meta" };
  const _hoisted_17$2 = ["value", "aria-label"];
  const _hoisted_18$2 = { class: "chips" };
  const _hoisted_19$2 = { id: "endpoints-heading" };
  const _hoisted_20$2 = { class: "muted" };
  const _hoisted_21$2 = { class: "field" };
  const _hoisted_22$2 = { value: "" };
  const _hoisted_23$2 = ["value"];
  const _hoisted_24$2 = { class: "field" };
  const _hoisted_25$2 = { value: "" };
  const _hoisted_26$2 = ["value"];
  const _hoisted_27$1 = { class: "provider-summary meta" };
  const _hoisted_28$1 = { class: "chips" };
  const _hoisted_29$1 = { id: "provider-add-heading" };
  const _hoisted_30$1 = { class: "muted" };
  const _hoisted_31 = { class: "field" };
  const _hoisted_32 = { class: "field" };
  const _hoisted_33 = { class: "field" };
  const _hoisted_34 = { class: "muted" };
  const _hoisted_35 = { class: "toggle" };
  const _hoisted_36 = { class: "field" };
  const _hoisted_37 = { id: "endpoint-model-options" };
  const _hoisted_38 = ["value"];
  const _hoisted_39 = { class: "chips" };
  const _hoisted_40 = { class: "toggle" };
  const _hoisted_41 = { class: "toggle" };
  const _hoisted_42 = { class: "chips" };
  const _sfc_main$9 = /* @__PURE__ */ defineComponent({
    __name: "PublishedProvidersView",
    setup(__props) {
      const site = usePublishedSite();
      function cloneResearchSettings(value) {
        return { ...value, works: [...value.works] };
      }
      const researchDraft = /* @__PURE__ */ ref(cloneResearchSettings(site.researchDefaults.value));
      const researchStatus = /* @__PURE__ */ ref("");
      watch(site.researchDefaults, (value) => {
        researchDraft.value = cloneResearchSettings(value);
      });
      function saveResearchDefaults() {
        researchDraft.value = cloneResearchSettings(site.updateResearchDefaults(researchDraft.value));
        researchStatus.value = site.t("site.runtime.research_defaults_saved");
      }
      function resetResearchDefaults() {
        researchDraft.value = cloneResearchSettings(site.resetResearchDefaults());
        researchStatus.value = site.t("site.runtime.research_defaults_reset");
      }
      const providerStatus = /* @__PURE__ */ ref("");
      const providerStatusTone = /* @__PURE__ */ ref("");
      const embeddingSelection = /* @__PURE__ */ ref(site.selectedEmbeddingId.value);
      const generationSelection = /* @__PURE__ */ ref(site.selectedGenerationId.value);
      watch(site.selectedEmbeddingId, (value) => {
        embeddingSelection.value = value;
      });
      watch(site.selectedGenerationId, (value) => {
        generationSelection.value = value;
      });
      const endpointSummary = computed(() => {
        const embedding = site.endpointById(embeddingSelection.value);
        const generation = site.endpointById(generationSelection.value);
        return [
          embedding ? site.t("site.runtime.embedding_uses_endpoint", {
            name: embedding.name,
            model: embedding.model
          }) : site.t("site.runtime.embedding_uses_browser"),
          generation ? site.t("site.runtime.generation_uses_endpoint", {
            name: generation.name,
            model: generation.model
          }) : site.t("site.runtime.provider_generation_none_help")
        ].join(" ");
      });
      const localModelName = /* @__PURE__ */ ref(site.localModel.value.model);
      const localDevice = /* @__PURE__ */ ref(site.localModel.value.device);
      const localStatus = /* @__PURE__ */ ref("");
      const localStatusTone = /* @__PURE__ */ ref("");
      const localProgressVisible = /* @__PURE__ */ ref(false);
      const localProgress = /* @__PURE__ */ ref(0);
      const testingModel = /* @__PURE__ */ ref(false);
      function saveLocalDraft() {
        site.updateLocalModel(localModelName.value, localDevice.value);
      }
      async function testModel() {
        saveLocalDraft();
        if (!site.localModel.value.model) {
          localStatusTone.value = "warning";
          localStatus.value = site.t("site.runtime.provider_model_required");
          return;
        }
        testingModel.value = true;
        localProgressVisible.value = true;
        localProgress.value = 0;
        localStatusTone.value = "";
        localStatus.value = site.t("site.runtime.model_download_start", {
          model: site.localModel.value.model
        });
        try {
          const result = await site.testLocalModel((info) => {
            if (info?.status !== "progress") return;
            localProgress.value = Math.round(Number(info.progress) || 0);
            localStatus.value = site.t("site.runtime.model_download", {
              file: String(info.file || site.localModel.value.model).split("/").pop(),
              percent: localProgress.value
            });
          });
          localStatusTone.value = result.ok ? "success" : "error";
          localStatus.value = result.message;
        } finally {
          localProgressVisible.value = false;
          testingModel.value = false;
        }
      }
      async function deleteCachedModel() {
        if (!window.confirm(site.t("site.runtime.delete_model_cache_confirm"))) return;
        await site.deleteModelCache();
        localStatusTone.value = "";
        localStatus.value = site.t("site.runtime.model_cache_cleared");
      }
      async function applyProviderSelection() {
        providerStatusTone.value = "";
        providerStatus.value = site.t("site.runtime.provider_applying");
        try {
          await site.applySelections(embeddingSelection.value, generationSelection.value);
          providerStatus.value = "";
        } catch (error) {
          providerStatusTone.value = "error";
          providerStatus.value = site.t("site.runtime.provider_apply_failed", {
            error: error instanceof Error ? error.message : String(error)
          });
        }
      }
      async function deleteSelectedEndpoint() {
        const id = generationSelection.value || embeddingSelection.value;
        const endpoint = site.endpointById(id);
        if (!endpoint) {
          providerStatusTone.value = "warning";
          providerStatus.value = site.t("site.runtime.endpoint_select_required");
          return;
        }
        if (!window.confirm(site.t("site.runtime.delete_endpoint_confirm", { name: endpoint.name }))) {
          return;
        }
        await site.removeEndpoint(endpoint.id);
        embeddingSelection.value = site.selectedEmbeddingId.value;
        generationSelection.value = site.selectedGenerationId.value;
        providerStatus.value = "";
        providerStatusTone.value = "";
      }
      const endpointName = /* @__PURE__ */ ref("");
      const endpointUrl = /* @__PURE__ */ ref("");
      const endpointToken = /* @__PURE__ */ ref("");
      const rememberToken = /* @__PURE__ */ ref(false);
      const endpointModel = /* @__PURE__ */ ref("");
      const useForEmbeddings = /* @__PURE__ */ ref(false);
      const useForAnswers = /* @__PURE__ */ ref(true);
      const endpointStatus = /* @__PURE__ */ ref("");
      const endpointStatusTone = /* @__PURE__ */ ref("");
      const discoveredModels = /* @__PURE__ */ ref([]);
      const modelDialogOpen = /* @__PURE__ */ ref(false);
      function endpointDraft() {
        let base = endpointUrl.value.trim();
        try {
          base = new URL(base).href.replace(/\/$/, "");
        } catch {
          base = base.replace(/\/$/, "");
        }
        return {
          id: "endpoint-draft",
          name: endpointName.value.trim() || "endpoint",
          base_url: base,
          model: endpointModel.value.trim(),
          remember_key: rememberToken.value && Boolean(endpointToken.value)
        };
      }
      async function discover() {
        endpointStatusTone.value = "";
        endpointStatus.value = site.t("site.runtime.discovering");
        const result = await site.discoverModels(
          endpointDraft(),
          endpointToken.value,
          useForEmbeddings.value && !useForAnswers.value ? "embedding" : "generation"
        );
        if (!result.ok) {
          endpointStatusTone.value = "error";
          endpointStatus.value = result.message;
          return;
        }
        discoveredModels.value = result.models;
        endpointStatusTone.value = result.models.length ? "success" : "warning";
        endpointStatus.value = site.t("site.runtime.models_loaded", {
          count: result.models.length
        });
        modelDialogOpen.value = true;
      }
      async function saveEndpoint() {
        endpointStatusTone.value = "";
        endpointStatus.value = site.t("site.runtime.provider_applying");
        try {
          await site.addEndpoint({
            name: endpointName.value,
            baseUrl: endpointUrl.value,
            model: endpointModel.value,
            apiKey: endpointToken.value,
            rememberKey: rememberToken.value,
            useForEmbeddings: useForEmbeddings.value,
            useForAnswers: useForAnswers.value
          });
          embeddingSelection.value = site.selectedEmbeddingId.value;
          generationSelection.value = site.selectedGenerationId.value;
          endpointName.value = "";
          endpointUrl.value = "";
          endpointToken.value = "";
          rememberToken.value = false;
          endpointModel.value = "";
          useForEmbeddings.value = false;
          useForAnswers.value = true;
          endpointStatus.value = "";
        } catch (error) {
          endpointStatusTone.value = "error";
          endpointStatus.value = error instanceof Error ? error.message : String(error);
        }
      }
      const activeDeviceText = computed(
        () => site.activeDevice.value ? site.t("site.runtime.local_device_active", {
          device: site.t(
            site.activeDevice.value === "webgpu" ? "site.runtime.local_device_webgpu" : "site.runtime.local_device_wasm"
          )
        }) : site.t("site.runtime.local_model_help")
      );
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("section", _hoisted_1$9, [
          createBaseVNode("h2", _hoisted_2$8, toDisplayString(unref(site).t("site.runtime.providers")), 1),
          createBaseVNode("p", _hoisted_3$8, toDisplayString(unref(site).t("site.runtime.providers_intro")), 1),
          createVNode(UiCard, {
            class: "card stack",
            "heading-id": "research-defaults-heading"
          }, {
            default: withCtx(() => [
              createBaseVNode("h3", _hoisted_4$8, toDisplayString(unref(site).t("site.runtime.research_defaults_heading")), 1),
              createBaseVNode("p", _hoisted_5$8, toDisplayString(unref(site).t("site.runtime.research_defaults_help")), 1),
              createVNode(PublishedResearchConfig, {
                modelValue: researchDraft.value,
                "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => researchDraft.value = $event),
                "id-prefix": "published-research-defaults"
              }, null, 8, ["modelValue"]),
              createBaseVNode("div", _hoisted_6$8, [
                createVNode(UiButton, {
                  variant: "primary",
                  label: unref(site).t("site.runtime.save_research_defaults"),
                  onClick: saveResearchDefaults
                }, null, 8, ["label"]),
                createVNode(UiButton, {
                  label: unref(site).t("site.runtime.reset_research_defaults"),
                  onClick: resetResearchDefaults
                }, null, 8, ["label"])
              ]),
              createBaseVNode("div", _hoisted_7$6, toDisplayString(researchStatus.value), 1)
            ]),
            _: 1
          }),
          createVNode(UiCard, {
            class: "card stack",
            "heading-id": "local-model-heading"
          }, {
            default: withCtx(() => [
              createBaseVNode("h3", _hoisted_8$5, toDisplayString(unref(site).t("site.runtime.local_model_heading")), 1),
              createBaseVNode("p", _hoisted_9$5, toDisplayString(unref(site).t("site.runtime.local_model_help")), 1),
              createBaseVNode("label", _hoisted_10$3, [
                createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.local_model")), 1),
                createVNode(_sfc_main$g, {
                  modelValue: localModelName.value,
                  "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => localModelName.value = $event),
                  class: "control",
                  list: "local-model-options",
                  autocomplete: "off",
                  "aria-label": unref(site).t("site.runtime.local_model"),
                  onChange: saveLocalDraft
                }, null, 8, ["modelValue", "aria-label"]),
                createBaseVNode("datalist", _hoisted_11$3, [
                  (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).transformerSuggestions, (item) => {
                    return openBlock(), createElementBlock("option", {
                      key: item.id,
                      value: item.id,
                      label: unref(site).t(item.note)
                    }, null, 8, _hoisted_12$3);
                  }), 128))
                ])
              ]),
              createBaseVNode("label", _hoisted_13$2, [
                createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.local_device")), 1),
                createVNode(_sfc_main$m, {
                  modelValue: localDevice.value,
                  "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => localDevice.value = $event),
                  class: "control",
                  "aria-label": unref(site).t("site.runtime.local_device"),
                  onChange: saveLocalDraft
                }, {
                  default: withCtx(() => [
                    createBaseVNode("option", _hoisted_14$2, toDisplayString(unref(site).t("site.runtime.local_device_wasm")), 1),
                    createBaseVNode("option", _hoisted_15$2, toDisplayString(unref(site).t("site.runtime.local_device_webgpu")), 1)
                  ]),
                  _: 1
                }, 8, ["modelValue", "aria-label"])
              ]),
              createBaseVNode("div", _hoisted_16$2, toDisplayString(activeDeviceText.value), 1),
              localProgressVisible.value ? (openBlock(), createElementBlock("progress", {
                key: 0,
                value: localProgress.value,
                max: "100",
                "aria-label": unref(site).t("site.runtime.model_download_label")
              }, null, 8, _hoisted_17$2)) : createCommentVNode("", true),
              createBaseVNode("div", _hoisted_18$2, [
                createVNode(UiButton, {
                  variant: "primary",
                  label: unref(site).t("site.runtime.download_model"),
                  disabled: testingModel.value,
                  onClick: testModel
                }, null, 8, ["label", "disabled"]),
                createVNode(UiButton, {
                  variant: "danger",
                  label: unref(site).t("site.runtime.delete_model_cache"),
                  onClick: deleteCachedModel
                }, null, 8, ["label"])
              ]),
              createBaseVNode("div", {
                class: normalizeClass(["status", localStatusTone.value]),
                role: "status",
                "aria-live": "polite"
              }, toDisplayString(localStatus.value), 3),
              !unref(site).selectedEmbeddingId.value ? (openBlock(), createBlock(_sfc_main$f, {
                key: 1,
                "prepare-local-model": "",
                "initial-build-label-key": "site.runtime.index_build_browser"
              })) : createCommentVNode("", true)
            ]),
            _: 1
          }),
          createVNode(UiCard, {
            class: "card stack",
            "heading-id": "endpoints-heading"
          }, {
            default: withCtx(() => [
              createBaseVNode("h3", _hoisted_19$2, toDisplayString(unref(site).t("site.runtime.endpoints_heading")), 1),
              createBaseVNode("p", _hoisted_20$2, toDisplayString(unref(site).t("site.runtime.endpoints_help")), 1),
              createBaseVNode("label", _hoisted_21$2, [
                createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.provider_embedding_heading")), 1),
                createVNode(_sfc_main$m, {
                  modelValue: embeddingSelection.value,
                  "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => embeddingSelection.value = $event),
                  class: "control",
                  "aria-label": unref(site).t("site.runtime.provider_embedding_select")
                }, {
                  default: withCtx(() => [
                    createBaseVNode("option", _hoisted_22$2, toDisplayString(unref(site).t("site.runtime.local_model_heading")), 1),
                    (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).endpoints.value, (endpoint) => {
                      return openBlock(), createElementBlock("option", {
                        key: endpoint.id,
                        value: endpoint.id
                      }, toDisplayString(endpoint.name) + " · " + toDisplayString(endpoint.model), 9, _hoisted_23$2);
                    }), 128))
                  ]),
                  _: 1
                }, 8, ["modelValue", "aria-label"])
              ]),
              createBaseVNode("label", _hoisted_24$2, [
                createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.provider_generation_heading")), 1),
                createVNode(_sfc_main$m, {
                  modelValue: generationSelection.value,
                  "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => generationSelection.value = $event),
                  class: "control",
                  "aria-label": unref(site).t("site.runtime.provider_generation_select")
                }, {
                  default: withCtx(() => [
                    createBaseVNode("option", _hoisted_25$2, toDisplayString(unref(site).t("site.runtime.provider_generation_none")), 1),
                    (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).endpoints.value, (endpoint) => {
                      return openBlock(), createElementBlock("option", {
                        key: endpoint.id,
                        value: endpoint.id
                      }, toDisplayString(endpoint.name) + " · " + toDisplayString(endpoint.model), 9, _hoisted_26$2);
                    }), 128))
                  ]),
                  _: 1
                }, 8, ["modelValue", "aria-label"])
              ]),
              createBaseVNode("div", _hoisted_27$1, toDisplayString(endpointSummary.value), 1),
              createBaseVNode("div", _hoisted_28$1, [
                createVNode(UiButton, {
                  variant: "primary",
                  label: unref(site).t("site.runtime.apply_provider"),
                  onClick: applyProviderSelection
                }, null, 8, ["label"]),
                createVNode(UiButton, {
                  variant: "danger",
                  label: unref(site).t("site.runtime.delete_endpoint"),
                  onClick: deleteSelectedEndpoint
                }, null, 8, ["label"])
              ]),
              createBaseVNode("div", {
                class: normalizeClass(["status", providerStatusTone.value]),
                role: "status",
                "aria-live": "polite"
              }, toDisplayString(providerStatus.value), 3),
              unref(site).selectedEmbeddingId.value ? (openBlock(), createBlock(_sfc_main$f, { key: 0 })) : createCommentVNode("", true)
            ]),
            _: 1
          }),
          createBaseVNode("form", {
            class: "provider-form",
            "aria-labelledby": "provider-add-heading",
            onSubmit: withModifiers(saveEndpoint, ["prevent"])
          }, [
            createBaseVNode("h3", _hoisted_29$1, toDisplayString(unref(site).t("site.runtime.add_endpoint")), 1),
            createBaseVNode("p", _hoisted_30$1, toDisplayString(unref(site).t("site.runtime.provider_local_help")), 1),
            createBaseVNode("label", _hoisted_31, [
              createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.endpoint_name")), 1),
              createVNode(_sfc_main$g, {
                modelValue: endpointName.value,
                "onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => endpointName.value = $event),
                class: "control",
                required: "",
                autocomplete: "off",
                placeholder: unref(site).t("site.runtime.endpoint_name_placeholder")
              }, null, 8, ["modelValue", "placeholder"])
            ]),
            createBaseVNode("label", _hoisted_32, [
              createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.provider_url")), 1),
              createVNode(_sfc_main$g, {
                modelValue: endpointUrl.value,
                "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => endpointUrl.value = $event),
                class: "control",
                required: "",
                type: "text",
                inputmode: "url",
                autocomplete: "url",
                placeholder: unref(site).t("site.runtime.provider_url_placeholder")
              }, null, 8, ["modelValue", "placeholder"])
            ]),
            createBaseVNode("label", _hoisted_33, [
              createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.api_token")), 1),
              createVNode(_sfc_main$g, {
                modelValue: endpointToken.value,
                "onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => endpointToken.value = $event),
                class: "control",
                type: "password",
                autocomplete: "off",
                placeholder: unref(site).t("site.runtime.api_token_optional")
              }, null, 8, ["modelValue", "placeholder"]),
              createBaseVNode("small", _hoisted_34, toDisplayString(unref(site).t("site.runtime.api_token_help")), 1)
            ]),
            createBaseVNode("label", _hoisted_35, [
              withDirectives(createBaseVNode("input", {
                "onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => rememberToken.value = $event),
                type: "checkbox"
              }, null, 512), [
                [vModelCheckbox, rememberToken.value]
              ]),
              createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.store_token")), 1)
            ]),
            createBaseVNode("label", _hoisted_36, [
              createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.provider_model")), 1),
              createVNode(_sfc_main$g, {
                modelValue: endpointModel.value,
                "onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => endpointModel.value = $event),
                class: "control",
                required: "",
                autocomplete: "off",
                list: "endpoint-model-options",
                placeholder: unref(site).t("site.runtime.provider_model_placeholder")
              }, null, 8, ["modelValue", "placeholder"]),
              createBaseVNode("datalist", _hoisted_37, [
                (openBlock(true), createElementBlock(Fragment, null, renderList(discoveredModels.value, (item) => {
                  return openBlock(), createElementBlock("option", {
                    key: item.name,
                    value: item.name
                  }, null, 8, _hoisted_38);
                }), 128))
              ])
            ]),
            createBaseVNode("div", _hoisted_39, [
              createVNode(UiButton, {
                label: unref(site).t("site.runtime.discover_models"),
                onClick: discover
              }, null, 8, ["label"])
            ]),
            createBaseVNode("label", _hoisted_40, [
              withDirectives(createBaseVNode("input", {
                "onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => useForEmbeddings.value = $event),
                type: "checkbox"
              }, null, 512), [
                [vModelCheckbox, useForEmbeddings.value]
              ]),
              createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.use_for_embeddings")), 1)
            ]),
            createBaseVNode("label", _hoisted_41, [
              withDirectives(createBaseVNode("input", {
                "onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => useForAnswers.value = $event),
                type: "checkbox"
              }, null, 512), [
                [vModelCheckbox, useForAnswers.value]
              ]),
              createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.use_for_answers")), 1)
            ]),
            createBaseVNode("div", _hoisted_42, [
              createVNode(UiButton, {
                variant: "primary",
                type: "submit",
                label: unref(site).t("site.runtime.save_provider")
              }, null, 8, ["label"])
            ]),
            createBaseVNode("div", {
              class: normalizeClass(["status", endpointStatusTone.value]),
              role: "status",
              "aria-live": "polite"
            }, toDisplayString(endpointStatus.value), 3)
          ], 32),
          createVNode(PublishedModelDialog, {
            open: modelDialogOpen.value,
            models: discoveredModels.value,
            current: endpointModel.value,
            onClose: _cache[12] || (_cache[12] = ($event) => modelDialogOpen.value = false),
            onSelect: _cache[13] || (_cache[13] = ($event) => endpointModel.value = $event)
          }, null, 8, ["open", "models", "current"])
        ]);
      };
    }
  });
  const _hoisted_1$8 = ["value", "aria-invalid"];
  const _sfc_main$8 = /* @__PURE__ */ defineComponent({
    __name: "UiTextarea",
    props: {
      modelValue: { default: "" },
      invalid: { type: Boolean, default: false }
    },
    emits: ["update:modelValue"],
    setup(__props, { emit: __emit }) {
      const emit2 = __emit;
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("textarea", {
          class: "ui-control ui-textarea",
          value: __props.modelValue ?? "",
          "aria-invalid": __props.invalid ? "true" : void 0,
          onInput: _cache[0] || (_cache[0] = ($event) => emit2("update:modelValue", $event.target.value))
        }, null, 40, _hoisted_1$8);
      };
    }
  });
  const TERM_PATTERN = /[\p{L}\p{N}’'_-]+/gu;
  function queryTerms(query, locale) {
    return [
      ...new Set(
        String(query || "").toLocaleLowerCase(locale).match(TERM_PATTERN) ?? []
      )
    ];
  }
  function matchRanges(text, query, locale) {
    const terms = new Set(queryTerms(query, locale));
    if (!terms.size) return [];
    const ranges = [];
    for (const match of text.matchAll(TERM_PATTERN)) {
      if (terms.has(match[0].toLocaleLowerCase(locale))) {
        ranges.push([match.index, match.index + match[0].length]);
      }
    }
    const phrase = String(query || "").trim().toLocaleLowerCase(locale);
    const folded = text.toLocaleLowerCase(locale);
    if (terms.size > 1 && folded.length === text.length) {
      for (let at = folded.indexOf(phrase); phrase && at !== -1; at = folded.indexOf(phrase, at + 1)) {
        ranges.push([at, at + phrase.length]);
      }
    }
    ranges.sort((left, right) => left[0] - right[0] || right[1] - left[1]);
    const merged = [];
    for (const range of ranges) {
      const last = merged.at(-1);
      if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
      else merged.push([...range]);
    }
    return merged;
  }
  function highlightSegments(text, query, locale) {
    const segments = [];
    let from = 0;
    for (const [start, end] of matchRanges(text, query, locale)) {
      if (start > from) segments.push({ text: text.slice(from, start), highlighted: false });
      segments.push({ text: text.slice(start, end), highlighted: true });
      from = end;
    }
    if (from < text.length) segments.push({ text: text.slice(from), highlighted: false });
    if (!segments.length && text) segments.push({ text, highlighted: false });
    return segments;
  }
  function snippetText(text, query, locale, limit = 640) {
    if (text.length <= limit) return text;
    const first = matchRanges(text, query, locale)[0];
    if (!first || first[1] <= limit - 40) return text.slice(0, limit);
    const start = Math.max(text.lastIndexOf(" ", Math.max(first[0] - 200, 0)), 0);
    return `${start ? "…" : ""}${text.slice(start, start + limit).trimStart()}`;
  }
  const _hoisted_1$7 = { class: "dialog-head" };
  const _hoisted_2$7 = { id: "record-title" };
  const _hoisted_3$7 = { class: "dialog-body record-dialog-content" };
  const _hoisted_4$7 = {
    id: "record-citation",
    class: "meta"
  };
  const _hoisted_5$7 = {
    class: "record-text",
    tabindex: "0"
  };
  const _hoisted_6$7 = { key: 0 };
  const _hoisted_7$5 = { class: "metadata" };
  const _hoisted_8$4 = { class: "chips" };
  const _hoisted_9$4 = {
    class: "status success",
    role: "status",
    "aria-live": "polite"
  };
  const _sfc_main$7 = /* @__PURE__ */ defineComponent({
    __name: "PublishedRecordDialog",
    setup(__props) {
      const site = usePublishedSite();
      const dialog = /* @__PURE__ */ ref(null);
      const quote = /* @__PURE__ */ ref("");
      const note = /* @__PURE__ */ ref("");
      const tags = /* @__PURE__ */ ref("");
      const saved = /* @__PURE__ */ ref("");
      const state = computed(() => site.recordDialog.value);
      const record = computed(() => state.value?.record || null);
      const searchedQuery = computed(() => state.value?.searchedQuery || "");
      const textSegments = computed(
        () => highlightSegments(String(record.value?.text || ""), searchedQuery.value, site.locale.value)
      );
      const metadata = computed(() => {
        if (!record.value) return [];
        return Object.entries(record.value).sort(([left], [right]) => left.localeCompare(right)).filter(
          ([key, value]) => !["text", "field_assertions", "source_spans"].includes(key) && value != null && value !== "" && (typeof value !== "object" || Array.isArray(value))
        ).map(([key, value]) => ({
          key,
          label: key.replaceAll("_", " "),
          value: Array.isArray(value) ? value.map((item) => typeof item === "object" ? JSON.stringify(item) : String(item)).join(", ") : String(value)
        }));
      });
      watch(state, async (next) => {
        quote.value = "";
        note.value = "";
        tags.value = "";
        saved.value = "";
        await nextTick();
        if (next && dialog.value && !dialog.value.open) {
          dialog.value.showModal();
          dialog.value.querySelector(".record-close")?.focus();
          dialog.value.querySelector("mark")?.scrollIntoView({ block: "center" });
        } else if (!next && dialog.value?.open) {
          dialog.value.close();
        }
      });
      function close() {
        dialog.value?.close();
      }
      function onClose() {
        site.closeRecord();
      }
      async function saveAnnotation() {
        if (!record.value || !site.client.value) return;
        if (!quote.value.trim() && !note.value.trim() && !tags.value.trim()) return;
        await site.client.value.annotations.add({
          recordId: String(record.value.record_id),
          recordRevision: record.value.record_revision == null ? void 0 : String(record.value.record_revision),
          work: record.value.work == null ? void 0 : String(record.value.work),
          quote: quote.value,
          note: note.value,
          tags: tags.value.split(",").map((item) => item.trim()).filter(Boolean)
        });
        quote.value = "";
        note.value = "";
        tags.value = "";
        saved.value = site.t("site.runtime.annotation_saved");
      }
      return (_ctx, _cache) => {
        return openBlock(), createBlock(Teleport, { to: "body" }, [
          createBaseVNode("dialog", {
            ref_key: "dialog",
            ref: dialog,
            class: "record-dialog",
            "aria-labelledby": "record-title",
            "aria-describedby": "record-citation",
            onClose
          }, [
            record.value ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
              createBaseVNode("div", _hoisted_1$7, [
                createBaseVNode("h2", _hoisted_2$7, toDisplayString(record.value.work || record.value.record_id), 1),
                createVNode(UiButton, {
                  "button-class": "record-close",
                  label: unref(site).t("site.runtime.close"),
                  onClick: close
                }, null, 8, ["label"])
              ]),
              createBaseVNode("div", _hoisted_3$7, [
                createBaseVNode("div", _hoisted_4$7, toDisplayString(unref(site).client.value?.citations.format(record.value).plain), 1),
                createBaseVNode("div", _hoisted_5$7, [
                  (openBlock(true), createElementBlock(Fragment, null, renderList(textSegments.value, (segment, index) => {
                    return openBlock(), createElementBlock(Fragment, { key: index }, [
                      segment.highlighted ? (openBlock(), createElementBlock("mark", _hoisted_6$7, toDisplayString(segment.text), 1)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
                        createTextVNode(toDisplayString(segment.text), 1)
                      ], 64))
                    ], 64);
                  }), 128))
                ]),
                createBaseVNode("dl", _hoisted_7$5, [
                  (openBlock(true), createElementBlock(Fragment, null, renderList(metadata.value, (item) => {
                    return openBlock(), createElementBlock(Fragment, {
                      key: item.key
                    }, [
                      createBaseVNode("dt", null, toDisplayString(item.label), 1),
                      createBaseVNode("dd", null, toDisplayString(item.value), 1)
                    ], 64);
                  }), 128))
                ]),
                createBaseVNode("h3", null, toDisplayString(unref(site).t("site.runtime.add_annotation")), 1),
                createVNode(_sfc_main$8, {
                  modelValue: quote.value,
                  "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => quote.value = $event),
                  class: "control",
                  placeholder: unref(site).t("site.runtime.quote_placeholder"),
                  "aria-label": unref(site).t("site.runtime.quotation")
                }, null, 8, ["modelValue", "placeholder", "aria-label"]),
                createVNode(_sfc_main$8, {
                  modelValue: note.value,
                  "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => note.value = $event),
                  class: "control",
                  placeholder: unref(site).t("site.runtime.note_placeholder"),
                  "aria-label": unref(site).t("site.runtime.note")
                }, null, 8, ["modelValue", "placeholder", "aria-label"]),
                createVNode(_sfc_main$g, {
                  modelValue: tags.value,
                  "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => tags.value = $event),
                  class: "control",
                  placeholder: unref(site).t("site.runtime.tags_placeholder"),
                  "aria-label": unref(site).t("site.runtime.tags")
                }, null, 8, ["modelValue", "placeholder", "aria-label"]),
                createBaseVNode("div", _hoisted_8$4, [
                  createVNode(UiButton, {
                    variant: "primary",
                    label: unref(site).t("site.runtime.save_annotation"),
                    onClick: saveAnnotation
                  }, null, 8, ["label"])
                ]),
                createBaseVNode("span", _hoisted_9$4, toDisplayString(saved.value), 1)
              ])
            ], 64)) : createCommentVNode("", true)
          ], 544)
        ]);
      };
    }
  });
  const PublishedRecordDialog = /* @__PURE__ */ _export_sfc(_sfc_main$7, [["__scopeId", "data-v-33452b27"]]);
  const _hoisted_1$6 = ["aria-label"];
  const _hoisted_2$6 = ["data-active"];
  const _hoisted_3$6 = { class: "state" };
  const _hoisted_4$6 = ["data-active"];
  const _hoisted_5$6 = { class: "state" };
  const _hoisted_6$6 = ["data-active"];
  const _hoisted_7$4 = { class: "state" };
  const _sfc_main$6 = /* @__PURE__ */ defineComponent({
    __name: "PublishedMethodStrip",
    props: {
      text: { type: Boolean },
      vector: { type: Boolean },
      llm: { type: Boolean }
    },
    setup(__props) {
      const site = usePublishedSite();
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("div", {
          class: "method-strip",
          "data-tour": "methods",
          role: "group",
          "aria-label": unref(site).t("site.runtime.method_disclosure")
        }, [
          createBaseVNode("span", {
            class: "method-badge",
            "data-active": __props.text ? "true" : "false"
          }, [
            createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.method_text")), 1),
            createBaseVNode("span", _hoisted_3$6, toDisplayString(unref(site).t(__props.text ? "site.runtime.method_on" : "site.runtime.method_off")), 1)
          ], 8, _hoisted_2$6),
          createBaseVNode("span", {
            class: "method-badge",
            "data-active": __props.vector ? "true" : "false"
          }, [
            createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.method_vector")), 1),
            createBaseVNode("span", _hoisted_5$6, toDisplayString(unref(site).t(__props.vector ? "site.runtime.method_on" : "site.runtime.method_off")), 1)
          ], 8, _hoisted_4$6),
          createBaseVNode("span", {
            class: "method-badge",
            "data-active": __props.llm ? "true" : "false"
          }, [
            createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.method_llm")), 1),
            createBaseVNode("span", _hoisted_7$4, toDisplayString(unref(site).t(__props.llm ? "site.runtime.method_on" : "site.runtime.method_off")), 1)
          ], 8, _hoisted_6$6)
        ], 8, _hoisted_1$6);
      };
    }
  });
  const _hoisted_1$5 = { class: "published-research-answer" };
  const _hoisted_2$5 = ["data-evidence-id", "href"];
  const _hoisted_3$5 = { class: "published-evidence-list" };
  const _hoisted_4$5 = ["id", "data-evidence-id"];
  const _hoisted_5$5 = { class: "published-evidence-copy" };
  const _hoisted_6$5 = { class: "sr-only" };
  const _sfc_main$5 = /* @__PURE__ */ defineComponent({
    __name: "PublishedResearchResult",
    props: {
      answer: {},
      evidence: {},
      recordsById: {},
      evidenceTarget: {},
      evidenceLabel: {},
      openRecordLabel: {},
      onOpenRecord: { type: Function }
    },
    setup(__props) {
      const props = __props;
      const evidenceHeadingId = `${useId()}-published-evidence-heading`;
      function evidenceTargetId(evidenceId) {
        return `research-evidence-${String(evidenceId || "").replace(/[^A-Za-z0-9_-]+/g, "-")}`;
      }
      function inlineCitation(item) {
        const record = props.recordsById.get(String(item.recordId));
        const inline = String(record?.inline_citation || "").trim();
        if (inline) {
          return inline.startsWith("(") && inline.endsWith(")") ? inline : `(${inline})`;
        }
        const fallback = String(
          item.citation || record?.full_citation || record?.citation || item.work || item.recordId || ""
        ).trim();
        if (!fallback) return `[${item.evidenceId}]`;
        return fallback.startsWith("(") && fallback.endsWith(")") ? fallback : `(${fallback})`;
      }
      const evidenceById = computed(
        () => new Map(
          props.evidence.map((item) => [String(item.evidenceId || "").toUpperCase(), item])
        )
      );
      const answerSegments = computed(() => {
        const raw = String(props.answer || "");
        const marker = /\[(E\d+)\]/gi;
        const segments = [];
        let cursor = 0;
        for (let match = marker.exec(raw); match; match = marker.exec(raw)) {
          if (match.index > cursor) {
            segments.push({ kind: "text", text: raw.slice(cursor, match.index) });
          }
          const item = evidenceById.value.get(match[1].toUpperCase());
          if (item) {
            segments.push({ kind: "citation", text: inlineCitation(item), evidence: item });
          } else {
            segments.push({ kind: "text", text: match[0] });
          }
          cursor = marker.lastIndex;
        }
        if (cursor < raw.length) {
          segments.push({ kind: "text", text: raw.slice(cursor) });
        }
        return segments;
      });
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock(Fragment, null, [
          createBaseVNode("div", _hoisted_1$5, [
            (openBlock(true), createElementBlock(Fragment, null, renderList(answerSegments.value, (segment, index) => {
              return openBlock(), createElementBlock(Fragment, { key: index }, [
                segment.kind === "citation" ? (openBlock(), createElementBlock("a", {
                  key: 0,
                  class: "inline-citation",
                  "data-evidence-id": segment.evidence.evidenceId,
                  href: `#${evidenceTargetId(segment.evidence.evidenceId)}`
                }, toDisplayString(segment.text), 9, _hoisted_2$5)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
                  createTextVNode(toDisplayString(segment.text), 1)
                ], 64))
              ], 64);
            }), 128))
          ]),
          (openBlock(), createBlock(Teleport, { to: __props.evidenceTarget }, [
            createVNode(UiCard, {
              class: "published-evidence-card",
              "heading-id": evidenceHeadingId
            }, {
              default: withCtx(() => [
                createBaseVNode("h3", { id: evidenceHeadingId }, toDisplayString(__props.evidenceLabel), 1),
                createBaseVNode("div", _hoisted_3$5, [
                  (openBlock(true), createElementBlock(Fragment, null, renderList(__props.evidence, (item) => {
                    return openBlock(), createElementBlock("div", {
                      id: evidenceTargetId(item.evidenceId),
                      key: item.evidenceId,
                      class: "evidence-item",
                      "data-evidence-id": item.evidenceId
                    }, [
                      createVNode(UiButton, {
                        label: __props.openRecordLabel,
                        "button-class": "published-evidence-button",
                        onClick: ($event) => __props.onOpenRecord(item.recordId)
                      }, {
                        default: withCtx(() => [
                          createBaseVNode("span", _hoisted_5$5, [
                            createBaseVNode("span", _hoisted_6$5, toDisplayString(__props.openRecordLabel) + ": ", 1),
                            createBaseVNode("strong", null, "[" + toDisplayString(item.evidenceId) + "] " + toDisplayString(item.work || item.recordId), 1),
                            createBaseVNode("small", null, toDisplayString(item.citation || __props.recordsById.get(String(item.recordId))?.full_citation || __props.recordsById.get(String(item.recordId))?.citation || ""), 1)
                          ])
                        ]),
                        _: 2
                      }, 1032, ["label", "onClick"])
                    ], 8, _hoisted_4$5);
                  }), 128))
                ])
              ]),
              _: 1
            })
          ], 8, ["to"]))
        ], 64);
      };
    }
  });
  const PublishedResearchResult = /* @__PURE__ */ _export_sfc(_sfc_main$5, [["__scopeId", "data-v-89110dd1"]]);
  const _hoisted_1$4 = { class: "research-layout" };
  const _hoisted_2$4 = {
    class: "panel stack",
    "data-tour": "research",
    "aria-labelledby": "research-heading"
  };
  const _hoisted_3$4 = { id: "research-heading" };
  const _hoisted_4$4 = { class: "research-run-settings" };
  const _hoisted_5$4 = { class: "research-run-settings-body" };
  const _hoisted_6$4 = { class: "muted" };
  const _hoisted_7$3 = {
    key: 0,
    class: "research-run-progress"
  };
  const _hoisted_8$3 = ["aria-label"];
  const _hoisted_9$3 = {
    class: "meta",
    "aria-hidden": "true"
  };
  const _hoisted_10$2 = {
    class: "answer",
    "aria-live": "polite"
  };
  const _hoisted_11$2 = ["aria-label"];
  const _hoisted_12$2 = ["aria-label"];
  const _sfc_main$4 = /* @__PURE__ */ defineComponent({
    __name: "PublishedResearchView",
    setup(__props) {
      const site = usePublishedSite();
      const question = /* @__PURE__ */ ref("");
      const running = /* @__PURE__ */ ref(false);
      const status = /* @__PURE__ */ ref("");
      const statusTone = /* @__PURE__ */ ref("");
      const evidenceTarget = /* @__PURE__ */ ref(null);
      const response = /* @__PURE__ */ ref(null);
      const recordsById = /* @__PURE__ */ ref(/* @__PURE__ */ new Map());
      function cloneResearchSettings(value) {
        return { ...value, works: [...value.works] };
      }
      const runSettings = /* @__PURE__ */ ref(cloneResearchSettings(site.researchDefaults.value));
      const progressStage = /* @__PURE__ */ ref(0);
      const elapsedSeconds = /* @__PURE__ */ ref(0);
      let elapsedTimer;
      const progressSummary = computed(
        () => site.t("site.runtime.research_progress_summary", {
          current: progressStage.value,
          total: 3,
          seconds: elapsedSeconds.value
        })
      );
      const methods = /* @__PURE__ */ ref({
        text: true,
        vector: site.semanticReady(),
        llm: Boolean(site.capabilities.value?.provider?.generation)
      });
      const localIndexVisible = computed(
        () => Boolean(site.capabilities.value?.localIndex) && !site.capabilities.value?.localIndex?.usesPublishedVectors
      );
      const answerText = computed(
        () => response.value?.answer ? String(response.value.answer) : response.value?.evidencePacket?.evidence?.length ? site.t("site.runtime.generation_unavailable_evidence") : ""
      );
      function resolvedMode(settings) {
        return settings.mode === "auto" ? site.semanticReady() ? "hybrid" : "keyword" : settings.mode;
      }
      function startElapsedTimer() {
        stopElapsedTimer();
        elapsedSeconds.value = 0;
        elapsedTimer = window.setInterval(() => {
          elapsedSeconds.value += 1;
        }, 1e3);
      }
      function stopElapsedTimer() {
        if (elapsedTimer !== void 0) {
          window.clearInterval(elapsedTimer);
          elapsedTimer = void 0;
        }
      }
      function resetRunSettings() {
        runSettings.value = cloneResearchSettings(site.researchDefaults.value);
      }
      onBeforeUnmount(stopElapsedTimer);
      async function openEvidenceRecord(recordId) {
        const known = recordsById.value.get(String(recordId));
        const record = known || await site.client.value?.records.get(recordId);
        if (record) site.openRecord(record);
      }
      async function runResearch() {
        const q = question.value.trim();
        if (!q || !site.client.value) return;
        const config = site.normalizeResearchSettings(runSettings.value);
        runSettings.value = cloneResearchSettings(config);
        const mode = resolvedMode(config);
        running.value = true;
        response.value = null;
        recordsById.value = /* @__PURE__ */ new Map();
        progressStage.value = 1;
        startElapsedTimer();
        methods.value = {
          text: mode !== "semantic",
          vector: mode !== "keyword",
          llm: Boolean(site.capabilities.value?.provider?.generation)
        };
        statusTone.value = "";
        status.value = site.t("site.runtime.activity_research_retrieving");
        const stopProgress = site.subscribeResearchProgress(({ message, stage }) => {
          status.value = message;
          progressStage.value = stage;
        });
        try {
          const result = await site.client.value.research({
            question: q,
            retrieval: {
              mode,
              limit: config.k,
              fetchLimit: config.fetchK,
              evidenceLimit: config.topN,
              mmrLambda: config.mmrLambda,
              filters: config.works.length ? { work: config.works } : void 0
            }
          });
          recordsById.value = new Map(
            (result.retrieval.results || []).map((item) => [
              String(item.record?.record_id || ""),
              item.record
            ])
          );
          response.value = result;
          methods.value = {
            text: result.retrieval.modeUsed !== "semantic",
            vector: result.retrieval.modeUsed !== "keyword",
            llm: Boolean(result.generation)
          };
          const retrievalWarning = site.warningText(result.retrieval.warnings);
          const generationWarning = result.warnings.some(
            (warning) => warning.code === "generation_unavailable"
          );
          if (result.answer) {
            statusTone.value = retrievalWarning ? "warning" : "success";
            status.value = retrievalWarning ? site.t("site.runtime.complete_with_warning", { warning: retrievalWarning }) : site.t("site.runtime.complete");
          } else if (result.evidencePacket.evidence.length) {
            statusTone.value = "warning";
            status.value = generationWarning ? site.t("site.runtime.sdk_generation_unavailable") : site.t("site.runtime.complete");
          } else {
            statusTone.value = "warning";
            status.value = site.t("site.runtime.no_evidence");
          }
        } catch (error) {
          statusTone.value = "error";
          status.value = site.t("site.runtime.research_failed", {
            error: error instanceof Error ? error.message : String(error)
          });
        } finally {
          stopProgress();
          stopElapsedTimer();
          running.value = false;
        }
      }
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("div", _hoisted_1$4, [
          createBaseVNode("section", _hoisted_2$4, [
            createBaseVNode("h2", _hoisted_3$4, toDisplayString(unref(site).t("site.runtime.research")), 1),
            createVNode(_sfc_main$6, {
              text: methods.value.text,
              vector: methods.value.vector,
              llm: methods.value.llm
            }, null, 8, ["text", "vector", "llm"]),
            createVNode(_sfc_main$8, {
              modelValue: question.value,
              "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => question.value = $event),
              class: "control",
              placeholder: unref(site).t("site.runtime.question_placeholder"),
              "aria-label": unref(site).t("site.runtime.question")
            }, null, 8, ["modelValue", "placeholder", "aria-label"]),
            createBaseVNode("details", _hoisted_4$4, [
              createBaseVNode("summary", null, toDisplayString(unref(site).t("site.runtime.research_run_settings")), 1),
              createBaseVNode("div", _hoisted_5$4, [
                createBaseVNode("p", _hoisted_6$4, toDisplayString(unref(site).t("site.runtime.research_run_settings_help")), 1),
                createVNode(PublishedResearchConfig, {
                  modelValue: runSettings.value,
                  "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => runSettings.value = $event),
                  "id-prefix": "published-research-run",
                  disabled: running.value
                }, null, 8, ["modelValue", "disabled"]),
                createVNode(UiButton, {
                  label: unref(site).t("site.runtime.research_reset_to_defaults"),
                  disabled: running.value,
                  onClick: resetRunSettings
                }, null, 8, ["label", "disabled"])
              ])
            ]),
            createVNode(UiButton, {
              variant: "primary",
              label: unref(site).t("site.runtime.ask"),
              disabled: running.value,
              onClick: runResearch
            }, null, 8, ["label", "disabled"]),
            running.value ? (openBlock(), createElementBlock("div", _hoisted_7$3, [
              createBaseVNode("progress", { "aria-label": status.value }, null, 8, _hoisted_8$3),
              createBaseVNode("div", _hoisted_9$3, toDisplayString(progressSummary.value), 1)
            ])) : createCommentVNode("", true),
            createBaseVNode("div", {
              class: normalizeClass(["status", statusTone.value]),
              role: "status",
              "aria-live": "polite",
              "aria-atomic": "true"
            }, toDisplayString(status.value), 3),
            localIndexVisible.value ? (openBlock(), createBlock(_sfc_main$f, {
              key: 1,
              "initial-build-label-key": "site.runtime.index_build_browser"
            })) : createCommentVNode("", true),
            createBaseVNode("div", _hoisted_10$2, [
              response.value && evidenceTarget.value && (answerText.value || response.value.evidencePacket.evidence.length) ? (openBlock(), createBlock(PublishedResearchResult, {
                key: 0,
                answer: answerText.value,
                evidence: response.value.evidencePacket.evidence,
                "records-by-id": recordsById.value,
                "evidence-target": evidenceTarget.value,
                "evidence-label": unref(site).t("site.runtime.evidence"),
                "open-record-label": unref(site).t("site.runtime.view_record"),
                "on-open-record": openEvidenceRecord
              }, null, 8, ["answer", "evidence", "records-by-id", "evidence-target", "evidence-label", "open-record-label"])) : createCommentVNode("", true)
            ])
          ]),
          createBaseVNode("aside", {
            class: "stack research-evidence-pane",
            "aria-label": unref(site).t("site.runtime.research_tools")
          }, [
            createBaseVNode("section", {
              ref_key: "evidenceTarget",
              ref: evidenceTarget,
              class: "research-evidence-panel",
              "data-tour": "evidence",
              role: "region",
              "aria-label": unref(site).t("site.runtime.evidence")
            }, null, 8, _hoisted_12$2)
          ], 8, _hoisted_11$2)
        ]);
      };
    }
  });
  const PublishedResearchView = /* @__PURE__ */ _export_sfc(_sfc_main$4, [["__scopeId", "data-v-14d4b029"]]);
  const _hoisted_1$3 = { class: "stack" };
  const _hoisted_2$3 = {
    class: "search-surface",
    "aria-labelledby": "search-heading"
  };
  const _hoisted_3$3 = { class: "search-head" };
  const _hoisted_4$3 = { id: "search-heading" };
  const _hoisted_5$3 = ["aria-label"];
  const _hoisted_6$3 = {
    class: "search-row",
    "data-tour": "search"
  };
  const _hoisted_7$2 = { class: "search-toolbar" };
  const _hoisted_8$2 = { class: "search-mode-field" };
  const _hoisted_9$2 = { value: "keyword" };
  const _hoisted_10$1 = ["disabled"];
  const _hoisted_11$1 = ["disabled"];
  const _hoisted_12$1 = {
    class: "search-refine",
    "data-tour": "filters"
  };
  const _hoisted_13$1 = { class: "filters" };
  const _hoisted_14$1 = { class: "field" };
  const _hoisted_15$1 = { value: "" };
  const _hoisted_16$1 = ["value"];
  const _hoisted_17$1 = { class: "field" };
  const _hoisted_18$1 = { value: "" };
  const _hoisted_19$1 = ["value"];
  const _hoisted_20$1 = { class: "field" };
  const _hoisted_21$1 = { class: "field" };
  const _hoisted_22$1 = { class: "sr-only" };
  const _hoisted_23$1 = {
    key: 0,
    class: "results-heading"
  };
  const _hoisted_24$1 = { class: "meta" };
  const _hoisted_25$1 = {
    class: "search-results",
    "aria-live": "polite"
  };
  const _hoisted_26$1 = {
    key: 0,
    class: "empty"
  };
  const _hoisted_27 = { class: "result-head" };
  const _hoisted_28 = { class: "meta" };
  const _hoisted_29 = { class: "snippet" };
  const _hoisted_30 = { key: 0 };
  const _sfc_main$3 = /* @__PURE__ */ defineComponent({
    __name: "PublishedSearchView",
    setup(__props) {
      const site = usePublishedSite();
      const query = /* @__PURE__ */ ref("");
      const mode = /* @__PURE__ */ ref(
        site.capabilities.value?.publicationVectors?.available || site.capabilities.value?.localIndex?.complete ? "semantic" : "keyword"
      );
      const work = /* @__PURE__ */ ref(site.searchWork.value);
      site.searchWork.value = "";
      const field = /* @__PURE__ */ ref("");
      const filterValue = /* @__PURE__ */ ref("");
      const running = /* @__PURE__ */ ref(false);
      const status = /* @__PURE__ */ ref(
        site.t("site.runtime.search_prompt", {
          count: site.recordCount.value.toLocaleString(site.locale.value)
        })
      );
      const statusTone = /* @__PURE__ */ ref("");
      const results = /* @__PURE__ */ ref([]);
      const searchedQuery = /* @__PURE__ */ ref("");
      const methods = /* @__PURE__ */ ref({
        text: mode.value !== "semantic",
        vector: mode.value !== "keyword",
        llm: false
      });
      const localIndexVisible = computed(
        () => Boolean(site.capabilities.value?.localIndex) && !site.capabilities.value?.localIndex?.usesPublishedVectors
      );
      const resultCountText = computed(
        () => site.t("site.runtime.results_count", { count: results.value.length })
      );
      watch(mode, (value) => {
        methods.value = {
          text: value !== "semantic",
          vector: value !== "keyword",
          llm: false
        };
      });
      watch(
        () => Boolean(site.capabilities.value?.localIndex?.complete),
        (complete) => {
          if (complete) mode.value = "semantic";
          else if (!site.capabilities.value?.publicationVectors?.available && mode.value !== "keyword") {
            mode.value = "keyword";
          }
        }
      );
      function clearFilters() {
        work.value = "";
        field.value = "";
        filterValue.value = "";
      }
      async function runSearch() {
        if (!site.client.value) return;
        running.value = true;
        statusTone.value = "";
        status.value = mode.value === "keyword" ? site.t("site.runtime.activity_text_search") : mode.value === "semantic" ? site.t("site.runtime.activity_vector_search") : site.t("site.runtime.activity_hybrid_search");
        results.value = [];
        searchedQuery.value = "";
        const stopProgress = site.subscribeProgress((message) => {
          status.value = message;
        });
        try {
          const filters = {};
          if (work.value) filters.work = work.value;
          if (field.value && filterValue.value) filters[field.value] = filterValue.value;
          const response = await site.client.value.search({
            query: query.value,
            mode: mode.value,
            filters,
            limit: 50
          });
          methods.value = {
            text: response.modeUsed !== "semantic",
            vector: response.modeUsed !== "keyword",
            llm: false
          };
          const warning = site.warningText(response.warnings);
          statusTone.value = warning ? "warning" : "";
          status.value = warning ? site.t("site.runtime.results_with_warning", {
            count: response.results.length,
            warning
          }) : site.t("site.runtime.results_count", { count: response.results.length });
          results.value = response.results;
          searchedQuery.value = mode.value === "keyword" ? query.value : "";
        } catch (error) {
          statusTone.value = "error";
          status.value = site.t("site.runtime.search_failed", {
            error: error instanceof Error ? error.message : String(error)
          });
        } finally {
          stopProgress();
          running.value = false;
        }
      }
      function snippet(record) {
        return snippetText(String(record.text || ""), searchedQuery.value, site.locale.value);
      }
      function segments(record) {
        return highlightSegments(snippet(record), searchedQuery.value, site.locale.value);
      }
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("div", _hoisted_1$3, [
          createBaseVNode("section", _hoisted_2$3, [
            createBaseVNode("div", _hoisted_3$3, [
              createBaseVNode("h2", _hoisted_4$3, toDisplayString(unref(site).t("site.runtime.search")), 1),
              createBaseVNode("p", null, toDisplayString(unref(site).t("site.runtime.search_intro")), 1)
            ]),
            createBaseVNode("form", {
              class: "search-form",
              role: "search",
              "aria-label": unref(site).t("site.runtime.search"),
              onSubmit: withModifiers(runSearch, ["prevent"])
            }, [
              createBaseVNode("div", _hoisted_6$3, [
                createVNode(_sfc_main$g, {
                  modelValue: query.value,
                  "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => query.value = $event),
                  class: "control",
                  type: "search",
                  autocomplete: "off",
                  placeholder: unref(site).t("site.runtime.search_placeholder"),
                  "aria-label": unref(site).t("site.runtime.search_query_label")
                }, null, 8, ["modelValue", "placeholder", "aria-label"]),
                createVNode(UiButton, {
                  variant: "primary",
                  type: "submit",
                  label: unref(site).t("site.runtime.search"),
                  disabled: running.value
                }, null, 8, ["label", "disabled"])
              ]),
              createBaseVNode("div", _hoisted_7$2, [
                createBaseVNode("label", _hoisted_8$2, [
                  createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.search_mode")), 1),
                  createVNode(_sfc_main$m, {
                    modelValue: mode.value,
                    "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => mode.value = $event),
                    class: "control",
                    "aria-label": unref(site).t("site.runtime.search_mode")
                  }, {
                    default: withCtx(() => [
                      createBaseVNode("option", _hoisted_9$2, toDisplayString(unref(site).t("site.runtime.keyword")), 1),
                      createBaseVNode("option", {
                        value: "semantic",
                        disabled: !unref(site).capabilities.value?.provider?.embeddings
                      }, toDisplayString(unref(site).t("site.runtime.semantic")), 9, _hoisted_10$1),
                      createBaseVNode("option", {
                        value: "hybrid",
                        disabled: !unref(site).capabilities.value?.provider?.embeddings
                      }, toDisplayString(unref(site).t("site.runtime.hybrid")), 9, _hoisted_11$1)
                    ]),
                    _: 1
                  }, 8, ["modelValue", "aria-label"])
                ]),
                createVNode(_sfc_main$6, {
                  text: methods.value.text,
                  vector: methods.value.vector,
                  llm: methods.value.llm
                }, null, 8, ["text", "vector", "llm"])
              ]),
              createBaseVNode("details", _hoisted_12$1, [
                createBaseVNode("summary", null, toDisplayString(unref(site).t("site.runtime.refine_search")), 1),
                createBaseVNode("div", _hoisted_13$1, [
                  createBaseVNode("label", _hoisted_14$1, [
                    createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.work_filter")), 1),
                    createVNode(_sfc_main$m, {
                      modelValue: work.value,
                      "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => work.value = $event),
                      class: "control",
                      "aria-label": unref(site).t("site.runtime.work_filter")
                    }, {
                      default: withCtx(() => [
                        createBaseVNode("option", _hoisted_15$1, toDisplayString(unref(site).t("site.runtime.all_works")), 1),
                        (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).publication.works || [], (item) => {
                          return openBlock(), createElementBlock("option", {
                            key: item.work,
                            value: item.work
                          }, toDisplayString(item.work), 9, _hoisted_16$1);
                        }), 128))
                      ]),
                      _: 1
                    }, 8, ["modelValue", "aria-label"])
                  ]),
                  createBaseVNode("label", _hoisted_17$1, [
                    createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.field_filter")), 1),
                    createVNode(_sfc_main$m, {
                      modelValue: field.value,
                      "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => field.value = $event),
                      class: "control",
                      "aria-label": unref(site).t("site.runtime.field_filter")
                    }, {
                      default: withCtx(() => [
                        createBaseVNode("option", _hoisted_18$1, toDisplayString(unref(site).t("site.runtime.any_field")), 1),
                        (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).filterFields(), (key) => {
                          return openBlock(), createElementBlock("option", {
                            key,
                            value: key
                          }, toDisplayString(key.replaceAll("_", " ")), 9, _hoisted_19$1);
                        }), 128))
                      ]),
                      _: 1
                    }, 8, ["modelValue", "aria-label"])
                  ]),
                  createBaseVNode("label", _hoisted_20$1, [
                    createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.filter_value")), 1),
                    createVNode(_sfc_main$g, {
                      modelValue: filterValue.value,
                      "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => filterValue.value = $event),
                      class: "control",
                      placeholder: unref(site).t("site.runtime.filter_value"),
                      "aria-label": unref(site).t("site.runtime.filter_value")
                    }, null, 8, ["modelValue", "placeholder", "aria-label"])
                  ]),
                  createBaseVNode("div", _hoisted_21$1, [
                    createBaseVNode("span", _hoisted_22$1, toDisplayString(unref(site).t("site.runtime.clear_filters")), 1),
                    createVNode(UiButton, {
                      label: unref(site).t("site.runtime.clear_filters"),
                      onClick: clearFilters
                    }, null, 8, ["label"])
                  ])
                ])
              ])
            ], 40, _hoisted_5$3),
            createBaseVNode("div", {
              class: normalizeClass(["status", statusTone.value]),
              role: "status",
              "aria-live": "polite"
            }, toDisplayString(status.value), 3),
            localIndexVisible.value ? (openBlock(), createBlock(_sfc_main$f, {
              key: 0,
              "initial-build-label-key": "site.runtime.index_build_browser"
            })) : createCommentVNode("", true)
          ]),
          results.value.length || searchedQuery.value ? (openBlock(), createElementBlock("div", _hoisted_23$1, [
            createBaseVNode("h2", null, toDisplayString(unref(site).t("site.runtime.search_results")), 1),
            createBaseVNode("span", _hoisted_24$1, toDisplayString(resultCountText.value), 1)
          ])) : createCommentVNode("", true),
          createBaseVNode("div", _hoisted_25$1, [
            searchedQuery.value && !results.value.length ? (openBlock(), createElementBlock("div", _hoisted_26$1, toDisplayString(unref(site).t("site.runtime.no_results")), 1)) : createCommentVNode("", true),
            (openBlock(true), createElementBlock(Fragment, null, renderList(results.value, (item) => {
              return openBlock(), createElementBlock("article", {
                key: item.record.record_id,
                class: "result card"
              }, [
                createBaseVNode("div", _hoisted_27, [
                  createBaseVNode("div", null, [
                    createBaseVNode("strong", null, toDisplayString(item.record.work || item.record.record_id), 1),
                    createBaseVNode("div", _hoisted_28, toDisplayString(unref(site).client.value?.citations.format(item.record).plain), 1)
                  ])
                ]),
                createBaseVNode("div", _hoisted_29, [
                  (openBlock(true), createElementBlock(Fragment, null, renderList(segments(item.record), (segment, index) => {
                    return openBlock(), createElementBlock(Fragment, { key: index }, [
                      segment.highlighted ? (openBlock(), createElementBlock("mark", _hoisted_30, toDisplayString(segment.text), 1)) : (openBlock(), createElementBlock(Fragment, { key: 1 }, [
                        createTextVNode(toDisplayString(segment.text), 1)
                      ], 64))
                    ], 64);
                  }), 128))
                ]),
                createVNode(UiButton, {
                  label: unref(site).t("site.runtime.view_record"),
                  onClick: ($event) => unref(site).openRecord(item.record, searchedQuery.value)
                }, null, 8, ["label", "onClick"])
              ]);
            }), 128))
          ])
        ]);
      };
    }
  });
  const _hoisted_1$2 = {
    class: "tour-bar",
    "aria-hidden": "true"
  };
  const _hoisted_2$2 = {
    "aria-live": "polite",
    "aria-atomic": "true"
  };
  const _hoisted_3$2 = { class: "dialog-head" };
  const _hoisted_4$2 = { id: "tutorial-title" };
  const _hoisted_5$2 = { class: "tutorial-progress" };
  const _hoisted_6$2 = { class: "dialog-body" };
  const _hoisted_7$1 = {
    id: "tutorial-body",
    class: "tutorial-copy"
  };
  const _hoisted_8$1 = { class: "dialog-body muted tour-hint" };
  const _hoisted_9$1 = { class: "dialog-actions" };
  const _sfc_main$2 = /* @__PURE__ */ defineComponent({
    __name: "PublishedTutorial",
    props: {
      open: { type: Boolean }
    },
    emits: ["close"],
    setup(__props, { emit: __emit }) {
      const props = __props;
      const emit2 = __emit;
      const site = usePublishedSite();
      const steps = [
        { id: "welcome" },
        { id: "nav", target: "nav" },
        { id: "works", view: "works", target: "works" },
        { id: "search", view: "search", target: "search" },
        { id: "filters", view: "search", target: "filters" },
        { id: "methods", view: "search", target: "methods" },
        { id: "research", view: "research", target: "research" },
        { id: "provider", view: "providers", target: "provider" },
        { id: "evidence", view: "research", target: "evidence" },
        { id: "notes", view: "notes", target: "notes" },
        { id: "controls", target: "controls" },
        { id: "restart", target: "tutorial" }
      ];
      const dialog = /* @__PURE__ */ ref(null);
      const spot = /* @__PURE__ */ ref(null);
      const card = /* @__PURE__ */ ref(null);
      const index = /* @__PURE__ */ ref(0);
      const centered = /* @__PURE__ */ ref(true);
      const dockClass = /* @__PURE__ */ ref("");
      const currentTarget = /* @__PURE__ */ ref(null);
      const busy = /* @__PURE__ */ ref(false);
      let startView = "search";
      let priorActive = null;
      let outcome = "skipped";
      let queued = 0;
      const step = computed(() => steps[index.value]);
      const title = computed(() => site.t(`site.runtime.tutorial_${step.value.id}_title`));
      const body = computed(() => site.t(`site.runtime.tutorial_${step.value.id}_body`));
      const progress = computed(
        () => site.t("site.runtime.tutorial_progress", {
          current: index.value + 1,
          total: steps.length
        })
      );
      const fillWidth = computed(() => `${(index.value + 1) / steps.length * 100}%`);
      const nextLabel = computed(
        () => index.value === steps.length - 1 ? site.t("site.runtime.finish") : site.t("site.runtime.next")
      );
      function resetCardPosition() {
        if (!card.value) return;
        card.value.style.top = "";
        card.value.style.left = "";
      }
      function place() {
        const target = currentTarget.value;
        const targetRect = target?.getBoundingClientRect() || null;
        const shouldCenter = !targetRect || targetRect.width === 0 && targetRect.height === 0;
        centered.value = shouldCenter;
        dockClass.value = "";
        resetCardPosition();
        if (shouldCenter || !spot.value || !card.value || !targetRect) return;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const pad = 6;
        const edge = 8;
        const gap = 14;
        const box = {
          left: Math.max(targetRect.left - pad, 4),
          top: Math.max(targetRect.top - pad, 4),
          right: Math.min(targetRect.right + pad, viewportWidth - 4),
          bottom: Math.min(targetRect.bottom + pad, viewportHeight - 4)
        };
        Object.assign(spot.value.style, {
          left: `${box.left}px`,
          top: `${box.top}px`,
          width: `${Math.max(box.right - box.left, 0)}px`,
          height: `${Math.max(box.bottom - box.top, 0)}px`
        });
        const width = card.value.offsetWidth;
        const height = card.value.offsetHeight;
        const clampLeft = (value) => Math.min(Math.max(value, edge), Math.max(viewportWidth - width - edge, edge));
        const clampTop = (value) => Math.min(Math.max(value, edge), Math.max(viewportHeight - height - edge, edge));
        const put = (left, top) => {
          if (!card.value) return;
          card.value.style.left = `${clampLeft(left)}px`;
          card.value.style.top = `${clampTop(top)}px`;
        };
        const dock = () => {
          dockClass.value = box.bottom + edge + height > viewportHeight && box.top - edge >= height ? "tour-dock-top" : "tour-dock";
        };
        if (viewportWidth <= 760) dock();
        else if (viewportHeight - box.bottom - gap - edge >= height) put(box.left, box.bottom + gap);
        else if (box.top - gap - edge >= height) put(box.left, box.top - gap - height);
        else if (viewportWidth - box.right - gap - edge >= width) put(box.right + gap, box.top);
        else if (box.left - gap - edge >= width) put(box.left - gap - width, box.top);
        else dock();
      }
      function reveal() {
        const target = currentTarget.value;
        if (!target || target.closest("header.top") || !card.value) return;
        const rect = target.getBoundingClientRect();
        const usable = window.innerHeight - (window.innerWidth <= 760 ? card.value.offsetHeight + 24 : 0);
        if (rect.top < 72 || rect.bottom > usable) {
          if (window.innerWidth <= 760) window.scrollBy(0, rect.top - 16);
          else {
            target.scrollIntoView({
              block: rect.height > usable ? "start" : "center",
              inline: "nearest"
            });
          }
        }
      }
      function reposition() {
        if (queued) return;
        queued = window.requestAnimationFrame(() => {
          queued = 0;
          place();
        });
      }
      async function show(nextIndex) {
        if (busy.value || nextIndex < 0 || nextIndex >= steps.length) return;
        busy.value = true;
        try {
          index.value = nextIndex;
          const nextStep = steps[nextIndex];
          if (nextStep.view && nextStep.view !== site.view.value) {
            site.view.value = nextStep.view;
            await nextTick();
          }
          await nextTick();
          currentTarget.value = nextStep.target ? document.querySelector(`[data-tour="${nextStep.target}"]`) : null;
          place();
          reveal();
          place();
          await nextTick();
          card.value?.querySelector("button.ui-button.variant-primary")?.focus();
        } finally {
          busy.value = false;
        }
      }
      function move(delta) {
        if (busy.value) return;
        if (delta > 0 && index.value === steps.length - 1) {
          outcome = "done";
          dialog.value?.close();
          return;
        }
        void show(index.value + delta);
      }
      function skip() {
        outcome = "skipped";
        dialog.value?.close();
      }
      function onKeydown(event) {
        if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
        const rtl = document.documentElement.dir === "rtl";
        if (event.key === (rtl ? "ArrowLeft" : "ArrowRight")) {
          event.preventDefault();
          move(1);
        } else if (event.key === (rtl ? "ArrowRight" : "ArrowLeft")) {
          event.preventDefault();
          move(-1);
        }
      }
      function onCancel() {
        outcome = "skipped";
      }
      async function onClose() {
        window.removeEventListener("resize", reposition);
        window.removeEventListener("scroll", reposition, true);
        site.markTutorial(outcome);
        if (site.view.value !== startView) {
          site.view.value = startView;
          await nextTick();
        }
        emit2("close");
        if (priorActive?.dataset?.tour === "tutorial") {
          document.querySelector('[data-tour="tutorial"]')?.focus();
        }
      }
      async function openDialog() {
        if (!dialog.value || dialog.value.open) return;
        startView = site.view.value;
        priorActive = document.activeElement;
        outcome = "skipped";
        index.value = 0;
        dialog.value.showModal();
        window.addEventListener("resize", reposition);
        window.addEventListener("scroll", reposition, true);
        await show(0);
      }
      watch(
        () => props.open,
        async (open) => {
          await nextTick();
          if (open) await openDialog();
          else if (dialog.value?.open) dialog.value.close();
        }
      );
      onMounted(() => {
        if (props.open) void openDialog();
      });
      onBeforeUnmount(() => {
        if (queued) cancelAnimationFrame(queued);
        window.removeEventListener("resize", reposition);
        window.removeEventListener("scroll", reposition, true);
      });
      return (_ctx, _cache) => {
        return openBlock(), createBlock(Teleport, { to: "body" }, [
          createBaseVNode("dialog", {
            ref_key: "dialog",
            ref: dialog,
            class: normalizeClass(["tour", [centered.value ? "tour-centered" : "", dockClass.value]]),
            "aria-labelledby": "tutorial-title",
            "aria-describedby": "tutorial-body",
            onKeydown,
            onCancel,
            onClose
          }, [
            createBaseVNode("div", {
              ref_key: "spot",
              ref: spot,
              class: "tour-spot",
              "aria-hidden": "true"
            }, null, 512),
            createBaseVNode("div", {
              ref_key: "card",
              ref: card,
              class: "tour-card"
            }, [
              createBaseVNode("div", _hoisted_1$2, [
                createBaseVNode("span", {
                  style: normalizeStyle({ width: fillWidth.value })
                }, null, 4)
              ]),
              createBaseVNode("div", _hoisted_2$2, [
                createBaseVNode("div", _hoisted_3$2, [
                  createBaseVNode("h2", _hoisted_4$2, toDisplayString(title.value), 1),
                  createBaseVNode("div", _hoisted_5$2, toDisplayString(progress.value), 1)
                ]),
                createBaseVNode("div", _hoisted_6$2, [
                  createBaseVNode("p", _hoisted_7$1, toDisplayString(body.value), 1)
                ])
              ]),
              createBaseVNode("div", _hoisted_8$1, toDisplayString(unref(site).t("site.runtime.tutorial_hint")), 1),
              createBaseVNode("div", _hoisted_9$1, [
                createVNode(UiButton, {
                  label: unref(site).t("site.runtime.skip_tutorial"),
                  onClick: skip
                }, null, 8, ["label"]),
                createVNode(UiButton, {
                  label: unref(site).t("site.runtime.previous"),
                  disabled: index.value === 0,
                  onClick: _cache[0] || (_cache[0] = ($event) => move(-1))
                }, null, 8, ["label", "disabled"]),
                createVNode(UiButton, {
                  variant: "primary",
                  label: nextLabel.value,
                  onClick: _cache[1] || (_cache[1] = ($event) => move(1))
                }, null, 8, ["label"])
              ])
            ], 512)
          ], 34)
        ]);
      };
    }
  });
  const _hoisted_1$1 = ["aria-label"];
  const _hoisted_2$1 = { class: "work-card-copy" };
  const _hoisted_3$1 = { class: "work-title" };
  const _hoisted_4$1 = { class: "meta" };
  const _hoisted_5$1 = { class: "count" };
  const _hoisted_6$1 = { class: "muted" };
  const _sfc_main$1 = /* @__PURE__ */ defineComponent({
    __name: "PublishedWorksView",
    setup(__props) {
      const site = usePublishedSite();
      function openWork(work) {
        site.searchWork.value = work;
        site.view.value = "search";
      }
      return (_ctx, _cache) => {
        return openBlock(), createElementBlock("section", {
          class: "grid",
          "data-tour": "works",
          "aria-label": unref(site).t("site.runtime.works")
        }, [
          (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).publication.works || [], (item) => {
            return openBlock(), createBlock(UiButton, {
              key: item.work,
              "button-class": "work-button card",
              onClick: ($event) => openWork(item.work)
            }, {
              default: withCtx(() => [
                createBaseVNode("span", _hoisted_2$1, [
                  createBaseVNode("span", _hoisted_3$1, toDisplayString(item.work), 1),
                  createBaseVNode("span", _hoisted_4$1, toDisplayString((item.authors || []).join(", ")), 1),
                  createBaseVNode("span", _hoisted_5$1, toDisplayString(Number(item.record_count || 0).toLocaleString(unref(site).locale.value)), 1),
                  createBaseVNode("span", _hoisted_6$1, toDisplayString(unref(site).t("site.runtime.records")), 1)
                ])
              ]),
              _: 2
            }, 1032, ["onClick"]);
          }), 128))
        ], 8, _hoisted_1$1);
      };
    }
  });
  const PublishedWorksView = /* @__PURE__ */ _export_sfc(_sfc_main$1, [["__scopeId", "data-v-c054ebca"]]);
  const _hoisted_1 = {
    key: 0,
    class: "main"
  };
  const _hoisted_2 = {
    class: "panel status error",
    role: "alert"
  };
  const _hoisted_3 = {
    key: 1,
    class: "main",
    role: "status",
    "aria-live": "polite"
  };
  const _hoisted_4 = {
    key: 2,
    class: "shell"
  };
  const _hoisted_5 = { class: "top" };
  const _hoisted_6 = { class: "top-inner" };
  const _hoisted_7 = { class: "brand" };
  const _hoisted_8 = ["aria-label"];
  const _hoisted_9 = ["aria-current"];
  const _hoisted_10 = ["aria-current"];
  const _hoisted_11 = ["aria-current"];
  const _hoisted_12 = ["aria-current"];
  const _hoisted_13 = ["aria-current"];
  const _hoisted_14 = ["aria-label"];
  const _hoisted_15 = { class: "compact-field" };
  const _hoisted_16 = ["value"];
  const _hoisted_17 = { class: "compact-field" };
  const _hoisted_18 = { value: "light" };
  const _hoisted_19 = { value: "dark" };
  const _hoisted_20 = { class: "toggle" };
  const _hoisted_21 = ["checked"];
  const _hoisted_22 = {
    id: "site-main",
    class: "main",
    tabindex: "-1"
  };
  const _hoisted_23 = {
    class: "hero",
    "aria-labelledby": "site-title"
  };
  const _hoisted_24 = { id: "site-title" };
  const _hoisted_25 = { key: 0 };
  const _hoisted_26 = { class: "footer" };
  const _sfc_main = /* @__PURE__ */ defineComponent({
    __name: "PublishedSiteApp",
    setup(__props) {
      const site = createPublishedSiteContext();
      providePublishedSiteContext(site);
      const ready = /* @__PURE__ */ ref(false);
      const error = /* @__PURE__ */ ref("");
      const tutorialOpen = /* @__PURE__ */ ref(false);
      const publicationSummary = computed(
        () => site.t("site.runtime.publication_summary", {
          works: (site.publication.works || []).length,
          records: site.recordCount.value,
          date: site.formatDate(site.publication.created_at)
        })
      );
      async function initialize() {
        try {
          await site.initialize();
          ready.value = true;
          await nextTick();
          if (!site.tutorialSeen.value) tutorialOpen.value = true;
        } catch (caught) {
          error.value = caught instanceof Error ? caught.message : String(caught);
        }
      }
      function setView(view) {
        site.view.value = view;
      }
      function focusMain() {
        window.setTimeout(() => document.getElementById("site-main")?.focus(), 0);
      }
      async function changeLocale(event) {
        await site.setLocaleAndRebuild(event.target.value);
      }
      onMounted(initialize);
      return (_ctx, _cache) => {
        return error.value ? (openBlock(), createElementBlock("div", _hoisted_1, [
          createBaseVNode("div", _hoisted_2, toDisplayString(error.value), 1)
        ])) : !ready.value ? (openBlock(), createElementBlock("div", _hoisted_3, toDisplayString(unref(site).t("site.runtime.loading_site")), 1)) : (openBlock(), createElementBlock("div", _hoisted_4, [
          createBaseVNode("a", {
            class: "skip-link",
            href: "#site-main",
            onClick: focusMain
          }, toDisplayString(unref(site).t("site.runtime.skip_to_content")), 1),
          createBaseVNode("header", _hoisted_5, [
            createBaseVNode("div", _hoisted_6, [
              createBaseVNode("div", _hoisted_7, [
                createBaseVNode("strong", null, toDisplayString(unref(site).publication.title || unref(site).t("site.runtime.site_title")), 1),
                createBaseVNode("small", null, toDisplayString(unref(site).t("site.runtime.powered_by")), 1)
              ]),
              createBaseVNode("nav", {
                "data-tour": "nav",
                "aria-label": unref(site).t("site.runtime.navigation")
              }, [
                createBaseVNode("button", {
                  type: "button",
                  "aria-current": unref(site).view.value === "search" ? "page" : void 0,
                  onClick: _cache[0] || (_cache[0] = ($event) => setView("search"))
                }, toDisplayString(unref(site).t("site.runtime.search")), 9, _hoisted_9),
                createBaseVNode("button", {
                  type: "button",
                  "aria-current": unref(site).view.value === "works" ? "page" : void 0,
                  onClick: _cache[1] || (_cache[1] = ($event) => setView("works"))
                }, toDisplayString(unref(site).t("site.runtime.works")), 9, _hoisted_10),
                createBaseVNode("button", {
                  type: "button",
                  "aria-current": unref(site).view.value === "research" ? "page" : void 0,
                  onClick: _cache[2] || (_cache[2] = ($event) => setView("research"))
                }, toDisplayString(unref(site).t("site.runtime.research")), 9, _hoisted_11),
                createBaseVNode("button", {
                  type: "button",
                  "aria-current": unref(site).view.value === "providers" ? "page" : void 0,
                  onClick: _cache[3] || (_cache[3] = ($event) => setView("providers"))
                }, toDisplayString(unref(site).t("site.runtime.providers")), 9, _hoisted_12),
                createBaseVNode("button", {
                  type: "button",
                  "aria-current": unref(site).view.value === "notes" ? "page" : void 0,
                  onClick: _cache[4] || (_cache[4] = ($event) => setView("notes"))
                }, toDisplayString(unref(site).t("site.runtime.annotations")), 9, _hoisted_13)
              ], 8, _hoisted_8),
              createBaseVNode("div", {
                class: "header-controls",
                "data-tour": "controls",
                role: "group",
                "aria-label": unref(site).t("site.runtime.display_controls")
              }, [
                createBaseVNode("label", _hoisted_15, [
                  createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.language")), 1),
                  createVNode(_sfc_main$m, {
                    "model-value": unref(site).locale.value,
                    class: "control",
                    "aria-label": unref(site).t("site.runtime.language"),
                    onChange: changeLocale
                  }, {
                    default: withCtx(() => [
                      (openBlock(true), createElementBlock(Fragment, null, renderList(unref(site).availableLocales, (code) => {
                        return openBlock(), createElementBlock("option", {
                          key: code,
                          value: code
                        }, toDisplayString(unref(site).languageLabel(code)), 9, _hoisted_16);
                      }), 128))
                    ]),
                    _: 1
                  }, 8, ["model-value", "aria-label"])
                ]),
                createBaseVNode("label", _hoisted_17, [
                  createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.theme")), 1),
                  createVNode(_sfc_main$m, {
                    "model-value": unref(site).theme.value,
                    class: "control",
                    "aria-label": unref(site).t("site.runtime.theme"),
                    onChange: _cache[5] || (_cache[5] = ($event) => unref(site).setTheme($event.target.value))
                  }, {
                    default: withCtx(() => [
                      createBaseVNode("option", _hoisted_18, toDisplayString(unref(site).t("site.runtime.theme_light")), 1),
                      createBaseVNode("option", _hoisted_19, toDisplayString(unref(site).t("site.runtime.theme_dark")), 1)
                    ]),
                    _: 1
                  }, 8, ["model-value", "aria-label"])
                ]),
                createBaseVNode("label", _hoisted_20, [
                  createBaseVNode("input", {
                    type: "checkbox",
                    checked: unref(site).highContrast.value,
                    onChange: _cache[6] || (_cache[6] = ($event) => unref(site).setHighContrast($event.target.checked))
                  }, null, 40, _hoisted_21),
                  createBaseVNode("span", null, toDisplayString(unref(site).t("site.runtime.high_contrast")), 1)
                ]),
                createBaseVNode("button", {
                  type: "button",
                  "data-tour": "tutorial",
                  onClick: _cache[7] || (_cache[7] = ($event) => tutorialOpen.value = true)
                }, toDisplayString(unref(site).t("site.runtime.tutorial")), 1)
              ], 8, _hoisted_14)
            ])
          ]),
          createBaseVNode("main", _hoisted_22, [
            createBaseVNode("section", _hoisted_23, [
              createBaseVNode("h1", _hoisted_24, toDisplayString(unref(site).publication.title || unref(site).t("site.runtime.site_title")), 1),
              unref(site).publication.description ? (openBlock(), createElementBlock("p", _hoisted_25, toDisplayString(unref(site).publication.description), 1)) : createCommentVNode("", true)
            ]),
            unref(site).view.value === "search" ? (openBlock(), createBlock(_sfc_main$3, { key: 0 })) : unref(site).view.value === "works" ? (openBlock(), createBlock(PublishedWorksView, { key: 1 })) : unref(site).view.value === "research" ? (openBlock(), createBlock(PublishedResearchView, { key: 2 })) : unref(site).view.value === "providers" ? (openBlock(), createBlock(_sfc_main$9, { key: 3 })) : unref(site).view.value === "notes" ? (openBlock(), createBlock(_sfc_main$i, { key: 4 })) : createCommentVNode("", true),
            createBaseVNode("footer", _hoisted_26, toDisplayString(publicationSummary.value), 1)
          ]),
          createVNode(PublishedRecordDialog),
          createVNode(_sfc_main$2, {
            open: tutorialOpen.value,
            onClose: _cache[8] || (_cache[8] = ($event) => tutorialOpen.value = false)
          }, null, 8, ["open"])
        ]));
      };
    }
  });
  const root = document.getElementById("app");
  if (root) {
    root.removeAttribute("role");
    root.removeAttribute("aria-live");
    createApp(_sfc_main).mount(root);
    globalThis.__DERRIDAI_SITE_VUE__ = true;
  }
})();
