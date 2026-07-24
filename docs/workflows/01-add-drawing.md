---
title: Add a drawing
audience: beginner
status: current
source_files:
  - poggio_webapp/static/app/stages/scan.js
  - poggio_webapp/backend/routes/scans.py
verified_against: 077f108
---

# Add a drawing

This page covers the first step of the manual workflow: upload a source image or PDF and choose the sheet type that matches the drawing.

## Before you start

Open the local app and choose the page that asks you to add a trench drawing. You will need one supported file and a clear idea of whether the sheet is an illustrated trench sheet or a hand-drawn field sheet.

Synthetic documentation example: the generated fixtures in [docs/fixtures/README.md](../fixtures/README.md) are a safe way to practice the workflow without using real excavation data.

## Do this

1. Input: a supported drawing file and the local app.
   - Action: choose the upload option and either drag the file into the drop zone or use the file picker. The app accepts PNG, JPEG, TIFF, and PDF files.
   - Artifact: the file is saved to the job's scan folder and the preview area is populated.
2. Input: the file name and the sketch type you want to trace.
   - Action: pick the sheet type. Choose an illustrated trench sheet for a more polished drawing with layer labels, or a hand-drawn field sheet for a graph-paper style drawing with locus numbers.
   - Artifact: the job metadata records the sheet type and the scan URL.

<!-- SCREENSHOT: 01-add-drawing.png
State: synthetic illustrated fixture, upload complete
Callouts: upload area, sheet type choice, preview
-->

## What the application creates

- A scan preview image or PDF marker in the browser.
- A saved scan artifact in the job folder for later preprocessing.
- Job metadata that records the sheet type, the file name, the scan path, and whether the upload was a PDF.

## Check your result

- The uploaded file appears in the preview area.
- The sheet type is selected and the app shows the drawing as ready.
- The step can continue to preprocessing without requesting an API key.

## Common problems

- The file is rejected because the extension is not in the supported list.
- The preview never appears because the upload did not finish or the file is too large for the current browser session.
- The wrong sheet type was chosen, which will change the later naming conventions for layers or loci.

## Under the hood

The upload screen is driven by [poggio_webapp/static/app/stages/scan.js](../../poggio_webapp/static/app/stages/scan.js). The server route in [poggio_webapp/backend/routes/scans.py](../../poggio_webapp/backend/routes/scans.py) accepts the file, saves it, checks the file extension, and stores the scan metadata for the job.

## Next

Continue to [Prepare the image](02-prepare-image.md) so the drawing is ready to trace.
