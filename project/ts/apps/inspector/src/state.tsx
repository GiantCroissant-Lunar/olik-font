import * as React from "react";
import {
  loadGlyphRecordUrl,
  loadPrototypeLibraryUrl,
  loadRuleTraceUrl,
} from "@olik/glyph-loader";
import type {
  GlyphRecord,
  PrototypeLibrary,
  RuleTrace,
} from "@olik/glyph-schema";

export type ViewKey = "decomposition" | "library" | "rules" | "placement";

export interface AppState {
  library: PrototypeLibrary | null;
  records: Record<string, GlyphRecord>;
  traces: Record<string, RuleTrace>;
  char: string;
  view: ViewKey;
  loading: boolean;
  error: string | null;
}

export type AppAction =
  | {
      type: "loaded";
      library: PrototypeLibrary;
      records: AppState["records"];
      traces: AppState["traces"];
    }
  | { type: "error"; message: string }
  | { type: "setChar"; char: string }
  | { type: "setView"; view: ViewKey };

export const SEED_CHARS = ["明", "清", "國", "森"] as const;

const initial: AppState = {
  library: null,
  records: {},
  traces: {},
  char: "明",
  view: "decomposition",
  loading: true,
  error: null,
};

function reducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "loaded":
      return {
        ...state,
        library: action.library,
        records: action.records,
        traces: action.traces,
        loading: false,
      };
    case "error":
      return { ...state, loading: false, error: action.message };
    case "setChar":
      return { ...state, char: action.char };
    case "setView":
      return { ...state, view: action.view };
  }
}

const Ctx = React.createContext<
  [AppState, React.Dispatch<AppAction>] | null
>(null);

export const AppStateProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [state, dispatch] = React.useReducer(reducer, initial);

  React.useEffect(() => {
    void (async () => {
      try {
        const library = await loadPrototypeLibraryUrl(
          "/data/prototype-library.json",
        );
        const records: AppState["records"] = {};
        const traces: AppState["traces"] = {};

        for (const ch of SEED_CHARS) {
          records[ch] = await loadGlyphRecordUrl(`/data/glyph-record-${ch}.json`);
          traces[ch] = await loadRuleTraceUrl(`/data/rule-trace-${ch}.json`);
        }

        dispatch({ type: "loaded", library, records, traces });
      } catch (error) {
        dispatch({ type: "error", message: (error as Error).message });
      }
    })();
  }, []);

  return <Ctx.Provider value={[state, dispatch]}>{children}</Ctx.Provider>;
};

export function useAppState(): [AppState, React.Dispatch<AppAction>] {
  const ctx = React.useContext(Ctx);
  if (!ctx) {
    throw new Error("useAppState outside AppStateProvider");
  }
  return ctx;
}
