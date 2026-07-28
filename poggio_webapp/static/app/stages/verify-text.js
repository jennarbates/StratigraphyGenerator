import {
  api,
  apiJson,
  extractWaitStatus,
  pollTask,
} from "../core/api.js";
import { goToStep, refreshChrome } from "../core/navigation.js";
import { state } from "../core/state.js";
import {
  acceptAllHighConfidenceProposals,
  areTextCandidateReviewsComplete,
  buildVerifiedTextPayload,
  changeTextCandidateFinalValue,
  createTextReviewRows,
  flattenTextCandidates,
  normalizedBboxToPixels,
  padPixelBbox,
  setTextCandidateReviewStatus,
} from "../text-metadata.js";
import {
  $content,
  banner,
  errorBanner,
  esc,
} from "../core/ui.js";

const FIELD_SECTIONS = Object.freeze([
  {
    title: "Trench name",
    matches: (path) => path === "document.trenchLabel",
  },
  {
    title: "Face",
    matches: (path) => path === "document.faceLabel",
  },
  {
    title: "Date",
    matches: (path) => path === "document.date",
  },
  {
    title: "Grid-square size",
    matches: (path) => path === "document.gridSquareCm",
  },
  {
    title: "North-arrow presence",
    matches: (path) => path === "document.northArrowPresent",
  },
  {
    title: "Illustrators",
    matches: (path) => path.startsWith("document.illustrators."),
  },
  {
    title: "Grid tie labels",
    matches: (path) => path.startsWith("document.gridTiePoints."),
  },
  {
    title: "Locus number",
    matches: (path) => /^loci\.\d+\.locusNumber$/.test(path),
  },
  {
    title: "Munsell notation",
    matches: (path) => /^loci\.\d+\.munsellRaw$/.test(path),
  },
  {
    title: "Locus description",
    matches: (path) => /^loci\.\d+\.description$/.test(path),
  },
  {
    title: "Marginal notes",
    matches: (path) => path.startsWith("document.marginalia."),
  },
  {
    title: "Other readable text",
    matches: (path) => path.startsWith("document.otherText."),
  },
]);

const reviewRowsByJob = new Map();
const taskProgressByJob = new Map();
const activeTaskPolls = new Map();
const SOURCE_PREVIEW_MAX_WIDTH = 320;
const SOURCE_PREVIEW_MAX_HEIGHT = 112;
let renderToken = 0;

function currentReviews() {
  return reviewRowsByJob.get(state.jobId) || [];
}

function setCurrentReviews(rows) {
  reviewRowsByJob.set(state.jobId, rows);
}

function replaceReview(row) {
  const reviews = currentReviews();
  const index = reviews.findIndex(
    (candidateReview) => candidateReview.fieldPath === row.fieldPath,
  );
  const next = reviews.map((candidateReview) => ({ ...candidateReview }));
  if (index === -1) next.push(row);
  else next[index] = row;
  setCurrentReviews(next);
}

function candidateValue(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return `<span class="vt-empty-value">No proposal</span>`;
  }
  if (value === true) return "Yes";
  if (value === false) return "No";
  return esc(value);
}

function displayedError(message) {
  return errorBanner(
    message instanceof Error ? message : new Error(message || "Something went wrong."),
  );
}

function reviewLabel(status) {
  if (status === "accepted") return "Accepted";
  if (status === "corrected") return "Corrected";
  if (status === "unreadable") return "Unreadable";
  return "Not reviewed";
}

function initializeReviews(candidates, verified = null, restoreLocal = true) {
  const fresh = createTextReviewRows(candidates, verified);
  if (verified || !restoreLocal) {
    setCurrentReviews(fresh);
    return;
  }

  const existing = new Map(
    currentReviews().map((row) => [row.fieldPath, row]),
  );
  setCurrentReviews(
    fresh.map((row) => (
      existing.has(row.fieldPath) ? existing.get(row.fieldPath) : row
    )),
  );
}

export async function completeVerifyText(requestSkip = apiJson) {
  state.verifyText.error = null;

  if (state.sheetType === "fieldwall") {
    const result = await requestSkip(
      `/api/jobs/${state.jobId}/text-verification/skip`,
      {},
    );
    state.verifyText.status = result.status || "skipped";
  } else {
    state.verifyText.status = "skipped";
  }

  state.completed.verifyText = true;
}

function renderIllustratorStage() {
  const isComplete = !!state.completed.verifyText;
  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 3 of 9</div>
      <h2>Check the writing</h2>
      <p class="lede">Automatic text reading for illustrated trench sheets
      is not included in this version.</p>
      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">i</span>
        <span>Continue to tracing and enter any labels there. No geometry is
        generated in this step.</span>
      </div>
      ${isComplete
        ? banner("ok", "The writing step is complete. You can continue to tracing.")
        : ""}
      <div class="btn-row">
        <button id="vtContinue">
          ${isComplete ? "Continue to trace the layers" : "Continue"}
        </button>
      </div>
      <div id="vtError"></div>
    </div>
  `;

  document.getElementById("vtContinue").addEventListener("click", async () => {
    if (isComplete) {
      goToStep("draw");
      return;
    }
    const button = document.getElementById("vtContinue");
    const error = document.getElementById("vtError");
    error.innerHTML = "";
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span>Continuing...`;
    try {
      await completeVerifyText();
      refreshChrome();
      goToStep("draw");
    } catch (requestError) {
      state.verifyText.status = "error";
      state.verifyText.error = requestError.message;
      error.innerHTML = errorBanner(requestError);
      button.disabled = false;
      button.textContent = "Continue";
    }
  });
}

function extractionControls({
  disabled = false,
  retry = false,
  loading = false,
} = {}) {
  return `
    <div class="vt-extraction-controls action-card">
      <h3>${retry ? "Try automatic reading again" : "Read the writing automatically"}</h3>
      <label class="field">
        <span class="label-text">Gemini API key</span>
        <input type="password" id="vtApiKey" placeholder="Paste the key here"
               autocomplete="off" spellcheck="false" ${disabled ? "disabled" : ""}>
        <span class="hint">The key is sent to the local server for this request
        and kept only in this page’s runtime memory.</span>
      </label>
      <label class="field">
        <span class="label-text">Large grid-square size, in centimetres</span>
        <input type="number" id="vtSquareCm" placeholder="For example: 20"
               step="0.5" min="0.1" value="${state.draw.squareCm ?? ""}"
               ${disabled ? "disabled" : ""}>
        <span class="hint">The existing Gemini drawing reader uses this value
        to calibrate the field-wall sheet.</span>
      </label>
      <div class="btn-row">
        <button id="vtStart" ${disabled ? "disabled" : ""}>
          ${loading
            ? `<span class="spinner"></span>Checking saved text...`
            : (retry ? "Retry automatic reading" : "Read the writing")}
        </button>
        <button class="secondary" id="vtSkip" ${disabled ? "disabled" : ""}>
          Continue without automatic reading
        </button>
      </div>
    </div>
  `;
}

function bindApiKeyInput() {
  const input = document.getElementById("vtApiKey");
  if (!input) return;
  input.value = state.apiKey;
  input.addEventListener("input", () => {
    state.apiKey = input.value;
  });

  const squareInput = document.getElementById("vtSquareCm");
  if (squareInput) {
    squareInput.addEventListener("input", () => {
      state.draw.squareCm = Number(squareInput.value) || null;
    });
  }
}

function bindSkipButton() {
  const button = document.getElementById("vtSkip");
  if (!button || button.disabled) return;
  button.addEventListener("click", async () => {
    const error = document.getElementById("vtError");
    error.innerHTML = "";
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span>Continuing...`;
    try {
      await completeVerifyText();
      refreshChrome();
      goToStep("draw");
    } catch (requestError) {
      state.verifyText.status = "error";
      state.verifyText.error = requestError.message;
      error.innerHTML = errorBanner(requestError);
      button.disabled = false;
      button.textContent = "Continue without automatic reading";
    }
  });
}

function bindStartButton(token) {
  const button = document.getElementById("vtStart");
  if (!button || button.disabled) return;
  button.addEventListener("click", async () => {
    const error = document.getElementById("vtError");
    const apiKeyInput = document.getElementById("vtApiKey");
    const squareInput = document.getElementById("vtSquareCm");
    error.innerHTML = "";
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
      error.innerHTML = banner(
        "err",
        "Paste a Gemini API key before asking the app to read the writing.",
      );
      apiKeyInput.focus();
      return;
    }
    const squareCm = Number(squareInput.value);
    if (!squareCm) {
      error.innerHTML = banner(
        "err",
        "Enter the large grid-square size shown on the field sheet.",
      );
      squareInput.focus();
      return;
    }

    state.apiKey = apiKey;
    state.draw.squareCm = squareCm;
    state.verifyText.status = "extracting";
    state.verifyText.error = null;
    taskProgressByJob.set(state.jobId, { log: [], elapsed: 0 });
    renderFieldWallBody(token);

    try {
      const started = await apiJson(
        `/api/jobs/${state.jobId}/text-extraction`,
        { api_key: apiKey, square_cm: squareCm },
      );
      state.verifyText.taskId = started.task_id;
      monitorExtraction(started.task_id, token);
    } catch (requestError) {
      state.verifyText.status = "error";
      state.verifyText.error = requestError.message;
      if (token === renderToken) renderFieldWallBody(token);
    }
  });
}

function renderPreExtraction(token, options = {}) {
  const body = document.getElementById("vtBody");
  body.innerHTML = `
    ${options.error ? displayedError(options.error) : ""}
    ${extractionControls(options)}
    <div id="vtError"></div>
  `;
  bindApiKeyInput();
  bindStartButton(token);
  bindSkipButton();
}

function updateVisibleTaskLog() {
  const progress = taskProgressByJob.get(state.jobId) || {
    log: [],
    elapsed: 0,
  };
  const log = document.getElementById("vtLog");
  if (!log) return;
  const messages = Array.isArray(progress.log) ? progress.log : [];
  log.textContent = `[${progress.elapsed}s elapsed] ${extractWaitStatus(progress.elapsed)}`
    + (messages.length ? `\n${messages.join("\n")}` : "\nWaiting for the first update...");
}

function renderRunning() {
  const body = document.getElementById("vtBody");
  body.innerHTML = `
    <div class="vt-running" role="status" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span>
      <strong>Reading the field-wall drawing…</strong>
      <span>The existing Gemini extraction is running; its writing will be
      shown here for review.</span>
    </div>
    ${extractionControls({ disabled: true })}
    <div id="vtLog" class="log-box"></div>
    <div id="vtError"></div>
  `;
  bindApiKeyInput();
  updateVisibleTaskLog();
}

function candidateCard(candidate, review, index) {
  const status = review?.status || "";
  const finalValue = review?.finalValue ?? "";
  const notes = candidate.notes
    ? `<p class="vt-candidate-notes">${esc(candidate.notes)}</p>`
    : "";
  const hasPotentialSource = Array.isArray(candidate.bbox);
  return `
    <article class="vt-candidate ${status ? `is-${status}` : ""}"
             data-candidate-index="${index}">
      <figure class="vt-source-preview">
        <figcaption>Source preview</figcaption>
        ${hasPotentialSource
          ? `<canvas class="vt-source-canvas"
                     data-source-index="${index}"
                     aria-label="Source preview for ${esc(candidate.fieldPath)}"></canvas>
             <p class="vt-source-unavailable" hidden>Source area unavailable.</p>`
          : `<p class="vt-source-unavailable">Source area unavailable.</p>`}
      </figure>
      <div class="vt-candidate-source">
        <div>
          <span class="vt-data-label">Raw transcription</span>
          <div class="vt-raw">${candidate.raw ? esc(candidate.raw) : "<em>Empty</em>"}</div>
        </div>
        <div>
          <span class="vt-data-label">Proposed value</span>
          <div class="vt-proposed">${displayValue(candidate.proposed)}</div>
        </div>
        <span class="vt-confidence is-${esc(candidate.confidence || "low")}">
          ${esc(candidate.confidence || "low")} confidence
        </span>
      </div>
      ${notes}
      <label class="field vt-final-field">
        <span class="label-text">Editable final value</span>
        <input type="text" class="vt-final-value"
               value="${esc(candidateValue(finalValue))}">
      </label>
      <div class="vt-review-actions" role="group"
           aria-label="Review ${esc(candidate.fieldPath)}">
        ${["accepted", "corrected", "unreadable"].map((action) => `
          <button type="button" class="secondary vt-review-button"
                  data-review-action="${action}"
                  aria-pressed="${status === action}">
            ${action === "accepted"
              ? "Accept"
              : (action === "corrected" ? "Correct" : "Unreadable")}
          </button>
        `).join("")}
        <span class="vt-review-status">${reviewLabel(status)}</span>
      </div>
    </article>
  `;
}

function markSourcePreviewUnavailable(canvas) {
  if (!canvas) return;
  canvas.hidden = true;
  const fallback = canvas.parentElement?.querySelector(
    ".vt-source-unavailable",
  );
  if (fallback) fallback.hidden = false;
}

function renderSourcePreview(canvas, candidate, image) {
  const pixelBbox = normalizedBboxToPixels(
    candidate.bbox,
    image.naturalWidth,
    image.naturalHeight,
  );
  if (!pixelBbox) {
    markSourcePreviewUnavailable(canvas);
    return;
  }

  const textHeight = pixelBbox[3] - pixelBbox[1];
  const padding = Math.max(12, Math.round(textHeight * 0.65));
  const crop = padPixelBbox(
    pixelBbox,
    image.naturalWidth,
    image.naturalHeight,
    padding,
  );
  if (!crop) {
    markSourcePreviewUnavailable(canvas);
    return;
  }

  const cropWidth = crop[2] - crop[0];
  const cropHeight = crop[3] - crop[1];
  const scale = Math.min(
    SOURCE_PREVIEW_MAX_WIDTH / cropWidth,
    SOURCE_PREVIEW_MAX_HEIGHT / cropHeight,
  );
  canvas.width = Math.max(1, Math.round(cropWidth * scale));
  canvas.height = Math.max(1, Math.round(cropHeight * scale));

  const context = canvas.getContext("2d");
  if (!context) {
    markSourcePreviewUnavailable(canvas);
    return;
  }
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  try {
    context.drawImage(
      image,
      crop[0],
      crop[1],
      cropWidth,
      cropHeight,
      0,
      0,
      canvas.width,
      canvas.height,
    );
  } catch {
    markSourcePreviewUnavailable(canvas);
  }
}

function bindSourcePreviews(candidates, token) {
  const canvases = Array.from(
    document.querySelectorAll(".vt-source-canvas"),
  );
  if (canvases.length === 0) return;

  const sourceUrl = state.preprocess.cleanUrl || state.scan.url;
  if (!sourceUrl) {
    canvases.forEach(markSourcePreviewUnavailable);
    return;
  }

  const image = new Image();
  image.onload = () => {
    if (token !== renderToken || state.current !== "verifyText") return;
    canvases.forEach((canvas) => {
      const candidate = candidates[Number(canvas.dataset.sourceIndex)];
      if (candidate) renderSourcePreview(canvas, candidate, image);
      else markSourcePreviewUnavailable(canvas);
    });
  };
  image.onerror = () => {
    if (token !== renderToken || state.current !== "verifyText") return;
    canvases.forEach(markSourcePreviewUnavailable);
  };
  image.src = sourceUrl;
}

function sectionHtml(section, candidates, reviewsByPath, candidateIndexes) {
  const matching = candidates.filter((candidate) => (
    section.matches(candidate.fieldPath)
  ));
  return `
    <section class="vt-field-section">
      <h3>${section.title}</h3>
      ${matching.length
        ? matching.map((candidate) => candidateCard(
          candidate,
          reviewsByPath.get(candidate.fieldPath),
          candidateIndexes.get(candidate.fieldPath),
        )).join("")
        : `<p class="vt-no-candidates">No readable candidates were returned.</p>`}
    </section>
  `;
}

function syncCandidateCard(index, review) {
  const card = document.querySelector(
    `.vt-candidate[data-candidate-index="${index}"]`,
  );
  if (!card) return;
  card.classList.remove("is-accepted", "is-corrected", "is-unreadable");
  if (review.status) card.classList.add(`is-${review.status}`);
  card.querySelectorAll("[data-review-action]").forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.reviewAction === review.status),
    );
  });
  const label = card.querySelector(".vt-review-status");
  if (label) label.textContent = reviewLabel(review.status);
}

function updateReviewSummary(candidates) {
  const reviews = currentReviews();
  const reviewed = reviews.filter((row) => (
    ["accepted", "corrected", "unreadable"].includes(row.status)
  )).length;
  const summary = document.getElementById("vtReviewSummary");
  if (summary) {
    summary.textContent = candidates.length
      ? `${reviewed} of ${candidates.length} candidates reviewed.`
      : "No readable text candidates were returned; there is nothing to review.";
  }
  const save = document.getElementById("vtSave");
  if (save) {
    save.disabled = !areTextCandidateReviewsComplete(candidates, reviews);
  }
  const bulk = document.getElementById("vtAcceptHigh");
  if (bulk) {
    const statusByPath = new Map(
      reviews.map((row) => [row.fieldPath, row.status]),
    );
    bulk.disabled = !candidates.some((candidate) => (
      candidate.confidence === "high"
      && !["accepted", "corrected", "unreadable"].includes(
        statusByPath.get(candidate.fieldPath),
      )
    ));
  }
}

function bindReviewControls(candidates, token) {
  document.querySelectorAll(".vt-candidate").forEach((card) => {
    const index = Number(card.dataset.candidateIndex);
    const candidate = candidates[index];
    const input = card.querySelector(".vt-final-value");

    input.addEventListener("input", () => {
      const current = currentReviews().find(
        (row) => row.fieldPath === candidate.fieldPath,
      );
      const next = changeTextCandidateFinalValue(
        candidate,
        current,
        input.value,
      );
      replaceReview(next);
      syncCandidateCard(index, next);
      updateReviewSummary(candidates);
    });

    card.querySelectorAll("[data-review-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const current = currentReviews().find(
          (row) => row.fieldPath === candidate.fieldPath,
        );
        const next = setTextCandidateReviewStatus(
          candidate,
          current,
          button.dataset.reviewAction,
        );
        replaceReview(next);
        input.value = candidateValue(next.finalValue);
        syncCandidateCard(index, next);
        updateReviewSummary(candidates);
        if (next.status === "corrected") input.focus();
      });
    });
  });

  document.getElementById("vtAcceptHigh").addEventListener("click", () => {
    setCurrentReviews(
      acceptAllHighConfidenceProposals(candidates, currentReviews()),
    );
    renderReview(token);
  });

  document.getElementById("vtSave").addEventListener("click", async () => {
    const button = document.getElementById("vtSave");
    const error = document.getElementById("vtError");
    if (!areTextCandidateReviewsComplete(candidates, currentReviews())) return;

    error.innerHTML = "";
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span>Saving...`;
    try {
      const payload = buildVerifiedTextPayload(
        state.verifyText.candidates,
        currentReviews(),
      );
      const verified = await apiJson(
        `/api/jobs/${state.jobId}/text-verification`,
        payload,
      );
      state.verifyText.verified = verified;
      state.verifyText.status = "verified";
      state.verifyText.error = null;
      state.completed.verifyText = true;
      initializeReviews(state.verifyText.candidates, verified, false);
      refreshChrome();
      if (
        token === renderToken
        && state.current === "verifyText"
        && document.getElementById("vtBody")
      ) {
        renderReview(token, true);
      }
    } catch (requestError) {
      state.verifyText.error = requestError.message;
      error.innerHTML = errorBanner(requestError);
      button.disabled = false;
      button.textContent = "Save verified text";
    }
  });

  const continueButton = document.getElementById("vtContinueDraw");
  if (continueButton) {
    continueButton.addEventListener("click", () => goToStep("draw"));
  }
}

function renderReview(token, justSaved = false) {
  const body = document.getElementById("vtBody");
  const candidates = flattenTextCandidates(state.verifyText.candidates);
  const reviews = currentReviews();
  const reviewsByPath = new Map(
    reviews.map((row) => [row.fieldPath, row]),
  );
  const candidateIndexes = new Map(
    candidates.map((candidate, index) => [candidate.fieldPath, index]),
  );
  const isVerified = state.verifyText.status === "verified"
    && !!state.verifyText.verified;

  body.innerHTML = `
    ${isVerified || justSaved
      ? banner("ok", "Verified text is saved separately from the original extraction candidates.")
      : ""}
    ${candidates.length === 0
      ? banner("ok", "The model found no readable text. You can save this empty review and continue.")
      : ""}
    <div class="vt-review-toolbar">
      <div>
        <h3>Review the transcription</h3>
        <p id="vtReviewSummary" class="hint"></p>
      </div>
      <button type="button" class="secondary" id="vtAcceptHigh">
        Accept all high-confidence proposals
      </button>
    </div>
    <div class="vt-sections">
      ${FIELD_SECTIONS.map((section) => sectionHtml(
        section,
        candidates,
        reviewsByPath,
        candidateIndexes,
      )).join("")}
    </div>
    <div class="vt-save-row">
      <button id="vtSave">Save verified text</button>
      ${state.completed.verifyText
        ? `<button class="secondary" id="vtContinueDraw">Continue to trace the layers</button>`
        : ""}
    </div>
    <div id="vtError"></div>
  `;
  bindReviewControls(candidates, token);
  bindSourcePreviews(candidates, token);
  updateReviewSummary(candidates);
}

function renderVerifiedWithoutCandidates() {
  const body = document.getElementById("vtBody");
  body.innerHTML = `
    ${banner("ok", "Verified text is saved and ready to use.")}
    <p class="hint">The saved verification was retrieved, but its original
    candidates are not available to display.</p>
    <div class="btn-row">
      <button id="vtContinueDraw">Continue to trace the layers</button>
    </div>
  `;
  document.getElementById("vtContinueDraw").addEventListener(
    "click",
    () => goToStep("draw"),
  );
}

function renderSkipped(token) {
  const body = document.getElementById("vtBody");
  body.innerHTML = `
    ${banner("ok", "Automatic reading was skipped. You can continue to tracing.")}
    <div class="btn-row">
      <button id="vtContinueDraw">Continue to trace the layers</button>
      <button class="secondary" id="vtReadAfterSkip">Read the writing instead</button>
    </div>
  `;
  document.getElementById("vtContinueDraw").addEventListener(
    "click",
    () => goToStep("draw"),
  );
  document.getElementById("vtReadAfterSkip").addEventListener("click", () => {
    state.verifyText.status = "not_started";
    delete state.completed.verifyText;
    renderPreExtraction(token);
  });
}

function renderFieldWallBody(token, options = {}) {
  if (token !== renderToken || !document.getElementById("vtBody")) return;
  if (options.loading) {
    renderPreExtraction(token, { disabled: true, loading: true });
    return;
  }
  if (options.loadError) {
    renderPreExtraction(token, {
      error: options.loadError,
      retry: true,
    });
    return;
  }

  if (state.verifyText.status === "extracting") {
    renderRunning();
  } else if (state.verifyText.status === "error") {
    renderPreExtraction(token, {
      error: state.verifyText.error || "Text extraction failed. Please try again.",
      retry: true,
    });
  } else if (state.verifyText.status === "skipped") {
    renderSkipped(token);
  } else if (state.verifyText.candidates !== null) {
    renderReview(token);
  } else if (
    state.verifyText.status === "verified"
    && state.verifyText.verified
  ) {
    renderVerifiedWithoutCandidates();
  } else {
    renderPreExtraction(token);
  }
}

async function hydrateFieldWallState(token) {
  try {
    const result = await api(
      `/api/jobs/${state.jobId}/text-extraction`,
    );
    if (token !== renderToken) return;

    state.verifyText.status = result.status || "not_started";
    state.verifyText.error = result.error || null;
    if (Object.prototype.hasOwnProperty.call(result, "candidates")) {
      state.verifyText.candidates = result.candidates;
    }
    if (Object.prototype.hasOwnProperty.call(result, "verified_text")) {
      state.verifyText.verified = result.verified_text;
    }

    if (state.verifyText.verified) {
      state.verifyText.status = "verified";
      state.completed.verifyText = true;
    } else if (state.verifyText.status === "skipped") {
      state.completed.verifyText = true;
    }

    if (state.verifyText.candidates !== null) {
      initializeReviews(
        state.verifyText.candidates,
        state.verifyText.verified,
      );
    }
    renderFieldWallBody(token);
    refreshChrome();

    if (
      state.verifyText.status === "extracting"
      && state.verifyText.taskId
    ) {
      monitorExtraction(state.verifyText.taskId, token);
    }
  } catch (requestError) {
    if (token === renderToken) {
      renderFieldWallBody(token, { loadError: requestError });
    }
  }
}

function monitorExtraction(taskId, token) {
  if (!taskId || activeTaskPolls.has(taskId)) return;
  const jobId = state.jobId;
  const promise = pollTask(taskId, (log, elapsed) => {
    taskProgressByJob.set(jobId, { log, elapsed });
    if (state.jobId === jobId && state.current === "verifyText") {
      updateVisibleTaskLog();
    }
  })
    .then(async (task) => {
      if (state.jobId !== jobId) return;
      state.verifyText.status = "ready_for_review";
      state.verifyText.error = null;
      if (task.result) {
        state.verifyText.candidates = task.result;
      } else {
        const result = await api(`/api/jobs/${jobId}/text-extraction`);
        state.verifyText.status = result.status || "ready_for_review";
        if (Object.prototype.hasOwnProperty.call(result, "candidates")) {
          state.verifyText.candidates = result.candidates;
        }
      }
      initializeReviews(state.verifyText.candidates, null, false);
      if (state.current === "verifyText") {
        renderFieldWallBody(renderToken);
      }
    })
    .catch((requestError) => {
      if (state.jobId !== jobId) return;
      state.verifyText.status = "error";
      state.verifyText.error = requestError.message;
      if (state.current === "verifyText") {
        renderFieldWallBody(renderToken);
      }
    })
    .finally(() => {
      activeTaskPolls.delete(taskId);
    });
  activeTaskPolls.set(taskId, promise);
}

export function renderVerifyText() {
  const token = ++renderToken;
  if (state.sheetType !== "fieldwall") {
    renderIllustratorStage();
    return;
  }

  $content.innerHTML = `
    <div class="panel verify-text-stage">
      <div class="stage-kicker">Step 3 of 9</div>
      <h2>Check the writing</h2>
      <p class="lede">Review the written labels returned by the existing
      Gemini field-wall extraction. Automatic reading can make mistakes, so
      every candidate needs a person’s decision.</p>
      <div class="plain-note">
        <span class="note-icon" aria-hidden="true">i</span>
        <span>This review accepts only the writing. Any automatically generated
        geometry remains separate and is not treated as a human trace.</span>
      </div>
      <div id="vtBody"></div>
    </div>
  `;
  renderFieldWallBody(token, { loading: true });
  hydrateFieldWallState(token);
}
