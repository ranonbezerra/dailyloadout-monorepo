import {
	Badge,
	Button,
	Card,
	Group,
	Image,
	Loader,
	Modal,
	Select,
	Stack,
	Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useCapture, useConfirmCandidate, useRejectCandidate } from "../hooks/useCapture";
import { usePlatforms } from "../hooks/useLibrary";
import { safeImageUrl } from "../lib/safe-image";
import type { CaptureCandidate } from "../types/capture";
import type { LibraryStatus } from "../types/library";

interface CaptureReviewModalProps {
	captureId: string | null;
	onClose: () => void;
}

const STATUS_OPTIONS: { value: LibraryStatus; label: string }[] = [
	{ value: "backlog", label: "Backlog" },
	{ value: "playing", label: "Playing" },
	{ value: "paused", label: "Paused" },
	{ value: "completed", label: "Completed" },
	{ value: "dropped", label: "Dropped" },
];

const CANDIDATE_STATUS_COLORS: Record<string, string> = {
	pending: "yellow",
	confirmed: "green",
	rejected: "red",
};

const CONFIDENCE_COLORS: Record<string, string> = {
	high: "green",
	medium: "yellow",
	low: "red",
};

function getConfidenceLabel(confidence: number | null): {
	label: string;
	color: string;
} {
	if (confidence === null) return { label: "Unknown", color: "gray" };
	if (confidence >= 0.8) return { label: "High", color: CONFIDENCE_COLORS.high };
	if (confidence >= 0.5) return { label: "Medium", color: CONFIDENCE_COLORS.medium };
	return { label: "Low", color: CONFIDENCE_COLORS.low };
}

export function CaptureReviewModal({ captureId, onClose }: CaptureReviewModalProps) {
	const { data: capture, isLoading } = useCapture(captureId ?? "");
	const { data: platforms = [] } = usePlatforms();
	const confirmMutation = useConfirmCandidate();
	const rejectMutation = useRejectCandidate();

	const platformOptions = platforms.map((p) => ({
		value: String(p.id),
		label: p.label,
	}));

	const pendingCount = capture?.candidates.filter((c) => c.status === "pending").length ?? 0;

	if (!captureId) return null;

	return (
		<Modal opened={!!captureId} onClose={onClose} title="Review Candidates" size="lg">
			{isLoading ? (
				<Stack align="center" py="xl">
					<Loader />
					<Text size="sm" c="dimmed">
						Loading capture...
					</Text>
				</Stack>
			) : !capture ? (
				<Text c="dimmed" ta="center" py="xl">
					Capture not found.
				</Text>
			) : (
				<Stack>
					{capture.rawText && (
						<Text size="sm" c="dimmed" lineClamp={3}>
							Original text: {capture.rawText}
						</Text>
					)}

					{capture.candidates.length === 0 ? (
						<Text c="dimmed" ta="center" py="xl">
							No candidates were extracted from this capture.
						</Text>
					) : (
						capture.candidates.map((candidate) => (
							<CandidateCard
								key={candidate.publicId}
								candidate={candidate}
								platformOptions={platformOptions}
								onConfirm={async (platformId, status) => {
									try {
										await confirmMutation.mutateAsync({
											captureId,
											candidateId: candidate.publicId,
											platformId,
											status,
										});
										notifications.show({
											title: "Candidate confirmed",
											message: `"${candidate.igdbTitle ?? candidate.title}" added to library.`,
											color: "green",
										});
										if (pendingCount <= 1) onClose();
									} catch (err) {
										notifications.show({
											title: "Confirm failed",
											message: err instanceof Error ? err.message : "An unexpected error occurred",
											color: "red",
										});
									}
								}}
								onReject={async () => {
									try {
										await rejectMutation.mutateAsync({
											captureId,
											candidateId: candidate.publicId,
										});
										notifications.show({
											title: "Candidate rejected",
											message: `"${candidate.igdbTitle ?? candidate.title}" has been rejected.`,
											color: "gray",
										});
										if (pendingCount <= 1) onClose();
									} catch (err) {
										notifications.show({
											title: "Reject failed",
											message: err instanceof Error ? err.message : "An unexpected error occurred",
											color: "red",
										});
									}
								}}
								isPending={confirmMutation.isPending || rejectMutation.isPending}
							/>
						))
					)}
				</Stack>
			)}
		</Modal>
	);
}

// ---------------------------------------------------------------------------
// Candidate card
// ---------------------------------------------------------------------------

interface CandidateCardProps {
	candidate: CaptureCandidate;
	platformOptions: { value: string; label: string }[];
	onConfirm: (platformId: number, status: LibraryStatus) => Promise<void>;
	onReject: () => Promise<void>;
	isPending: boolean;
}

function CandidateCard({
	candidate,
	platformOptions,
	onConfirm,
	onReject,
	isPending,
}: CandidateCardProps) {
	const [platformId, setPlatformId] = useState<string | null>(null);
	const [status, setStatus] = useState<string | null>("backlog");
	const isResolved = candidate.status !== "pending";
	const confidence = getConfidenceLabel(candidate.confidence);

	return (
		<Card withBorder radius="sm" p="md" opacity={isResolved ? 0.6 : 1}>
			<Group align="flex-start" wrap="nowrap" gap="md">
				{safeImageUrl(candidate.igdbCoverUrl) && (
					<Image
						src={safeImageUrl(candidate.igdbCoverUrl)}
						alt={candidate.igdbTitle ?? candidate.title}
						w={80}
						h={110}
						radius="sm"
						fit="cover"
					/>
				)}

				<Stack gap="xs" style={{ flex: 1 }}>
					<Group justify="space-between" align="flex-start">
						<div>
							<Text fw={600} size="sm">
								{candidate.igdbTitle ?? candidate.title}
							</Text>
							{candidate.igdbTitle && candidate.igdbTitle !== candidate.title && (
								<Text size="xs" c="dimmed">
									Extracted as: {candidate.title}
								</Text>
							)}
						</div>
						<Group gap="xs">
							<Badge color={confidence.color} variant="light" size="sm">
								{confidence.label}
							</Badge>
							<Badge
								color={CANDIDATE_STATUS_COLORS[candidate.status] ?? "gray"}
								variant="light"
								size="sm"
							>
								{candidate.status}
							</Badge>
						</Group>
					</Group>

					{candidate.platformHint && (
						<Text size="xs" c="dimmed">
							Platform hint: {candidate.platformHint}
						</Text>
					)}

					{candidate.igdbSummary && (
						<Text size="xs" c="dimmed" lineClamp={2}>
							{candidate.igdbSummary}
						</Text>
					)}

					{candidate.igdbGenres && candidate.igdbGenres.length > 0 && (
						<Group gap={4}>
							{candidate.igdbGenres.map((genre) => (
								<Badge key={genre} size="xs" variant="outline">
									{genre}
								</Badge>
							))}
						</Group>
					)}

					{!isResolved && (
						<>
							<Group gap="sm">
								<Select
									placeholder="Platform"
									data={platformOptions}
									value={platformId}
									onChange={setPlatformId}
									searchable
									size="xs"
									w={180}
								/>
								<Select
									placeholder="Status"
									data={STATUS_OPTIONS}
									value={status}
									onChange={setStatus}
									size="xs"
									w={140}
								/>
							</Group>

							<Group gap="xs">
								<Button
									size="xs"
									color="green"
									leftSection={<IconCheck size={14} />}
									loading={isPending}
									disabled={!platformId}
									onClick={() =>
										onConfirm(Number(platformId), (status as LibraryStatus) ?? "backlog")
									}
								>
									Confirm
								</Button>
								<Button
									size="xs"
									color="red"
									variant="light"
									leftSection={<IconX size={14} />}
									loading={isPending}
									onClick={onReject}
								>
									Reject
								</Button>
							</Group>
						</>
					)}
				</Stack>
			</Group>
		</Card>
	);
}
