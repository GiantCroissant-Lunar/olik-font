export function strokeStartFrame(params: {
  strokeIndex: number;
  framesPerStroke: number;
}): number {
  return params.strokeIndex * params.framesPerStroke;
}

export function strokeProgress(params: {
  frame: number;
  strokeIndex: number;
  framesPerStroke: number;
}): number {
  const start = strokeStartFrame(params);
  const end = start + params.framesPerStroke;
  if (params.frame <= start) return 0;
  if (params.frame >= end) return 1;
  return (params.frame - start) / params.framesPerStroke;
}

export function totalStrokeFrames(params: {
  strokeCount: number;
  framesPerStroke: number;
}): number {
  return params.strokeCount * params.framesPerStroke;
}
