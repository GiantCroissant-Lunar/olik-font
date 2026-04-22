import { Surreal } from "surrealdb";

import type { GlyphRecord } from "@olik/glyph-schema";
import type {
  GlyphSummary,
  ListOpts,
  ListPage,
  PrototypeSummary,
  ReviewUpdate,
  StyleVariant,
  Unsubscribe,
} from "./types.js";

export interface DbConfig {
  url: string;
  namespace: string;
  database: string;
  user: string;
  pass: string;
}

export const DEFAULT_DB_CONFIG: DbConfig = {
  url: "ws://127.0.0.1:6480/rpc",
  namespace: "hanfont",
  database: "olik",
  user: "root",
  pass: "root",
};

export interface OlikDb {
  listGlyphs(opts?: ListOpts): Promise<ListPage<GlyphSummary>>;
  getGlyph(char: string): Promise<GlyphRecord | null>;
  listPrototypes(): Promise<PrototypeSummary[]>;
  getPrototypeUsers(id: string): Promise<GlyphSummary[]>;
  listVariants(char: string): Promise<StyleVariant[]>;
  subscribeVariants(char: string, cb: (v: StyleVariant) => void): Promise<Unsubscribe>;
  updateGlyphStatus(char: string, update: ReviewUpdate): Promise<void>;
  close(): Promise<void>;
}

export async function createDb(config: Partial<DbConfig> = {}): Promise<OlikDb> {
  const cfg: DbConfig = { ...DEFAULT_DB_CONFIG, ...config };
  const raw = new Surreal();
  await raw.connect(cfg.url);
  await raw.signin({ username: cfg.user, password: cfg.pass });
  await raw.use({ namespace: cfg.namespace, database: cfg.database });

  const { makeQueries } = await import("./queries.js");
  return makeQueries(raw);
}
