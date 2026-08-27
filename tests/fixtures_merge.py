"""Shared synthetic fixture for the multi-wall merge work (contract A6).

Trench "T900", 4 m by 3 m, two adjacent walls sharing the corner (4, 3).
North wall runs from site (0, 3) to (4, 3): bearing 90 (east).
East wall runs from (4, 3) to (4, 0): bearing 180 (south).
Both sheets record the same two loci. Locus 2's Munsell reading disagrees
between the sheets ON PURPOSE (exercises the disagreement note). Vertex
spacing is irregular ON PURPOSE (keeps the validator's even-spacing
fabrication check quiet)."""


def _pts(pairs):
    return [{"xMeters": x, "depthMeters": d} for x, d in pairs]


NORTH_WALL = {
    "trenchLabel": "T900",
    "faceLabel": "north wall",
    "loci": [
        {"locusNumber": "1", "munsell": "10YR 5/3 brown"},
        {"locusNumber": "2", "munsell": "10YR 3/2 very dark grayish brown"},
    ],
    "layers": [
        {
            "locusNumber": "1",
            "topBoundary": _pts(
                [(0.0, 0.02), (0.9, 0.05), (2.1, 0.03), (3.2, 0.07), (4.0, 0.04)]
            ),
            "bottomBoundary": _pts(
                [(0.0, 0.41), (1.1, 0.44), (2.0, 0.39), (3.3, 0.47), (4.0, 0.42)]
            ),
        },
        {
            "locusNumber": "2",
            "topBoundary": _pts(
                [(0.0, 0.41), (1.1, 0.44), (2.0, 0.39), (3.3, 0.47), (4.0, 0.42)]
            ),
            "bottomBoundary": _pts(
                [(0.0, 0.83), (0.8, 0.88), (2.2, 0.81), (3.1, 0.90), (4.0, 0.85)]
            ),
        },
    ],
}

EAST_WALL = {
    "trenchLabel": "T900",
    "faceLabel": "east wall",
    "loci": [
        {"locusNumber": "1", "munsell": "10YR 5/3 brown"},
        # Disagrees with NORTH_WALL on purpose:
        {"locusNumber": "2", "munsell": "10YR 3/1 very dark gray"},
    ],
    "layers": [
        {
            "locusNumber": "1",
            "topBoundary": _pts(
                [(0.0, 0.04), (0.7, 0.06), (1.6, 0.02), (2.4, 0.08), (3.0, 0.05)]
            ),
            "bottomBoundary": _pts(
                [(0.0, 0.42), (0.8, 0.46), (1.5, 0.40), (2.5, 0.48), (3.0, 0.43)]
            ),
        },
        {
            "locusNumber": "2",
            "topBoundary": _pts(
                [(0.0, 0.42), (0.8, 0.46), (1.5, 0.40), (2.5, 0.48), (3.0, 0.43)]
            ),
            "bottomBoundary": _pts(
                [(0.0, 0.86), (0.9, 0.90), (1.7, 0.82), (2.3, 0.91), (3.0, 0.87)]
            ),
        },
    ],
}


def _ipts(pairs):
    return [{"xCoordinateMeters": x, "yCoordinateMeters": d} for x, d in pairs]


# The same trench's west wall, recorded on the other medium: an illustrator
# sheet naming the same two loci. Materials differ from the layer names ON
# PURPOSE (the E2 shape), and layer 2's top is null per the illustrator
# drawing convention (the shared line is drawn once, in layer 1's bottom).
WEST_ILLUSTRATOR = {
    "metadata": {"trenchLabel": "T900"},
    "trenchProfiles": [
        {
            "face": "west baulk",
            "layers": [
                {
                    "layerName": "Locus 1",
                    "inferredMaterial": "compacted silt",
                    "visualPattern": "stipple",
                    "topBoundary": _ipts(
                        [
                            (0.0, 0.03),
                            (0.7, 0.06),
                            (1.6, 0.02),
                            (2.2, 0.07),
                            (3.0, 0.05),
                        ]
                    ),
                    "bottomBoundary": _ipts(
                        [
                            (0.0, 0.43),
                            (0.8, 0.45),
                            (1.4, 0.40),
                            (2.3, 0.46),
                            (3.0, 0.44),
                        ]
                    ),
                },
                {
                    "layerName": "Locus 2",
                    "inferredMaterial": "ashy clay",
                    "topBoundary": None,
                    "bottomBoundary": _ipts(
                        [
                            (0.0, 0.84),
                            (0.9, 0.89),
                            (1.6, 0.83),
                            (2.4, 0.90),
                            (3.0, 0.86),
                        ]
                    ),
                },
            ],
        }
    ],
}

GRID_T900 = {
    "faces": {
        "north wall": {
            "originX": 0.0,
            "originY": 3.0,
            "surfaceZ": 100.0,
            "bearing_deg": 90.0,
        },
        "east wall": {
            "originX": 4.0,
            "originY": 3.0,
            "surfaceZ": 100.0,
            "bearing_deg": 180.0,
        },
    }
}

# North wall plus the illustrator west baulk: the west wall runs south from
# the shared corner (0, 3), so the two walls close at the trench's NW corner.
GRID_T900_WEST = {
    "faces": {
        "north wall": {
            "originX": 0.0,
            "originY": 3.0,
            "surfaceZ": 100.0,
            "bearing_deg": 90.0,
        },
        "west baulk": {
            "originX": 0.0,
            "originY": 3.0,
            "surfaceZ": 100.0,
            "bearing_deg": 180.0,
        },
    }
}

# Surface identities the merge should produce from this fixture. Identity is
# the locus number alone: the fixture's two walls disagree about locus 2's
# Munsell reading ON PURPOSE, and they must still model one surface.
SURFACE_L1 = "Locus 1"
SURFACE_L2 = "Locus 2"

# The display labels those surfaces carry. Locus 2 takes the NORTH wall's
# reading because that sheet comes first; the east wall's differing reading is
# reported as a note rather than resolved away.
LABEL_L1 = "Locus 1 (10YR 5/3 brown)"
LABEL_L2 = "Locus 2 (10YR 3/2 very dark grayish brown)"
