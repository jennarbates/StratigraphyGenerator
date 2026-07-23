"""
build_gempy.py — build and compute a GemPy geological model from the
interface points / orientation seeds produced by convert_coords.py.

Adapted from 06_gempy_model/buildGempyModel.py into an importable function.
Logic unchanged; requires `pip install gempy gempy_viewer` in the environment
running this web app.
"""

import os
import re

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
    return (
        points.groupby("surface")["Z"]
        .mean()
        .sort_values(ascending=False)
        .index
        .tolist()
    )


def middle_zoom_range(points, surf_order, surfaces=None, padding_frac=0.25,
                       min_padding=0.05):
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
    written = []
    for surf_name, verts, faces in zip(surf_order, vertices[:n], edges[:n]):
        path = os.path.join(outdir, f"{safe_filename(surf_name)}.obj")
        with open(path, "w") as f:
            f.write(f"# {surf_name}\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in faces:
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
        written.append(path)
    return written


def run_build(points_csv, orientations_csv, out_prefix,
              project_name="trench_model",
              resolution=(50, 50, 30),
              extent=None,
              padding_xy=2.0,
              padding_z=1.0,
              series_order=None,
              make_plot=True,
              section_direction="y",
              vertical_exaggeration=5.0,
              make_meshes=True,
              save_model=True,
              make_zoom_plot=True,
              zoom_surfaces=None,
              zoom_vertical_exaggeration=None,
              log_cb=None):
    """Runs the full GemPy build stage. Returns a dict describing outputs."""

    def log(msg):
        if log_cb:
            log_cb(msg)

    import gempy as gp

    points = pd.read_csv(points_csv)
    if points.empty:
        raise RuntimeError(f"{points_csv} has no rows — nothing to model.")

    resolved_extent = extent or infer_extent(points, padding_xy, padding_z)
    log(f"extent: {resolved_extent}")

    if series_order:
        surf_order = [s.strip() for s in series_order] if isinstance(series_order, list) \
            else [s.strip() for s in series_order.split(";")]
        missing = set(surf_order) - set(points["surface"].unique())
        if missing:
            raise RuntimeError(f"--series-order names not found in {points_csv}: "
                                f"{', '.join(sorted(missing))}")
    else:
        surf_order = infer_series_order(points)
    log(f"stratigraphic order (young -> old): {surf_order}")

    coverage = points.groupby("surface")["face"].unique()
    single_face = {surf: faces[0] for surf, faces in coverage.items() if len(faces) == 1}
    single_face_note = None
    if single_face:
        single_face_note = (
            "These surfaces have points from only ONE face and will still be "
            "interpolated across the whole model extent: " +
            ", ".join(f"{surf!r} (only on {face})" for surf, face in single_face.items())
        )
        log("NOTE: " + single_face_note)

    importer = gp.data.ImporterHelper(
        path_to_surface_points=points_csv,
        path_to_orientations=orientations_csv,
    )
    geo_model = gp.create_geomodel(
        project_name=project_name,
        extent=resolved_extent,
        resolution=list(resolution),
        importer_helper=importer,
    )
    gp.map_stack_to_surfaces(geo_model, {"Strat_Series": surf_order})

    log("computing model...")
    solution = gp.compute_model(geo_model)
    log("model computed.")

    result = {
        "extent": resolved_extent,
        "series_order": surf_order,
        "single_face_note": single_face_note,
        "outputs": {},
    }

    if save_model:
        model_path = f"{out_prefix}.gempy"
        gp.save_model(geo_model, path=model_path)
        result["outputs"]["model"] = model_path
        log(f"wrote {model_path}")

    lith_path = f"{out_prefix}_lith_block.npz"
    np.savez(lith_path,
             lith_block=solution.raw_arrays.lith_block,
             resolution=np.array(resolution),
             extent=np.array(resolved_extent))
    result["outputs"]["lith_block"] = lith_path
    log(f"wrote {lith_path}")

    if make_meshes:
        meshdir = f"{out_prefix}_meshes"
        written = export_meshes(geo_model, solution, surf_order, meshdir)
        result["outputs"]["meshes"] = written
        log(f"wrote {len(written)} mesh(es) -> {meshdir}/")

    if make_plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import gempy_viewer as gpv
            nx, ny, nz = resolution
            cell = {"x": nx, "y": ny, "z": nz}[section_direction] // 2

            def render(ve, ylim, path):
                p = gpv.plot_2d(geo_model, cell_number=[cell],
                                 direction=[section_direction],
                                 show_data=True, show=False, ve=ve)
                ax = p.axes[0]
                if ylim is not None:
                    ax.set_ylim(*ylim)
                legend = ax.get_legend()
                if legend is not None:
                    legend.set_bbox_to_anchor((1.02, 1.0))
                    legend.set_loc("upper left")
                p.fig.savefig(path, dpi=110, bbox_inches="tight")
                log(f"wrote {path}")

            main_path = f"{out_prefix}_section_{section_direction}.png"
            render(vertical_exaggeration, None, main_path)
            result["outputs"]["section"] = main_path

            if make_zoom_plot:
                zsurfs = (
                    [s.strip() for s in zoom_surfaces.split(";")]
                    if isinstance(zoom_surfaces, str) else zoom_surfaces
                )
                zrange = middle_zoom_range(points, surf_order, zsurfs)
                if zrange is None:
                    log("NOTE: no middle layers to zoom into — skipping the zoomed plot.")
                else:
                    zoom_ve = (zoom_vertical_exaggeration
                               if zoom_vertical_exaggeration is not None
                               else vertical_exaggeration * 3)
                    zoom_path = f"{out_prefix}_section_{section_direction}_zoom.png"
                    render(zoom_ve, zrange, zoom_path)
                    result["outputs"]["section_zoom"] = zoom_path
        except Exception as e:
            log(f"WARNING: 2D plot failed ({e}); skipping. The model itself "
                f"was still computed and saved.")

    return result
