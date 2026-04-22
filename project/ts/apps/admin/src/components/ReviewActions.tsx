import { useEffect } from "react";
import { Button, Group, Stack, Text, Textarea } from "@mantine/core";
import type { Status } from "@olik/glyph-db";

interface ReviewActionsProps {
  currentStatus: Status;
  reviewNote: string;
  onNoteChange: (note: string) => void;
  onApprove: () => void;
  onReject: (note: string) => void;
  onNext: () => void;
  onPrev: () => void;
}

export function ReviewActions({
  currentStatus,
  reviewNote,
  onNoteChange,
  onApprove,
  onReject,
  onNext,
  onPrev,
}: ReviewActionsProps) {
  const alreadyVerified = currentStatus === "verified";
  const alreadyRejected = currentStatus === "failed_extraction";

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      switch (event.key.toLowerCase()) {
        case "y":
          if (!alreadyVerified) onApprove();
          break;
        case "n":
          if (!alreadyRejected) onReject(reviewNote);
          break;
        case "j":
          onNext();
          break;
        case "k":
          onPrev();
          break;
        case "r":
          document.getElementById("review-note")?.focus();
          break;
        default:
          break;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [alreadyRejected, alreadyVerified, onApprove, onNext, onPrev, onReject, reviewNote]);

  return (
    <Stack>
      <Textarea
        id="review-note"
        label="Review note (optional)"
        placeholder="e.g. top component placement off by ~10 units"
        value={reviewNote}
        onChange={(e) => onNoteChange(e.currentTarget.value)}
        autosize
        minRows={2}
      />
      <Group>
        <Button color="green" onClick={() => onApprove()} disabled={alreadyVerified}>
          {alreadyVerified ? "Already verified" : "Approve (Y)"}
        </Button>
        <Button
          color="red"
          variant="outline"
          onClick={() => onReject(reviewNote)}
          disabled={alreadyRejected}
        >
          {alreadyRejected ? "Already rejected" : "Reject (N)"}
        </Button>
        <Button variant="subtle" onClick={onPrev}>
          Prev (K)
        </Button>
        <Button variant="subtle" onClick={onNext}>
          Next (J)
        </Button>
      </Group>
      <Text size="xs" c="dimmed">
        Shortcuts: Y approve · N reject · J next · K prev · R focus note · Esc back
      </Text>
    </Stack>
  );
}
