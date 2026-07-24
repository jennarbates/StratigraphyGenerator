#!/usr/bin/env python3
"""Split visualizer.html into CSS and focused ES modules."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "visualizer.html"
BACKUP = ROOT / "visualizer.legacy.html"
OUT = ROOT / "visualizer"


def stop(message: str) -> None:
    raise SystemExit(message)


def cut(text: str, start: str, end: str | None = None) -> str:
    start_index = text.find(start)
    if start_index < 0:
        stop(f"Missing expected marker: {start!r}")

    if end is None:
        end_index = len(text)
    else:
        end_index = text.find(end, start_index)
        if end_index < 0:
            stop(f"Missing expected marker: {end!r}")

    return text[start_index:end_index].strip() + "\n"


def replace_state_names(code: str) -> str:
    replacements = {
        "DATA_A": "state.dataA",
        "DATA_B": "state.dataB",
        "IMG_URL": "state.imageUrl",
        "activeFace": "state.activeFace",
        "compare": "state.compare",
    }

    for old, new in replacements.items():
        code = re.sub(rf"\b{old}\b", new, code)

    # Undo one comment-only replacement so the generated prose stays readable.
    return code.replace("A/B state.compare works", "A/B compare works")


def write(name: str, content: str) -> Path:
    target = OUT / name
    target.write_text(content.rstrip() + "\n", encoding="utf-8")
    return target


def main() -> None:
    if not SOURCE.exists():
        stop("Put this script beside visualizer.html and run it again.")

    if BACKUP.exists():
        stop("visualizer.legacy.html already exists; move or remove it first.")

    if OUT.exists():
        stop("visualizer/ already exists; move or remove it first.")

    source = SOURCE.read_text(encoding="utf-8")

    style_match = re.search(
        r"<style>\s*(.*?)\s*</style>",
        source,
        flags=re.DOTALL,
    )
    script_match = re.search(
        r"<script>\s*(.*?)\s*</script>",
        source,
        flags=re.DOTALL,
    )

    if not style_match or not script_match:
        stop("Expected one inline <style> and one inline <script>.")

    javascript = script_match.group(1)

    colors = cut(
        javascript,
        "const PALETTE",
        "let DATA_A",
    ).replace(
        "function colorFor(",
        "export function colorFor(",
        1,
    )

    schema = cut(
        javascript,
        "function ingest",
        "function readJSON",
    ).replace(
        "function ingest(",
        "export function ingest(",
        1,
    )

    file_controls = replace_state_names(
        cut(
            javascript,
            "function readJSON",
            "function ready",
        )
        + "\n"
        + cut(
            javascript,
            "// --- auto-load from the pipeline job",
        )
    )

    file_controls = """\
import { $ } from "./dom.js";
import { ingest } from "./schema.js";
import { state } from "./state.js";
import { ready } from "./view.js";

""" + file_controls

    alignment = cut(
        javascript,
        "// --- overlay alignment",
        "function drawablePoints",
    ).replace(
        "function applyAlign(",
        "export function applyAlign(",
        1,
    )

    svg = replace_state_names(
        cut(
            javascript,
            "// extent across a face's points",
            "// --- overlay alignment",
        )
    )

    svg = svg.replace(
        "function faceExtent(",
        "export function faceExtent(",
        1,
    ).replace(
        "function buildSVG(",
        "export function buildSVG(",
        1,
    )

    svg = """\
import { applyAlign } from "./alignment.js";
import { colorFor } from "./colors.js";
import { $, esc } from "./dom.js";

""" + svg

    view = replace_state_names(
        cut(
            javascript,
            "function ready",
            "// extent across a face's points",
        )
        + "\n"
        + cut(
            javascript,
            "function drawablePoints",
            "// --- auto-load from the pipeline job",
        )
    )

    # esc() is moved into dom.js so both the view and SVG renderer share it.
    view = re.sub(
        r'\nfunction esc\(s\)\{return String\(s\)\.replace'
        r'\(/\[&<>\"\]/g,c=>\(\{.*?\}\[c\]\)\);\}\s*$',
        "\n",
        view,
        flags=re.DOTALL,
    )

    view = view.replace(
        "function ready(",
        "export function ready(",
        1,
    ).replace(
        "function draw(",
        "export function draw(",
        1,
    )

    # The original first draw removes #empty from <main>. Without this guard,
    # a later checkbox redraw accesses a node that no longer exists.
    view = view.replace(
        '$("empty").style.display="none";',
        'const empty = $("empty"); if(empty) empty.style.display="none";',
        1,
    )

    view = """\
import { colorFor } from "./colors.js";
import { $, esc } from "./dom.js";
import { buildSVG, faceExtent } from "./svg.js";
import { state } from "./state.js";

""" + view

    state = """\
export const state = {
  dataA: null,
  dataB: null,
  imageUrl: null,
  activeFace: 0,
  compare: false,
};
"""

    dom = """\
export const $ = (id) => document.getElementById(id);

export function esc(value) {
  return String(value).replace(
    /[&<>"]/g,
    (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
    })[char],
  );
}
"""

    index = 'import "./files.js";\n'

    OUT.mkdir()

    generated = [
        write("state.js", state),
        write("dom.js", dom),
        write("colors.js", colors),
        write("schema.js", schema),
        write("alignment.js", alignment),
        write("svg.js", svg),
        write("view.js", view),
        write("files.js", file_controls),
        write("index.js", index),
        write("visualizer.css", style_match.group(1)),
    ]

    module_tag = (
        '<script type="module" '
        'src="/static/visualizer/index.js"></script>'
    )
    stylesheet_tag = (
        '<link rel="stylesheet" '
        'href="/static/visualizer/visualizer.css">'
    )

    new_html = (
        source[:style_match.start()]
        + stylesheet_tag
        + "\n"
        + source[style_match.end():script_match.start()]
        + module_tag
        + source[script_match.end():]
    )

    if "<style>" in new_html or re.search(r"<script>\s", new_html):
        stop("Inline style/script removal verification failed.")

    if shutil.which("node"):
        for path in generated:
            if path.suffix == ".js":
                subprocess.run(
                    ["node", "--check", str(path)],
                    check=True,
                )

    shutil.copy2(SOURCE, BACKUP)
    SOURCE.write_text(new_html, encoding="utf-8")

    print("Done.")
    print("Original saved as visualizer.legacy.html")
    print("visualizer.html now loads:")
    print("  /static/visualizer/visualizer.css")
    print("  /static/visualizer/index.js")
    print("The existing style.css and app/stages/visualize.js were not changed.")


if __name__ == "__main__":
    main()