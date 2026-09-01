const API_BASE = "/api/v0.1.0";
const POLL_INTERVAL_MS = 2000;
const RESULTS_STORAGE_KEY = "derridai.results";
const JOBS_STORAGE_KEY = "derridai.active-jobs";

const form = document.getElementById("query-form");
const promptInput = document.getElementById("prompt-input");
const submitButton = document.getElementById("submit-button");
const loadingSpinner = document.getElementById("loading-spinner");
const statusMessage = document.getElementById("status-message");
const errorMessage = document.getElementById("error-message");
const resultsSection = document.getElementById("results-section");
const resultsFilterInput = document.getElementById("results-filter-input");
const clearHistoryButton = document.getElementById("clear-history-button");
const resultCards = document.getElementById("result-cards");

const pollTimers = new Map();
let activeJobs = [];

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function load(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return value ?? fallback;
  } catch {
    return fallback;
  }
}

function stopPolling(jobId) {
  const timer = pollTimers.get(jobId);
  if (timer !== undefined) {
    clearInterval(timer);
    pollTimers.delete(jobId);
  }
}

function saveActiveJobs() {
  save(JOBS_STORAGE_KEY, activeJobs);
}

function removeActiveJob(jobId) {
  activeJobs = activeJobs.filter((job) => job.jobId !== jobId);
  saveActiveJobs();
  stopPolling(jobId);
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy;
  form.setAttribute("aria-busy", String(isBusy));
  loadingSpinner.hidden = !isBusy;
}

function showError(message) {
  errorMessage.textContent = message;
}

function appendFormattedText(container, text) {
  const fragments = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);

  for (const fragment of fragments) {
    if (fragment.startsWith("**") && fragment.endsWith("**")) {
      const strong = document.createElement("strong");
      strong.textContent = fragment.slice(2, -2);
      container.append(strong);
    } else if (fragment.startsWith("*") && fragment.endsWith("*")) {
      const emphasis = document.createElement("em");
      emphasis.textContent = fragment.slice(1, -1);
      container.append(emphasis);
    } else {
      container.append(document.createTextNode(fragment));
    }
  }
}

function appendResponseContent(container, response) {
  const lines = String(response).trim().split(/\n{2,}/);
  let list = null;

  for (const line of lines) {
    const trimmedLine = line.trim();
    const heading = trimmedLine.match(/^#{1,3}\s+(.+)$/);
    const orderedItems = [...trimmedLine.matchAll(/^(\d+)\.\s+(.+)$/gm)];
    const unorderedItem = trimmedLine.match(/^[-*]\s+(.+)$/);

    if (heading) {
      list = null;
      const title = document.createElement("h3");
      appendFormattedText(title, heading[1]);
      container.append(title);
    } else if (orderedItems.length || unorderedItem) {
      const tagName = orderedItems.length ? "ol" : "ul";
      if (!list || list.tagName.toLowerCase() !== tagName) {
        list = document.createElement(tagName);
        container.append(list);
      }
      const items = orderedItems.length ? orderedItems : [[unorderedItem[1]]];
      for (const itemMatch of items) {
        const item = document.createElement("li");
        appendFormattedText(item, itemMatch.at(-1));
        list.append(item);
      }
    } else {
      list = null;
      const paragraph = document.createElement("p");
      appendFormattedText(paragraph, trimmedLine.replace(/\n/g, " "));
      container.append(paragraph);
    }
  }
}

function createMetadataDetails(metadata) {
  const entries = Object.entries(metadata || {}).filter(
    ([key, value]) => (
      key !== "response"
      && !key.includes("record")
      && value !== null
      && value !== ""
      && !(Array.isArray(value) && value.length === 0)
    ),
  );
  if (!entries.length) return null;

  const details = document.createElement("details");
  details.className = "result-card__details";
  const summary = document.createElement("summary");
  summary.textContent = "Query details";
  const list = document.createElement("dl");
  list.className = "metadata-list";

  for (const [key, value] of entries) {
    const term = document.createElement("dt");
    term.textContent = key.replaceAll("_", " ");
    const description = document.createElement("dd");
    description.textContent = Array.isArray(value) ? value.join(", ") : String(value);
    list.append(term, description);
  }
  details.append(summary, list);
  return details;
}

function renderResponse(response, prompt, metadata = {}, focus = false) {
  const card = document.createElement("article");
  card.className = "result-card";
  card.tabIndex = -1;

  const answerDetails = document.createElement("details");
  answerDetails.open = true;
  const summary = document.createElement("summary");
  summary.className = "result-card__summary";
  const question = document.createElement("p");
  question.className = "result-card__question";
  question.textContent = `Question: ${prompt}`;
  summary.append(question);

  const body = document.createElement("div");
  body.className = "result-card__body";
  const [answer, citations = ""] = String(response).split(/\n{2,}\*\*Works Cited\*\*\s*/i);
  const content = document.createElement("div");
  content.className = "result-card__content";
  appendResponseContent(content, answer);
  body.append(content);

  if (citations.trim()) {
    const worksCited = document.createElement("details");
    worksCited.className = "result-card__details works-cited";
    const worksSummary = document.createElement("summary");
    worksSummary.textContent = "Works cited";
    const worksList = document.createElement("ol");
    worksList.className = "works-cited__list";
    for (const citation of citations.matchAll(/^\d+\.\s+(.+)$/gm)) {
      const item = document.createElement("li");
      appendFormattedText(item, citation[1]);
      worksList.append(item);
    }
    worksCited.append(worksSummary, worksList);
    body.append(worksCited);
  }

  const metadataDetails = createMetadataDetails(metadata);
  if (metadataDetails) body.append(metadataDetails);
  answerDetails.append(summary, body);
  card.append(answerDetails);
  resultCards.prepend(card);
  if (focus) card.focus();
}

function saveResult(prompt, response, metadata) {
  const results = load(RESULTS_STORAGE_KEY, []);
  results.unshift({ prompt, response, metadata, completedAt: new Date().toISOString() });
  save(RESULTS_STORAGE_KEY, results.slice(0, 30));
}

function renderSavedResults(focusLatest = false) {
  const filter = resultsFilterInput.value.trim().toLocaleLowerCase();
  const results = load(RESULTS_STORAGE_KEY, []);
  const filteredResults = results.filter((result) => (
    `${result.prompt}\n${result.response}`.toLocaleLowerCase().includes(filter)
  ));

  resultCards.innerHTML = ""; // Clear all existing children for clean redraw\n  for (const result of [...filteredResults].reverse()) {\n    renderResponse(result.response, result.prompt, result.metadata);\n  }
  for (const result of filteredResults.reverse()) {
    renderResponse(result.response, result.prompt, result.metadata);
  }
  resultsSection.hidden = filteredResults.length === 0;

  if (focusLatest && filteredResults.length) {
    resultCards.firstElementChild.focus();
  }
}

function startPolling(job) {
  if (pollTimers.has(job.jobId)) return;
  pollJobStatus(job);
  pollTimers.set(job.jobId, setInterval(() => pollJobStatus(job), POLL_INTERVAL_MS));
}

async function pollJobStatus(job) {
  try {
    const response = await fetch(`${API_BASE}/query/${job.jobId}`);
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status}`);
    }
    const jobStatus = await response.json();
    statusMessage.textContent = `Status: ${jobStatus.status}`;

    if (jobStatus.status === "completed") {
      removeActiveJob(job.jobId);
      if (activeJobs.length === 0) setBusy(false);
      const responseText = jobStatus.result?.content?.response;
      if (typeof responseText !== "string") throw new Error("Completed job did not include a response.");
      saveResult(job.prompt, responseText, jobStatus.result.content);
      renderSavedResults(true);
      statusMessage.textContent = "Status: completed";
    }
  } catch (err) {
    removeActiveJob(job.jobId);
    if (activeJobs.length === 0) setBusy(false);
    showError(`Error: ${err.message}`);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const prompt = promptInput.value.trim();
  if (!prompt) return;

  setBusy(true);
  showError("");
  statusMessage.textContent = "Submitting...";

  try {
    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    if (!response.ok) {
      throw new Error(`Submit failed: ${response.status}`);
    }
    const { job_id } = await response.json();
    const job = { jobId: job_id, prompt };
    activeJobs.push(job);
    saveActiveJobs();
    statusMessage.textContent = "Status: [pending] Contacting DerridAI...";
    startPolling(job);
  } catch (err) {
    if (activeJobs.length === 0) setBusy(false);
    showError(`Error: ${err.message}`);
  }
});


resultsFilterInput.addEventListener("input", () => {
  // Debounce the update by clearing any existing timer and setting a new one.
  clearTimeout(resultsFilterInput.debounceTimer);
  resultsFilterInput.debounceTimer = setTimeout(() => renderSavedResults(), 200);
});

// Initial call to render the results
renderSavedResults();

activeJobs = load(JOBS_STORAGE_KEY, []).filter(
  (job) => typeof job?.jobId === "string" && typeof job?.prompt === "string",
);
if (activeJobs.length) {
  setBusy(true);
  statusMessage.textContent = "Status: resuming saved queries...";
  activeJobs.forEach(startPolling);
}
