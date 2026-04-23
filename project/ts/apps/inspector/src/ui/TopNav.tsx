import * as React from "react";
import { useAppState, type ViewKey } from "../state.js";

const VIEWS: Array<{ key: ViewKey; label: string }> = [
  { key: "decomposition", label: "Decomposition Explorer" },
  { key: "prototype", label: "Prototype Browser" },
  { key: "rules", label: "Rule Browser" },
  { key: "placement", label: "Placement Debugger" },
];

export const TopNav: React.FC = () => {
  const [state, dispatch] = useAppState();

  return (
    <nav
      style={{
        display: "flex",
        gap: 8,
        padding: 12,
        borderBottom: "1px solid #cbd5e1",
      }}
    >
      {VIEWS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => dispatch({ type: "setView", view: key })}
          style={{
            padding: "6px 12px",
            background: state.view === key ? "#0ea5e9" : "transparent",
            color: state.view === key ? "#fff" : "#0f172a",
            border: "1px solid #0ea5e9",
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          {label}
        </button>
      ))}
    </nav>
  );
};
