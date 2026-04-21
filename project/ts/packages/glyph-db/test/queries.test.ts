import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { Surreal } from "surrealdb";

import { createDb } from "../src/index.js";
import { startSurreal, type EphemeralSurreal } from "./helpers.js";

let srv: EphemeralSurreal;

async function seedMulti(url: string): Promise<void> {
  const s = new Surreal();
  await s.connect(url);
  await s.signin({ username: "root", password: "root" });
  await s.use({ namespace: "hanfont", database: "olik" });
  await s.query(
    "DEFINE TABLE glyph SCHEMALESS;"
      + "DEFINE INDEX glyph_char_uniq ON glyph FIELDS char UNIQUE;"
      + "DEFINE INDEX glyph_stroke_ct ON glyph FIELDS stroke_count;"
      + "DEFINE INDEX glyph_radical ON glyph FIELDS radical;"
      + "DEFINE TABLE prototype SCHEMALESS;"
      + "DEFINE INDEX proto_id_uniq ON prototype FIELDS id UNIQUE;"
      + "DEFINE TABLE uses SCHEMALESS;",
  );
  for (const [char, ct, rad] of [
    ["明", 8, "日"],
    ["清", 11, "氵"],
    ["森", 12, "木"],
  ] as const) {
    await s.query(
      "UPSERT type::record('glyph', $c) MERGE {char:$c, stroke_count:$n, radical:$r, iou_mean:1.0};",
      { c: char, n: ct, r: rad },
    );
  }
  await s.query(
    "UPSERT type::record('prototype', 'proto:moon') MERGE {id:'proto:moon', name:'moon'};",
  );
  await s.query(
    "RELATE glyph:`明`->uses->prototype:`proto:moon` CONTENT {instance_id:'inst1'};",
  );
  await s.close();
}

beforeAll(async () => {
  srv = await startSurreal();
  await seedMulti(srv.url);
});

afterAll(async () => {
  await srv.stop();
});

describe("@olik/glyph-db queries", () => {
  test("listGlyphs filter by radical", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const page = await db.listGlyphs({ filter: { radical: "日" } });
      expect(page.items.map((g) => g.char)).toEqual(["明"]);
    } finally {
      await db.close();
    }
  });

  test("listGlyphs filter by stroke count range", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const page = await db.listGlyphs({ filter: { strokeCountRange: [10, 12] } });
      expect(page.items.map((g) => g.char).sort()).toEqual(["森", "清"].sort());
    } finally {
      await db.close();
    }
  });

  test("listGlyphs sort + paginate", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const first = await db.listGlyphs({ sort: "stroke_count", pageSize: 2 });
      expect(first.items.map((g) => g.char)).toEqual(["明", "清"]);
      expect(first.nextCursor).toBeDefined();
      const second = await db.listGlyphs({
        sort: "stroke_count",
        pageSize: 2,
        cursor: first.nextCursor,
      });
      expect(second.items.map((g) => g.char)).toEqual(["森"]);
      expect(second.nextCursor).toBeUndefined();
    } finally {
      await db.close();
    }
  });

  test("getPrototypeUsers finds chars using a prototype", async () => {
    const db = await createDb({ url: srv.url });
    try {
      const users = await db.getPrototypeUsers("proto:moon");
      expect(users.map((g) => g.char)).toEqual(["明"]);
    } finally {
      await db.close();
    }
  });
});
