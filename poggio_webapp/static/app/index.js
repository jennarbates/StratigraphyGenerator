import {
  configureNavigation,
  renderSidebar,
  renderStepNav,
} from "./core/navigation.js";
import { state } from "./core/state.js";

import { renderConvert } from "./stages/convert.js";
import { renderDraw } from "./stages/draw.js";
import { renderExtract } from "./stages/extract.js";
import { renderGempy } from "./stages/gempy.js";
import { renderNormalize } from "./stages/normalize.js";
import { renderPreprocess } from "./stages/preprocess.js";
import { renderScan } from "./stages/scan.js";
import { renderValidate } from "./stages/validate.js";
import { renderVisualize } from "./stages/visualize.js";

const RENDERERS = {
  scan: renderScan,
  preprocess: renderPreprocess,
  draw: renderDraw,
  extract: renderExtract,
  normalize: renderNormalize,
  validate: renderValidate,
  convert: renderConvert,
  gempy: renderGempy,
  visualize: renderVisualize,
};

function render() {
  renderSidebar();
  (RENDERERS[state.current] || renderScan)();
  renderStepNav();
}

configureNavigation(render);
render();
