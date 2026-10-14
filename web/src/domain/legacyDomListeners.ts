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

// Document-level listeners the legacy runtime used to register at module scope. The tooltip and file-drop listeners
// register when this module loads (the runtime imports it); metadata-search delegation is wired from bootstrap.
import { importFiles } from "./sharedFileLifecycle";
import { isResearcher } from "./sharedSession";
import { searchByMetadata } from "./workspaceActions";

let chartTooltip: HTMLDivElement | null = null;
function ensureChartTooltip() {
  if (chartTooltip?.isConnected) return chartTooltip;
  chartTooltip = document.createElement("div");
  chartTooltip.className = "chart-hover-tooltip";
  document.body.appendChild(chartTooltip);
  return chartTooltip;
}
document.addEventListener("pointermove", (event) => {
  const target = (event.target as Element | null)?.closest?.<HTMLElement>("[data-chart-tip]");
  if (!target) {
    if (chartTooltip) chartTooltip.classList.remove("show");
    return;
  }
  const tip = ensureChartTooltip();
  tip.textContent = target.dataset.chartTip || "";
  tip.style.left = `${Math.min(window.innerWidth - 280, event.clientX + 14)}px`;
  tip.style.top = `${Math.max(8, event.clientY + 14)}px`;
  tip.classList.add("show");
});

window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => {
  if (e.dataTransfer?.files?.length) {
    e.preventDefault();
    if (!isResearcher())
      importFiles(
        [...e.dataTransfer.files].filter((f) => /\.(jsonl|ndjson|json|zst)$/i.test(f.name)),
      );
  }
});

let metadataSearchDelegationWired = false;
export function wireMetadataSearchDelegation() {
  if (metadataSearchDelegationWired) return;
  metadataSearchDelegationWired = true;
  document.addEventListener(
    "click",
    (event) => {
      const button =
        event.target instanceof Element
          ? event.target.closest<HTMLElement>("[data-meta-search-field][data-meta-search-value]")
          : null;
      if (!button) return;
      if (button.closest("#main")) {
        event.preventDefault();
        event.stopPropagation();
        searchByMetadata(
          button.dataset.metaSearchField as string,
          button.dataset.metaSearchValue as string,
          {
            contains: button.dataset.metaSearchContains === "true",
          },
        );
      }
    },
    true,
  );
}
