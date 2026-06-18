import { Badge, Button, Group, Skeleton, Stack, Text, Title } from "@mantine/core";
import dayjs from "dayjs";
import { DataTable } from "mantine-datatable";
import { useState } from "react";
import { QuickAddMenu } from "../components/QuickAddMenu";
import { useCaptures } from "../hooks/useCapture";
import type { CaptureListItem } from "../types/capture";
import { CapturePhotoModal } from "./CapturePhotoModal";
import { CaptureReviewModal } from "./CaptureReviewModal";
import { CaptureTextModal } from "./CaptureTextModal";
import { CaptureVoiceModal } from "./CaptureVoiceModal";

const STATUS_TABS: { value: string; label: string }[] = [
	{ value: "all", label: "All" },
	{ value: "review", label: "Review" },
	{ value: "committed", label: "Committed" },
	{ value: "failed", label: "Failed" },
	{ value: "cancelled", label: "Cancelled" },
];

const STATUS_COLORS: Record<string, string> = {
	queued: "gray",
	processing: "orange",
	review: "blue",
	committed: "green",
	partially_committed: "yellow",
	failed: "red",
	cancelled: "gray",
};

export function CapturesPage() {
	const [statusFilter, setStatusFilter] = useState("all");
	const [textModalOpened, setTextModalOpened] = useState(false);
	const [voiceModalOpened, setVoiceModalOpened] = useState(false);
	const [photoModalOpened, setPhotoModalOpened] = useState(false);
	const [reviewCaptureId, setReviewCaptureId] = useState<string | null>(null);

	const activeStatus = statusFilter === "all" ? undefined : statusFilter;
	const { data, isLoading } = useCaptures(activeStatus);
	const captures = data?.items ?? [];

	if (isLoading) {
		return (
			<Stack p="md">
				<Group justify="space-between">
					<Skeleton height={36} width={200} />
					<Skeleton height={36} width={150} />
				</Group>
				<Skeleton height={40} />
				{Array.from({ length: 5 }).map((_, i) => (
					// biome-ignore lint/suspicious/noArrayIndexKey: skeleton placeholders have no stable key
					<Skeleton key={i} height={48} />
				))}
			</Stack>
		);
	}

	return (
		<Stack>
			<Group justify="space-between">
				<Title order={2}>Capture History</Title>
				<QuickAddMenu
					onText={() => setTextModalOpened(true)}
					onVoice={() => setVoiceModalOpened(true)}
					onPhoto={() => setPhotoModalOpened(true)}
				/>
			</Group>

			<Group gap="xs">
				{STATUS_TABS.map((tab) => (
					<Button
						key={tab.value}
						variant={statusFilter === tab.value ? "filled" : "default"}
						size="xs"
						onClick={() => setStatusFilter(tab.value)}
					>
						{tab.label}
					</Button>
				))}
			</Group>

			{captures.length === 0 ? (
				<Text c="dimmed" ta="center" py="xl">
					No captures yet. Use the New button above to get started.
				</Text>
			) : (
				<DataTable
					withTableBorder
					borderRadius="sm"
					striped
					highlightOnHover
					noRecordsText="No captures match this filter"
					records={captures}
					idAccessor="publicId"
					onRowClick={({ record }) => setReviewCaptureId(record.publicId)}
					columns={[
						{
							accessor: "rawText",
							title: "Text",
							render: (capture: CaptureListItem) => (
								<Text size="sm" lineClamp={1} maw={400}>
									{capture.rawText ?? "--"}
								</Text>
							),
						},
						{
							accessor: "inputType",
							title: "Type",
							width: 80,
							render: (capture: CaptureListItem) => <Text size="sm">{capture.inputType}</Text>,
						},
						{
							accessor: "status",
							title: "Status",
							width: 140,
							render: (capture: CaptureListItem) => (
								<Badge color={STATUS_COLORS[capture.status] ?? "gray"} variant="light">
									{capture.status.replace("_", " ")}
								</Badge>
							),
						},
						{
							accessor: "createdAt",
							title: "Created",
							width: 140,
							render: (capture: CaptureListItem) => (
								<Text size="xs">{dayjs(capture.createdAt).format("MMM D, YYYY")}</Text>
							),
						},
					]}
				/>
			)}

			<CaptureTextModal
				opened={textModalOpened}
				onClose={() => setTextModalOpened(false)}
				onSuccess={(captureId) => {
					setTextModalOpened(false);
					setReviewCaptureId(captureId);
				}}
			/>

			<CaptureVoiceModal
				opened={voiceModalOpened}
				onClose={() => setVoiceModalOpened(false)}
				onSuccess={(captureId) => {
					setVoiceModalOpened(false);
					setReviewCaptureId(captureId);
				}}
			/>

			<CapturePhotoModal
				opened={photoModalOpened}
				onClose={() => setPhotoModalOpened(false)}
				onSuccess={(captureId) => {
					setPhotoModalOpened(false);
					setReviewCaptureId(captureId);
				}}
			/>

			<CaptureReviewModal captureId={reviewCaptureId} onClose={() => setReviewCaptureId(null)} />
		</Stack>
	);
}
