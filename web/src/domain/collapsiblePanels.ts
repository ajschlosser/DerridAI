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

import { state } from "./sharedUrlState";
import { persistLayoutPreferences } from "./sharedWorkspaceStorage";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

// Adds collapse toggles to the cards of a rendered view and remembers which panels the user collapsed. Views call
// this after each refresh; it only touches elements it has not already prepared.
function collapseKeyFor(element: Any, index: number) {
  const heading =
    element
      .querySelector(".cardhead b,.cardhead h2,.section-title-row h3,.dash-chart-title")
      ?.textContent?.trim() ||
    element.getAttribute("aria-label") ||
    element.className ||
    element.tagName;
  return `${state.view}::${heading}::${index}`;
}
export function enhanceCollapsibles(root: ParentNode | null = document.querySelector("#main")) {
  if (!root) return;
  const targets: Any[] = [
    ...root.querySelectorAll(
      ".card:not(.work):not(.faq-card),.card-inset,.dash-chart,.provider-profile-card,.rag-live-job",
    ),
  ];
  targets.forEach((element: Any, index: number) => {
    if (
      element.dataset.collapsibleReady === "1" ||
      element.closest("dialog") ||
      element.matches("[data-no-collapse=true]") ||
      element.closest("[data-no-collapse=true]")
    )
      return;
    const host =
      element.querySelector(":scope > .cardhead") ||
      element.querySelector(":scope > .dash-chart-head") ||
      element.querySelector(":scope > .provider-profile-card-head") ||
      element.querySelector(":scope > .rag-live-job-head") ||
      element.querySelector(":scope > .section-title-row");
    if (!host) return;
    const fullHeight = Math.max(element.scrollHeight, element.getBoundingClientRect().height);
    const headerHeight = Math.max(30, host.getBoundingClientRect().height || 30);
    if (fullHeight <= headerHeight * 2) {
      element.dataset.collapsibleReady = "skip";
      return;
    }
    element.dataset.collapsibleReady = "1";
    const key = collapseKeyFor(element, index);
    element.dataset.collapseKey = key;
    const collapsed = Boolean(state.collapsedPanels?.[key]);
    element.classList.toggle("ui-collapsed", collapsed);
    const compactTitle = document.createElement("span");
    compactTitle.className = "ui-collapse-title";
    compactTitle.textContent =
      element
        .querySelector(
          ":scope > .cardhead b,:scope > .dash-chart-head .dash-chart-title,:scope > .section-title-row h3,:scope > .rag-live-job-head b",
        )
        ?.textContent?.trim() ||
      element.querySelector(":scope > .provider-profile-card-head [data-profile-field='name']")
        ?.value ||
      element.querySelector("h1,h2,h3,h4,b")?.textContent?.trim() ||
      "Section";
    host.appendChild(compactTitle);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ui-collapse-toggle";
    button.title = collapsed ? "Expand" : "Collapse";
    button.setAttribute("aria-label", button.title);
    button.textContent = collapsed ? "＋" : "−";
    button.onclick = (e: Event) => {
      e.stopPropagation();
      const next = !element.classList.contains("ui-collapsed");
      element.classList.toggle("ui-collapsed", next);
      button.textContent = next ? "＋" : "−";
      button.title = next ? "Expand" : "Collapse";
      state.collapsedPanels[key] = next;
      persistLayoutPreferences();
    };
    host.appendChild(button);
  });
}
