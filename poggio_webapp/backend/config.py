"""Web-layer configuration.

Filesystem roots live in the top-level ``storage`` module, which ``pipeline``
also depends on. Import that directly rather than re-exporting the paths here:
a re-export would rebind them and reintroduce the stale-copy problem.
"""

ALLOWED_SCAN_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".tif",
    ".tiff",
}
