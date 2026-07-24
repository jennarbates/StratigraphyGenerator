// Run with: node poggio_webapp/static/app/stages/start-options.test.mjs
import assert from "node:assert/strict";
import { state } from "../core/state.js";
import {
  editorCreationPayload,
  schemaTypeForSheetType,
} from "./start-options.mjs";

function test(name, callback) {
  callback();
  console.log(`✓ ${name}`);
}

test("illustrator maps to ArchaeologicalDiagram", () => {
  assert.equal(
    schemaTypeForSheetType("illustrator"),
    "ArchaeologicalDiagram",
  );
});

test("fieldwall maps to FieldWallProfile", () => {
  assert.equal(
    schemaTypeForSheetType("fieldwall"),
    "FieldWallProfile",
  );
});

test("an unknown sheet type is rejected clearly", () => {
  assert.throws(
    () => schemaTypeForSheetType("unknown"),
    {
      name: "RangeError",
      message: "Unknown sheet type: unknown",
    },
  );
});

test("the illustrator editor payload uses the archaeological schema", () => {
  assert.deepEqual(
    editorCreationPayload("illustrator"),
    { schema_type: "ArchaeologicalDiagram" },
  );
});

test("the fieldwall editor payload uses the field-wall schema", () => {
  assert.deepEqual(
    editorCreationPayload("fieldwall"),
    { schema_type: "FieldWallProfile" },
  );
});

test("the application defaults to the upload start method", () => {
  assert.equal(state.startMethod, "upload");
});
