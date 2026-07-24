(() => {
  const resultsView = document.querySelector(
    "[data-results-view][data-status-url]",
  );
  if (!resultsView) return;

  const pollingStatuses = new Set(["finalizing", "building"]);
  if (!pollingStatuses.has(resultsView.dataset.resultStatus)) return;

  const statusUrl = resultsView.dataset.statusUrl;
  const statusHeading = resultsView.querySelector(
    "[data-result-status-heading]",
  );
  const statusText = resultsView.querySelector("[data-result-status-text]");
  const sidebarStatus = document.querySelector(
    "[data-result-sidebar-status]",
  );
  const recovery = resultsView.querySelector("[data-result-recovery]");
  const configuredInterval = Number(resultsView.dataset.pollIntervalMs);
  const configuredMaxFailures = Number(
    resultsView.dataset.pollMaxFailures,
  );
  const pollInterval = (
    configuredInterval >= 1500 && configuredInterval <= 3000
  ) ? configuredInterval : 2000;
  const maxFailures = configuredMaxFailures > 0
    ? configuredMaxFailures
    : 3;

  let stopped = false;
  let consecutiveFailures = 0;
  let timerId;

  function stopPolling() {
    stopped = true;
    if (timerId !== undefined) window.clearTimeout(timerId);
  }

  function showError(message) {
    stopPolling();
    resultsView.dataset.resultStatus = "error";
    if (statusHeading) statusHeading.textContent = "This drawing needs attention";
    if (statusText) statusText.textContent = message;
    if (sidebarStatus) sidebarStatus.textContent = "Needs attention";
    if (recovery) recovery.hidden = false;
  }

  function schedulePoll() {
    if (!stopped) {
      timerId = window.setTimeout(pollStatus, pollInterval);
    }
  }

  async function pollStatus() {
    if (stopped) return;

    try {
      const response = await window.fetch(statusUrl, {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("Status request failed");

      const payload = await response.json();
      consecutiveFailures = 0;
      resultsView.dataset.resultStatus = payload.status;

      if (payload.status === "complete") {
        stopPolling();
        window.location.reload();
        return;
      }

      if (payload.status === "error") {
        showError(
          "We could not finish creating this model. "
          + "Your saved drawing has not been lost.",
        );
        return;
      }

      if (typeof payload.message === "string" && statusText) {
        statusText.textContent = `${payload.message} This page updates automatically.`;
      }
      if (payload.status === "building" && sidebarStatus) {
        sidebarStatus.textContent = "Creating 3D model";
      }

      if (pollingStatuses.has(payload.status)) {
        schedulePoll();
      } else {
        stopPolling();
      }
    } catch (_error) {
      consecutiveFailures += 1;
      if (consecutiveFailures >= maxFailures) {
        showError(
          "We could not check the latest model status. "
          + "Refresh this page to try again.",
        );
        return;
      }
      schedulePoll();
    }
  }

  window.addEventListener("pagehide", stopPolling, { once: true });
  schedulePoll();
})();
