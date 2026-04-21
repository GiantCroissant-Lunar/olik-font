import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { Surreal } from "surrealdb";

import { createDb } from "../src/index.js";
import { startSurreal, type EphemeralSurreal } from "./helpers.js";

let srv: EphemeralSurreal;

async function seed(url: string): Promise<void> {
  const s = new Surreal();
  await s.connect(url);
  await s.signin({ username: "root", password: "root" });
  await s.use({ namespace: "hanfont", database: "olik" });
  await s.query(
    "DEFINE TABLE glyph SCHEMALESS;"
    + "DEFINE TABLE style_variant SCHEMALESS;"
    + "DEFINE INDEX sv_char_style ON style_variant FIELDS char, style_name UNIQUE;",
  );
  await s.query(
    "UPSERT type::record('glyph', '明') MERGE {char:'明', stroke_count:8};",
  );
  await s.close();
}

beforeAll(async () => {
  srv = await startSurreal();
  await seed(srv.url);
});

afterAll(async () => { await srv.stop(); });

describe("live variants", () => {
  test("listVariants empty initially", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const v = await db.listVariants("明");
      expect(v).toEqual([]);
    } finally { await db.close(); }
  });

  test("subscribeVariants receives new rows", async () => {
    const db = await createDb({ url: srv.url });
    const received: unknown[] = [];
    const unsub = await db.subscribeVariants("明", (v) => received.push(v));
    // Insert a variant row via a separate client so the LIVE query fires.
    const writer = new Surreal();
    await writer.connect(srv.url);
    await writer.signin({ username: "root", password: "root" });
    await writer.use({ namespace: "hanfont", database: "olik" });
    await writer.query(
      "CREATE style_variant CONTENT "
      + "{char:'明', style_name:'brush', image_ref:'/tmp/x.png', status:'done'};",
    );
    await writer.close();
    // Poll up to 5s for delivery
    const deadline = Date.now() + 5000;
    while (received.length === 0 && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 100));
    }
    await unsub();
    await db.close();
    expect(received.length).toBeGreaterThan(0);
  });
});
