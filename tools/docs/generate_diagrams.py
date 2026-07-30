"""Generate the documentation's spatial diagrams as deterministic SVGs.

Only diagrams that are genuinely *spatial* live here -- anatomy of a trench
section, the three coordinate spaces, four walls around a pit. Flows, trees,
and sequences are Mermaid fences inline in the Markdown instead: same source
renders on GitHub and in the built site, with no file to keep in step.

Every diagram produced here satisfies the manifest's SVG contract, which
`validate_visual_manifest.py` enforces:

* a `viewBox`, and no fixed pixel width, so it scales
* a `<title>` and `<desc>` for screen readers
* legible at 720 CSS pixels wide
* no embedded raster data
* state carried by shape and text, never by colour alone
* readable in both light and dark themes

Regenerate with:

    python tools/docs/generate_diagrams.py
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
from xml.sax.saxutils import escape

# One light palette, and each diagram paints its own background.
#
# An earlier version flipped colours with `prefers-color-scheme`. That is the
# wrong mechanism here: an SVG loaded through <img> cannot see the page's
# stylesheet, so the query tracks the reader's *operating system* rather than
# the theme of the page the diagram sits on. A reader with a dark OS viewing
# the light MkDocs site got dark diagrams with near-invisible headings.
#
# A self-contained light card is predictable instead: it renders identically
# everywhere, and stays legible on a dark GitHub README as an ordinary light
# figure.
STYLE = """
:root {
  --bg: #ffffff; --ink: #1b1b1b; --muted: #5c5c5c; --line: #6b6b6b;
  --panel: #f7f9fb; --fill: #e8edf2; --edge: #b3bcc5;
  --accent: #1f6feb; --warn: #a8481a; --good: #266048;
  --band-a: #ddcdb2; --band-b: #c8ae80; --band-c: #ac8f63; --band-d: #8f7248;
}
text { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
       fill: var(--ink); font-size: 15px; }
.sm { font-size: 13px; }
.muted { fill: var(--muted); }
.bold { font-weight: 650; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
.panel { fill: var(--panel); stroke: var(--edge); stroke-width: 1.5; }
.fill { fill: var(--fill); stroke: var(--edge); stroke-width: 1.5; }
.edge { fill: none; stroke: var(--line); stroke-width: 2; }
.thin { fill: none; stroke: var(--edge); stroke-width: 1; }
.accent { stroke: var(--accent); fill: none; stroke-width: 2.5; }
.accent-f { fill: var(--accent); }
.warn { stroke: var(--warn); fill: none; stroke-width: 2.5; }
.warn-f { fill: var(--warn); }
.good { stroke: var(--good); fill: none; stroke-width: 2.5; }
.good-f { fill: var(--good); }
.dash { stroke-dasharray: 6 4; }
.dot { stroke-dasharray: 2 3; }
"""


def document(
    view_w: int,
    view_h: int,
    title: str,
    desc: str,
    body: str,
    extra_defs: str = "",
) -> str:
    """Wrap diagram body markup in a complete, accessible SVG document."""

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}" '
        f'role="img" aria-labelledby="t d">\n'
        f"  <title id=\"t\">{escape(title)}</title>\n"
        f"  <desc id=\"d\">{escape(desc)}</desc>\n"
        f"  <style>{STYLE}</style>\n"
        f"  <defs>\n"
        f'    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        f'      <path d="M0,0 L10,5 L0,10 z" fill="var(--line)"/>\n'
        f"    </marker>\n"
        f'    <marker id="arrow-a" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        f'      <path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/>\n'
        f"    </marker>\n"
        f"{extra_defs}"
        f"  </defs>\n"
        f'  <rect width="{view_w}" height="{view_h}" fill="var(--bg)"/>\n'
        f"{body}\n"
        f"</svg>\n"
    )


# ----------------------------------------------------------------- primitives


def txt(x, y, s, cls="", anchor="start") -> str:
    attrs = f' class="{cls}"' if cls else ""
    return (
        f'  <text x="{x}" y="{y}" text-anchor="{anchor}"{attrs}>{escape(str(s))}</text>'
    )


def box(x, y, w, h, cls="panel", rx=6) -> str:
    return f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>'


def labelled_box(x, y, w, h, label, sub=None, cls="panel") -> str:
    parts = [box(x, y, w, h, cls)]
    if sub:
        parts.append(txt(x + w / 2, y + h / 2 - 4, label, "bold", "middle"))
        parts.append(txt(x + w / 2, y + h / 2 + 15, sub, "sm muted", "middle"))
    else:
        parts.append(txt(x + w / 2, y + h / 2 + 5, label, "bold", "middle"))
    return "\n".join(parts)


def arrow(x1, y1, x2, y2, cls="edge", marker="arrow") -> str:
    return (
        f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" '
        f'marker-end="url(#{marker})"/>'
    )


def path(d, cls="edge", marker=None) -> str:
    m = f' marker-end="url(#{marker})"' if marker else ""
    return f'  <path d="{d}" class="{cls}"{m}/>'


def poly(points, cls="edge") -> str:
    d = " ".join(f"{x},{y}" for x, y in points)
    return f'  <polyline points="{d}" class="{cls}"/>'


def dot(x, y, r=4, cls="accent-f") -> str:
    return f'  <circle cx="{x}" cy="{y}" r="{r}" class="{cls}"/>'


def heading(x, y, s) -> str:
    return txt(x, y, s, "bold")


def band(x, y, w, h, colour) -> str:
    """One stratigraphic layer, filled with a named band colour."""
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'fill="var(--{colour})" stroke="var(--edge)" stroke-width="1.5"/>'
    )


def wavy(x0, x1, y, amp=6, steps=6) -> str:
    """A hand-drawn-looking boundary between two deposits."""
    step = (x1 - x0) / steps
    d = f"M{x0},{y}"
    for i in range(steps):
        cx = x0 + step * (i + 0.5)
        cy = y + (amp if i % 2 == 0 else -amp)
        d += f" Q{cx},{cy} {x0 + step * (i + 1)},{y}"
    return d


# ------------------------------------------------------------------- diagrams


def glossary_anatomy() -> str:
    b = [
        heading(24, 30, "One trench section, with every term it defines"),
        band(60, 60, 480, 60, "band-a"),
        band(60, 120, 480, 70, "band-b"),
        band(60, 190, 480, 80, "band-c"),
        band(60, 270, 480, 60, "band-d"),
        path(wavy(60, 540, 120), "edge"),
        path(wavy(60, 540, 190), "edge"),
        path(wavy(60, 540, 270), "edge"),
        '  <ellipse cx="300" cy="225" rx="46" ry="26" class="fill"/>',
        txt(300, 230, "feature", "sm", "middle"),
        arrow(600, 90, 548, 90),
        txt(608, 95, "layer — one deposit"),
        arrow(600, 150, 548, 128),
        txt(608, 155, "boundary — the surface between two"),
        arrow(600, 225, 350, 225),
        txt(608, 230, "feature — inclusion inside a layer"),
        arrow(600, 300, 548, 300),
        txt(608, 305, "locus — the excavator's number"),
        '  <line x1="60" y1="345" x2="540" y2="345" class="thin"/>',
        txt(300, 368, "face — one wall of the trench, drawn on one sheet",
            "sm muted", "middle"),
        txt(24, 400, "The trench is the whole excavated hole; this is one of its faces.",
            "sm muted"),
    ]
    return document(
        980, 420,
        "Anatomy of a trench section",
        "A stratigraphic section with four layers, the boundaries between them, "
        "an internal feature, and labels naming layer, boundary, feature, locus, "
        "and face.",
        "\n".join(b),
    )


def three_coordinate_spaces() -> str:
    panels = [(40, "Pixel space", "origin top-left, y grows down"),
              (350, "Face-local metres", "origin at the face's x=0, depth grows down"),
              (660, "Site coordinates", "surveyed X, Y, Z across the whole site")]
    b = [heading(24, 30, "The same point, in all three spaces")]
    for x, name, sub in panels:
        b += [box(x, 50, 280, 250, "panel"),
              txt(x + 14, 76, name, "bold"),
              txt(x + 14, 96, sub, "sm muted")]
    # pixel panel. The axes are labelled at the end each one grows toward:
    # x to the right, y downward.
    b += ['  <rect x="80" y="132" width="210" height="132" class="fill"/>',
          dot(180, 200), txt(190, 195, "(1240, 860)", "mono"),
          arrow(72, 124, 72, 276), arrow(72, 124, 296, 124),
          txt(292, 116, "x px", "sm muted", "end"),
          txt(80, 292, "y px", "sm muted")]
    # local panel
    b += ['  <rect x="380" y="132" width="210" height="132" class="fill"/>',
          dot(452, 200), txt(462, 195, "(2.10, 0.85) m", "mono"),
          txt(386, 292, "x metres along the face", "sm muted"),
          txt(386, 152, "depth below surface", "sm muted")]
    # site panel
    b += ['  <rect x="690" y="132" width="210" height="132" class="fill"/>',
          dot(762, 200), txt(772, 195, "(X, Y, Z)", "mono"),
          txt(696, 292, "north-oriented site grid", "sm muted")]
    b += [arrow(325, 175, 348, 175, "accent", "arrow-a"),
          arrow(635, 175, 658, 175, "accent", "arrow-a"),
          txt(180, 330, "three calibration clicks", "sm accent-f", "middle"),
          txt(180, 348, "+ one real measurement", "sm accent-f", "middle"),
          txt(490, 330, "registration per face", "sm accent-f", "middle"),
          txt(490, 348, "originX, originY, surfaceZ, bearing", "sm accent-f", "middle"),
          txt(24, 386,
              "Most confusion in this project is a mix-up between two of these.",
              "sm muted")]
    return document(
        960, 405,
        "The three coordinate spaces",
        "One point shown in pixel coordinates, in face-local metres, and in "
        "surveyed site coordinates, with the conversion required between each pair.",
        "\n".join(b),
    )


def calibration_clicks() -> str:
    b = [
        heading(24, 30, "Three clicks turn pixels into metres"),
        box(40, 50, 520, 300, "fill"),
        band(60, 90, 480, 70, "band-a"),
        band(60, 160, 480, 90, "band-b"),
        band(60, 250, 480, 80, "band-c"),
        path(wavy(60, 540, 160), "edge"),
        path(wavy(60, 540, 250), "edge"),
        dot(110, 100, 7), txt(110, 84, "1", "bold accent-f", "middle"),
        dot(470, 100, 7), txt(470, 84, "2", "bold accent-f", "middle"),
        dot(300, 330, 7), txt(300, 352, "3", "bold accent-f", "middle"),
        '  <line x1="110" y1="100" x2="470" y2="100" class="accent dash"/>',
        txt(290, 118, "a distance you measured on the sheet",
            "sm accent-f", "middle"),
        heading(600, 80, "Click 1 and 2"),
        txt(600, 102, "Two points a known real", "sm"),
        txt(600, 120, "distance apart. This sets", "sm"),
        txt(600, 138, "the scale.", "sm"),
        heading(600, 180, "Click 3"),
        txt(600, 202, "The lowest point anywhere", "sm"),
        txt(600, 220, "on the drawing. This sets", "sm"),
        txt(600, 238, "the depth reference.", "sm"),
        heading(600, 285, "Then type the width"),
        txt(600, 307, "The real distance between", "sm"),
        txt(600, 325, "clicks 1 and 2, in metres.", "sm"),
        txt(24, 382,
            "Clicks too close together make the scale unstable; spread them out.",
            "sm muted"),
    ]
    return document(
        960, 400,
        "The three calibration clicks",
        "A trench drawing with three numbered calibration points: two defining a "
        "known horizontal distance, and a third setting the depth reference.",
        "\n".join(b),
    )


def boundary_anatomy() -> str:
    b = [
        heading(24, 30, "You trace boundaries. A layer is what lies between two."),
        band(60, 70, 400, 70, "band-a"),
        band(60, 140, 400, 90, "band-b"),
        band(60, 230, 400, 70, "band-c"),
        path(wavy(60, 460, 140), "accent"),
        path(wavy(60, 460, 230), "accent"),
        txt(480, 78, "top of the drawing", "sm muted"),
        arrow(560, 140, 470, 140, "accent", "arrow-a"),
        txt(570, 145, "boundary you trace", "accent-f"),
        arrow(560, 232, 470, 232, "accent", "arrow-a"),
        txt(570, 237, "the next boundary down", "accent-f"),
        '  <line x1="500" y1="150" x2="500" y2="222" class="edge"/>',
        '  <line x1="492" y1="150" x2="508" y2="150" class="edge"/>',
        '  <line x1="492" y1="222" x2="508" y2="222" class="edge"/>',
        txt(516, 190, "the layer between them"),
        txt(24, 340,
            "A layer is never traced directly. It is defined by the boundary above it",
            "sm muted"),
        txt(24, 360,
            "and the boundary below it, which is why boundary order matters.",
            "sm muted"),
    ]
    return document(
        900, 380,
        "Boundaries and the layers between them",
        "Three stratigraphic layers with the two traced boundaries highlighted, "
        "showing that a layer is the region between consecutive boundaries.",
        "\n".join(b),
    )


def marker_anatomy() -> str:
    b = [
        heading(24, 30, "Three records that are easy to confuse"),
        box(40, 50, 420, 300, "fill"),
        band(60, 80, 380, 80, "band-a"),
        band(60, 160, 380, 90, "band-b"),
        band(60, 250, 380, 80, "band-c"),
        path(wavy(60, 440, 160), "edge"),
        path(wavy(60, 440, 250), "edge"),
        # marker: a scale/grid reference on the sheet
        '  <rect x="80" y="96" width="26" height="26" class="panel"/>',
        txt(93, 114, "20", "sm", "middle"),
        # feature: an inclusion inside a layer
        '  <ellipse cx="250" cy="200" rx="44" ry="24" class="panel"/>',
        txt(250, 205, "stone", "sm", "middle"),
        # find: a recovered object
        '  <path d="M340,290 l16,-10 l14,12 l-10,16 z" class="fill"/>',
        arrow(520, 110, 112, 110),
        heading(530, 100, "Marker"),
        txt(530, 122, "A reference printed or drawn on the", "sm"),
        txt(530, 140, "sheet — grid square, scale bar. It", "sm"),
        txt(530, 158, "measures the drawing, not the soil.", "sm"),
        arrow(520, 200, 298, 200),
        heading(530, 190, "Feature"),
        txt(530, 212, "Something physically in the deposit —", "sm"),
        txt(530, 230, "a stone, a cut, a burnt patch. It sits", "sm"),
        txt(530, 248, "inside a layer, and is not a layer.", "sm"),
        arrow(520, 300, 372, 296),
        heading(530, 290, "Find"),
        txt(530, 312, "An object recovered and catalogued.", "sm"),
        txt(530, 330, "Logged against a job, with its own", "sm"),
        txt(530, 348, "record, separate from the geometry.", "sm"),
    ]
    return document(
        1000, 380,
        "Marker, feature, and find",
        "One drawing showing a grid marker, a feature inside a layer, and a "
        "recovered find, each labelled with what it records.",
        "\n".join(b),
    )


def registration_fields() -> str:
    b = [
        heading(24, 30, "Four numbers place one face on the site"),
        # plan view
        txt(60, 70, "Plan view, looking down", "bold"),
        '  <line x1="60" y1="100" x2="60" y2="300" class="thin"/>',
        '  <line x1="60" y1="300" x2="330" y2="300" class="thin"/>',
        txt(46, 96, "Y", "sm muted", "end"), txt(338, 304, "X", "sm muted"),
        '  <line x1="120" y1="250" x2="290" y2="160" class="accent"/>',
        dot(120, 250, 6),
        txt(112, 272, "originX, originY", "sm accent-f", "middle"),
        txt(258, 172, "the face", "sm", "middle"),
        '  <line x1="120" y1="250" x2="120" y2="150" class="thin dot"/>',
        txt(126, 146, "north", "sm muted"),
        path("M120,196 A54,54 0 0,1 166,222", "warn"),
        txt(176, 214, "bearing_deg", "sm warn-f"),
        # section view
        txt(430, 70, "Section view, looking at the face", "bold"),
        '  <line x1="430" y1="120" x2="760" y2="120" class="edge"/>',
        txt(430, 110, "ground surface  =  surfaceZ", "sm"),
        band(430, 122, 330, 60, "band-a"),
        band(430, 182, 330, 80, "band-b"),
        path(wavy(430, 760, 182), "edge"),
        '  <line x1="800" y1="120" x2="800" y2="262" class="edge"/>',
        '  <line x1="792" y1="120" x2="808" y2="120" class="edge"/>',
        txt(812, 124, "Z = surfaceZ", "sm"),
        txt(812, 196, "Z = surfaceZ − depth", "sm"),
        txt(430, 292, "x runs along the face from originX, originY", "sm muted"),
        txt(24, 340,
            "bearing_deg is the compass direction of the face's local +x axis,",
            "sm muted"),
        txt(24, 360,
            "measured clockwise from north — not a slope and not a screen angle.",
            "sm muted"),
    ]
    return document(
        1010, 380,
        "The four registration fields",
        "A plan view showing originX, originY and bearing measured clockwise from "
        "north, beside a section view showing surfaceZ and depth.",
        "\n".join(b),
    )


def points_to_surface() -> str:
    pts = [(80, 120), (150, 138), (220, 126), (290, 152), (360, 144), (430, 168)]
    b = [
        heading(24, 30, "Interface points become an interpolated surface"),
        box(40, 50, 440, 240, "panel"),
        txt(56, 76, "What you recorded", "bold"),
    ]
    b += [dot(x, y + 60) for x, y in pts]
    b += [txt(56, 276, "one row per point in points.csv", "sm muted")]
    b += [
        box(530, 50, 440, 240, "panel"),
        txt(546, 76, "What the model builds", "bold"),
    ]
    b += [dot(x + 450, y + 60, 3, "muted") for x, y in pts]
    b += [
        poly([(x + 450, y + 60) for x, y in pts], "accent"),
        f'  <path d="M530,{pts[0][1] + 60} L530,290 L930,290 L930,{pts[-1][1] + 60}" '
        f'class="thin dash"/>',
        txt(546, 276, "a continuous surface, extrapolated to the extent", "sm muted"),
        arrow(490, 170, 522, 170, "accent", "arrow-a"),
        txt(24, 330,
            "The surface between points is interpolation, not evidence. A single "
            "face is stretched",
            "sm muted"),
        txt(24, 350,
            "across the whole model extent, so confidence falls off away from the "
            "recorded points.",
            "sm muted"),
    ]
    return document(
        1000, 370,
        "From interface points to an interpolated surface",
        "Scattered recorded interface points on the left, and on the right the "
        "continuous surface interpolated between them and extrapolated to the "
        "model extent.",
        "\n".join(b),
    )


def surface_vs_volume() -> str:
    b = [
        heading(24, 30, "Two ways to view one model"),
        box(40, 50, 430, 250, "panel"),
        txt(56, 76, "Surface mode", "bold"),
        poly([(70, 130), (150, 118), (230, 140), (310, 126), (400, 146)], "accent"),
        poly([(70, 190), (150, 202), (230, 182), (310, 200), (400, 188)], "accent"),
        poly([(70, 250), (150, 244), (230, 258), (310, 246), (400, 262)], "accent"),
        txt(56, 288, "interpolated boundaries; resolution-independent", "sm muted"),
        box(530, 50, 430, 250, "panel"),
        txt(546, 76, "Volume mode", "bold"),
    ]
    for row, colour in enumerate(["band-a", "band-b", "band-c"]):
        for col in range(11):
            b.append(band(556 + col * 36, 108 + row * 60, 34, 58, colour))
    b += [
        txt(546, 288, "classified cells; size depends on grid resolution", "sm muted"),
        txt(24, 340,
            "The default gate covers 75,000 instances. Larger grids grow in binary "
            "size, memory, and slice work.",
            "sm muted"),
    ]
    return document(
        1000, 360,
        "Surface mode compared with volume mode",
        "The same model shown as smooth interpolated boundary surfaces and as a "
        "grid of resolution-dependent classified cells.",
        "\n".join(b),
    )


def walls_to_pit() -> str:
    b = [
        heading(24, 30, "Four sheets, correctly registered, enclose one pit"),
        txt(40, 66, "Four drawings, each its own job", "bold sm"),
    ]
    names = ["North", "East", "South", "West"]
    for i, name in enumerate(names):
        x = 40 + i * 105
        b += [box(x, 80, 92, 66, "fill"),
              txt(x + 46, 108, name, "sm bold", "middle"),
              txt(x + 46, 128, "one wall", "sm muted", "middle")]
        b.append(arrow(x + 46, 152, x + 46, 176))
    b += [
        txt(40, 200, "one shared trench label", "sm accent-f"),
        '  <line x1="40" y1="208" x2="460" y2="208" class="accent"/>',
        arrow(250, 214, 250, 250, "accent", "arrow-a"),
        txt(262, 240, "merge, then register each face", "sm accent-f"),
    ]
    # the pit
    cx, cy = 700, 200
    b += [
        txt(600, 66, "Registered into one trench", "bold sm"),
        f'  <rect x="{cx - 130}" y="{cy - 95}" width="260" height="190" class="fill"/>',
        f'  <rect x="{cx - 90}" y="{cy - 60}" width="180" height="120" class="panel"/>',
        txt(cx, cy - 74, "North", "sm", "middle"),
        txt(cx, cy + 84, "South", "sm", "middle"),
        txt(cx - 110, cy + 4, "West", "sm", "middle"),
        txt(cx + 110, cy + 4, "East", "sm", "middle"),
        txt(cx, cy + 4, "the pit", "sm muted", "middle"),
        f'  <line x1="{cx - 130}" y1="{cy - 95}" x2="{cx - 130}" y2="{cy + 95}" class="accent"/>',
        f'  <line x1="{cx + 130}" y1="{cy - 95}" x2="{cx + 130}" y2="{cy + 95}" class="accent"/>',
        f'  <line x1="{cx - 130}" y1="{cy - 95}" x2="{cx + 130}" y2="{cy - 95}" class="accent"/>',
        f'  <line x1="{cx - 130}" y1="{cy + 95}" x2="{cx + 130}" y2="{cy + 95}" class="accent"/>',
        txt(24, 330,
            "Walls meet at a corner only when adjacent faces really share corner "
            "coordinates.",
            "sm muted"),
        txt(24, 350,
            "A per-sheet starter config cannot know that, so it cannot check it "
            "for you.",
            "sm muted"),
    ]
    return document(
        900, 370,
        "Four registered walls enclosing one trench",
        "Four separate wall drawings joined by a shared trench label and placed by "
        "their registration so they enclose one rectangular pit.",
        "\n".join(b),
    )


def placeholder_failure() -> str:
    b = [
        heading(24, 30, "Why placeholder registration is fatal for a merged build"),
        box(40, 56, 420, 250, "panel"),
        txt(56, 82, "Real registration", "bold good-f"),
    ]
    cx, cy = 250, 190
    b += [
        f'  <rect x="{cx - 90}" y="{cy - 60}" width="180" height="120" class="fill"/>',
        f'  <line x1="{cx - 90}" y1="{cy - 60}" x2="{cx + 90}" y2="{cy - 60}" class="good"/>',
        f'  <line x1="{cx - 90}" y1="{cy + 60}" x2="{cx + 90}" y2="{cy + 60}" class="good"/>',
        f'  <line x1="{cx - 90}" y1="{cy - 60}" x2="{cx - 90}" y2="{cy + 60}" class="good"/>',
        f'  <line x1="{cx + 90}" y1="{cy - 60}" x2="{cx + 90}" y2="{cy + 60}" class="good"/>',
        txt(cx, cy + 4, "walls around a pit", "sm", "middle"),
        txt(56, 292, "four distinct bearings and origins", "sm muted"),
        box(530, 56, 420, 250, "panel"),
        txt(546, 82, "Starter placeholders left in place", "bold warn-f"),
    ]
    for i in range(4):
        y = 130 + i * 42
        b += [f'  <line x1="570" y1="{y}" x2="880" y2="{y}" class="warn"/>',
              txt(890, y + 5, f"wall {i + 1}", "sm muted")]
    b += [
        txt(546, 292, "identical bearing 90 — every wall parallel", "sm muted"),
        txt(24, 340,
            "Every face carries the same 0, 0, 100, 90, so the walls lie in a row "
            "about 10 m apart",
            "sm muted"),
        txt(24, 360,
            "instead of around a pit. The build refuses rather than producing a "
            "confident model of nothing.",
            "sm muted"),
    ]
    return document(
        1000, 380,
        "Correct registration compared with placeholder registration",
        "On the left four walls enclosing a pit; on the right the same walls laid "
        "out as parallel lines because every face shares the placeholder bearing.",
        "\n".join(b),
    )


def reading_a_matrix() -> str:
    nodes = [("Topsoil", 420, 70), ("Fill 2", 300, 150), ("Fill 3", 540, 150),
             ("Floor 4", 420, 230), ("Natural 5", 420, 310)]
    b = [heading(24, 30, "Reading a Harris matrix")]
    for name, x, y in nodes:
        b += [box(x - 68, y - 22, 136, 44, "panel"),
              txt(x, y + 5, name, "sm bold", "middle")]
    for x1, y1, x2, y2 in [(420, 92, 300, 128), (420, 92, 540, 128),
                           (300, 172, 420, 208), (540, 172, 420, 208),
                           (420, 252, 420, 288)]:
        b.append(arrow(x1, y1, x2, y2))
    b += [
        '  <line x1="150" y1="70" x2="150" y2="320" class="accent" '
        'marker-end="url(#arrow-a)"/>',
        txt(140, 70, "younger", "sm accent-f", "end"),
        txt(140, 320, "older", "sm accent-f", "end"),
        txt(660, 120, "Every arrow runs from a younger", "sm"),
        txt(660, 140, "unit to an older one, so the", "sm"),
        txt(660, 160, "youngest sit at the top.", "sm"),
        txt(660, 200, "Two units side by side are not", "sm"),
        txt(660, 220, "dated relative to each other —", "sm"),
        txt(660, 240, "the matrix records only what", "sm"),
        txt(660, 260, "the stratigraphy actually shows.", "sm"),
        txt(24, 370,
            "The matrix is an archaeological interpretation, not an automatically "
            "verified result.",
            "sm muted"),
    ]
    return document(
        1000, 390,
        "How to read a Harris matrix",
        "A small Harris matrix with the youngest unit at the top and arrows "
        "running downward to progressively older units.",
        "\n".join(b),
    )


def correlation_not_merge() -> str:
    b = [
        heading(24, 30, "Correlation is an interpretation, not an automatic merge"),
        txt(60, 80, "Two walls each record a unit numbered 4", "sm muted"),
        box(60, 100, 150, 50, "panel"), txt(135, 130, "North · 4", "sm bold", "middle"),
        box(320, 100, 150, 50, "panel"), txt(395, 130, "South · 4", "sm bold", "middle"),
        '  <line x1="212" y1="125" x2="318" y2="125" class="accent dash"/>',
        txt(265, 116, "correlation", "sm accent-f", "middle"),
        txt(265, 168, "proposed, then accepted by a person", "sm muted", "middle"),
        '  <line x1="540" y1="70" x2="540" y2="300" class="thin"/>',
        txt(590, 100, "They stay two nodes.", "bold"),
        txt(590, 126, "Equal labels never merge on their own —", "sm"),
        txt(590, 146, "two excavators can reuse a number for", "sm"),
        txt(590, 166, "genuinely different deposits.", "sm"),
        txt(590, 200, "Boundary and label matches produce", "sm"),
        txt(590, 220, "proposals only. Every proposal must be", "sm"),
        txt(590, 240, "individually accepted or rejected.", "sm"),
        txt(60, 230, "Not this:", "bold warn-f"),
        box(60, 248, 150, 50, "panel"),
        txt(135, 278, "unit 4", "sm bold", "middle"),
        '  <line x1="66" y1="294" x2="204" y2="252" class="warn"/>',
    ]
    return document(
        1000, 330,
        "Correlation compared with merging",
        "Two identically numbered units on different walls shown as separate nodes "
        "joined by a correlation, beside a crossed-out single merged node.",
        "\n".join(b),
    )


def genuine_vs_fabricated() -> str:
    ink = [(70, 150), (130, 142), (190, 158), (250, 148), (310, 164), (370, 156),
           (430, 170)]
    b = [
        heading(24, 30, "A boundary that does not lie on ink is fabricated"),
        box(40, 56, 440, 230, "panel"),
        txt(56, 82, "Genuine trace", "bold good-f"),
    ]
    b += [f'  <circle cx="{x}" cy="{y + 40}" r="5" fill="var(--muted)" opacity="0.55"/>'
          for x, y in ink]
    b += [poly([(x, y + 40) for x, y in ink], "good"),
          txt(56, 272, "follows the drawn line, wobble and all", "sm muted"),
          box(530, 56, 440, 230, "panel"),
          txt(546, 82, "Fabricated", "bold warn-f")]
    b += [f'  <circle cx="{x + 490}" cy="{y + 40}" r="5" fill="var(--muted)" '
          f'opacity="0.55"/>' for x, y in ink]
    b += [
        path("M560,205 C660,196 800,196 920,205", "warn"),
        txt(546, 272, "smooth, evenly spaced, and off the ink", "sm muted"),
        txt(24, 322,
            "Statistical signatures — suspiciously even spacing, implausible "
            "smoothness — are hints.",
            "sm muted"),
        txt(24, 342,
            "Overlap with actual ink pixels is direct evidence, and is the check "
            "worth automating.",
            "sm muted"),
    ]
    return document(
        1000, 362,
        "A genuine trace compared with a fabricated boundary",
        "On the left a boundary following the drawn ink; on the right a smooth "
        "evenly spaced curve lying away from the ink entirely.",
        "\n".join(b),
    )


def normalization_steps() -> str:
    b = [
        heading(24, 30, "Normalization repairs the sheet, never the geometry"),
        box(40, 60, 260, 230, "panel"),
        txt(56, 86, "As scanned", "bold"),
        '  <g transform="rotate(-7 170 190)">'
        '<rect x="70" y="110" width="200" height="150" class="fill"/></g>',
        txt(56, 278, "skewed on the platen", "sm muted"),
        arrow(312, 175, 344, 175, "accent", "arrow-a"),
        box(356, 60, 260, 230, "panel"),
        txt(372, 86, "Deskewed", "bold"),
        '  <rect x="386" y="110" width="200" height="150" class="fill"/>',
        txt(372, 278, "rotated to the detected horizontal", "sm muted"),
        arrow(628, 175, 660, 175, "accent", "arrow-a"),
        box(672, 60, 260, 230, "panel"),
        txt(688, 86, "Scaled", "bold"),
        '  <rect x="702" y="110" width="200" height="150" class="fill"/>',
        '  <line x1="702" y1="276" x2="902" y2="276" class="accent"/>',
        txt(802, 268, "known width", "sm accent-f", "middle"),
        txt(24, 330,
            "Every step here changes how the sheet sits, not what it records. "
            "Boundary shapes are untouched.",
            "sm muted"),
    ]
    return document(
        960, 350,
        "The normalization steps",
        "A skewed scan, the same scan rotated to horizontal, and the result scaled "
        "against a known real-world width.",
        "\n".join(b),
    )


def archaeology_to_3d() -> str:
    stages = [
        ("The trench wall", "what was excavated", 40),
        ("The drawing", "measured by hand on site", 280),
        ("Structured data", "boundaries as coordinates", 520),
        ("The model", "interpolated geometry", 760),
    ]
    b = [heading(24, 30, "Four representations of one trench")]
    for name, sub, x in stages:
        b += [box(x, 60, 200, 170, "panel"),
              txt(x + 100, 90, name, "bold", "middle"),
              txt(x + 100, 218, sub, "sm muted", "middle")]
    b += [
        band(56, 108, 168, 30, "band-a"), band(56, 138, 168, 36, "band-b"),
        band(56, 174, 168, 28, "band-c"),
        path(wavy(296, 464, 130, 4, 4), "edge"),
        path(wavy(296, 464, 172, 4, 4), "edge"),
        '  <rect x="296" y="106" width="168" height="96" class="thin"/>',
    ]
    b += [dot(540 + i * 24, 126 + (i % 3) * 20, 3) for i in range(7)]
    b += [
        txt(620, 186, '"xMeters": 2.10', "mono muted", "middle"),
        txt(620, 202, '"depthMeters": 0.85', "mono muted", "middle"),
        poly([(776, 180), (826, 164), (876, 186), (926, 170)], "accent"),
        poly([(776, 132), (826, 120), (876, 140), (926, 126)], "accent"),
    ]
    for x in (248, 488, 728):
        b.append(arrow(x, 145, x + 26, 145))
    b += [
        txt(24, 268,
            "Each step loses something. The project's job is to record what was "
            "lost, so the model",
            "sm muted"),
        txt(24, 288,
            "can be judged against the drawing it came from rather than trusted "
            "on its own.",
            "sm muted"),
    ]
    return document(
        1000, 305,
        "From excavated wall to 3D model",
        "Four panels in sequence: the excavated trench wall, its measured drawing, "
        "the structured coordinate data, and the interpolated model.",
        "\n".join(b),
    )


def two_sheet_types() -> str:
    b = [
        heading(24, 30, "Two sheets that record material differently"),
        box(40, 56, 440, 260, "panel"),
        txt(56, 82, "Illustrated trench sheet", "bold"),
        txt(56, 102, "layers identified by pattern or shading", "sm muted"),
        band(60, 118, 400, 56, "band-a"), band(60, 174, 400, 62, "band-b"),
        band(60, 236, 400, 56, "band-c"),
    ]
    for row, y in enumerate((118, 174, 236)):
        step = 14 + row * 6
        b += [f'  <line x1="{x}" y1="{y + 4}" x2="{x - 12}" y2="{y + 50}" '
              f'class="thin"/>' for x in range(74, 460, step)]
    b += [
        txt(56, 306, "one sheet may hold several faces", "sm accent-f"),
        box(530, 56, 440, 260, "panel"),
        txt(546, 82, "Hand-drawn field sheet", "bold"),
        txt(546, 102, "layers identified by locus number and Munsell", "sm muted"),
        band(550, 118, 400, 56, "band-a"), band(550, 174, 400, 62, "band-b"),
        band(550, 236, 400, 56, "band-c"),
        txt(566, 150, "L1 · 10YR 5/4", "mono"),
        txt(566, 210, "L2 · 7.5YR 4/3", "mono"),
        txt(566, 270, "L3 · 10YR 3/2", "mono"),
        txt(546, 306, "one sheet records exactly one wall", "sm accent-f"),
        txt(24, 350,
            "They use different extraction schemas because they record material "
            "differently — but both",
            "sm muted"),
        txt(24, 370,
            "converge on the same coordinate conversion and model build.",
            "sm muted"),
    ]
    return document(
        1000, 390,
        "The two source drawing types",
        "An illustrated sheet whose layers are identified by hatch patterns, "
        "beside a field sheet whose layers carry locus numbers and Munsell colours.",
        "\n".join(b),
    )


def good_vs_bad_drawing() -> str:
    b = [
        heading(24, 30, "What makes a sheet extractable"),
        box(40, 56, 440, 250, "panel"),
        txt(56, 82, "Works well", "bold good-f"),
        band(60, 100, 400, 56, "band-a"), band(60, 156, 400, 62, "band-b"),
        path(wavy(60, 460, 156), "edge"),
        '  <line x1="60" y1="240" x2="160" y2="240" class="good"/>',
        '  <line x1="60" y1="234" x2="60" y2="246" class="good"/>',
        '  <line x1="160" y1="234" x2="160" y2="246" class="good"/>',
        txt(168, 245, "scale bar", "sm good-f"),
        txt(60, 274, "L1 · 10YR 5/4", "mono"),
        txt(60, 296, "boundaries closed and continuous", "sm muted"),
        box(530, 56, 440, 250, "panel"),
        txt(546, 82, "Causes trouble", "bold warn-f"),
        band(550, 100, 400, 56, "band-a"), band(550, 156, 400, 62, "band-b"),
        path("M550,156 L640,160 L700,152", "warn"),
        path("M760,158 L860,150 L950,160", "warn"),
        txt(700, 200, "boundary breaks", "sm warn-f", "middle"),
        txt(550, 274, "no scale, no locus label", "sm warn-f"),
        txt(550, 296, "and scanned below 300 DPI", "sm muted"),
        txt(24, 350,
            "Most extraction failures start on the sheet. A missing scale cannot "
            "be recovered later,",
            "sm muted"),
        txt(24, 370,
            "and a broken boundary becomes a gap the model silently interpolates "
            "across.",
            "sm muted"),
    ]
    return document(
        1000, 390,
        "A well-drawn sheet compared with a problematic one",
        "A sheet with a scale bar, closed boundaries, and legible locus labels "
        "beside one with broken boundaries and no scale or labels.",
        "\n".join(b),
    )


def status_labels() -> str:
    b = [
        heading(24, 30, "What the five capability labels mean"),
        txt(300, 76, "Backend implemented", "bold sm", "middle"),
        txt(640, 76, "Backend absent or unusable", "bold sm", "middle"),
        txt(150, 150, "User control exists", "bold sm", "middle"),
        txt(150, 280, "No user control", "bold sm", "middle"),
        box(230, 100, 280, 100, "panel"),
        txt(370, 138, "supported", "bold good-f", "middle"),
        txt(370, 162, "wired end to end", "sm muted", "middle"),
        box(230, 220, 280, 100, "panel"),
        txt(370, 258, "backend-only", "bold", "middle"),
        txt(370, 282, "routes exist, nothing reaches them", "sm muted", "middle"),
        box(540, 100, 280, 100, "panel"),
        txt(680, 138, "blocked", "bold warn-f", "middle"),
        txt(680, 162, "advertised, but cannot complete", "sm muted", "middle"),
        box(540, 220, 280, 100, "panel"),
        txt(680, 258, "historical", "bold muted", "middle"),
        txt(680, 282, "kept only as reference", "sm muted", "middle"),
        '  <line x1="230" y1="210" x2="820" y2="210" class="thin"/>',
        '  <line x1="530" y1="100" x2="530" y2="320" class="thin"/>',
        txt(24, 366,
            "experimental cuts across the grid: user-facing, but dependent on an "
            "optional package,",
            "sm muted"),
        txt(24, 386,
            "an API key, or a path not yet covered well enough to depend on.",
            "sm muted"),
    ]
    return document(
        900, 406,
        "The five capability status labels",
        "A grid separating supported, backend-only, blocked, and historical by "
        "whether a user control and a backend implementation exist, with "
        "experimental noted as cutting across the grid.",
        "\n".join(b),
    )


def normalization_diff() -> str:
    before = ['{', '  "locusNumber": "L1",', '  "munsell": "null",',
              '  "description": "  loose fill ",', '  "topBoundary": [ … ]', '}']
    after = ['{', '  "locusNumber": "L1",', '  "munsell": null,',
             '  "description": "loose fill",', '  "topBoundary": [ … ]', '}']
    b = [
        heading(24, 30, "Normalization cleans formatting, not geometry"),
        box(40, 56, 430, 210, "panel"),
        txt(56, 82, "Before", "bold"),
    ]
    b += [txt(56, 112 + i * 24, line, "mono") for i, line in enumerate(before)]
    b += [box(530, 56, 430, 210, "panel"), txt(546, 82, "After", "bold")]
    b += [txt(546, 112 + i * 24, line,
              "mono good-f" if before[i] != after[i] else "mono")
          for i, line in enumerate(after)]
    b += [
        arrow(482, 160, 518, 160, "accent", "arrow-a"),
        txt(24, 300,
            'The null-like string "null" becomes a real null and the padded '
            "description is trimmed.",
            "sm muted"),
        txt(24, 320,
            "topBoundary is passed through untouched — normalization never moves "
            "a coordinate.",
            "sm muted"),
    ]
    return document(
        1000, 340,
        "Extraction data before and after normalization",
        "The same extraction record shown before and after normalization, with the "
        "cleaned null-like string and trimmed description highlighted and the "
        "boundary coordinates unchanged.",
        "\n".join(b),
    )


def _sheet(rotate: float, label: str, note: str) -> str:
    """One trench sheet, optionally skewed. Both variants share a viewBox so the
    before/after comparison slider can overlay them exactly."""
    inner = "\n".join([
        band(0, 0, 460, 70, "band-a"),
        band(0, 70, 460, 84, "band-b"),
        band(0, 154, 460, 76, "band-c"),
        path(wavy(0, 460, 70), "edge"),
        path(wavy(0, 460, 154), "edge"),
    ])
    return document(
        720, 420,
        f"Trench sheet {label.lower()}",
        note,
        "\n".join([
            heading(24, 34, label),
            f'  <g transform="translate(130 90) rotate({rotate} 230 115)">',
            inner,
            "  </g>",
            '  <line x1="130" y1="360" x2="590" y2="360" class="thin"/>',
            txt(360, 386, note, "sm muted", "middle"),
        ]),
    )


def normalization_before() -> str:
    return _sheet(
        -6.5, "Before", "As scanned: the sheet sits crooked on the platen."
    )


def normalization_after() -> str:
    return _sheet(
        0, "After", "Deskewed: rotated to the detected horizontal."
    )


DIAGRAMS: dict[str, Callable[[], str]] = {
    "normalization-before": normalization_before,
    "normalization-after": normalization_after,
    "glossary-anatomy": glossary_anatomy,
    "three-coordinate-spaces": three_coordinate_spaces,
    "w03-calibration-clicks": calibration_clicks,
    "w03-boundary-anatomy": boundary_anatomy,
    "w03b-marker-anatomy": marker_anatomy,
    "w04-normalization-diff": normalization_diff,
    "w06-registration-fields": registration_fields,
    "w07-points-to-surface": points_to_surface,
    "w08-surface-vs-volume": surface_vs_volume,
    "w09-walls-to-pit": walls_to_pit,
    "w09-placeholder-failure": placeholder_failure,
    "wh-reading-a-matrix": reading_a_matrix,
    "wh-correlation-not-merge": correlation_not_merge,
    "archaeology-to-3d": archaeology_to_3d,
    "two-sheet-types": two_sheet_types,
    "normalization-steps": normalization_steps,
    "genuine-vs-fabricated": genuine_vs_fabricated,
    "r-good-vs-bad-drawing": good_vs_bad_drawing,
    "p-status-labels": status_labels,
}


def write_diagrams(output_root: Path) -> list[Path]:
    """Write every diagram and return the paths written."""

    target = output_root / "docs" / "assets" / "diagrams"
    target.mkdir(parents=True, exist_ok=True)

    written = []
    for name, build in DIAGRAMS.items():
        path = target / f"{name}.svg"
        path.write_text(build(), encoding="utf-8")
        written.append(path)
    return written


def main(argv: Sequence[str] | None = None) -> int:
    """Generate every documentation diagram."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_root",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="repository root (defaults to the current directory)",
    )
    args = parser.parse_args(argv)

    written = write_diagrams(args.output_root.resolve())
    for path in written:
        print(path)
    print(f"\n{len(written)} diagrams written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
