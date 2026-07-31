"""Links back to the records this application's data came from.

Poggio Civitate's system of record is KoboToolbox feeding Open Context, with
stable ARK-backed persistent URLs. This application is a modelling tool that
sits beside that, and until now it has known nothing about it: a job here could
not say which locus record it was built from, and a model that left the machine
carried no way back to the published evidence.

These are the cheapest fields in the alignment work and among the most useful.
They cost a string each and make every model traceable.

**Read-only by design.** This module records where something came from. It
never writes to Kobo or Open Context, and nothing here performs a network
request -- a URI is validated by its shape, not by fetching it. The
application's promise is that data stays on the machine, and resolving a link
to check it would quietly break that.

Only the project's own hosts are accepted. An arbitrary URL stored as
provenance would be a link the operator did not vouch for, presented in the
interface as though they had.
"""

from __future__ import annotations

import re

OPEN_CONTEXT_HOST = "opencontext.org"
ARK_HOST = "n2t.net"

# opencontext.org/subjects/<uuid>, /documents/<uuid>, /media/<uuid>, /predicates/...
_OPEN_CONTEXT = re.compile(
    r"^https?://(?:www\.)?opencontext\.org/"
    r"(subjects|documents|media|types|predicates|projects)/"
    r"([0-9a-zA-Z][0-9a-zA-Z-]{7,})/?$",
    re.IGNORECASE,
)

# The project's persistent-URL prefix, n2t.net/ark:/28722/r2p24/<id>. The
# naming authority is followed by a shoulder and then the identifier, so the
# tail is one or more path segments rather than exactly one.
_ARK = re.compile(
    r"^https?://(?:www\.)?n2t\.net/ark:/(\d+)/"
    r"([0-9a-zA-Z][0-9a-zA-Z_.-]*(?:/[0-9a-zA-Z][0-9a-zA-Z_.-]*)*)/?$",
    re.IGNORECASE,
)

# A Kobo submission id is a UUID, sometimes prefixed "uuid:".
_KOBO_RECORD = re.compile(
    r"^(?:uuid:)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# "p. 17", "17", "17-19", "pp. 17-19".
_TRENCHBOOK_PAGE = re.compile(
    r"^(?:pp?\.?\s*)?(\d+)(?:\s*[-–]\s*(\d+))?$", re.IGNORECASE)


class ProvenanceError(ValueError):
    """A provenance value that cannot be recorded. User-facing message."""


def open_context_uri(value):
    """A canonical Open Context or ARK URI, or '' when absent.

    Upgraded to https: these are public read-only records and the project's own
    links are https, so storing a plain-http variant only creates two spellings
    of one reference.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if not isinstance(value, str):
        raise ProvenanceError(f"provenance URI {value!r} is not a string")

    text = value.strip()
    match = _OPEN_CONTEXT.match(text)
    if match:
        kind, identifier = match.groups()
        return f"https://{OPEN_CONTEXT_HOST}/{kind.lower()}/{identifier}"

    match = _ARK.match(text)
    if match:
        authority, identifier = match.groups()
        return f"https://{ARK_HOST}/ark:/{authority}/{identifier}"

    raise ProvenanceError(
        f"{text!r} is not a Poggio Civitate record link. Expected an Open "
        f"Context URL like https://{OPEN_CONTEXT_HOST}/subjects/<id> or a "
        f"persistent https://{ARK_HOST}/ark:/28722/r2p24/<id>"
    )


def kobo_record_id(value):
    """A Kobo submission UUID without its optional 'uuid:' prefix, or ''."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    if not isinstance(value, str):
        raise ProvenanceError(f"Kobo record id {value!r} is not a string")
    text = value.strip()
    if not _KOBO_RECORD.match(text):
        raise ProvenanceError(
            f"{text!r} is not a Kobo submission id (expected a UUID, "
            "optionally prefixed 'uuid:')"
        )
    return text.split(":", 1)[-1].lower()


def trenchbook_page(value):
    """A trenchbook page or page range, normalized to '17' or '17-19'.

    Trenchbooks are written on odd-numbered right-hand pages only, so an even
    page is worth questioning rather than storing -- but it is a note, not a
    refusal: a supplemental find is written on the facing left-hand page, and
    that reference is real.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return "", []
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        raise ProvenanceError(f"trenchbook page {value!r} is not a page number")

    match = _TRENCHBOOK_PAGE.match(value.strip())
    if not match:
        raise ProvenanceError(
            f"{value.strip()!r} is not a trenchbook page. Expected a number "
            "like '17' or a range like '17-19'"
        )
    first, last = match.groups()
    pages = f"{int(first)}-{int(last)}" if last else str(int(first))

    notes = []
    even = [p for p in (first, last) if p and int(p) % 2 == 0]
    if even:
        notes.append(
            f"trenchbook page {pages} includes an even page. Entries are "
            "written on the odd-numbered right-hand pages; even pages carry "
            "addenda such as supplemental finds"
        )
    return pages, notes


def read(payload):
    """Pull the provenance fields out of a request body or form.

    Returns ``(record, notes)`` where record holds only the fields that were
    actually supplied, so it can be merged into metadata without writing empty
    keys over something already stored.
    """
    source = payload if isinstance(payload, dict) else {}
    record = {}
    notes = []

    uri = open_context_uri(source.get("open_context_uri")
                           or source.get("openContextUri"))
    if uri:
        record["open_context_uri"] = uri

    kobo = kobo_record_id(source.get("kobo_record_id")
                          or source.get("koboRecordId"))
    if kobo:
        record["kobo_record_id"] = kobo

    page, page_notes = trenchbook_page(source.get("trenchbook_page")
                                       or source.get("trenchbookPage"))
    if page:
        record["trenchbook_page"] = page
    notes.extend(page_notes)

    return record, notes
