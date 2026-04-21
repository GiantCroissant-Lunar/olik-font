import {describe, expect, test} from 'vitest';
import {strokeProgress, strokeStartFrame, totalStrokeFrames} from '../src/timing.js';

describe('stroke timing', () => {
  test('sequential: stroke N starts after stroke N-1 completes', () => {
    expect(strokeStartFrame({strokeIndex: 0, framesPerStroke: 10})).toBe(0);
    expect(strokeStartFrame({strokeIndex: 1, framesPerStroke: 10})).toBe(10);
    expect(strokeStartFrame({strokeIndex: 3, framesPerStroke: 10})).toBe(30);
  });

  test('progress: 0 before start, 1 after completion', () => {
    expect(strokeProgress({frame: 0, strokeIndex: 1, framesPerStroke: 10})).toBe(0);
    expect(strokeProgress({frame: 15, strokeIndex: 1, framesPerStroke: 10})).toBeCloseTo(0.5, 2);
    expect(strokeProgress({frame: 25, strokeIndex: 1, framesPerStroke: 10})).toBe(1);
  });

  test('totalStrokeFrames covers all strokes', () => {
    expect(totalStrokeFrames({strokeCount: 8, framesPerStroke: 10})).toBe(80);
  });
});
