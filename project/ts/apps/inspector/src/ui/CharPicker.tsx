import * as React from "react";
import { SEED_CHARS, useAppState } from "../state.js";

export const CharPicker: React.FC = () => {
  const [state, dispatch] = useAppState();

  return (
    <div style={{ display: "flex", gap: 8, padding: 8 }}>
      {SEED_CHARS.map((ch) => (
        <button
          key={ch}
          onClick={() => dispatch({ type: "setChar", char: ch })}
          style={{
            fontSize: 24,
            fontFamily: "serif",
            padding: "4px 12px",
            background: state.char === ch ? "#fef3c7" : "#fff",
            border: "1px solid #cbd5e1",
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          {ch}
        </button>
      ))}
    </div>
  );
};
