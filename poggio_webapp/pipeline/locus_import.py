"""Reading a Kobo Locus Entry export into this application's locus records.

The 2025 deployment runs a **Locus Entry** form -- "data entry for loci
described during fieldwork" -- and *Excavation and Documentation Procedures*
says what ends up attached to it: elevations taken at every trench corner, a
Munsell designation, and the top plans drawn at opening and closing. That is
most of what the modelling side otherwise asks an operator to retype.

This reads a **downloaded export**, not the API. Kobo's own guide recommends
periodic XLS/ZIP downloads, so a file is the normal artifact, and it keeps the
promise that nothing leaves the machine. An API path would need a token, and a
token belongs in the environment rather than in this repository.

**Column names are not guessed.** A Kobo form's export headers depend on how
the form was built, and this module has never seen the real one. Rather than
pattern-match hopefully and mis-map a column in silence, it takes an explicit
map from the caller and offers candidates only as a starting suggestion. When a
required column cannot be identified it refuses and lists the headers it
actually saw, which is the one thing that makes the mapping easy to fix.
"""

from __future__ import annotations

import csv
import io

from naming import canonical_locus, canonical_trench

from . import provenance, site_elevation

# Required fields, and header spellings worth suggesting for each. These are
# guesses at what the export may call them -- offered to the operator, never
# applied without confirmation.
FIELDS = {
    "locus_number": ("locus", "locus_number", "locusnumber", "locus number"),
    "trench": ("trench", "trench_id", "trenchid", "trench id"),
    "season": ("season", "year", "excavation_year"),
    "munsell": ("munsell", "munsell_colour", "munsell_color", "soil_colour"),
    "description": ("description", "locus_description", "notes"),
    "opening_elevation": (
        "opening_elevation",
        "elevation_opening",
        "opening elevation",
        "top_elevation",
    ),
    "closing_elevation": (
        "closing_elevation",
        "elevation_closing",
        "closing elevation",
        "bottom_elevation",
    ),
    "open_context_uri": ("open_context_uri", "opencontext", "uri", "ark"),
    "kobo_record_id": ("_uuid", "uuid", "kobo_record_id", "submission_uuid"),
}

REQUIRED = ("locus_number",)


class LocusImportError(ValueError):
    """An export that cannot be read. The message is user-facing."""


def _headers(text):
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if any(cell.strip() for cell in row):
            return [cell.strip() for cell in row]
    raise LocusImportError("this file has no header row")


def suggest_column_map(headers):
    """A starting column map, plus the fields nothing plausible matched.

    Matching is on a normalized header (lowercased, punctuation flattened), so
    "Locus Number" and "locus_number" both land. Anything it cannot place is
    returned for the operator to map, not filled in with a nearby column.
    """

    def normalize(value):
        return "".join(
            character.lower() for character in str(value) if character.isalnum()
        )

    by_normalized = {}
    for header in headers:
        by_normalized.setdefault(normalize(header), header)

    mapping = {}
    unmatched = []
    for field, candidates in FIELDS.items():
        for candidate in candidates:
            header = by_normalized.get(normalize(candidate))
            if header is not None:
                mapping[field] = header
                break
        else:
            unmatched.append(field)
    return mapping, unmatched


def _require_columns(mapping, headers):
    missing = [field for field in REQUIRED if not mapping.get(field)]
    if missing:
        raise LocusImportError(
            "this export has no column mapped to "
            + ", ".join(missing)
            + ". Its columns are: "
            + ", ".join(repr(header) for header in headers)
            + ". Map the right one and import again -- guessing here would "
            "silently attach the wrong numbers to real loci"
        )
    unknown = [
        f"{field} -> {header!r}"
        for field, header in mapping.items()
        if header not in headers
    ]
    if unknown:
        raise LocusImportError(
            "the column map names columns this export does not have: "
            + ", ".join(unknown)
        )


def _elevation(raw, vertical, what, notes):
    text = (raw or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        notes.append(f"{what} {text!r} is not a number; left unrecorded")
        return None
    try:
        return round(site_elevation.resolve(value, vertical, what=what), 4)
    except site_elevation.ElevationError as error:
        raise LocusImportError(str(error)) from error


def read_export(text, column_map=None, *, vertical=None, trench=None):
    """Parse a Locus Entry export into locus records.

    ``column_map`` maps this module's field names to the export's own column
    headers; when omitted, ``suggest_column_map`` is used and the result says
    which mapping it settled on so the operator can check it.

    ``trench``, when given, keeps only that trench's rows -- one export usually
    covers a whole season.

    Returns ``{"loci": [...], "column_map": {...}, "unmatched": [...],
    "notes": [...]}``. Never raises for a single bad row: a row that cannot be
    read becomes a note, because one malformed entry should not cost the
    operator the other forty.
    """
    if not isinstance(text, str) or not text.strip():
        raise LocusImportError("this export is empty")

    headers = _headers(text)
    suggested, unmatched = suggest_column_map(headers)
    mapping = dict(suggested)
    if column_map:
        mapping.update(
            {
                field: header
                for field, header in column_map.items()
                if field in FIELDS and header
            }
        )
    _require_columns(mapping, headers)

    wanted_trench = canonical_trench(trench) if trench else ""
    notes = []
    loci = []
    seen = {}

    def cell(row, field):
        header = mapping.get(field)
        return (row.get(header) or "").strip() if header else ""

    for index, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        number = canonical_locus(cell(row, "locus_number"))
        if not number:
            continue

        row_trench = canonical_trench(cell(row, "trench"))
        if wanted_trench and row_trench and row_trench != wanted_trench:
            continue

        if number in seen:
            notes.append(
                f"row {index}: locus {number} was already read from row "
                f"{seen[number]}; keeping the first and ignoring this one"
            )
            continue
        seen[number] = index

        try:
            uri = provenance.open_context_uri(cell(row, "open_context_uri"))
        except provenance.ProvenanceError as error:
            uri = ""
            notes.append(f"row {index}: {error}")
        try:
            kobo = provenance.kobo_record_id(cell(row, "kobo_record_id"))
        except provenance.ProvenanceError as error:
            kobo = ""
            notes.append(f"row {index}: {error}")

        record = {
            "locusNumber": number,
            "trench": row_trench or wanted_trench or None,
            "season": cell(row, "season") or None,
            "munsell": cell(row, "munsell") or None,
            "description": cell(row, "description") or None,
            "openingElevation": _elevation(
                cell(row, "opening_elevation"),
                vertical,
                f"row {index} opening elevation",
                notes,
            ),
            "closingElevation": _elevation(
                cell(row, "closing_elevation"),
                vertical,
                f"row {index} closing elevation",
                notes,
            ),
            "confidence": "imported-from-locus-record",
        }
        if uri:
            record["openContextUri"] = uri
        if kobo:
            record["koboRecordId"] = kobo
        loci.append(record)

    if not loci:
        notes.append(
            "no locus rows were read from this export"
            + (f" for trench {wanted_trench}" if wanted_trench else "")
        )

    if unmatched:
        notes.append(
            "no column was matched for: "
            + ", ".join(sorted(unmatched))
            + ". Those fields are empty on every imported locus"
        )

    return {
        "loci": loci,
        "column_map": mapping,
        "unmatched": sorted(unmatched),
        "notes": notes,
    }


def merge_into_sheet(sheet, imported, *, overwrite=False):
    """Fill a field-wall extraction's ``loci`` from imported records.

    Only fills what the sheet is missing unless ``overwrite`` is set. The
    recorder traced the sheet and typed what they saw on it; an import is a
    second source, and quietly preferring it would replace an observation with
    a transcription of a different one.
    """
    if not isinstance(sheet, dict):
        raise LocusImportError("sheet must be an extraction document")

    by_number = {
        canonical_locus(record.get("locusNumber")): record
        for record in imported
        if canonical_locus(record.get("locusNumber"))
    }
    notes = []
    filled = 0

    existing = sheet.setdefault("loci", [])
    seen = set()
    for entry in existing:
        if not isinstance(entry, dict):
            continue
        number = canonical_locus(entry.get("locusNumber"))
        seen.add(number)
        source = by_number.get(number)
        if source is None:
            continue
        for target_key, source_key in (
            ("munsell", "munsell"),
            ("description", "description"),
        ):
            value = source.get(source_key)
            if not value:
                continue
            if entry.get(target_key) and not overwrite:
                if str(entry[target_key]) != str(value):
                    notes.append(
                        f"locus {number}: the sheet records "
                        f"{target_key} {entry[target_key]!r} and the locus "
                        f"record says {value!r}; the sheet's own reading is "
                        "kept"
                    )
                continue
            entry[target_key] = value
            filled += 1
        for key in (
            "openingElevation",
            "closingElevation",
            "openContextUri",
            "koboRecordId",
        ):
            if source.get(key) is not None and entry.get(key) is None:
                entry[key] = source[key]

    for number, source in by_number.items():
        if number not in seen:
            existing.append({k: v for k, v in source.items() if v is not None})
            notes.append(
                f"locus {number} was in the locus record but not on this "
                "sheet; added without boundary geometry"
            )

    if filled:
        notes.append(f"filled {filled} empty field(s) from the locus record")
    return sheet, notes
