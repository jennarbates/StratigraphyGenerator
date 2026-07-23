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
