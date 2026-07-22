"""
buildGempyModel.py — build and compute a GemPy geological model from the
interface points / orientation seeds produced by convertCoords.py.

Usage:
    python buildGempyModel.py points.csv points_orientations.csv
    python buildGempyModel.py points.csv points_orientations.csv \\
        --out-prefix trench23 --resolution 60 60 30 --extent 0 30 -10 10 90 105
    python buildGempyModel.py points.csv points_orientations.csv \\
        --series-order "Topsoil;Fill;Virgin Soil"

Requires:
    pip install gempy gempy_viewer --break-system-packages

============================================================
WHAT THIS SCRIPT ASSUMES
============================================================
- `points.csv` has columns X, Y, Z, surface, face (as written by
  convertCoords.py). Every row is a point ON THE BOUNDARY between the named
  `surface` and whatever sits below it.
- `points_orientations.csv` has columns X, Y, Z, surface, face, dip, azimuth,
  polarity (also written by convertCoords.py). GemPy's CSV reader converts
  dip/azimuth/polarity to gradient vectors automatically — no manual
  conversion needed here.
- All surfaces belong to ONE conformable stratigraphic series (no faults,
  no unconformities). This is a reasonable default for a single trench
  sequence but is a simplification — if the real geology has a fault or an
  unconformity, the model needs more than one series/StackRelationType, and
  that requires geological judgement this script does not attempt to make.
- Stratigraphic order (which surface sits on top of which) is inferred
  automatically from each surface's mean Z across all its points: the
  shallowest (highest mean Z) surface is treated as youngest/top, the
  deepest as oldest/bottom. This matches how the drawings are read (topsoil
  first, downward from there), but it's a heuristic — pass --series-order
  explicitly if a surface's mean depth doesn't reflect its true stacking
  order (e.g. a lens-shaped feature that's locally deep but stratigraphically
  young).

============================================================
OUTPUTS (written to --out-prefix, default "gempy_model")
============================================================
    <prefix>.gempy                 native GemPy save file (gp.load_model)
    <prefix>_lith_block.npz        raw voxel lithology ids + resolution/extent
    <prefix>_meshes/<surface>.obj  one triangle mesh per surface (if requested)
    <prefix>_section_<dir>.png     a 2D cross-section plot (if requested)
    <prefix>_section_<dir>_zoom.png  same section cropped to the thin middle
                                      layers, at higher exaggeration, so they
                                      aren't dwarfed by the topsoil/subsoil
                                      bands above and below them (if requested)
"""

import argparse
import os
import re
import sys

import numpy as np
import pandas as pd


def infer_extent(points, pad_xy, pad_z):
    xmin, xmax = points["X"].min(), points["X"].max()
    ymin, ymax = points["Y"].min(), points["Y"].max()
    zmin, zmax = points["Z"].min(), points["Z"].max()

    def pad(lo, hi, minimum):
        span = hi - lo
        p = max(span * 0.1, minimum)
        return lo - p, hi + p

    xlo, xhi = pad(xmin, xmax, pad_xy)
    ylo, yhi = pad(ymin, ymax, pad_xy)
    zlo, zhi = pad(zmin, zmax, pad_z)
    return [xlo, xhi, ylo, yhi, zlo, zhi]


def infer_series_order(points):
    """Youngest (shallowest, highest mean Z) first, oldest (deepest) last —
    the order GemPy expects for a single conformable series."""
    return (
        points.groupby("surface")["Z"]
        .mean()
        .sort_values(ascending=False)
        .index
        .tolist()
    )


def middle_zoom_range(points, surf_order, surfaces=None, padding_frac=0.25,
                      min_padding=0.05):
    """Z-range spanning the 'middle' layers only — everything except the
    top and bottom (usually much thicker) surfaces — with a bit of padding
    so the crop isn't flush against the plotted lines. Pass `surfaces` to
    pick specific layers instead of the top/bottom-excluded default."""
    if surfaces is None:
        surfaces = surf_order[1:-1]
        if not surfaces:
            return None
    subset = points[points["surface"].isin(surfaces)]
    if subset.empty:
        return None
    zlo, zhi = subset["Z"].min(), subset["Z"].max()
    pad = max((zhi - zlo) * padding_frac, min_padding)
    return zlo - pad, zhi + pad


def safe_filename(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "surface"


def export_meshes(geo_model, solution, surf_order, outdir):
    os.makedirs(outdir, exist_ok=True)
    vertices = solution.raw_arrays.vertices
    edges = solution.raw_arrays.edges
    n = min(len(vertices), len(surf_order))
    if len(vertices) != len(surf_order):
        print(f"NOTE: got {len(vertices)} mesh(es) for {len(surf_order)} "
              f"surface(s) — pairing the first {n} in stratigraphic order; "
              f"a surface with no computed interface (e.g. the bottommost/"
              f"basement unit) legitimately produces no mesh of its own.")
    written = []
    for surf_name, verts, faces in zip(surf_order, vertices[:n], edges[:n]):
        path = os.path.join(outdir, f"{safe_filename(surf_name)}.obj")
        with open(path, "w") as f:
            f.write(f"# {surf_name}\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in faces:
                # OBJ face indices are 1-based
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
        written.append(path)
    return written


def warn_single_face_surfaces(points):
    """Flag surfaces whose points all come from one face. A single
    conformable series assumes every surface exists everywhere in the model
    extent, so a surface known from only one face gets interpolated/
    extrapolated across the OTHER faces too — including empty gaps between
    faces where nothing was actually drawn. This is expected GemPy behavior,
    not a bug, but it's worth knowing about before trusting the model
    outside the face(s) that actually constrain a given surface."""
    coverage = points.groupby("surface")["face"].unique()
    single_face = {surf: faces[0] for surf, faces in coverage.items() if len(faces) == 1}
    if single_face:
        print("\nNOTE: these surfaces have points from only ONE face and will "
              "still be interpolated across the whole model extent (including "
              "other faces and any gaps between them):")
        for surf, face in single_face.items():
            print(f"    {surf!r} (only on {face})")
        print("If different faces use different material names for what is "
              "actually the same stratigraphic unit, consider reconciling "
              "the naming before modeling — that judgement call belongs to "
              "whoever knows the site, not this script.\n")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("points_csv", help="interface points CSV (from convertCoords.py)")
    ap.add_argument("orientations_csv", help="orientation seeds CSV (from convertCoords.py)")
    ap.add_argument("--project-name", default="trench_model")
    ap.add_argument("--out-prefix", default="gempy_model")
    ap.add_argument("--resolution", type=int, nargs=3, metavar=("NX", "NY", "NZ"),
                    default=[50, 50, 30],
                    help="dense grid resolution (default: 50 50 30)")
    ap.add_argument("--extent", type=float, nargs=6,
                    metavar=("XMIN", "XMAX", "YMIN", "YMAX", "ZMIN", "ZMAX"),
                    default=None,
                    help="override the auto-computed model extent")
    ap.add_argument("--padding-xy", type=float, default=2.0,
                    help="minimum meters of horizontal padding around the "
                         "data bounding box when --extent is not given "
                         "(default: 2.0)")
    ap.add_argument("--padding-z", type=float, default=1.0,
                    help="minimum meters of vertical padding (default: 1.0)")
    ap.add_argument("--series-order", default=None,
                    help="semicolon-separated surface names, youngest/top "
                         "first, overriding the automatic mean-Z ordering "
                         "(semicolons, not commas, since a surface name "
                         "itself may contain a comma)")
    ap.add_argument("--no-plot", action="store_true",
                    help="skip the 2D cross-section plot")
    ap.add_argument("--section-direction", default="y", choices=["x", "y", "z"],
                    help="axis the 2D section slices across (default: y)")
    ap.add_argument("--vertical-exaggeration", type=float, default=5.0,
                    help="stretch factor applied to Z in the 2D section plot "
                         "(default: 5.0). Trench Z-ranges are usually much "
                         "smaller than X/Y, so at true scale (1.0) the "
                         "layers can be nearly invisible — raise this if the "
                         "section looks like a thin smear.")
    ap.add_argument("--no-meshes", action="store_true",
                    help="skip exporting per-surface OBJ meshes")
    ap.add_argument("--no-save-model", action="store_true",
                    help="skip writing the native .gempy save file")
    ap.add_argument("--no-zoom-plot", action="store_true",
                    help="skip the extra cropped/zoomed section of the "
                         "middle layers (on by default alongside the main "
                         "section plot)")
    ap.add_argument("--zoom-surfaces", default=None,
                    help="semicolon-separated surface names to include in "
                         "the zoomed plot, overriding the default (every "
                         "surface except the shallowest/topmost and "
                         "deepest/bottommost in stratigraphic order)")
    ap.add_argument("--zoom-vertical-exaggeration", type=float, default=None,
                    help="vertical exaggeration for the zoomed plot "
                         "(default: 3x --vertical-exaggeration, since a "
                         "cropped range benefits from extra stretch)")
    args = ap.parse_args()

    import gempy as gp

    points = pd.read_csv(args.points_csv)
    if points.empty:
        raise SystemExit(f"{args.points_csv} has no rows — nothing to model.")

    extent = args.extent or infer_extent(points, args.padding_xy, args.padding_z)
    print(f"extent: {extent}")

    if args.series_order:
        surf_order = [s.strip() for s in args.series_order.split(";")]
        missing = set(surf_order) - set(points["surface"].unique())
        if missing:
            raise SystemExit(f"--series-order names not found in {args.points_csv}: "
                             f"{', '.join(sorted(missing))}")
    else:
        surf_order = infer_series_order(points)
    print(f"stratigraphic order (young -> old): {surf_order}")
    warn_single_face_surfaces(points)

    importer = gp.data.ImporterHelper(
        path_to_surface_points=args.points_csv,
        path_to_orientations=args.orientations_csv,
    )
    geo_model = gp.create_geomodel(
        project_name=args.project_name,
        extent=extent,
        resolution=args.resolution,
        importer_helper=importer,
    )
    gp.map_stack_to_surfaces(geo_model, {"Strat_Series": surf_order})

    print("computing model...")
    solution = gp.compute_model(geo_model)
    print("done.")

    if not args.no_save_model:
        model_path = f"{args.out_prefix}.gempy"
        gp.save_model(geo_model, path=model_path)
        print(f"wrote {model_path}")

    lith_path = f"{args.out_prefix}_lith_block.npz"
    np.savez(lith_path,
             lith_block=solution.raw_arrays.lith_block,
             resolution=np.array(args.resolution),
             extent=np.array(extent))
    print(f"wrote {lith_path} (flat lith ids + resolution/extent metadata — "
          f"reshape order is GemPy's internal grid order, not guaranteed "
          f"here; treat resolution/extent as the source of truth for any "
          f"downstream reshape)")

    if not args.no_meshes:
        meshdir = f"{args.out_prefix}_meshes"
        written = export_meshes(geo_model, solution, surf_order, meshdir)
        print(f"wrote {len(written)} mesh(es) -> {meshdir}/")

    if not args.no_plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import gempy_viewer as gpv
            nx, ny, nz = args.resolution
            cell = {"x": nx, "y": ny, "z": nz}[args.section_direction] // 2

            def render(ve, ylim, path):
                p = gpv.plot_2d(geo_model, cell_number=[cell],
                                direction=[args.section_direction],
                                show_data=True, show=False, ve=ve)
                ax = p.axes[0]
                if ylim is not None:
                    ax.set_ylim(*ylim)
                legend = ax.get_legend()
                if legend is not None:
                    legend.set_bbox_to_anchor((1.02, 1.0))
                    legend.set_loc("upper left")
                p.fig.savefig(path, dpi=110, bbox_inches="tight")
                print(f"wrote {path}")

            main_path = f"{args.out_prefix}_section_{args.section_direction}.png"
            render(args.vertical_exaggeration, None, main_path)

            if not args.no_zoom_plot:
                zoom_surfaces = (
                    [s.strip() for s in args.zoom_surfaces.split(";")]
                    if args.zoom_surfaces else None
                )
                zrange = middle_zoom_range(points, surf_order, zoom_surfaces)
                if zrange is None:
                    print("NOTE: no middle layers to zoom into (need at "
                          "least 3 surfaces, or check --zoom-surfaces) — "
                          "skipping the zoomed plot.")
                else:
                    zoom_ve = (args.zoom_vertical_exaggeration
                              if args.zoom_vertical_exaggeration is not None
                              else args.vertical_exaggeration * 3)
                    zoom_path = (f"{args.out_prefix}_section_"
                                f"{args.section_direction}_zoom.png")
                    render(zoom_ve, zrange, zoom_path)
        except Exception as e:
            print(f"WARNING: 2D plot failed ({e}); skipping. The model "
                  f"itself was still computed and saved.")


if __name__ == "__main__":
    main()