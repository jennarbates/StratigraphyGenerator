"""The wall drawings the demo needs and no record on disk contains.

A trench's *layout* -- corners, elevations, the datum -- comes from the survey,
and the fixtures have it. Its *walls* come from four drawn sheets, and neither
the fixtures nor ``scans/`` hold any for these trenches. Without them there is
nothing to merge, so the build refuses for a reason that has nothing to teach:
"no jobs are labelled trench T905".

So the demo draws them. Each locus boundary is placed at the mean closing
elevation the fixture records for that locus, given a small deterministic
undulation so the four walls are not four identical planes. Depth is measured
down from each wall's own origin corner, which is why the west wall's layers
sit half a metre deeper than the south wall's: its corner is the one standing
on the old spoil heap, and the fixture says so.

This is invented geometry. ``seed`` will not generate it for a dataset marked
``real_records`` -- putting invented sections under a real trench's label is
the one thing the rest of this codebase consistently refuses to do, and a
demonstration is not a good enough reason to be the exception.
"""

import math

# The three deposits that run across the whole trench. Loci 4 and 5 are
# standing structures and 6-8 are confined to the sounding, so none of them
# appears as a layer on all four walls.
SPANNING_LOCI = (1, 2, 3)

# Points per boundary. Enough for the interpolator to have something to work
# with, few enough that the JSON stays readable.
SAMPLES = 11

# Peak undulation on an internal boundary. Deposit surfaces are not flat, and a
# stack of perfect planes models suspiciously well.
UNDULATION_M = 0.03

CONFIDENCE = "synthetic"


def mean_closing_elevations(loci_document: dict) -> dict[int, float]:
    """{locus number: mean closing elevation} for the spanning deposits.

    The mean rather than any single vertex: a locus closes at a surface, and
    these fixtures record between four and ten readings across it.
    """
    elevations = {}
    for locus in loci_document.get("loci") or []:
        number = locus.get("locus")
        if number not in SPANNING_LOCI:
            continue
        readings = [
            vertex["elevation"]
            for vertex in (locus.get("closing_vertices") or [])
            if isinstance(vertex.get("elevation"), (int, float))
        ]
        if readings:
            elevations[number] = sum(readings) / len(readings)

    missing = [n for n in SPANNING_LOCI if n not in elevations]
    if missing:
        raise ValueError(
            "the loci record has no closing elevations for loci "
            + ", ".join(str(n) for n in missing)
            + ", so no wall section can be drawn from it"
        )
    return elevations


def _boundary(depth_m: float, length_m: float, phase: float, *, flat=False):
    """One boundary, sampled across the wall.

    ``flat`` is the ground surface: it is the datum every other depth on this
    sheet is measured from, so giving it its own wobble would be measuring
    depths from a line that is not where the tape was held.
    """
    points = []
    for index in range(SAMPLES):
        fraction = index / (SAMPLES - 1)
        x = round(fraction * length_m, 4)
        offset = (
            0.0 if flat else UNDULATION_M * math.sin(2 * math.pi * fraction + phase)
        )
        points.append(
            {
                "xMeters": x,
                "depthMeters": round(depth_m + offset, 4),
                "confidence": CONFIDENCE,
                "uncertaintyCm": None,
            }
        )
    return points


def wall_profile(
    loci_document: dict,
    *,
    trench_label: str,
    wall_label: str,
    surface_z: float,
    length_m: float,
    phase_index: int,
) -> dict:
    """One FieldWallProfile-shaped sheet for one wall of the trench.

    ``surface_z`` is that wall's origin-corner opening elevation. It converts
    the fixture's absolute elevations into the depths a field sheet actually
    records, which is the form the rest of the pipeline reads.
    """
    elevations = mean_closing_elevations(loci_document)
    by_number = {
        locus.get("locus"): locus for locus in (loci_document.get("loci") or [])
    }
    phase = phase_index * math.pi / 2

    # The ground surface, then one closing surface per spanning locus. Each
    # boundary object is generated once and shared by the layer above and the
    # layer below it, so the two never drift apart by a rounding step.
    surfaces = [_boundary(0.0, length_m, phase, flat=True)]
    for number in SPANNING_LOCI:
        surfaces.append(_boundary(surface_z - elevations[number], length_m, phase))

    loci = []
    layers = []
    for position, number in enumerate(SPANNING_LOCI):
        record = by_number.get(number) or {}
        loci.append(
            {
                "locusNumber": str(number),
                "munsell": {
                    "raw": (record.get("munsell") or "").split(" ", 2)[0] or None,
                    "colorName": record.get("munsell"),
                },
                "description": record.get("summary"),
                "confidence": CONFIDENCE,
            }
        )
        layers.append(
            {
                "locusNumber": str(number),
                "topBoundary": surfaces[position],
                "bottomBoundary": surfaces[position + 1],
                "featuresInLayer": [],
            }
        )

    return {
        "trenchLabel": trench_label,
        "faceLabel": wall_label,
        "illustrators": [],
        "date": f"{loci_document.get('season', '')}-07-01",
        "northArrowPresent": True,
        "gridSquareCm": 20.0,
        "gridTiePoints": [],
        "loci": loci,
        "layers": layers,
        "marginalia": [
            "Section generated by the demo seeder, not drawn in the field. "
            "Boundary elevations follow the locus record; the undulation "
            "between the recorded readings is invented."
        ],
    }
