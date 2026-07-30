from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from tools.docs.validate_visual_manifest import (
    ASSET_TYPES,
    REQUIRED_KEYS,
    STATUSES,
    check_svg_contract,
    find_unmanifested_images,
    load_manifest,
    main,
    run_checks,
    summarize,
    validate_manifest_entries,
)

COMPLIANT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">'
    "<title>Example</title><desc>An example diagram.</desc></svg>"
)


VALID_ENTRY = {
    "id": "example-diagram",
    "type": "diagram",
    "path": "docs/assets/diagrams/example-diagram.svg",
    "pages": ["docs/index.md"],
    "alt": "An example diagram",
    "caption": "What the example teaches.",
    "status": "approved",
}


def make_repository(
    tmp_path: Path,
    entries: list[dict] | None = None,
    page_body: str = "# Index\n",
    create_asset: bool = True,
) -> Path:
    """Build a miniature repository with a docs page and a manifest."""

    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "index.md").write_text(page_body, encoding="utf-8")

    if create_asset:
        asset = tmp_path / VALID_ENTRY["path"]
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text(COMPLIANT_SVG, encoding="utf-8")

    if entries is not None:
        manifest = docs / "assets" / "visual-manifest.yml"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(yaml.safe_dump(entries), encoding="utf-8")

    return tmp_path


def entry(**overrides) -> dict:
    merged = copy.deepcopy(VALID_ENTRY)
    merged.update(overrides)
    return merged


def messages(issues) -> str:
    return "\n".join(str(issue) for issue in issues)


# --------------------------------------------------------------- the happy path


def test_valid_manifest_passes(tmp_path: Path) -> None:
    repo = make_repository(tmp_path, [entry()])

    assert validate_manifest_entries([entry()], repo) == []


def test_repository_manifest_is_valid() -> None:
    """The real manifest in this repository must always validate."""

    assert run_checks(Path(__file__).resolve().parents[2]) == []


# ------------------------------------------------------------ structural rules


@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_missing_required_key_fails(tmp_path: Path, key: str) -> None:
    incomplete = entry()
    del incomplete[key]
    repo = make_repository(tmp_path, [incomplete])

    assert f"missing required key: {key}" in messages(
        validate_manifest_entries([incomplete], repo)
    )


def test_duplicate_asset_id_fails(tmp_path: Path) -> None:
    repo = make_repository(tmp_path, [entry(), entry()])

    assert "duplicate asset id" in messages(
        validate_manifest_entries([entry(), entry()], repo)
    )


def test_unknown_type_fails(tmp_path: Path) -> None:
    bad = entry(type="painting")
    repo = make_repository(tmp_path, [bad])

    assert "unknown type" in messages(validate_manifest_entries([bad], repo))


def test_unknown_status_fails(tmp_path: Path) -> None:
    bad = entry(status="published")
    repo = make_repository(tmp_path, [bad])

    assert "unknown status" in messages(validate_manifest_entries([bad], repo))


@pytest.mark.parametrize("key", ["alt", "caption"])
def test_empty_text_fails(tmp_path: Path, key: str) -> None:
    bad = entry(**{key: "   "})
    repo = make_repository(tmp_path, [bad])

    assert f"{key} must be a non-empty string" in messages(
        validate_manifest_entries([bad], repo)
    )


def test_page_that_does_not_exist_fails(tmp_path: Path) -> None:
    bad = entry(pages=["docs/nowhere.md"])
    repo = make_repository(tmp_path, [bad])

    assert "page does not exist" in messages(validate_manifest_entries([bad], repo))


def test_empty_pages_list_fails(tmp_path: Path) -> None:
    bad = entry(pages=[])
    repo = make_repository(tmp_path, [bad])

    assert "pages must be a non-empty list" in messages(
        validate_manifest_entries([bad], repo)
    )


# -------------------------------------------------------------------- the path


def test_asset_outside_assets_directory_fails(tmp_path: Path) -> None:
    bad = entry(path="docs/diagrams/example-diagram.svg")
    repo = make_repository(tmp_path, [bad])

    assert "must sit under docs/assets" in messages(
        validate_manifest_entries([bad], repo)
    )


def test_missing_asset_file_fails_when_approved(tmp_path: Path) -> None:
    repo = make_repository(tmp_path, [entry()], create_asset=False)

    assert "the file is missing" in messages(validate_manifest_entries([entry()], repo))


def test_missing_asset_file_is_allowed_when_planned(tmp_path: Path) -> None:
    """A planned visual has not been produced yet, so its file cannot exist."""

    planned = entry(status="planned")
    repo = make_repository(tmp_path, [planned], create_asset=False)

    assert validate_manifest_entries([planned], repo) == []


def test_unstable_job_id_in_filename_fails(tmp_path: Path) -> None:
    bad = entry(
        id="w01-a3f9b2c1d4e5",
        path="docs/assets/screenshots/w01-a3f9b2c1d4e5.png",
        type="screenshot",
        status="planned",
        fixture="demo-fieldwall",
        ui_state="Step 1",
    )
    repo = make_repository(tmp_path, [bad])

    assert "unstable job id" in messages(validate_manifest_entries([bad], repo))


# ------------------------------------------------------------- per-type rules


def test_mermaid_entry_may_not_carry_a_path(tmp_path: Path) -> None:
    bad = entry(type="mermaid")
    repo = make_repository(tmp_path, [bad])

    assert "take no path" in messages(validate_manifest_entries([bad], repo))


def test_mermaid_entry_without_path_passes(tmp_path: Path) -> None:
    good = entry(type="mermaid")
    del good["path"]
    repo = make_repository(tmp_path, [good])

    assert validate_manifest_entries([good], repo) == []


def test_file_entry_without_path_fails(tmp_path: Path) -> None:
    bad = entry()
    del bad["path"]
    repo = make_repository(tmp_path, [bad])

    assert "entries need a path" in messages(validate_manifest_entries([bad], repo))


def test_generated_entry_needs_a_regenerate_command(tmp_path: Path) -> None:
    bad = entry(type="generated")
    repo = make_repository(tmp_path, [bad])

    assert "regenerate command" in messages(validate_manifest_entries([bad], repo))


@pytest.mark.parametrize("key", ["fixture", "ui_state"])
def test_screenshot_needs_capture_metadata(tmp_path: Path, key: str) -> None:
    bad = entry(type="screenshot", fixture="demo-fieldwall", ui_state="Step 1")
    del bad[key]
    repo = make_repository(tmp_path, [bad])

    assert f"screenshots need {key}" in messages(
        validate_manifest_entries([bad], repo)
    )


# ------------------------------------------------------- the reverse direction


def test_embedded_image_without_manifest_entry_fails(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        [],
        page_body="![A stray image](assets/diagrams/stray.svg)\n",
    )

    assert "no manifest entry" in messages(find_unmanifested_images([], repo))


def test_embedding_an_unapproved_visual_fails(tmp_path: Path) -> None:
    """A planned visual must not reach a page before it is reviewed."""

    planned = entry(status="planned")
    repo = make_repository(
        tmp_path,
        [planned],
        page_body="![An example diagram](assets/diagrams/example-diagram.svg)\n",
    )

    assert "not 'approved'" in messages(find_unmanifested_images([planned], repo))


def test_embedding_an_approved_visual_passes(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        [entry()],
        page_body="![An example diagram](assets/diagrams/example-diagram.svg)\n",
    )

    assert find_unmanifested_images([entry()], repo) == []


def test_remote_images_are_ignored(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        [],
        page_body="![Remote](https://example.invalid/x.png)\n",
    )

    assert find_unmanifested_images([], repo) == []


# ------------------------------------------------------------------- the tool


def test_manifest_must_be_a_list(tmp_path: Path) -> None:
    repo = make_repository(tmp_path, [])
    manifest = repo / "docs" / "assets" / "visual-manifest.yml"
    manifest.write_text("id: not-a-list\n", encoding="utf-8")

    assert "could not read manifest" in messages(run_checks(repo))


def test_missing_manifest_is_reported(tmp_path: Path) -> None:
    repo = make_repository(tmp_path)

    assert "manifest not found" in messages(run_checks(repo))


def test_empty_manifest_loads_as_no_entries(tmp_path: Path) -> None:
    repo = make_repository(tmp_path, [])
    manifest = repo / "docs" / "assets" / "visual-manifest.yml"
    manifest.write_text("", encoding="utf-8")

    assert load_manifest(manifest) == []


def test_summarize_counts_by_status() -> None:
    text = summarize([entry(), entry(status="planned"), entry(status="planned")])

    assert "3 visuals" in text
    assert "1 approved" in text
    assert "2 planned" in text


def test_main_returns_one_on_a_bad_manifest(tmp_path: Path, capsys) -> None:
    bad = entry(alt="")
    repo = make_repository(tmp_path, [bad])

    assert main([str(repo)]) == 1
    assert "alt must be" in capsys.readouterr().out


def test_main_returns_zero_on_a_good_manifest(tmp_path: Path, capsys) -> None:
    repo = make_repository(tmp_path, [entry()])

    assert main([str(repo)]) == 0
    assert "Visual manifest passed" in capsys.readouterr().out


# ---------------------------------------------------------- the SVG contract


def write_svg(tmp_path: Path, markup: str) -> Path:
    path = tmp_path / "diagram.svg"
    path.write_text(markup, encoding="utf-8")
    return path


def test_compliant_svg_has_no_contract_problems(tmp_path: Path) -> None:
    assert check_svg_contract(write_svg(tmp_path, COMPLIANT_SVG)) == []


def test_svg_without_viewbox_fails(tmp_path: Path) -> None:
    markup = COMPLIANT_SVG.replace('viewBox="0 0 100 50"', "")

    assert "no viewBox" in " ".join(check_svg_contract(write_svg(tmp_path, markup)))


def test_svg_without_title_fails(tmp_path: Path) -> None:
    markup = COMPLIANT_SVG.replace("<title>Example</title>", "")

    assert "no <title>" in " ".join(check_svg_contract(write_svg(tmp_path, markup)))


def test_svg_without_desc_fails(tmp_path: Path) -> None:
    markup = COMPLIANT_SVG.replace("<desc>An example diagram.</desc>", "")

    assert "no <desc>" in " ".join(check_svg_contract(write_svg(tmp_path, markup)))


def test_svg_with_fixed_width_fails(tmp_path: Path) -> None:
    markup = COMPLIANT_SVG.replace("<svg ", '<svg width="800" ')

    assert "fixed width" in " ".join(check_svg_contract(write_svg(tmp_path, markup)))


def test_svg_embedding_raster_data_fails(tmp_path: Path) -> None:
    markup = COMPLIANT_SVG.replace(
        "</svg>", '<image href="data:image/png;base64,AAAA"/></svg>'
    )

    assert "raster" in " ".join(check_svg_contract(write_svg(tmp_path, markup)))


def test_generated_diagrams_satisfy_the_contract() -> None:
    """Every SVG this repository ships must satisfy the contract."""

    root = Path(__file__).resolve().parents[2]
    svgs = sorted((root / "docs" / "assets" / "diagrams").glob("*.svg"))

    assert svgs, "expected generated diagrams to exist"
    for svg in svgs:
        assert check_svg_contract(svg) == [], svg.name


def test_statuses_and_types_are_the_documented_sets() -> None:
    assert STATUSES == {"planned", "captured", "approved"}
    assert ASSET_TYPES == {"screenshot", "diagram", "generated", "mermaid"}
