import { fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import * as React from "react";
import type { GlyphRecord, PrototypeLibrary } from "@olik/glyph-schema";
import { describe, expect, test } from "vitest";
import {
  AuthoringPanel,
  createAuthoringDocument,
  serializeAuthoringDocument,
  type AuthoringDocument,
} from "../src/views/AuthoringPanel.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const BRIGHT_RECORD = JSON.parse(
  readFileSync(resolve(HERE, "../../../../schema/examples/glyph-record-明.json"), "utf-8"),
) as GlyphRecord;
const LIBRARY = JSON.parse(
  readFileSync(resolve(HERE, "../../../../schema/examples/prototype-library.json"), "utf-8"),
) as PrototypeLibrary;

describe("AuthoringPanel", () => {
  test("replace with prototype updates authored state and serialized JSON", () => {
    let latestDocument = createAuthoringDocument(BRIGHT_RECORD);

    const Harness = () => {
      const [document, setDocument] = React.useState<AuthoringDocument>(latestDocument);

      return (
        <AuthoringPanel
          document={document}
          library={LIBRARY}
          selectedNodeId="inst:sun_1"
          onDocumentChange={(nextDocument) => {
            latestDocument = nextDocument;
            setDocument(nextDocument);
          }}
        />
      );
    };

    render(<Harness />);

    fireEvent.click(screen.getByRole("button", { name: "Replace with…" }));
    fireEvent.change(screen.getByPlaceholderText("Filter by name or proto id"), {
      target: { value: "proto:moon" },
    });
    fireEvent.click(screen.getByText("proto:moon"));

    const serialized = serializeAuthoringDocument(latestDocument);

    expect(serialized.partition[0]).toMatchObject({
      prototype_ref: "proto:sun",
      mode: "replace",
      replacement_proto_ref: "proto:moon",
    });
  });
});
