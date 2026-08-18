"""Persisting the canonical document alongside the legacy normalized one.

The legacy artifact is frozen: `output_clean.json` must come out of the
normalizer byte-for-byte as it did before canonicalization existed, because
every consumer still reads it until P4.
"""

import json
from pathlib import Path

import pytest

import storage
from pipeline import normalizer
from pipeline.canonical import is_canonical

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def legacy_bytes(document):
    """What run_normalize wrote before this phase, computed the old way."""
    data = json.loads(json.dumps(document))
    log = []
    normalizer.clean_null_strings(data, log)
    for face in data.get("trenchProfiles") or []:
        normalizer.dedupe_floor(face, log)
        normalizer.dedupe_cross_layer_features(face, log)
    return json.dumps(data, indent=2)


@pytest.fixture
def job(tmp_path):
    directory = tmp_path / "job"
    (directory / "04_normalize_validate").mkdir(parents=True)
    return directory


def run(job, document):
    source = job / "extraction_output.json"
    source.write_text(json.dumps(document, indent=2), encoding="utf-8")
    out_path = job / "04_normalize_validate" / "output_clean.json"
    data, log = normalizer.run_normalize(str(source), str(out_path))
    return data, log, out_path


# The artifact is written for both mediums


@pytest.mark.parametrize(
    "fixture,schema_type",
    [
        ("t907-parity-fieldwall.json", "FieldWallProfile"),
        ("t907-parity-illustrator.json", "ArchaeologicalDiagram"),
    ],
)
def test_canonical_artifact_is_written(job, fixture, schema_type):
    _, _, out_path = run(job, load_fixture(fixture))

    artifact = normalizer.canonical_path_for(out_path)
    assert artifact.name == "canonical.json"
    assert artifact.parent == out_path.parent

    canonical = json.loads(artifact.read_text(encoding="utf-8"))
    assert is_canonical(canonical)
    assert canonical["sourceSchema"] == schema_type
    assert canonical["faces"][0]["layers"][0]["surfaceId"] == "Locus 1"


# The legacy artifact does not move


@pytest.mark.parametrize(
    "fixture",
    ["t907-parity-fieldwall.json", "t907-parity-illustrator.json"],
)
def test_output_clean_bytes_are_unchanged(job, fixture):
    document = load_fixture(fixture)
    expected = legacy_bytes(document)

    _, _, out_path = run(job, document)

    assert out_path.read_text(encoding="utf-8") == expected


def test_the_raw_extraction_is_never_touched(job):
    document = load_fixture("t907-parity-illustrator.json")
    source = job / "extraction_output.json"
    source.write_text(json.dumps(document, indent=2), encoding="utf-8")
    before = source.read_bytes()

    normalizer.run_normalize(
        str(source), str(job / "04_normalize_validate" / "output_clean.json")
    )

    assert source.read_bytes() == before


# E7: the dedupe passes reach field documents now


def field_doc_with_duplicate_features():
    """A floor drawn as a feature and again as the deepest bottom line."""
    floor = [
        {"xMeters": 0.0, "depthMeters": 0.8},
        {"xMeters": 1.0, "depthMeters": 0.83},
    ]
    return {
        "faceLabel": "N baulk",
        "loci": [{"locusNumber": "1"}, {"locusNumber": "2"}],
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": [{"xMeters": 0.0, "depthMeters": 0.0}],
                "bottomBoundary": [{"xMeters": 0.0, "depthMeters": 0.3}],
                "featuresInLayer": [
                    {"feature": "stone", "shapePoints": floor},
                ],
            },
            {
                "locusNumber": "2",
                "topBoundary": [{"xMeters": 0.0, "depthMeters": 0.3}],
                "bottomBoundary": floor,
                "featuresInLayer": [
                    {"feature": "trench floor", "shapePoints": floor},
                    {"feature": "stone", "shapePoints": floor},
                ],
            },
        ],
    }


def test_dedupe_reaches_a_field_document_on_the_canonical_side(job):
    _, log, out_path = run(job, field_doc_with_duplicate_features())

    canonical = json.loads(
        normalizer.canonical_path_for(out_path).read_text(encoding="utf-8")
    )
    layers = canonical["faces"][0]["layers"]

    assert [f["feature"] for f in layers[0]["features"]] == []
    assert [f["feature"] for f in layers[1]["features"]] == ["stone"]
    assert any("trench-floor" in line for line in log)
    assert any("duplicate feature" in line for line in log)


def test_the_legacy_field_output_keeps_its_duplicates(job):
    """Proof the canonical dedupe did not leak into the frozen artifact."""
    document = field_doc_with_duplicate_features()
    expected = legacy_bytes(document)

    _, _, out_path = run(job, document)
    legacy = json.loads(out_path.read_text(encoding="utf-8"))

    assert out_path.read_text(encoding="utf-8") == expected
    assert len(legacy["layers"][1]["featuresInLayer"]) == 2


def test_illustrator_dedupe_still_runs_on_both_sides(job):
    floor = [
        {"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.8},
        {"xCoordinateMeters": 1.0, "yCoordinateMeters": 0.83},
    ]
    document = {
        "trenchProfiles": [
            {
                "face": "N baulk",
                "layers": [
                    {
                        "layerName": "Locus 1",
                        "bottomBoundary": floor,
                        "featuresInLayer": [
                            {"feature": "trench floor", "shapePoints": floor}
                        ],
                    }
                ],
            }
        ]
    }
    _, _, out_path = run(job, document)

    legacy = json.loads(out_path.read_text(encoding="utf-8"))
    canonical = json.loads(
        normalizer.canonical_path_for(out_path).read_text(encoding="utf-8")
    )

    assert legacy["trenchProfiles"][0]["layers"][0]["featuresInLayer"] is None
    assert canonical["faces"][0]["layers"][0]["features"] == []


# Warnings and failure


def test_canonicalization_warnings_reach_the_log(job):
    _, log, _ = run(job, load_fixture("t907-parity-illustrator.json"))
    assert any("derived it from the bottom of Locus 1" in line for line in log)


def test_a_document_of_neither_schema_fails_the_step(job):
    source = job / "extraction_output.json"
    source.write_text(json.dumps({"somethingElse": 1}), encoding="utf-8")
    out_path = job / "04_normalize_validate" / "output_clean.json"

    with pytest.raises(ValueError, match="schema"):
        normalizer.run_normalize(str(source), str(out_path))

    assert not out_path.exists()
    assert not normalizer.canonical_path_for(out_path).exists()


# D4: canonicalize on read for jobs that predate the artifact


def test_load_canonical_reads_the_written_artifact(job):
    _, _, out_path = run(job, load_fixture("t907-parity-fieldwall.json"))
    normalizer.canonical_path_for(out_path).write_text(
        json.dumps({"canonicalVersion": 1, "marker": "from disk"}), encoding="utf-8"
    )

    assert normalizer.load_canonical(job)["marker"] == "from disk"


def test_load_canonical_falls_back_to_the_normalized_document(job):
    _, _, out_path = run(job, load_fixture("t907-parity-fieldwall.json"))
    normalizer.canonical_path_for(out_path).unlink()

    canonical = normalizer.load_canonical(job)

    assert is_canonical(canonical)
    assert canonical["sourceSchema"] == "FieldWallProfile"


def test_load_canonical_falls_back_to_a_bare_editor_job(tmp_path):
    directory = tmp_path / "editor-job"
    directory.mkdir()
    (directory / "extraction_output.json").write_text(
        json.dumps(load_fixture("t907-parity-illustrator.json")), encoding="utf-8"
    )

    canonical = normalizer.load_canonical(directory)

    assert canonical["sourceSchema"] == "ArchaeologicalDiagram"


def test_load_canonical_says_what_is_missing(tmp_path):
    empty = tmp_path / "empty-job"
    empty.mkdir()

    with pytest.raises(FileNotFoundError, match="empty-job"):
        normalizer.load_canonical(empty)


# The route records the path and nothing else


@pytest.fixture
def normalize_job(client):
    job_id = "abcdef012345"
    directory = storage.JOBS_DIR / job_id
    (directory / "04_normalize_validate").mkdir(parents=True)
    extraction = directory / "extraction_output.json"
    extraction.write_text(
        json.dumps(load_fixture("t907-parity-fieldwall.json")), encoding="utf-8"
    )
    (directory / "meta.json").write_text(
        json.dumps({"job_id": job_id, "extraction_path": str(extraction)}),
        encoding="utf-8",
    )
    return job_id, directory


def test_normalize_route_records_only_the_canonical_path(client, normalize_job):
    job_id, directory = normalize_job
    before = set(json.loads((directory / "meta.json").read_text()))

    response = client.post(f"/api/jobs/{job_id}/normalize")

    assert response.status_code == 200
    meta = json.loads((directory / "meta.json").read_text())
    artifact = directory / "04_normalize_validate" / "canonical.json"
    assert meta["canonical_path"] == str(artifact)
    assert artifact.is_file()

    added = set(meta) - before
    assert added == {"normalized_path", "canonical_path", "updated_at"}


def test_normalize_route_reports_an_unusable_document(client, normalize_job):
    job_id, directory = normalize_job
    (directory / "extraction_output.json").write_text(
        json.dumps({"somethingElse": 1}), encoding="utf-8"
    )

    response = client.post(f"/api/jobs/{job_id}/normalize")

    assert response.status_code == 400
    assert "schema" in response.get_json()["error"]
