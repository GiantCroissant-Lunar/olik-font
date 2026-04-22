import { Container, Title, Text, Stack } from "@mantine/core";

export function App() {
  return (
    <Container size="sm" mt="xl">
      <Stack>
        <Title order={1}>olik admin</Title>
        <Text c="dimmed">
          Plan 10 scaffold. Resources wire up in subsequent tasks.
        </Text>
      </Stack>
    </Container>
  );
}
