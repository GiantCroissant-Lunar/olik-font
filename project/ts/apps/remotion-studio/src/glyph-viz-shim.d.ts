declare module "@olik/glyph-viz" {
  import type * as React from "react";
  import type {
    BBox,
    LayoutNode,
    Point,
    RenderLayer,
    StrokeInstance,
  } from "@olik/glyph-schema";

  export interface StrokePathProps {
    outlinePath: string;
    median: ReadonlyArray<readonly [number, number]>;
    progress: number;
    strokeWidth?: number;
    className?: string;
  }

  export interface VirtualCoordGridProps {
    size?: number;
    majorStep?: number;
    minorStep?: number;
    majorColor?: string;
    minorColor?: string;
  }

  export interface BBoxOverlayProps {
    bbox: BBox;
    label?: string;
    color?: string;
    dashed?: boolean;
  }

  export interface AnchorMarkerProps {
    name: string;
    point: Point;
    color?: string;
    radius?: number;
  }

  export interface AnchorBindingArrowProps {
    from: Point;
    to: Point;
    color?: string;
    label?: string;
  }

  export interface TreeLayoutProps {
    root: LayoutNode;
    width: number;
    height: number;
    nodeRadius?: number;
    linkColor?: string;
    renderNode: (node: LayoutNode) => React.ReactNode;
  }

  export interface GraphNode {
    id: string;
    x: number;
    y: number;
    data?: unknown;
  }

  export interface GraphLink {
    source: string;
    target: string;
    kind?: string;
  }

  export interface GraphLayoutProps {
    nodes: ReadonlyArray<GraphNode>;
    links: ReadonlyArray<GraphLink>;
    linkColor?: string;
    renderNode: (node: GraphNode) => React.ReactNode;
  }

  export interface LayerStackProps {
    layers: ReadonlyArray<RenderLayer>;
    strokes: ReadonlyArray<StrokeInstance>;
    panelHeight: number;
    panelWidth?: number;
    gap?: number;
    glyphSize?: number;
  }

  export interface IoUBadgeProps {
    value: number;
    label?: string;
    x?: number;
    y?: number;
  }

  export interface InputAdapterChipProps {
    adapter: string;
    x?: number;
    y?: number;
  }

  export interface ModeIndicatorProps {
    mode: "keep" | "refine" | "replace";
    x?: number;
    y?: number;
  }

  export function StrokePath(props: StrokePathProps): React.ReactElement;
  export function VirtualCoordGrid(props: VirtualCoordGridProps): React.ReactElement;
  export function BBoxOverlay(props: BBoxOverlayProps): React.ReactElement;
  export function AnchorMarker(props: AnchorMarkerProps): React.ReactElement;
  export function AnchorBindingArrow(props: AnchorBindingArrowProps): React.ReactElement;
  export function TreeLayout(props: TreeLayoutProps): React.ReactElement;
  export function GraphLayout(props: GraphLayoutProps): React.ReactElement;
  export function LayerStack(props: LayerStackProps): React.ReactElement;
  export function IoUBadge(props: IoUBadgeProps): React.ReactElement;
  export function InputAdapterChip(props: InputAdapterChipProps): React.ReactElement;
  export function ModeIndicator(props: ModeIndicatorProps): React.ReactElement;
}
