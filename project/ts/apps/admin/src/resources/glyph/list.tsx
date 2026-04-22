import { useMemo, useState } from "react";
import { Link } from "react-router";
import {
  Badge,
  Group,
  MultiSelect,
  Paper,
  RangeSlider,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useList, type CrudFilters } from "@refinedev/core";
import type { Status } from "@olik/glyph-db";
import { STATUS_VALUES } from "@olik/glyph-db";

import { GlyphThumb } from "../../components/GlyphThumb.js";

const STATUS_COLOR: Record<Status, string> = {
  verified: "green",
  needs_review: "yellow",
  unsupported_op: "gray",
  failed_extraction: "red",
};

export function GlyphList() {
  const [statuses, setStatuses] = useState<Status[]>(["verified", "needs_review"]);
  const [iouRange, setIouRange] = useState<[number, number]>([0, 1]);
  const [strokeRange, setStrokeRange] = useState<[number, number]>([1, 30]);
  const [radical, setRadical] = useState("");

  const filters = useMemo(() => {
    const out: CrudFilters = [
      { field: "status", operator: "in", value: statuses },
      { field: "iou_mean", operator: "between", value: iouRange },
      { field: "stroke_count", operator: "between", value: strokeRange },
    ];
    if (radical.trim().length > 0) {
      out.push({ field: "radical", operator: "eq", value: radical.trim() });
    }
    return out;
  }, [statuses, iouRange, strokeRange, radical]);

  const { query } = useList({
    resource: "glyph",
    filters,
    sorters: [{ field: "iou_mean", order: "desc" }],
    pagination: { pageSize: 200 },
  });

  const isLoading = query.isLoading;
  const rows = query.data?.data ?? [];

  return (
    <Stack p="md">
      <Title order={2}>Review queue</Title>
      <Paper shadow="xs" p="md" withBorder>
        <Group align="end" wrap="wrap">
          <MultiSelect
            label="Status filter"
            data={[...STATUS_VALUES] as string[]}
            value={statuses}
            onChange={(v) => setStatuses(v as Status[])}
            w={260}
          />
          <Stack gap={2}>
            <Text size="sm">
              IoU range ({iouRange[0].toFixed(2)}-{iouRange[1].toFixed(2)})
            </Text>
            <RangeSlider
              min={0}
              max={1}
              step={0.05}
              value={iouRange}
              onChange={(v) => setIouRange(v)}
              w={240}
            />
          </Stack>
          <Stack gap={2}>
            <Text size="sm">
              Stroke count ({strokeRange[0]}-{strokeRange[1]})
            </Text>
            <RangeSlider
              min={1}
              max={30}
              step={1}
              value={strokeRange}
              onChange={(v) => setStrokeRange(v)}
              w={220}
            />
          </Stack>
          <TextInput
            label="Radical"
            value={radical}
            onChange={(e) => setRadical(e.currentTarget.value)}
            placeholder="e.g. 木"
            w={140}
          />
        </Group>
      </Paper>

      <Paper shadow="xs" withBorder>
        <Table striped highlightOnHover stickyHeader>
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={80}>Char</Table.Th>
              <Table.Th w={130}>Status</Table.Th>
              <Table.Th w={100}>IoU</Table.Th>
              <Table.Th w={100}>Strokes</Table.Th>
              <Table.Th w={100}>Radical</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading && (
              <Table.Tr>
                <Table.Td colSpan={5}>Loading...</Table.Td>
              </Table.Tr>
            )}
            {rows.map((row) => {
              const r = row as unknown as {
                char: string;
                stroke_count: number;
                radical: string | null;
                iou_mean: number;
                status?: Status;
              };
              return (
                <Table.Tr key={r.char}>
                  <Table.Td>
                    <Group gap={6}>
                      <GlyphThumb char={r.char} size={28} />
                      <Link to={`/glyph/${encodeURIComponent(r.char)}`}>{r.char}</Link>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={STATUS_COLOR[r.status ?? "needs_review"]} variant="light">
                      {r.status ?? "needs_review"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{r.iou_mean.toFixed(3)}</Table.Td>
                  <Table.Td>{r.stroke_count}</Table.Td>
                  <Table.Td>{r.radical ?? "—"}</Table.Td>
                </Table.Tr>
              );
            })}
            {!isLoading && rows.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={5}>No rows match the current filter.</Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}
