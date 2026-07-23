"""User-facing pipeline error messages."""


def _friendly_error(e):
    """Translate the errors users actually hit into what-to-do-next text.
    The raw exception + traceback still travels alongside as error_detail;
    this string is the one shown in the red banner."""
    import json as _json
    if isinstance(e, _json.JSONDecodeError):
        return (f"{e} — this is almost always a truncated Gemini response "
                 "(cut off by the output-token limit). Go back to the "
                 "Extraction step, raise max_output_tokens, and re-run.")

    # Gemini API errors, matched by status code so this works whether the
    # SDK raises ServerError or ClientError.
    code = getattr(e, "code", None)
    if code in (504, 503, 500, 502):
        return (
            f"Gemini's servers failed with a {code} on every retry attempt. "
            "This is a problem on Google's side, not with your scan or this "
            "app. What to do: (1) wait 15–30 minutes and try once more — "
            "don't hammer re-run, each attempt re-sends the whole image and "
            "uses your quota; (2) if it persists, check Google's status at "
            "https://status.cloud.google.com and the AI Studio forum; "
            "(3) as a workaround, shrink the request — lower "
            "max_output_tokens, or reduce MAX_SEND_DIMENSION in the "
            "extraction module. If it still fails after a day, report it "
            "on this project's issue tracker with the log above."
        )
    if code == 429:
        return (
            "Gemini says your API key is out of quota (429). Retrying will "
            "not help until the quota resets. Check your usage and limits "
            "at https://aistudio.google.com — free-tier keys have daily "
            "caps that a few large extractions can exhaust. Wait for the "
            "reset (or use a key from a project with billing enabled), "
            "then re-run once."
        )
    if code in (400, 401, 403):
        return (
            f"Gemini rejected the request ({code}) — usually an invalid or "
            "restricted API key, or a key from a project without the "
            "Gemini API enabled. Double-check the key you pasted (get one "
            "at https://aistudio.google.com/apikey) and re-run. Retrying "
            "with the same key will keep failing."
        )
    return str(e)
