import json
from types import SimpleNamespace

import pytest
from PIL import Image

from poggio_webapp.pipeline import extract_text


def _valid_payload():
    return {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "document": {
            "trenchLabel": {
                "raw": "T 104",
                "proposed": "T104",
                "confidence": "high",
                "bbox": [120, 310, 290, 360],
                "notes": None,
            },
            "faceLabel": None,
            "date": None,
            "gridSquareCm": None,
            "northArrowPresent": None,
            "illustrators": [],
            "gridTiePoints": [],
            "marginalia": [],
            "otherText": [],
        },
        "loci": [],
    }


@pytest.mark.parametrize(
    "prohibition",
    [
        "do not trace boundaries",
        "do not return layer coordinates",
        "do not identify marker positions",
        "do not classify features",
        "do not estimate geometry",
        "do not interpret archaeological chronology",
    ],
)
def test_prompt_contains_every_geometry_prohibition(prohibition):
    assert prohibition in extract_text.build_prompt().lower()


def test_prompt_defines_bounding_box_order():
    prompt = extract_text.build_prompt()

    assert "[xMin, yMin, xMax, yMax]" in prompt
    assert "0-1000" in prompt


def test_prompt_says_uncertainty_should_produce_null():
    prompt = extract_text.build_prompt().lower()

    assert "use null when text is unreadable or uncertain" in prompt


def test_prompt_contains_all_text_transcription_requirements():
    prompt = extract_text.build_prompt().lower()

    assert "transcribe visible text only" in prompt
    assert "do not complete partially visible text" in prompt
    assert "preserve raw transcription" in prompt
    assert "standardized text only in proposed" in prompt
    assert "munsell value with a locus only when" in prompt
    assert "unrelated readable text under othertext" in prompt


def test_image_capping_does_not_enlarge_small_image():
    image = Image.new("RGB", (640, 480))

    capped = extract_text._cap_for_sending(image)

    assert capped is image
    assert capped.size == (640, 480)


def test_image_capping_reduces_oversized_image():
    image = Image.new("RGB", (6144, 3072))

    capped = extract_text._cap_for_sending(image)

    assert capped is not image
    assert capped.size == (3072, 1536)


def _mock_gemini(monkeypatch, payload):
    client_calls = []
    generate_calls = []

    def fake_client(**kwargs):
        client_calls.append(kwargs)
        return object()

    def fake_generate(client, **kwargs):
        generate_calls.append((client, kwargs))
        return SimpleNamespace(text=json.dumps(payload), candidates=[])

    monkeypatch.setattr(extract_text.genai, "Client", fake_client)
    monkeypatch.setattr(extract_text, "generate_with_retry", fake_generate)
    return client_calls, generate_calls


def test_valid_response_is_validated_written_and_returned(tmp_path, monkeypatch):
    payload = _valid_payload()
    api_key = "test-secret-api-key"
    client_calls, generate_calls = _mock_gemini(monkeypatch, payload)
    image_path = tmp_path / "input.png"
    Image.new("RGB", (120, 80)).save(image_path)
    output_path = tmp_path / "nested" / "results" / "text.json"

    result = extract_text.run_text_extraction(
        str(image_path),
        api_key,
        str(output_path),
    )

    written_text = output_path.read_text(encoding="utf-8")
    written = json.loads(written_text)
    assert result == payload
    assert result == written
    assert written_text.startswith("{\n  ")
    assert output_path.parent.is_dir()
    assert api_key not in written_text
    assert client_calls[0]["api_key"] == api_key
    assert len(generate_calls) == 1
    assert generate_calls[0][1]["config"].response_schema is (
        extract_text.FieldWallTextCandidates
    )


def test_invalid_structured_output_raises_clear_error(
    tmp_path,
    monkeypatch,
):
    payload = _valid_payload()
    payload["layers"] = []
    _mock_gemini(monkeypatch, payload)
    image_path = tmp_path / "input.png"
    Image.new("RGB", (120, 80)).save(image_path)
    output_path = tmp_path / "text.json"

    with pytest.raises(
        ValueError,
        match="Invalid structured output for FieldWallTextCandidates",
    ):
        extract_text.run_text_extraction(
            str(image_path),
            "test-secret-api-key",
            str(output_path),
        )

    assert not output_path.exists()
