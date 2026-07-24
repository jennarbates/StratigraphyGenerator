---
title: Alternative import and AI extraction
audience: beginner
status: current
source_files:
  - poggio_webapp/static/app/stages/extract.js
  - poggio_webapp/backend/routes/extraction.py
  - poggio_webapp/pipeline/extract_fieldwall.py
  - poggio_webapp/pipeline/extract_illustrator.py
verified_against: a8b58f1
---

# Alternative import and AI extraction

This page covers the optional routes that can supply drawing data when you already have a file or when a person asks for automatic reading.

## Before you start

Manual tracing remains the main path. Use these alternatives only when you already have a data file, have been told to test AI output, or need to skip the manual drawing step for a specific reason.

Synthetic documentation example: the JSON below is invented for documentation and is not a real excavation record.

```json
{
  "source": "extraction",
  "trenchProfiles": [
    {
      "face": "Synthetic face",
      "layers": [
        {
          "layerName": "Layer A",
          "topBoundary": [{"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.0}],
          "bottomBoundary": [{"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.25}]
        }
      ]
    }
  ]
}
```

## Do this

1. Input: an existing JSON file.
   - Action: choose the import option from the optional alternative page. The app accepts a JSON file that matches one of the two supported extraction shapes: an illustrator-style extraction with `trenchProfiles`, or a field-wall extraction with `loci` and `layers`.
   - Artifact: the file is installed as the current extraction so the later cleanup and validation steps can continue.
2. Input: a prepared image and a Gemini API key.
   - Action: open the automatic-reading option only after preprocessing is complete. Paste a temporary API key into the browser field, choose the field-wall grid-square size if needed, and start the request. The app sends the key to the local server for that one request.
   - Artifact: a background task writes a new extraction file and reports whether it finished successfully.
3. Input: AI output and the original drawing.
   - Action: compare the AI result with the drawing before you trust it. The current UI labels this path as experimental, and the geometry is not treated as verified simply because the extraction finished.
   - Artifact: a saved extraction file that you can inspect, clean, and validate.

## What the application creates

- A new extraction file from an uploaded JSON file or from an AI run.
- A task record for the AI request so you can follow progress.
- A replacement extraction that later steps can clean and validate.

## Check your result

- The imported or AI-generated extraction opens in the result area and can be inspected.
- The later cleanup and validation steps can run on the new file.
- You do not treat AI geometry as proven without a human comparison to the original drawing.

## Common problems

- The file is not valid JSON or does not match either supported extraction shape.
- The automatic-reading request is started before preprocessing, so the server rejects it.
- No API key is entered, so the request cannot start.
- The AI response is slow or fails because the network is unavailable or the key is invalid.
- The output looks plausible but still needs manual review against the original drawing.

## Under the hood

The optional page is driven by the extraction stage in `poggio_webapp/static/app/stages/extract.js`. The server route in `poggio_webapp/backend/routes/extraction.py` accepts either an uploaded JSON file or a Gemini request and writes the output into the job's extraction folder. The AI code is in `poggio_webapp/pipeline/extract_illustrator.py` and `poggio_webapp/pipeline/extract_fieldwall.py`, and the backend retries transient request failures through `poggio_webapp/pipeline/_extract_common.py`.

## Next

Continue to [Clean up the data](04-clean-data.md) after you have a saved extraction, or return to [Trace the layers](03-trace-layers.md) if you want to stay on the main manual path.
