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

// Side-effect registrations for the legacy runtime: importing this module loads the shared modules in the order the
// app depends on (the Step 3b gotcha in the retirement plan), registers the jobs/dock/panel hooks and starts the PDF
// worker. It exports nothing; the app-facing functions are in domain/appBootstrap.ts.
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import PdfWorker from "pdfjs-dist/legacy/build/pdf.worker.mjs?worker";
import "diff";
import "../domain/operationsDock";
import "./operationsPanelHost";
import "../domain/operationsPanel";
import "../domain/recordValues";
import "../domain/urlState";
import "../domain/recordTableHelpers";
import "../domain/recordQuery";
import "../domain/researchPayloads";
import "../domain/citations";
import "../domain/recordsFiles";
import "../domain/legacyCompat.js";
import "../domain/runtimeConstants";
import "../domain/reviewPresentation";
import "../domain/workMetadata";
import "../domain/numberFormatting";
import "../domain/researcherInputFilter";
import "../domain/tabScrollPreservation";
import "../domain/searchFilterSchema";
import "../domain/recordPayloads";
import "../domain/recordFormatting";
import "../domain/legacyApi";
import "../domain/pastedRecord";
import "../domain/providerRequest";
import "../domain/disabledControls";
import "../domain/sharedRecordScopes";
import "../domain/recordHistory";
import "../domain/dashboardCharts";
import "../domain/sharedDbPresence";
import "../domain/storeAvailability";
import "../domain/operationHooks";
import "../domain/operationProgressHooks";
import "../domain/storeExport";
import "../domain/sharedSearchSupport";
import "../domain/sharedRecordHelpers";
import "../domain/sharedPdfLinking";
import "../domain/sharedRecordWorkspace";
import "../domain/sharedRecordPresenters";
import "../domain/sharedProviderProfiles";
import "../domain/sharedSearchWorkspace";
import "../domain/tableColumns";
import "../domain/sharedRecordsWorkspace";
import "../domain/legacyDomListeners";
import "../domain/legacyClickDelegation";
import "../domain/listPaging";
import "../domain/sharedWorksWorkspace";
import "../domain/sharedWorkDialogs";
import "../domain/sharedOperationPresenters";
import "../domain/storeWorks";
import "../domain/jobsWorkspace";
import "../domain/jobsActions";
import "../domain/researchActions";
import "../domain/sharedVectorCollections";
import "../domain/vectorStoreActions";
import "../domain/touchupActions";
import "../domain/sharedTouchupWorkflow";
import "../domain/operationsPanelHooks";
import "../domain/sharedDashboardData";
import "../domain/sharedPdfExplorerRenderer";
import "../domain/pdfPageLlmActions";
import "../domain/ragGradeHtml";
import "../domain/jobDialogs";
import "../domain/workDialogs";
import "../domain/operationDock";
import "../domain/clipboardCopy";
import "../domain/sharedNavigation";
import "../domain/sharedUrlState";
import "../domain/navigation";
import "../domain/sharedWorkspaceStorage";
import "../domain/sharedRecordEditing";
import "../domain/operationsPanelBridge";
import "../domain/fileDerivedState";
import "../domain/sharedFileLifecycle";
import "../domain/sharedWorkspacePersistence";
import "../domain/sharedAppLifecycle";
import "../domain/sharedCompareLibrary";
import "../domain/recordOptionLabel";
import "../domain/sharedStoreRecords";
import "../domain/researchWorkspace";
import "../domain/sharedAnnotations";
import "../state/jobsState";
import "../domain/corpusCache";
import "../domain/sharedUrlState";
import "./jobsUiComposition.js";
import "../domain/sharedStores";
import "../domain/sharedSession";
import "../domain/databaseCreationRequest";
import "../domain/sharedAppearance";
import "../domain/relativeTimeLabel";

pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker();
