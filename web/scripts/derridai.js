const API_BASE = "/api/v0.1.0";
const POLL_INTERVAL_MS = 2000;

const form = document.getElementById("query-form");
const promptInput = document.getElementById("prompt-input");
const submitButton = document.getElementById("submit-button");
const loadingSpinner = document.getElementById("loading-spinner");
const statusMessage = document.getElementById("status-message");
const errorMessage = document.getElementById("error-message");
const resultOutput = document.getElementById("result-output");

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

async function pollJobStatus(jobId) {
  try {
    const response = await fetch(`${API_BASE}/query/${jobId}`);
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status}`);
    }
    const job = await response.json();
    statusMessage.textContent = `Status: ${job.status}`;

    if (job.status === "prompting_done") {
      stopPolling();
      setBusy(false);
      resultOutput.textContent = JSON.stringify(job.result, null, 2);
      // Move focus to the result so screen reader and keyboard users land on the new content.
      resultOutput.focus();
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
  resultOutput.textContent = "";
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
    statusMessage.textContent = "Status: pending";
    pollTimer = setInterval(() => pollJobStatus(job_id), POLL_INTERVAL_MS);
  } catch (err) {
    setBusy(false);
    showError(`Error: ${err.message}`);
  }
});
