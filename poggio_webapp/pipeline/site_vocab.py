"""The site's own controlled vocabularies and identifier formats.

Every list and format here is transcribed from Poggio Civitate's recording
standards, not invented for this application:

  * bulk-find material letters and the ``bf-``/``sf-`` identifier formats --
    *Conservation Kobo Form Instructions*, restated in
    *2025 Poggio Civitate Kobo Deployment Data Entry*
  * catalogued-object numbers (``pc``/``vdm``) -- the same two documents
  * total-station feature codes -- *260715 Murlo Site Total Station Workflow*

A leaf module, like ``naming`` and ``storage``: it imports nothing from this
package so that both the pipeline and the route layer can depend on it.

Why this exists at all: the application previously carried its own parallel
vocabularies -- a hand-written feature-type list in the drawing UI, and
``uuid4`` find identifiers -- which meant nothing it recorded could be matched
against the project's own records without a human translating. Identifiers are
the part of a record that has to survive leaving the machine that made it.

Case: hand-written tags use lowercase (``sf-t108-2024-2-2``) while the Kobo
form examples use the canonical trench spelling (``sf-T111-2025-1-1``). Both
name the same find, so parsing is case-insensitive and construction emits the
canonical form. ``as_tag`` renders the lowercase variant for writing on a tag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from naming import canonical_locus, canonical_trench

# Vocabularies

# The letter codes used in bulk-find identifiers. 'O' takes a free suffix
# ("O-Slag", "O-Iron", "O-Bronze") when a trench needs to separate several
# kinds of other material.
BULK_MATERIALS = {
    "T": "Tile",
    "P": "Plaster",
    "C": "Pottery/Ceramic",
    "B": "Bone",
    "M": "Metal",
    "S": "Stone",
    "A": "Architectural",
    "O": "Other",
}

# The four categories every trench bulk-finds from the start, in the
# procedures' own words. Kept separate from BULK_MATERIALS because these are
# the *default* collection categories, not the full letter vocabulary.
DEFAULT_BULK_CATEGORIES = (
    "Non-decorative terracotta tiles (pan and cover tiles)",
    "Plaster",
    "Pottery",
    "Bone",
)

# Total-station point codes. Relevant here because a shot carries Northing,
# Easting and Elevation on the local grid -- i.e. exactly the interface points
# this application otherwise reconstructs from drawings.
SURVEY_POINT_CODES = {
    "CTRL": "Control point",
    "UNIT": "Unit corner",
    "WALL": "Wall",
    "STONE": "Isolated stone",
    "ART": "Artifact",
    "FEAT": "Feature",
    "TEST": "Test pit",
    "TOPO": "Ground surface",
}

# What a recorder can mark on a drawing. Ordered for a dropdown: the things
# actually drawn on the T104 sheets first.
#
# `material` entries carry a bulk-find letter so a drawn shape can be matched
# to the material record. `unit` entries are stratigraphic and carry a Harris
# unit type instead -- they are contexts, not finds. `intrusion` is neither:
# a tree stump is modern root disturbance, and filing it as either a find or a
# deposit would misrepresent it.
DRAWN_FEATURE_TYPES = (
    {
        "key": "stone",
        "label": "Stone",
        "kind": "material",
        "material": "S",
        "surveyCode": "STONE",
    },
    {
        "key": "terracotta",
        "label": "Terracotta (tile)",
        "kind": "material",
        "material": "T",
        "surveyCode": None,
    },
    {
        "key": "bone",
        "label": "Bone",
        "kind": "material",
        "material": "B",
        "surveyCode": None,
    },
    {
        "key": "pottery",
        "label": "Pottery/Ceramic",
        "kind": "material",
        "material": "C",
        "surveyCode": None,
    },
    {
        "key": "architectural",
        "label": "Architectural terracotta",
        "kind": "material",
        "material": "A",
        "surveyCode": None,
    },
    {
        "key": "plaster",
        "label": "Plaster",
        "kind": "material",
        "material": "P",
        "surveyCode": None,
    },
    {
        "key": "metal",
        "label": "Metal",
        "kind": "material",
        "material": "M",
        "surveyCode": None,
    },
    {
        "key": "wall",
        "label": "Wall",
        "kind": "unit",
        "unitType": "structure",
        "surveyCode": "WALL",
    },
    {
        "key": "cut",
        "label": "Cut",
        "kind": "unit",
        "unitType": "cut",
        "surveyCode": None,
    },
    {
        "key": "interface",
        "label": "Interface / surface",
        "kind": "unit",
        "unitType": "interface",
        "surveyCode": None,
    },
    {
        "key": "natural",
        "label": "Natural",
        "kind": "unit",
        "unitType": "natural",
        "surveyCode": None,
    },
    {
        "key": "void",
        "label": "Void",
        "kind": "unit",
        "unitType": "interface",
        "surveyCode": None,
    },
    {
        "key": "tree-stump",
        "label": "Tree stump",
        "kind": "intrusion",
        "surveyCode": None,
    },
    {
        "key": "other",
        "label": "Other",
        "kind": "other",
        "material": "O",
        "surveyCode": None,
    },
)

# The Harris unit vocabulary already modelled in pipeline/harris_matrix.py.
# Repeated here only so DRAWN_FEATURE_TYPES can be checked against it.
HARRIS_UNIT_TYPES = frozenset(
    {"deposit", "cut", "structure", "interface", "natural", "unknown"}
)


def feature_type(key):
    """One DRAWN_FEATURE_TYPES entry by key, or None."""
    for entry in DRAWN_FEATURE_TYPES:
        if entry["key"] == key:
            return entry
    return None


def material_name(code):
    """'Tile' for 'T'. Accepts the 'O-Slag' suffix form."""
    if not isinstance(code, str):
        return None
    head, _, suffix = code.strip().upper().partition("-")
    name = BULK_MATERIALS.get(head)
    if name is None:
        return None
    if head == "O" and suffix:
        return f"Other ({suffix.title()})"
    return name


# Identifiers

_MATERIAL_PART = r"[A-Za-z](?:-[A-Za-z]+)?"
_SPECIAL_FIND = re.compile(
    r"^sf-([A-Za-z]{1,4}\d+)-(\d{4})-(\d+)-(\d+)$", re.IGNORECASE
)
_BULK_FIND = re.compile(
    rf"^bf-([A-Za-z]{{1,4}}\d+)-(\d{{4}})-(\d+)-({_MATERIAL_PART})$",
    re.IGNORECASE,
)
_CATALOGUED = re.compile(r"^(pc|vdm)\s*(\d{4})(\d{4})$", re.IGNORECASE)


class VocabError(ValueError):
    """A malformed identifier, with a message naming what is wrong."""


@dataclass(frozen=True)
class FindId:
    """A parsed site identifier.

    ``kind`` is 'special', 'bulk' or 'catalogued'. ``material`` is set only for
    bulk finds, ``number`` only for special and catalogued ones.
    """

    kind: str
    text: str
    trench: str | None = None
    year: str | None = None
    locus: str | None = None
    number: str | None = None
    material: str | None = None

    def as_tag(self) -> str:
        """The lowercase form used on hand-written tags."""
        return self.text.lower()


def _year(value):
    text = str(value).strip()
    if not re.fullmatch(r"\d{4}", text):
        raise VocabError(
            f"year must be four digits, got {value!r} -- the identifier "
            "formats use a 4-digit season (e.g. 2025)"
        )
    return text


def _required(name, value, canonical):
    result = canonical(value)
    if not result:
        raise VocabError(f"{name} is required and cannot be blank")
    return result


def special_find_id(trench, year, locus, number) -> str:
    """``sf-T111-2025-1-1`` -- special/supplemental find."""
    trench = _required("trench", trench, canonical_trench)
    locus = _required("locus", locus, canonical_locus)
    number = _required("find number", number, canonical_locus)
    return f"sf-{trench}-{_year(year)}-{locus}-{number}"


def bulk_find_id(trench, year, locus, material) -> str:
    """``bf-T104-2025-1-T`` -- bulk find, material by letter code."""
    trench = _required("trench", trench, canonical_trench)
    locus = _required("locus", locus, canonical_locus)
    if material_name(material) is None:
        allowed = ", ".join(sorted(BULK_MATERIALS))
        raise VocabError(
            f"material {material!r} is not a bulk-find code (expected one of "
            f"{allowed}, optionally suffixed like 'O-Slag')"
        )
    head, _, suffix = str(material).strip().upper().partition("-")
    code = f"{head}-{suffix.title()}" if suffix else head
    return f"bf-{trench}-{_year(year)}-{locus}-{code}"


def catalogued_id(prefix, year, number) -> str:
    """``pc20240001`` -- catalogued object, number zero-padded to four."""
    prefix = str(prefix).strip().lower()
    if prefix not in ("pc", "vdm"):
        raise VocabError(f"catalogue prefix {prefix!r} must be 'pc' or 'vdm'")
    text = str(number).strip()
    if not text.isdigit() or len(text) > 4:
        raise VocabError(f"catalogue number {number!r} must be at most four digits")
    return f"{prefix}{_year(year)}{int(text):04d}"


def parse_find_id(text) -> FindId:
    """Parse any of the three identifier formats. Raises VocabError."""
    if not isinstance(text, str) or not text.strip():
        raise VocabError("identifier is empty")
    raw = text.strip()

    match = _SPECIAL_FIND.match(raw)
    if match:
        trench, year, locus, number = match.groups()
        return FindId(
            kind="special",
            text=f"sf-{canonical_trench(trench)}-{year}-{locus}-{number}",
            trench=canonical_trench(trench),
            year=year,
            locus=locus,
            number=number,
        )

    match = _BULK_FIND.match(raw)
    if match:
        trench, year, locus, material = match.groups()
        head, _, suffix = material.upper().partition("-")
        if head not in BULK_MATERIALS:
            raise VocabError(
                f"{raw!r} carries material code {head!r}, which is not one of "
                + ", ".join(sorted(BULK_MATERIALS))
            )
        code = f"{head}-{suffix.title()}" if suffix else head
        return FindId(
            kind="bulk",
            text=f"bf-{canonical_trench(trench)}-{year}-{locus}-{code}",
            trench=canonical_trench(trench),
            year=year,
            locus=locus,
            material=code,
        )

    match = _CATALOGUED.match(raw)
    if match:
        prefix, year, number = match.groups()
        return FindId(
            kind="catalogued",
            text=f"{prefix.lower()}{year}{number}",
            year=year,
            number=number,
        )

    raise VocabError(
        f"{raw!r} is not a recognised site identifier. Expected "
        "'sf-<trench>-<year>-<locus>-<n>', "
        "'bf-<trench>-<year>-<locus>-<material letter>', "
        "or a catalogue number like 'pc20240001'"
    )
