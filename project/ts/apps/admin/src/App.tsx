import { useEffect, useState } from "react";
import { Container, Title, Text, Stack, Loader, Alert } from "@mantine/core";
import { Refine } from "@refinedev/core";
import { createDb, type OlikDb } from "@olik/glyph-db";

import { createDataProvider } from "./data-provider.js";
import { noopAuthProvider } from "./auth-provider.js";

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
    <Refine
      dataProvider={createDataProvider(db)}
      authProvider={noopAuthProvider}
      resources={[{ name: "glyph" }, { name: "style_variant" }]}
    >
      <Container size="sm" mt="xl">
        <Stack>
          <Title order={1}>olik admin</Title>
          <Text c="dimmed">Refine is wired. Resources land in Task 7.</Text>
        </Stack>
      </Container>
    </Refine>
  );
}
