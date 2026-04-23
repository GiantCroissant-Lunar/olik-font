import * as React from "react";
import { AppStateProvider, useAppState } from "./state.js";
import { TopNav } from "./ui/TopNav.js";
import { CharPicker } from "./ui/CharPicker.js";
import { DecompositionExplorer } from "./views/DecompositionExplorer.js";
import { PrototypeBrowser } from "./views/PrototypeBrowser.js";
import { RuleBrowser } from "./views/RuleBrowser.js";
import { PlacementDebugger } from "./views/PlacementDebugger.js";

const Body: React.FC = () => {
  const [state] = useAppState();

  if (state.loading) {
    return <div style={{ padding: 24 }}>loading…</div>;
  }

  if (state.error) {
    return (
      <div style={{ padding: 24, color: "#dc2626" }}>error: {state.error}</div>
    );
  }

  return (
    <div>
      {state.view !== "prototype" ? <CharPicker /> : null}
      {state.view === "decomposition" ? <DecompositionExplorer /> : null}
      {state.view === "prototype" ? <PrototypeBrowser /> : null}
      {state.view === "rules" ? <RuleBrowser /> : null}
      {state.view === "placement" ? <PlacementDebugger /> : null}
    </div>
  );
};

export const App: React.FC = () => (
  <AppStateProvider>
    <div style={{ fontFamily: "system-ui, sans-serif" }}>
      <TopNav />
      <Body />
    </div>
  </AppStateProvider>
);
