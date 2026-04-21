import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { PrototypeLibrary } from "../src/prototype-library.js";

const exampleHello = resolve(
  __dirname,
  "../../../../schema/examples/hello-library.json",
);

describe("PrototypeLibrary", () => {
  test("hello example validates", () => {
    const raw = JSON.parse(readFileSync(exampleHello, "utf-8"));
    const parsed = PrototypeLibrary.parse(raw);
    expect(parsed.prototypes["proto:hello"].name).toBe("hello");
  });

  test("rejects library missing coord_space", () => {
    const raw: Record<string, unknown> = JSON.parse(
      readFileSync(exampleHello, "utf-8"),
    );
    delete raw.coord_space;
    expect(() => PrototypeLibrary.parse(raw)).toThrow();
  });

  test("rejects prototype whose id doesn't match proto: pattern", () => {
    const raw = JSON.parse(readFileSync(exampleHello, "utf-8"));
    raw.prototypes["bogus"] = raw.prototypes["proto:hello"];
    expect(() => PrototypeLibrary.parse(raw)).toThrow();
  });

  test("infers Prototype type with TS", () => {
    const raw = JSON.parse(readFileSync(exampleHello, "utf-8"));
    const parsed = PrototypeLibrary.parse(raw);
    const proto = parsed.prototypes["proto:hello"];
    const _canonical: [number, number, number, number] = proto.canonical_bbox;
    expect(_canonical).toHaveLength(4);
  });
});
