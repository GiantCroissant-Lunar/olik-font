import { Alert, Container, Stack, Title } from "@mantine/core";

export function StyleVariantList() {
  return (
    <Container size="md" mt="xl">
      <Stack>
        <Title order={2}>Style variants</Title>
        <Alert color="blue" title="Reserved for Plan 11">
          ComfyUI-generated style variants will appear here once Plan 11 lands.
          Plan 10 ships this route as a placeholder so the Refine resource
          declaration is non-empty.
        </Alert>
      </Stack>
    </Container>
  );
}
