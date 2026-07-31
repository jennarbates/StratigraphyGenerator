"""Reading the season's Geospatial Spreadsheet.

*Excavation and Documentation Procedures* sends every trench's corners here:

    please record your coordinates in the Geospatial Spreadsheet, under the
    "Opening Coordinates" column. The Geospatial Spreadsheet will be found in
    the Field and Mag Google Drive folder within the appropriate year's
    subfolder

So the numbers this application otherwise asks an operator to type -- origin,
bearing, wall length -- already exist, for every trench of a season, in one
file. This reads it and hands each trench to ``trench_layout``.

Three things about the sheet's shape drive the parsing:

**A trench spans several rows.** Only the first carries the trench id; the rest
are continuation rows holding the remaining corners and any second supervisor.
A blank id means "still the previous trench", not "no trench".

**Coordinates arrive already signed.** Cells read ``NW: 190/-53``, not
``190E/53S``. The cardinal inversion was applied before the number reached the
sheet, which is the fourth independent confirmation of the rule in
``site_grid`` -- and the first from live records rather than documentation. No
inversion is applied here; that would apply it twice.

**Not every trench is a rectangle.** Trenches extended mid-season have eight
corners and unlabelled cells, and their closing outline differs from their
opening one. Both phases are read, and which one a model registers to is the
operator's decision rather than this module's.

Nothing here carries elevation: the sheet has no Z column at all. What it has
instead is a set of *Adjusted Elevations* flags recording whether below-datum
readings have been corrected to absolute in each kind of record yet -- which is
worth surfacing, because a trench whose flags are still false has no usable
elevations anywhere.
"""

from __future__ import annotations

import csv
import io
import re

from naming import canonical_trench

# "NW: 190/-53", "212.27/62.84", "SE: 211/-32 ". The corner label is optional:
# the extra vertices of an extended trench are written without one.
_CORNER = re.compile(
    r"^\s*(?:(NW|NE|SE|SW|N|S|E|W)\s*:\s*)?"
    r"(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

_TRENCH_ID = re.compile(r"^[A-Za-z]{1,4}\d+$")

OPENING = "opening"
CLOSING = "closing"
PHASES = (OPENING, CLOSING)

# Column headings, as they appear in the 2025 sheet. Matched loosely so a
# heading that gains a word or changes its punctuation still lands.
_COLUMNS = {
    "trench": ("trench",),
    "supervisor": ("trenchsupervisors", "trenchsupervisor"),
    "secondary": ("secondarysupervisors", "secondarysupervisor"),
    "trenchbook": ("trenchbooktitle",),
    OPENING: ("openingcoordinatesxy", "openingcoordinates"),
    CLOSING: ("closingcoordinatesxy", "closingcoordinates"),
    "state": ("openclosed",),
    "notes": ("othernotes", "notes"),
}

# The compliance flags. Their values are TRUE/FALSE/N/A, not elevations.
_ADJUSTED_PREFIX = "adjustedelevations"


class SheetError(ValueError):
    """A sheet that cannot be read. The message is user-facing."""


def _normalize(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _map_columns(headers):
    by_normalized = {}
    for header in headers:
        by_normalized.setdefault(_normalize(header), header)

    mapping = {}
    for field, candidates in _COLUMNS.items():
        for candidate in candidates:
            if candidate in by_normalized:
                mapping[field] = by_normalized[candidate]
                break

    adjusted = [
        header for header in headers
        if _normalize(header).startswith(_ADJUSTED_PREFIX)
    ]
    return mapping, adjusted


def parse_corner(text):
    """``"NW: 190/-53"`` -> ``("NW", 190.0, -53.0)``. None when not a corner.

    The values are taken as written. They are already Grid X and Grid Y with
    South and West negative, so applying the cardinal inversion here would
    apply it twice and mirror the site.
    """
    if not isinstance(text, str):
        return None
    match = _CORNER.match(text)
    if not match:
        return None
    label, x, y = match.groups()
    return (label.upper() if label else None), float(x), float(y)


def wall_names(corners):
    """Default wall names from the corner labels, or '' where none applies.

    Two consecutive corners that share a cardinal letter name the wall between
    them: NW to NE is the north wall, NE to SE the east wall. An extended
    trench's unlabelled vertices get '' and have to be named by the operator --
    guessing "wall 5" would put a name in the grid config that matches nothing
    on any drawing.
    """
    names = []
    count = len(corners)
    for index in range(count):
        here = corners[index].get("corner")
        following = corners[(index + 1) % count].get("corner")
        if not here or not following:
            names.append("")
            continue
        shared = set(here) & set(following) & set("NSEW")
        if len(shared) == 1:
            names.append({
                "N": "north wall", "S": "south wall",
                "E": "east wall", "W": "west wall",
            }[shared.pop()])
        else:
            names.append("")
    return names


def read_sheet(text):
    """Parse a Geospatial Spreadsheet export.

    Returns ``{"trenches": {label: record}, "notes": [...]}``. Each record has
    ``opening`` and ``closing`` corner lists, the supervisors, the trenchbook
    title, the open/closed state and the elevation-adjustment flags.
    """
    if not isinstance(text, str) or not text.strip():
        raise SheetError("this spreadsheet is empty")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise SheetError("this spreadsheet has no header row")

    mapping, adjusted_columns = _map_columns(reader.fieldnames)
    for required in ("trench", OPENING):
        if required not in mapping:
            raise SheetError(
                f"this spreadsheet has no {required} column. Its columns are: "
                + ", ".join(repr(name) for name in reader.fieldnames)
                + ". This reader expects the season's Geospatial Spreadsheet"
            )

    def cell(row, field):
        header = mapping.get(field)
        return (row.get(header) or "").strip() if header else ""

    trenches = {}
    notes = []
    current = None

    for line, row in enumerate(reader, start=2):
        raw_id = cell(row, "trench")
        if raw_id:
            if _TRENCH_ID.match(raw_id):
                current = canonical_trench(raw_id)
                trenches[current] = {
                    "trench": current,
                    "recorded_label": raw_id,
                    "supervisors": [],
                    "trenchbook": cell(row, "trenchbook") or None,
                    "state": cell(row, "state") or None,
                    "notes": [],
                    OPENING: [],
                    CLOSING: [],
                    "adjusted_elevations": {
                        header: (row.get(header) or "").strip()
                        for header in adjusted_columns
                    },
                }
            else:
                notes.append(
                    f"row {line}: {raw_id!r} in the trench column is not a "
                    "trench identifier; ignored, and the row is read as part "
                    f"of {current or 'no trench'}")

        if current is None:
            continue

        record = trenches[current]
        for field in ("supervisor", "secondary"):
            person = cell(row, field)
            if person and person not in record["supervisors"]:
                record["supervisors"].append(person)

        for phase in PHASES:
            value = cell(row, phase)
            if not value:
                continue
            corner = parse_corner(value)
            if corner is None:
                # The notes column bleeds into these cells in the real sheet
                # (an email address, a sentence about missing forms), so this
                # is expected rather than a fault.
                record["notes"].append(f"row {line} ({phase}): {value}")
                continue
            name, x, y = corner
            # `corner` is the corner's name -- NW, SE. Deliberately not
            # `label`, which in a trench_layout means a grid label like
            # "190E/53S". Two different things, one word.
            record[phase].append({"corner": name, "gridX": x, "gridY": y})

        # The Adjusted Elevations columns are TRUE/FALSE/N/A flags, but the
        # real sheet also carries free text there -- an email address, a
        # sentence about which forms were corrected. Kept as notes rather than
        # read as a flag value.
        for header in adjusted_columns:
            value = (row.get(header) or "").strip()
            if value and value.upper() not in ("TRUE", "FALSE", "N/A"):
                record["notes"].append(f"{header.strip()}: {value}")

        free_text = cell(row, "notes")
        if free_text:
            record["notes"].append(free_text)

    if not trenches:
        notes.append("no trenches were read from this spreadsheet")
    return {"trenches": trenches, "notes": notes}


def elevation_readiness(record):
    """What the Adjusted Elevations flags say about this trench.

    The flags track whether below-datum readings have been corrected to
    absolute in each kind of record. They are not elevations, and this sheet
    holds none -- so a trench whose flags are still false has no usable
    elevation anywhere, and a model of it cannot be built to real heights yet.
    """
    flags = record.get("adjusted_elevations") or {}
    outstanding = [
        header for header, value in flags.items()
        if value.strip().upper() == "FALSE"
    ]
    if not flags:
        return []
    if not outstanding:
        return []
    return [
        "elevations have not been corrected to absolute for "
        + ", ".join(
            header.split(":", 1)[-1].strip() or header
            for header in outstanding
        )
        + ". Until they are, this trench has no elevations this application "
        "can build a model to"
    ]


def layout_for(record, phase=OPENING, *, walls=None, site_grid=None,
               vertical=None):
    """A ``trench_layout`` layout for one trench of this sheet.

    ``walls`` overrides the names derived from the corner labels, and is
    required for an extended trench whose extra vertices are unlabelled.
    """
    if phase not in PHASES:
        raise SheetError(f"phase must be one of {', '.join(PHASES)}")

    corners = [dict(corner) for corner in record.get(phase) or []]
    if not corners:
        raise SheetError(
            f"this trench has no {phase} coordinates in the spreadsheet")

    derived = wall_names(corners)
    resolved = list(walls) if walls else derived
    if len(resolved) != len(corners):
        raise SheetError(
            f"this trench has {len(corners)} {phase} corners, so it needs "
            f"{len(corners)} wall names; {len(resolved)} were given")
    unnamed = [index + 1 for index, name in enumerate(resolved) if not name]
    if unnamed:
        raise SheetError(
            "the corner labels do not name wall(s) "
            + ", ".join(str(index) for index in unnamed)
            + ". An extended trench's extra vertices are recorded without "
            "labels, so name its walls explicitly -- an invented name would "
            "match nothing on any drawing"
        )

    return {
        "site_grid": site_grid,
        "vertical": vertical,
        "corners": corners,
        "walls": resolved,
    }
