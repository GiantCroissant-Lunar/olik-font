import * as React from "react";
import {
  loadGlyphRecordUrl,
  loadPrototypeBrowserDataUrl,
  loadPrototypeLibraryUrl,
  loadRuleTraceUrl,
  type PrototypeBrowserData,
} from "@olik/glyph-loader";
import type {
  GlyphRecord,
  PrototypeLibrary,
  RuleTrace,
} from "@olik/glyph-schema";

export type ViewKey = "decomposition" | "prototype" | "rules" | "placement";

export interface AppState {
  library: PrototypeLibrary | null;
  prototypeGraphs: Record<string, PrototypeBrowserData>;
  records: Record<string, GlyphRecord>;
  traces: Record<string, RuleTrace>;
  char: string;
  protoId: string;
  view: ViewKey;
  loading: boolean;
  error: string | null;
}

export type AppAction =
  | {
      type: "loaded";
      library: PrototypeLibrary;
      prototypeGraphs: AppState["prototypeGraphs"];
      records: AppState["records"];
      traces: AppState["traces"];
    }
  | { type: "loadedPrototypeGraph"; protoId: string; graph: PrototypeBrowserData }
  | { type: "error"; message: string }
  | { type: "setChar"; char: string }
  | { type: "setProtoId"; protoId: string }
  | { type: "setView"; view: ViewKey };

export const SEED_CHARS = ["明", "清", "國", "森"] as const;

const initial = createInitialState();

function reducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "loaded":
      return {
        ...state,
        library: action.library,
        prototypeGraphs: action.prototypeGraphs,
        records: action.records,
        traces: action.traces,
        loading: false,
      };
    case "loadedPrototypeGraph":
      return {
        ...state,
        prototypeGraphs: {
          ...state.prototypeGraphs,
          [action.protoId]: action.graph,
        },
      };
    case "error":
      return { ...state, loading: false, error: action.message };
    case "setChar":
      return { ...state, char: action.char };
    case "setProtoId":
      return { ...state, protoId: action.protoId };
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
        const prototypeGraph = await loadPrototypeBrowserDataUrl(
          `/data/proto-graph-${initial.protoId}.json`,
        );
        const records: AppState["records"] = {};
        const traces: AppState["traces"] = {};

        for (const ch of SEED_CHARS) {
          records[ch] = await loadGlyphRecordUrl(`/data/glyph-record-${ch}.json`);
          traces[ch] = await loadRuleTraceUrl(`/data/rule-trace-${ch}.json`);
        }

        dispatch({
          type: "loaded",
          library,
          prototypeGraphs: { [initial.protoId]: prototypeGraph },
          records,
          traces,
        });
      } catch (error) {
        dispatch({ type: "error", message: (error as Error).message });
      }
    })();
  }, []);

  React.useEffect(() => {
    if (state.view !== "prototype" || state.prototypeGraphs[state.protoId]) {
      return;
    }
    void (async () => {
      try {
        const graph = await loadPrototypeBrowserDataUrl(
          `/data/proto-graph-${state.protoId}.json`,
        );
        dispatch({ type: "loadedPrototypeGraph", protoId: state.protoId, graph });
      } catch (error) {
        dispatch({ type: "error", message: (error as Error).message });
      }
    })();
  }, [state.protoId, state.prototypeGraphs, state.view]);

  React.useEffect(() => {
    const url = new URL(window.location.href);
    if (state.view === "prototype") {
      url.pathname = `/proto/${state.protoId}`;
      url.searchParams.delete("view");
    } else {
      url.pathname = `/glyph/${state.char}`;
      if (state.view === "decomposition") {
        url.searchParams.delete("view");
      } else {
        url.searchParams.set("view", state.view);
      }
    }
    window.history.replaceState({}, "", url);
  }, [state.char, state.protoId, state.view]);

  return <Ctx.Provider value={[state, dispatch]}>{children}</Ctx.Provider>;
};

export function useAppState(): [AppState, React.Dispatch<AppAction>] {
  const ctx = React.useContext(Ctx);
  if (!ctx) {
    throw new Error("useAppState outside AppStateProvider");
  }
  return ctx;
}

function createInitialState(): AppState {
  const route = readRoute(window.location);
  return {
    library: null,
    prototypeGraphs: {},
    records: {},
    traces: {},
    char: route.char,
    protoId: route.protoId,
    view: route.view,
    loading: true,
    error: null,
  };
}

function readRoute(location: Pick<Location, "pathname" | "search">): {
  char: string;
  protoId: string;
  view: ViewKey;
} {
  const params = new URLSearchParams(location.search);
  const prototypeMatch = location.pathname.match(/^\/proto\/(.+)$/);
  if (prototypeMatch?.[1]) {
    return {
      char: "明",
      protoId: decodeURIComponent(prototypeMatch[1]),
      view: "prototype",
    };
  }
  const pathnameMatch = location.pathname.match(/^\/glyph\/(.+)$/);
  const routeChar = pathnameMatch?.[1] ? decodeURIComponent(pathnameMatch[1]) : null;
  const char = routeChar && SEED_CHARS.includes(routeChar as (typeof SEED_CHARS)[number])
    ? routeChar
    : "明";
  const routeView = params.get("view");
  const view: ViewKey =
    routeView === "rules" || routeView === "placement"
      ? routeView
      : "decomposition";
  return { char, protoId: "u6708", view };
}
