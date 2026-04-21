import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { Surreal } from "surrealdb";

import { createDb } from "../src/index.js";
import { startSurreal, type EphemeralSurreal } from "./helpers.js";

let srv: EphemeralSurreal;
let seedUrl: string;

async function seed(url: string): Promise<void> {
  const s = new Surreal();
  await s.connect(url);
  await s.signin({ username: "root", password: "root" });
  await s.use({ namespace: "hanfont", database: "olik" });
  await s.query(
    "DEFINE TABLE glyph SCHEMALESS; "
      + "DEFINE INDEX glyph_char_uniq ON glyph FIELDS char UNIQUE;",
  );
  await s.query(
    "UPSERT type::record('glyph', '明') MERGE {char:'明', stroke_count:8, radical:'日', iou_mean:1.0};",
  );
  await s.close();
}

beforeAll(async () => {
  srv = await startSurreal();
  seedUrl = srv.url;
  await seed(seedUrl);
});

afterAll(async () => {
  await srv.stop();
});

describe("@olik/glyph-db contract", () => {
  test("listGlyphs returns the seeded glyph", async () => {
    const db = await createDb({ url: seedUrl });
    try {
      const page = await db.listGlyphs();
      expect(page.items).toEqual([
        {
          char: "明",
          stroke_count: 8,
          radical: "日",
          iou_mean: 1.0,
        },
      ]);
    } finally {
      await db.close();
    }
  });

  test("getGlyph returns the seeded glyph record", async () => {
    const db = await createDb({ url: seedUrl });
    try {
      const rec = await db.getGlyph("明");
      expect(rec?.char).toBe("明");
    } finally {
      await db.close();
    }
  });

  test("getGlyph returns null for unknown char", async () => {
    const db = await createDb({ url: seedUrl });
    try {
      const rec = await db.getGlyph("NOPE");
      expect(rec).toBeNull();
    } finally {
      await db.close();
    }
  });
});
