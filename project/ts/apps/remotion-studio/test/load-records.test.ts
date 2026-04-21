import {describe, expect, test} from 'vitest';
import {existsSync} from 'node:fs';
import {resolve} from 'node:path';
import {exampleDirPath, loadSeedBundle} from '../src/load-records.js';

const EXAMPLES = resolve(__dirname, '../../../../schema/examples');

describe('loadSeedBundle', () => {
  test('resolves path relative to ts/schema/examples', () => {
    expect(exampleDirPath()).toContain('schema/examples');
  });

  test.runIf(existsSync(resolve(EXAMPLES, 'prototype-library.json')))(
    'loads all four seed chars + library',
    async () => {
      const bundle = await loadSeedBundle();
      expect(Object.keys(bundle.records).sort()).toEqual(['國', '明', '清', '森'].sort());
      expect(Object.keys(bundle.library.prototypes).length).toBeGreaterThanOrEqual(7);
    },
  );
});
