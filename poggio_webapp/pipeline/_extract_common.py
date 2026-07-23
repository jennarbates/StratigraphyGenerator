"""
_extract_common.py — shared post-response checks for both extraction scripts.

Gemini's structured-output mode can still get cut off mid-generation if the
response would exceed max_output_tokens, especially on a drawing with many
layers/boundary points/features. When that happens the written JSON is
reliably invalid (an unterminated string or truncated array) — this is
exactly the failure mode normalize.py/validator.py will hit downstream as a
cryptic json.JSONDecodeError, so it's much better caught here, right after
the Gemini call, with an explanation and a concrete next step.
"""

import json
import time

from google.genai import errors

# Status codes worth retrying. 504 DEADLINE_EXCEEDED matters most here: a
# big scan + a long structured-output generation routinely blows past
# Google's server-side deadline, and the error body literally says "Please
# try again." The original per-module helpers only retried 500/503/429, so
# the single most retryable error raised straight through on attempt one.
TRANSIENT_STATUS_CODES = (429, 500, 502, 503, 504)


def generate_with_retry(client, progress_cb=None, max_attempts=5,
                        max_total_seconds=600, **kwargs):
    """client.models.generate_content with exponential backoff on transient
    server errors. Shared by both extraction modules (was duplicated in
    each). kwargs pass through to generate_content unchanged.

    max_total_seconds caps the whole retry loop's wall clock. Every retry
    re-sends the full image as input tokens, so an outage at Google's end
    shouldn't be allowed to quietly spend the user's quota five times over —
    past the budget we stop and tell them, rather than keep paying to fail."""
    t0 = time.time()
    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(**kwargs)
        except errors.ServerError as e:
            code = getattr(e, "code", None)
            wait = 2 ** attempt
            elapsed = time.time() - t0
            out_of_budget = elapsed + wait > max_total_seconds
            if (code in TRANSIENT_STATUS_CODES
                    and attempt < max_attempts - 1 and not out_of_budget):
                if progress_cb:
                    progress_cb(f"Gemini returned {code}; retrying in {wait}s "
                                f"(attempt {attempt + 2}/{max_attempts}, "
                                f"{elapsed:.0f}s elapsed)...")
                time.sleep(wait)
            else:
                if progress_cb and code in TRANSIENT_STATUS_CODES:
                    progress_cb(f"giving up after {attempt + 1} attempt(s) / "
                                f"{elapsed:.0f}s — not retrying further to "
                                "avoid spending more quota on a failing "
                                "request.")
                raise


def check_response(response, raw_json):
    """Returns a warning string (or None) describing why the raw JSON might
    be invalid/incomplete, checking both the API's own finish_reason and an
    actual parse attempt (belt and suspenders — a response can also get
    truncated by a network-level cutoff that finish_reason won't catch)."""

    truncated_by_limit = False
    try:
        finish_reason = response.candidates[0].finish_reason
        if str(finish_reason).endswith("MAX_TOKENS"):
            truncated_by_limit = True
    except (AttributeError, IndexError):
        finish_reason = None

    try:
        json.loads(raw_json)
        parse_ok = True
        parse_error = None
    except json.JSONDecodeError as e:
        parse_ok = False
        parse_error = str(e)

    if truncated_by_limit:
        return (
            "response was cut off by the output-token limit "
            f"(finish_reason={finish_reason}). The written JSON is almost "
            "certainly incomplete/invalid — raise max_output_tokens and "
            "re-run rather than trying to use this file as-is."
        )
    if not parse_ok:
        return (
            f"the response is not valid JSON ({parse_error}) even though "
            "the API didn't report a token-limit cutoff — this usually still "
            "means the response was truncated (e.g. an unterminated string "
            "near the end of the file is the classic symptom). Raise "
            "max_output_tokens and re-run; this file will fail at the "
            "normalize/validate step as written."
        )
    return None