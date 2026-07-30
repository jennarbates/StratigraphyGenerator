// Talking to this app's JSON API.
//
// Four modules -- trenches, harris/editor, harris/dashboard, finds -- each
// carried their own `responseJson`. They had drifted: two parsed the body
// tolerantly and two threw a raw SyntaxError when the server returned HTML
// (which it does for a 500), one attached the error payload and three did not,
// and the failure messages differed. This is the union of the four, which is
// the most forgiving of them, so adopting it everywhere only widens what
// callers can handle.

/**
 * The decoded JSON body, or a thrown Error carrying `status` and `payload`.
 *
 * A body that is not JSON becomes {} rather than a parse error: the server
 * answers a 500 with an HTML page, and "The request failed." is a better thing
 * to show a user than "Unexpected token < in JSON".
 */
export async function responseJson(response) {
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok) {
    const error = new Error(
      payload.error || payload.description || "The request failed.",
    );
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

/** GET (or any verb via opts), returning the decoded body. */
export async function api(path, opts = {}) {
  const response = await fetch(path, {
    ...opts,
    headers: { Accept: "application/json", ...(opts.headers || {}) },
  });
  return responseJson(response);
}

/** Send a JSON body and return the decoded reply. */
export async function apiJson(path, payload, method = "POST") {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
}

/**
 * Poll a background task until it finishes.
 *
 * onLog receives (lines, elapsedSeconds) after every poll so a caller can show
 * progress; it is optional.
 */
export async function pollTask(taskId, onLog, intervalMs = 1200) {
  for (;;) {
    const task = await api(`/api/tasks/${encodeURIComponent(taskId)}`);
    if (onLog) onLog(task.log || [], task.elapsed_seconds);
    if (task.status === "done") return task;
    if (task.status === "error") {
      const error = new Error(task.error);
      error.detail = task.error_detail || null;
      throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
