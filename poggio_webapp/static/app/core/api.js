import { state } from "./state.js";
import { $jobBadge } from "./ui.js";

export async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  let body;
  try { body = await res.json(); } catch (e) { body = null; }
  if (!res.ok) {
    const msg = (body && (body.error || body.description)) || res.statusText;
    throw new Error(msg);
  }
  return body;
}

export async function apiJson(path, payload, method = "POST") {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
}

export async function ensureJob() {
  if (state.jobId) return state.jobId;
  const r = await api("/api/jobs", { method: "POST" });
  state.jobId = r.job_id;
  $jobBadge.textContent = `job ${state.jobId}`;
  return state.jobId;
}

export async function pollTask(taskId, onLog) {
  while (true) {
    const t = await api(`/api/tasks/${taskId}`);
    if (onLog) onLog(t.log || [], t.elapsed_seconds);
    if (t.status === "done") return t;
    if (t.status === "error") {
      const err = new Error(t.error);
      err.detail = t.error_detail || null;
      throw err;
    }
    await new Promise((r) => setTimeout(r, 1200));
  }
}

// How long is too long for the extraction stage? Derived from the actual
// ceilings in the code: each attempt has a 4-minute client timeout
// (http_options in extract_*.py), up to 5 attempts with backoff, capped at
// a 10-minute total retry budget (generate_with_retry). So ~11 min is the
// true worst case; anything past that means the server thread is stuck.
const EXTRACT_TYPICAL_S = 240;   // most sheets finish well inside 4 min
const EXTRACT_HARD_S = 660;      // past the retry budget -- nothing good is coming
export function extractWaitStatus(elapsed) {
  if (elapsed < EXTRACT_TYPICAL_S) {
    return `Typically finishes in 1\u20134 minutes.`;
  }
  if (elapsed < EXTRACT_HARD_S) {
    return `\u26a0 Longer than typical. If the log shows "retrying", Gemini's ` +
      `servers are having trouble \u2014 the app retries automatically (max ~11 ` +
      `min total), so leave it be; re-running now would just spend more quota.`;
  }
  return `\u26a0 ${Math.round(elapsed / 60)} min is past the worst case this app ` +
    `allows (~11 min). The server thread is likely stuck \u2014 safe to close ` +
    `this tab and restart app.py. Before re-running: wait a while (each run ` +
    `re-sends the whole image and uses quota), check ` +
    `https://status.cloud.google.com, and if this keeps happening, report ` +
    `it on the project's issue tracker with the log below.`;
}
