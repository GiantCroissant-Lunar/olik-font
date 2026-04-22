import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import {
  Alert,
  Badge,
  Button,
  Grid,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useHotkeys } from "@mantine/hooks";
import { useList, useOne, useUpdate } from "@refinedev/core";
import type { Status } from "@olik/glyph-db";

import { GlyphSvg } from "../../components/GlyphSvg.js";
import { MmhSvg } from "../../components/MmhSvg.js";
import { ReviewActions } from "../../components/ReviewActions.js";

export function GlyphDetail() {
  const { id } = useParams<{ id: string }>();
  const char = id ? decodeURIComponent(id) : "";
  const navigate = useNavigate();

  const { data: one, isLoading } = useOne({ resource: "glyph", id: char });
  const { data: list } = useList({
    resource: "glyph",
    filters: [{ field: "status", operator: "in", value: ["needs_review"] }],
    sorters: [{ field: "iou_mean", order: "desc" }],
    pagination: { pageSize: 500 },
  });
  const { mutate: updateGlyph, isPending: updating } = useUpdate();

  const [reviewNote, setReviewNote] = useState("");
  useEffect(() => {
    const existing = (one?.data as { review_note?: string } | undefined)?.review_note;
    setReviewNote(existing ?? "");
  }, [one?.data]);

  const queue: string[] = ((list?.data as Array<{ char: string }>) ?? []).map((r) => r.char);
  const idx = queue.indexOf(char);

  const goTo = useCallback(
    (nextIdx: number) => {
      const target = queue[nextIdx];
      if (target !== undefined) navigate(`/glyph/${encodeURIComponent(target)}`);
    },
    [queue, navigate],
  );

  const transition = useCallback(
    (newStatus: Status, note: string | null) => {
      updateGlyph(
        {
          resource: "glyph",
          id: char,
          values: { status: newStatus, review_note: note },
        },
        {
          onSuccess: () => {
            notifications.show({
              color: newStatus === "verified" ? "green" : "red",
              message: `${char} → ${newStatus}`,
            });
            if (idx >= 0) goTo(idx + 1);
          },
          onError: (e) =>
            notifications.show({
              color: "red",
              title: "Update failed",
              message: String(e),
            }),
        },
      );
    },
    [char, idx, updateGlyph, goTo],
  );

  useHotkeys([["escape", () => navigate("/glyph")]]);

  if (isLoading || one?.data === undefined) {
    return (
      <Stack p="md">
        <Loader />
      </Stack>
    );
  }

  const row = one.data as unknown as {
    char: string;
    status: Status;
    iou_mean?: number;
    stroke_count?: number;
    radical?: string | null;
    stroke_instances?: Array<{ path?: string; d?: string }>;
    mmh_strokes?: string[];
    components?: unknown[];
    extraction_run?: string;
    reviewed_at?: string;
    reviewed_by?: string;
  };

  const composedPaths = (row.stroke_instances ?? [])
    .map((s) => s.path ?? s.d ?? "")
    .filter((d) => d.length > 0);
  const mmhPaths = row.mmh_strokes ?? [];

  if (mmhPaths.length === 0) {
    return (
      <Stack p="md">
        <Alert color="yellow" title="No MMH reference">
          This glyph row lacks <code>mmh_strokes</code> - pre-Plan-10 row. Re-run{" "}
          <code>olik extract retry</code> to backfill.
        </Alert>
        <Button component={Link} to="/glyph" variant="subtle">
          Back
        </Button>
      </Stack>
    );
  }

  return (
    <Stack p="md">
      <Group justify="space-between">
        <Group>
          <Title order={2}>{row.char}</Title>
          <Badge
            color={
              row.status === "verified"
                ? "green"
                : row.status === "failed_extraction"
                  ? "red"
                  : "yellow"
            }
          >
            {row.status}
          </Badge>
          <Text c="dimmed">iou={row.iou_mean?.toFixed(3) ?? "—"}</Text>
          {idx >= 0 && <Text c="dimmed">{idx + 1}/{queue.length}</Text>}
        </Group>
        <Button component={Link} to="/glyph" variant="subtle">
          Back (Esc)
        </Button>
      </Group>

      <Grid>
        <Grid.Col span={6}>
          <Paper shadow="xs" withBorder>
            <Stack p="xs">
              <Text size="sm" c="dimmed">
                Composed
              </Text>
              <GlyphSvg strokes={composedPaths} size={480} />
            </Stack>
          </Paper>
        </Grid.Col>
        <Grid.Col span={6}>
          <Paper shadow="xs" withBorder>
            <Stack p="xs">
              <Text size="sm" c="dimmed">
                MMH reference
              </Text>
              <MmhSvg strokes={mmhPaths} size={480} />
            </Stack>
          </Paper>
        </Grid.Col>
      </Grid>

      <Paper shadow="xs" p="md" withBorder>
        <Stack gap={4}>
          <Text size="sm">
            strokes: {row.stroke_count ?? composedPaths.length} · radical: {row.radical ?? "—"}
          </Text>
          <Text size="sm">extraction_run: {row.extraction_run ?? "—"}</Text>
          {row.reviewed_at && (
            <Text size="sm" c="dimmed">
              reviewed {row.reviewed_at} by {row.reviewed_by ?? "?"}
            </Text>
          )}
        </Stack>
      </Paper>

      <ReviewActions
        currentStatus={row.status}
        reviewNote={reviewNote}
        onNoteChange={setReviewNote}
        onApprove={() => transition("verified", reviewNote || null)}
        onReject={(note) => transition("failed_extraction", note || null)}
        onNext={() => goTo(idx + 1)}
        onPrev={() => goTo(idx - 1)}
      />

      {updating && (
        <Text size="xs" c="dimmed">
          Saving…
        </Text>
      )}
    </Stack>
  );
}
