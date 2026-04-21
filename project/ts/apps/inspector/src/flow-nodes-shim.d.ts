declare module "@olik/flow-nodes" {
  import type * as React from "react";

  export const NODE_TYPE_KEYS: {
    readonly decomp: "olik-decomp";
    readonly placement: "olik-placement";
    readonly prototype: "olik-prototype";
  };

  export const DecompNode: React.ComponentType<any>;
  export const PlacementNode: React.ComponentType<any>;
  export const PrototypeNode: React.ComponentType<any>;
}
