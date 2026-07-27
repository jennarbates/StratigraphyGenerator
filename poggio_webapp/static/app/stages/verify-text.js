import { apiJson } from "../core/api.js";
import { goToStep, refreshChrome } from "../core/navigation.js";
import { state } from "../core/state.js";
import { $content, banner, errorBanner } from "../core/ui.js";

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

export function renderVerifyText() {
  const isFieldWall = state.sheetType === "fieldwall";
  const isComplete = !!state.completed.verifyText;

  $content.innerHTML = `
    <div class="panel">
      <div class="stage-kicker">Step 3 of 9</div>
      <h2>Check the writing</h2>
      ${isFieldWall ? `
        <p class="lede">This step will read the written labels on the field
        sheet and let you verify them before tracing.</p>
        <div class="plain-note">
          <span class="note-icon" aria-hidden="true">i</span>
          <span>Automatic reading controls are not available yet. You can
          continue without them and enter the labels while tracing.</span>
        </div>
      ` : `
        <p class="lede">Automatic text reading for illustrated trench sheets
        is not included in this version.</p>
        <div class="plain-note">
          <span class="note-icon" aria-hidden="true">i</span>
          <span>Continue to tracing and enter any labels there.</span>
        </div>
      `}
      ${isComplete
        ? banner("ok", "The writing step is complete. You can continue to tracing.")
        : ""}
      <div class="btn-row">
        <button id="vtContinue">
          ${isComplete
            ? "Continue to trace the layers"
            : (isFieldWall ? "Continue without automatic reading" : "Continue")}
        </button>
      </div>
      <div id="vtError"></div>
    </div>
  `;

  document.getElementById("vtContinue").addEventListener("click", async () => {
    const button = document.getElementById("vtContinue");
    const error = document.getElementById("vtError");

    if (isComplete) {
      goToStep("draw");
      return;
    }

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
      button.textContent = isFieldWall
        ? "Continue without automatic reading"
        : "Continue";
    }
  });
}
