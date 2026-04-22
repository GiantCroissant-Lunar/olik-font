import { useEffect, useState } from "react";
import { Alert, Container, Loader } from "@mantine/core";
import { Refine } from "@refinedev/core";
import routerBindings from "@refinedev/react-router";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { createDb, type OlikDb } from "@olik/glyph-db";

import { createDataProvider } from "./data-provider.js";
import { noopAuthProvider } from "./auth-provider.js";
import { GlyphDetail } from "./resources/glyph/detail.js";
import { GlyphList } from "./resources/glyph/list.js";

export function App() {
  const [db, setDb] = useState<OlikDb | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    createDb()
      .then((instance) => {
        if (!cancelled) setDb(instance);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
      db?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <Container size="sm" mt="xl">
        <Alert color="red" title="SurrealDB connection failed">
          {error}
        </Alert>
      </Container>
    );
  }
  if (db === null) {
    return (
      <Container size="sm" mt="xl">
        <Loader />
      </Container>
    );
  }

  return (
    <BrowserRouter>
      <Refine
        dataProvider={createDataProvider(db)}
        authProvider={noopAuthProvider}
        routerProvider={routerBindings}
        resources={[
          { name: "glyph", list: "/glyph", show: "/glyph/:id" },
          { name: "style_variant", list: "/style_variant" },
        ]}
      >
        <Routes>
          <Route path="/" element={<Navigate to="/glyph" replace />} />
          <Route path="/glyph" element={<GlyphList />} />
          <Route path="/glyph/:id" element={<GlyphDetail />} />
        </Routes>
      </Refine>
    </BrowserRouter>
  );
}
