import * as React from "react";
import type { RenderLayer, StrokeInstance } from "@olik/glyph-schema";
import { LAYER_COLOR } from "./theme.js";

export interface LayerStackProps {
  layers: ReadonlyArray<RenderLayer>;
  strokes: ReadonlyArray<StrokeInstance>;
  panelHeight: number;
  panelWidth?: number;
  gap?: number;
  glyphSize?: number;
}

export function LayerStack({
  layers,
  strokes,
  panelHeight,
  panelWidth = 120,
  gap = 12,
  glyphSize = 1024,
}: LayerStackProps): React.ReactElement {
  const scale = panelWidth / glyphSize;
  const panelInnerH = panelHeight - 24;

  return (
    <g className="olik-layer-stack">
      {layers.map((layer, i) => {
        const inLayer = strokes.filter((s) => s.z >= layer.z_min && s.z <= layer.z_max);
        const yOffset = i * (panelHeight + gap);
        const color = LAYER_COLOR[layer.name] ?? "#0f172a";

        return (
          <g
            key={layer.name}
            className="olik-layer-panel"
            transform={`translate(0, ${yOffset})`}
          >
            <rect
              x={0}
              y={0}
              width={panelWidth}
              height={panelHeight}
              fill="#f8fafc"
              stroke={color}
              strokeWidth={1}
            />
            <text x={8} y={16} fontSize={11} fontFamily="monospace" fill={color}>
              {layer.name} ({inLayer.length})
            </text>
            <g transform={`translate(0, 24) scale(${scale} ${panelInnerH / glyphSize})`}>
              {inLayer.map((s) => (
                <path
                  key={s.id}
                  d={s.path}
                  fill="none"
                  stroke={color}
                  strokeWidth={48}
                  strokeLinecap="round"
                />
              ))}
            </g>
          </g>
        );
      })}
    </g>
  );
}
