import {loadBundleFs, type GlyphBundle} from '@olik/glyph-loader';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export const SEED_CHARS = ['明', '清', '國', '森'] as const;

export function exampleDirPath(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  return resolve(here, '../../../../schema/examples');
}

export async function loadSeedBundle(): Promise<GlyphBundle> {
  return await loadBundleFs(exampleDirPath(), SEED_CHARS);
}
