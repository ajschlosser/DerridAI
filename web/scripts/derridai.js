const API_BASE = "/api/v0.1.0";
const POLL_INTERVAL_MS = 2000;

const form = document.getElementById("query-form");
const promptInput = document.getElementById("prompt-input");
const submitButton = document.getElementById("submit-button");
const loadingSpinner = document.getElementById("loading-spinner");
const statusMessage = document.getElementById("status-message");
const errorMessage = document.getElementById("error-message");
const resultCards = document.getElementById("result-cards");

let pollTimer = null;

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
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

function renderResponse(response, prompt) {
  const card = document.createElement("article");
  card.className = "result-card";
  card.tabIndex = -1;

  const question = document.createElement("p");
  question.className = "result-card__question";
  question.textContent = `Question: ${prompt}`;

  const content = document.createElement("div");
  content.className = "result-card__content";
  const lines = String(response).trim().split(/\n{2,}/);
  let list = null;

  for (const line of lines) {
    const trimmedLine = line.trim();
    const heading = trimmedLine.match(/^#{1,3}\s+(.+)$/);
    const orderedItem = trimmedLine.match(/^\d+\.\s+(.+)$/);
    const unorderedItem = trimmedLine.match(/^[-*]\s+(.+)$/);

    if (heading) {
      list = null;
      const title = document.createElement("h3");
      appendFormattedText(title, heading[1]);
      content.append(title);
    } else if (orderedItem || unorderedItem) {
      const tagName = orderedItem ? "ol" : "ul";
      if (!list || list.tagName.toLowerCase() !== tagName) {
        list = document.createElement(tagName);
        content.append(list);
      }
      const item = document.createElement("li");
      appendFormattedText(item, (orderedItem || unorderedItem)[1]);
      list.append(item);
    } else {
      list = null;
      const paragraph = document.createElement("p");
      appendFormattedText(paragraph, trimmedLine.replace(/\n/g, " "));
      content.append(paragraph);
    }
  }

  card.append(question, content);
  resultCards.prepend(card);
  card.focus();
}

async function pollJobStatus(jobId) {
  try {
    const response = await fetch(`${API_BASE}/query/${jobId}`);
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status}`);
    }
    const job = await response.json();
    statusMessage.textContent = `Status: ${job.status}`;

    if (job.status === "completed") {
      stopPolling();
      setBusy(false);
      renderResponse(job.result.content.response, promptInput.value.trim());
      statusMessage.textContent = "Status: completed";
    }
  } catch (err) {
    stopPolling();
    setBusy(false);
    showError(`Error: ${err.message}`);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  stopPolling();

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
    statusMessage.textContent = "Status: [pending] Contacting DerridAI...";
    pollTimer = setInterval(() => pollJobStatus(job_id), POLL_INTERVAL_MS);
  } catch (err) {
    setBusy(false);
    showError(`Error: ${err.message}`);
  }
});
