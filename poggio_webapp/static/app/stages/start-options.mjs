const SCHEMA_TYPE_BY_SHEET_TYPE = Object.freeze({
  illustrator: "ArchaeologicalDiagram",
  fieldwall: "FieldWallProfile",
});

export function schemaTypeForSheetType(sheetType) {
  if (typeof sheetType !== "string") {
    throw new TypeError("Sheet type must be a string.");
  }

  const schemaType = SCHEMA_TYPE_BY_SHEET_TYPE[sheetType];
  if (schemaType === undefined) {
    throw new RangeError(`Unknown sheet type: ${sheetType}`);
  }

  return schemaType;
}

export function editorCreationPayload(sheetType) {
  return {
    schema_type: schemaTypeForSheetType(sheetType),
  };
}
