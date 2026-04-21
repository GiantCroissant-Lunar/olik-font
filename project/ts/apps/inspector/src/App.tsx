import * as React from "react";
import { AppStateProvider, useAppState } from "./state.js";
import { TopNav } from "./ui/TopNav.js";
import { CharPicker } from "./ui/CharPicker.js";

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
      <CharPicker />
      <div style={{ padding: 24 }}>
        view <code>{state.view}</code>, char <code>{state.char}</code> (views
        land in Task 6)
      </div>
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
