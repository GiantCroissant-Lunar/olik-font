declare module "@olik/glyph-viz" {
  import type * as React from "react";

  export interface ModeIndicatorProps {
    mode: "keep" | "refine" | "replace";
    x?: number;
    y?: number;
  }

  export interface InputAdapterChipProps {
    adapter: string;
    x?: number;
    y?: number;
  }

  export interface StrokePathProps {
    outlinePath: string;
    median: ReadonlyArray<readonly [number, number]>;
    progress: number;
    strokeWidth?: number;
    className?: string;
  }

  export function ModeIndicator(props: ModeIndicatorProps): React.ReactElement;
  export function InputAdapterChip(props: InputAdapterChipProps): React.ReactElement;
  export function StrokePath(props: StrokePathProps): React.ReactElement;
}
