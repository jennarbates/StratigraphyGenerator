import {
  CANVAS_HEIGHT_METERS,
  CANVAS_WIDTH_METERS,
  GRID_SPACING_METERS,
  PIXELS_PER_METER,
  metersToPixels,
  nearestGridPoint,
  pixelsToMeters,
} from "./grid.mjs";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const canvas = document.querySelector("#face-canvas");
const snapToggle = document.querySelector("#snap-to-grid");
const coordinateReport = document.querySelector("#coordinate-report");

const widthPixels = metersToPixels(CANVAS_WIDTH_METERS, PIXELS_PER_METER);
const heightPixels = metersToPixels(CANVAS_HEIGHT_METERS, PIXELS_PER_METER);
const gridSpacingPixels = metersToPixels(GRID_SPACING_METERS, PIXELS_PER_METER);

canvas.setAttribute("width", widthPixels);
canvas.setAttribute("height", heightPixels);
canvas.setAttribute("viewBox", `0 0 ${widthPixels} ${heightPixels}`);

const grid = document.createElementNS(SVG_NAMESPACE, "g");
grid.setAttribute("aria-hidden", "true");

function addGridLine(x1, y1, x2, y2) {
  const line = document.createElementNS(SVG_NAMESPACE, "line");
  line.setAttribute("class", "grid-line");
  line.setAttribute("x1", x1);
  line.setAttribute("y1", y1);
  line.setAttribute("x2", x2);
  line.setAttribute("y2", y2);
  grid.append(line);
}

for (let x = 0; x <= widthPixels; x += gridSpacingPixels) {
  addGridLine(x, 0, x, heightPixels);
}

for (let y = 0; y <= heightPixels; y += gridSpacingPixels) {
  addGridLine(0, y, widthPixels, y);
}

canvas.append(grid);

canvas.addEventListener("click", (event) => {
  const bounds = canvas.getBoundingClientRect();
  const scaleX = widthPixels / bounds.width;
  const scaleY = heightPixels / bounds.height;
  const rawPoint = {
    x: (event.clientX - bounds.left) * scaleX,
    y: (event.clientY - bounds.top) * scaleY,
  };
  const reportedPoint = snapToggle.checked
    ? nearestGridPoint(rawPoint.x, rawPoint.y, gridSpacingPixels)
    : rawPoint;
  const xMeters = pixelsToMeters(reportedPoint.x, PIXELS_PER_METER);
  const yMeters = pixelsToMeters(reportedPoint.y, PIXELS_PER_METER);

  coordinateReport.textContent = (
    `Coordinate: (${xMeters.toFixed(3)}m, ${yMeters.toFixed(3)}m)`
    + ` — snap ${snapToggle.checked ? "on" : "off"}`
  );
});
