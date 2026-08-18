"""
Build and compute a GemPy geological model from the
interface points / orientation seeds produced by convert_coords.py.

Adapted from 06_gempy_model/buildGempyModel.py into an importable function.
Logic unchanged; requires `pip install gempy gempy_viewer` in the environment
running this web app.
"""

import json
import os
from collections.abc import Mapping

import numpy as np
import pandas as pd

from naming import safe_filename

from . import series_order as series_order_module
from .series_order import ELEVATION, SUPPLIED


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
    """Order surfaces by mean elevation, highest first.

    This is an assumption, not evidence, and at this site it is one the
    excavation's own procedures contradict: "stratigraphically newer deposits
    may exist at lower elevations than stratigraphically older deposits". It
    stays because a model with no other information still has to be buildable,
    but every caller labels it -- see pipeline/series_order.py.
    """
    return (
        points.groupby("surface")["Z"]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )


def middle_zoom_range(
    points, surf_order, surfaces=None, padding_frac=0.25, min_padding=0.05
):
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


def wall_traces(points):
    """One polyline per (face, surface): the points actually traced on that
    wall, in along-wall order.

    A viewer can draw these over the interpolated surfaces so a reader can
    tell data from interpolation -- everything away from a trace is the
    interpolator's guess. The points are ordered along the wall rather than by
    X and then Y: a wall running north-south has one X for every point, so
    sorting by X first would leave the group in whatever order the file
    happened to carry. Whichever horizontal axis the group spreads along is
    the axis that orders it.
    """
    if "face" not in points.columns:
        return []
    traces = []
    for (face, surface), group in points.groupby(["face", "surface"], sort=True):
        x_span = group["X"].max() - group["X"].min()
        y_span = group["Y"].max() - group["Y"].min()
        ordered = group.sort_values("X" if x_span > y_span else "Y", kind="stable")
        traces.append(
            {
                "face": str(face),
                "surface": str(surface),
                "points": [
                    [float(x), float(y), float(z)]
                    for x, y, z in zip(ordered["X"], ordered["Y"], ordered["Z"])
                ],
            }
        )
    return traces


def write_viewer_manifest(
    manifest_path,
    *,
    extent,
    resolution,
    series_order,
    single_face_note,
    mesh_paths,
    lith_block_path,
    volume_path=None,
    volume_lithologies=None,
    traces=None,
    surface_labels=None,
    order_source=None,
    order_note=None,
    arbitrary_pairs=None,
):
    manifest_path = os.path.abspath(os.fspath(manifest_path))
    manifest_dir = os.path.dirname(manifest_path)

    def plain_number(value):
        return value.item() if isinstance(value, np.generic) else value

    def relative_path(path):
        relative = os.path.relpath(
            os.path.abspath(os.fspath(path)),
            manifest_dir,
        )
        return relative.replace(os.sep, "/")

    labels = dict(surface_labels or {})

    manifest = {
        # 2 adds surfaces[].label. A version 1 manifest has no labels and is
        # still valid: the viewer falls back to the surface name, which is what
        # it always displayed.
        "schema_version": 2,
        "kind": "gempy-surface-model",
        "coordinate_system": {
            "units": "m",
            "up_axis": "Z",
        },
        "extent": [plain_number(value) for value in extent],
        "resolution": [int(value) for value in resolution],
        "series_order": [str(name) for name in series_order],
        # Where that order came from, and what it is worth. An elevation sort
        # is an assumption this site's procedures contradict, and a reader
        # cannot tell one order from another by looking at it.
        "series_order_provenance": {
            "source": str(order_source or ELEVATION),
            "note": str(
                order_note
                if order_note is not None
                else series_order_module.describe(order_source or ELEVATION)
            ),
            "arbitrary_pairs": [
                [str(earlier), str(later)] for earlier, later in (arbitrary_pairs or [])
            ],
        },
        "single_face_note": (
            None if single_face_note is None else str(single_face_note)
        ),
        "surfaces": [
            {
                # `name` is the identity GemPy fused on -- "Locus 6". `label`
                # is what a reader should see -- "Locus 6 (10YR 5/3 brown)".
                # Keeping them apart is what stopped a soil colour from being
                # able to split one deposit into two model surfaces.
                "name": str(name),
                "label": str(labels.get(str(name), name)),
                "mesh_path": relative_path(mesh_path),
            }
            for name, mesh_path in zip(series_order, mesh_paths)
        ],
        "lith_block_path": relative_path(lith_block_path),
        "wallTraces": [
            {
                "face": str(trace["face"]),
                "surface": str(trace["surface"]),
                "points": [
                    [plain_number(value) for value in point]
                    for point in trace["points"]
                ],
            }
            for trace in (traces or [])
        ],
    }
    if volume_path is not None:
        manifest["volume"] = {
            "schema_version": 1,
            "format": "raw",
            "dtype": "uint16-le",
            "layout": "C",
            "axes": ["x", "y", "z"],
            "shape": [int(value) for value in resolution],
            "path": relative_path(volume_path),
            "lithologies": [
                {
                    "id": int(lithology["id"]),
                    "name": str(lithology["name"]),
                }
                for lithology in (volume_lithologies or [])
            ],
        }

    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2)
        manifest_file.write("\n")
    return manifest_path


def write_lithology_binary(
    lith_block,
    resolution,
    output_path,
    lithology_names=None,
):
    resolution_array = np.asarray(resolution)
    if (
        resolution_array.shape != (3,)
        or resolution_array.dtype.kind not in "iu"
        or np.any(resolution_array <= 0)
    ):
        raise ValueError("resolution must contain three positive integers")
    shape = tuple(int(value) for value in resolution_array)
    expected_count = int(np.prod(resolution_array, dtype=np.int64))

    values = np.asarray(lith_block)
    if values.size != expected_count:
        raise ValueError(
            "lithology block element count "
            f"{values.size} does not match resolution product {expected_count}"
        )
    if values.dtype.kind not in "iuf":
        raise ValueError("lithology block values must be numeric")
    if not np.isfinite(values).all():
        raise ValueError("lithology block values must be finite")
    if np.any(values < 0):
        raise ValueError("lithology block values must be non-negative")
    if np.any(values != np.floor(values)):
        raise ValueError("lithology block values must be integers")
    if np.any(values > 65535):
        raise ValueError("lithology block values must not exceed 65535")

    # `<u2` is pinned rather than left as the platform's native uint16: the
    # browser decodes this file with DataView.getUint16(i, true), so the file
    # has to be little-endian on every machine that writes one.
    encoded = np.asarray(values.reshape(shape, order="C"), dtype="<u2").ravel(order="C")
    with open(output_path, "wb") as binary_file:
        binary_file.write(encoded.tobytes(order="C"))

    if lithology_names is None:
        names_by_id = {}
    elif isinstance(lithology_names, Mapping):
        names_by_id = dict(lithology_names)
    elif isinstance(lithology_names, (str, bytes)):
        raise TypeError("lithology_names must be a mapping or sequence")
    else:
        names_by_id = {
            index: name for index, name in enumerate(lithology_names, start=1)
        }

    lithologies = []
    for raw_id in np.unique(encoded):
        lithology_id = int(raw_id)
        name = names_by_id.get(lithology_id)
        if not isinstance(name, str) or not name.strip():
            name = f"Lithology {lithology_id}"
        lithologies.append({"id": lithology_id, "name": name})
    return lithologies


def validate_mesh_arrays(vertices, faces):
    try:
        vertex_array = np.array(vertices, dtype=float, copy=True)
    except (TypeError, ValueError) as error:
        raise ValueError("mesh vertices must be a numeric N x 3 array") from error
    if vertex_array.ndim != 2 or vertex_array.shape[1] != 3:
        raise ValueError("mesh vertices must be shaped N x 3")
    if not np.isfinite(vertex_array).all():
        raise ValueError("mesh vertices must contain only finite values")

    face_array = np.asarray(faces)
    if face_array.size == 0:
        face_array = np.empty((0, 3), dtype=int)
    if face_array.ndim != 2 or face_array.shape[1] != 3:
        raise ValueError("mesh faces must be shaped N x 3")
    if not np.issubdtype(face_array.dtype, np.integer):
        raise ValueError("mesh face indices must be integers")
    face_array = np.array(face_array, dtype=int, copy=True)
    if np.any(face_array < 0) or np.any(face_array >= len(vertex_array)):
        raise ValueError("mesh face index is outside the vertex array")

    return vertex_array, face_array


def export_meshes(geo_model, solution, surf_order, outdir, log_cb=None):
    os.makedirs(outdir, exist_ok=True)
    vertices = solution.raw_arrays.vertices
    edges = solution.raw_arrays.edges
    n = min(len(vertices), len(surf_order))
    if n < len(surf_order) and log_cb:
        # Meshes stay aligned with surf_order because both are truncated from
        # the same end, so nothing is mislabelled -- but a surface silently
        # missing from the viewer is worth a line in the log.
        log_cb(
            f"NOTE: GemPy returned {n} mesh(es) for {len(surf_order)} surfaces; "
            f"no mesh was written for: "
            + ", ".join(repr(name) for name in surf_order[n:])
        )
    written = []
    for surf_name, verts, faces in zip(surf_order, vertices[:n], edges[:n]):
        _, validated_faces = validate_mesh_arrays(verts, faces)
        transformed = geo_model.input_transform.apply_inverse(verts)
        transformed_verts, validated_faces = validate_mesh_arrays(
            transformed,
            validated_faces,
        )
        path = os.path.join(outdir, f"{safe_filename(surf_name, 'surface')}.obj")
        with open(path, "w") as f:
            f.write(f"# {surf_name}\n")
            for v in transformed_verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in validated_faces:
                f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")
        written.append(path)
    return written


def run_build(
    points_csv,
    orientations_csv,
    out_prefix,
    project_name="trench_model",
    # Higher voxel count = smoother lith-block/mesh surfaces at the
    # cost of longer compute + bigger .bin/.npz files. GemPy's own
    # docs recommend staying under ~1,000,000 cells total; this is
    # 700,000. Drop back toward (50, 50, 30) only if compute time
    # becomes a problem on a given machine.
    resolution=(100, 100, 70),
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
    surface_labels=None,
    order_source=None,
    arbitrary_pairs=None,
    log_cb=None,
):
    """Runs the full GemPy build stage. Returns a dict describing outputs."""

    def log(msg):
        if log_cb:
            log_cb(msg)

    import gempy as gp

    points = pd.read_csv(points_csv)
    if points.empty:
        raise RuntimeError(f"{points_csv} has no rows. Nothing to model.")

    resolved_extent = extent or infer_extent(points, padding_xy, padding_z)
    log(f"extent: {resolved_extent}")

    if series_order:
        surf_order = (
            [s.strip() for s in series_order]
            if isinstance(series_order, list)
            else [s.strip() for s in series_order.split(";")]
        )
        missing = set(surf_order) - set(points["surface"].unique())
        if missing:
            raise RuntimeError(
                f"--series-order names not found in {points_csv}: "
                f"{', '.join(sorted(missing))}"
            )
        resolved_source = order_source or SUPPLIED
    else:
        surf_order = infer_series_order(points)
        # Nothing better was supplied, so this is the elevation assumption
        # regardless of what the caller claimed.
        resolved_source = ELEVATION
    order_note = series_order_module.describe(resolved_source)
    log(f"stratigraphic order (young -> old): {surf_order}")
    if resolved_source == ELEVATION:
        log("WARNING: " + order_note)
    else:
        log(order_note)
    if arbitrary_pairs:
        log(
            "NOTE: no recorded relationship orders "
            + "; ".join(f"{a!r} and {b!r}" for a, b in arbitrary_pairs)
            + " -- the model imposes an order the excavation did not record"
        )

    coverage = points.groupby("surface")["face"].unique()
    single_face = {
        surf: faces[0] for surf, faces in coverage.items() if len(faces) == 1
    }
    single_face_note = None
    if single_face:
        single_face_note = (
            "These surfaces have points from only ONE face and will still be "
            "interpolated across the whole model extent: "
            + ", ".join(
                f"{surf!r} (only on {face})" for surf, face in single_face.items()
            )
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
        "series_order_source": resolved_source,
        "series_order_note": order_note,
        "arbitrary_order_pairs": [list(pair) for pair in (arbitrary_pairs or [])],
        "single_face_note": single_face_note,
        "outputs": {},
    }

    if save_model:
        model_path = f"{out_prefix}.gempy"
        gp.save_model(geo_model, path=model_path)
        result["outputs"]["model"] = model_path
        log(f"wrote {model_path}")

    volume_ids = geo_model.structural_frame.volume_elements_enumerator
    volume_names = geo_model.structural_frame.volume_elements_names
    if len(volume_ids) != len(volume_names):
        raise ValueError("GemPy volume element IDs and names must have equal lengths")
    lithology_names = {
        int(lithology_id): str(name)
        for lithology_id, name in zip(volume_ids, volume_names)
    }

    lith_binary_path = f"{out_prefix}_lith_block.bin"
    volume_lithologies = write_lithology_binary(
        solution.raw_arrays.lith_block,
        resolution,
        lith_binary_path,
        lithology_names=lithology_names,
    )
    result["outputs"]["lith_block_binary"] = lith_binary_path
    log(f"wrote {lith_binary_path}")

    lith_path = f"{out_prefix}_lith_block.npz"
    np.savez(
        lith_path,
        lith_block=solution.raw_arrays.lith_block,
        resolution=np.array(resolution),
        extent=np.array(resolved_extent),
    )
    result["outputs"]["lith_block"] = lith_path
    log(f"wrote {lith_path}")

    written = []
    if make_meshes:
        meshdir = f"{out_prefix}_meshes"
        written = export_meshes(geo_model, solution, surf_order, meshdir, log_cb=log)
        result["outputs"]["meshes"] = written
        log(f"wrote {len(written)} mesh(es) -> {meshdir}/")

    manifest_path = write_viewer_manifest(
        f"{out_prefix}_viewer.json",
        extent=resolved_extent,
        resolution=resolution,
        series_order=surf_order,
        single_face_note=single_face_note,
        mesh_paths=written,
        lith_block_path=lith_path,
        volume_path=lith_binary_path,
        volume_lithologies=volume_lithologies,
        traces=wall_traces(points),
        surface_labels=surface_labels,
        order_source=resolved_source,
        order_note=order_note,
        arbitrary_pairs=arbitrary_pairs,
    )
    result["outputs"]["viewer_manifest"] = manifest_path
    log(f"wrote {manifest_path}")

    if make_plot:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import gempy_viewer as gpv

            nx, ny, nz = resolution
            cell = {"x": nx, "y": ny, "z": nz}[section_direction] // 2

            def render(ve, ylim, path):
                p = gpv.plot_2d(
                    geo_model,
                    cell_number=[cell],
                    direction=[section_direction],
                    show_data=True,
                    show=False,
                    ve=ve,
                )
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
                    if isinstance(zoom_surfaces, str)
                    else zoom_surfaces
                )
                zrange = middle_zoom_range(points, surf_order, zsurfs)
                if zrange is None:
                    log(
                        "NOTE: no middle layers to zoom into, skipping the zoomed plot."
                    )
                else:
                    zoom_ve = (
                        zoom_vertical_exaggeration
                        if zoom_vertical_exaggeration is not None
                        else vertical_exaggeration * 3
                    )
                    zoom_path = f"{out_prefix}_section_{section_direction}_zoom.png"
                    render(zoom_ve, zrange, zoom_path)
                    result["outputs"]["section_zoom"] = zoom_path
        except Exception as e:
            log(
                f"WARNING: 2D plot failed ({e}); skipping. The model itself "
                f"was still computed and saved."
            )

    return result
