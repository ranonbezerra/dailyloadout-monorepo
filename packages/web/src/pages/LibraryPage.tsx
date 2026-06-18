import {
	Badge,
	Button,
	Group,
	Select,
	Skeleton,
	Stack,
	Text,
	Textarea,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { DataTable } from "mantine-datatable";
import { useState } from "react";
import { QuickAddMenu } from "../components/QuickAddMenu";
import { useDeleteEntry, useLibrary, useUpdateEntry } from "../hooks/useLibrary";
import type { LibraryEntry, LibraryStatus } from "../types/library";
import { CapturePhotoModal } from "./CapturePhotoModal";
import { CaptureReviewModal } from "./CaptureReviewModal";
import { CaptureTextModal } from "./CaptureTextModal";
import { CaptureVoiceModal } from "./CaptureVoiceModal";

const STATUS_TABS: { value: string; label: string }[] = [
	{ value: "all", label: "All" },
	{ value: "backlog", label: "Backlog" },
	{ value: "playing", label: "Playing" },
	{ value: "paused", label: "Paused" },
	{ value: "completed", label: "Completed" },
	{ value: "dropped", label: "Dropped" },
];

const STATUS_COLORS: Record<string, string> = {
	backlog: "gray",
	playing: "blue",
	paused: "yellow",
	completed: "green",
	dropped: "red",
};

const STATUS_OPTIONS: { value: LibraryStatus; label: string }[] = [
	{ value: "backlog", label: "Backlog" },
	{ value: "playing", label: "Playing" },
	{ value: "paused", label: "Paused" },
	{ value: "completed", label: "Completed" },
	{ value: "dropped", label: "Dropped" },
];

const PAGE_SIZE = 50;

export function LibraryPage() {
	const [statusFilter, setStatusFilter] = useState("all");
	const [expandedIds, setExpandedIds] = useState<string[]>([]);
	const [textModalOpened, setTextModalOpened] = useState(false);
	const [voiceModalOpened, setVoiceModalOpened] = useState(false);
	const [photoModalOpened, setPhotoModalOpened] = useState(false);
	const [reviewCaptureId, setReviewCaptureId] = useState<string | null>(null);

	const queryParams = {
		status: statusFilter === "all" ? undefined : statusFilter,
		limit: PAGE_SIZE,
		offset: 0,
	};

	const { data, isLoading } = useLibrary(queryParams);
	const updateMutation = useUpdateEntry();
	const deleteMutation = useDeleteEntry();

	const entries = data?.items ?? [];

	if (isLoading) {
		return (
			<Stack p="md">
				<Group justify="space-between">
					<Skeleton height={36} width={200} />
					<Skeleton height={36} width={120} />
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
				<Title order={2}>Library</Title>
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

			{entries.length === 0 ? (
				<Text c="dimmed" ta="center" py="xl">
					Your library is empty. Use Quick Add to add your first game!
				</Text>
			) : (
				<DataTable
					withTableBorder
					borderRadius="sm"
					striped
					highlightOnHover
					noRecordsText="No games match this filter"
					records={entries}
					idAccessor="publicId"
					columns={[
						{
							accessor: "game.title",
							title: "Game",
							render: (entry: LibraryEntry) => (
								<Text size="sm" fw={500}>
									{entry.game.title}
								</Text>
							),
						},
						{
							accessor: "platform.label",
							title: "Platform",
							render: (entry: LibraryEntry) => <Text size="sm">{entry.platform.label}</Text>,
						},
						{
							accessor: "status",
							title: "Status",
							render: (entry: LibraryEntry) => (
								<Badge color={STATUS_COLORS[entry.status] ?? "gray"} variant="light">
									{entry.status}
								</Badge>
							),
						},
						{
							accessor: "notes",
							title: "Notes",
							render: (entry: LibraryEntry) => (
								<Text size="xs" c="dimmed" lineClamp={1}>
									{entry.notes ?? "--"}
								</Text>
							),
						},
						{
							accessor: "createdAt",
							title: "Added",
							render: (entry: LibraryEntry) => (
								<Text size="xs">{dayjs(entry.createdAt).format("MMM D, YYYY")}</Text>
							),
						},
					]}
					rowExpansion={{
						allowMultiple: false,
						expanded: {
							recordIds: expandedIds,
							onRecordIdsChange: setExpandedIds,
						},
						content: ({ record }) => (
							<ExpandedRow
								entry={record}
								onUpdate={async (entryData) => {
									try {
										await updateMutation.mutateAsync({
											publicId: record.publicId,
											data: entryData,
										});
										notifications.show({
											title: "Entry updated",
											message: `"${record.game.title}" has been updated.`,
											color: "green",
										});
										setExpandedIds([]);
									} catch (err) {
										notifications.show({
											title: "Update failed",
											message: err instanceof Error ? err.message : "An unexpected error occurred",
											color: "red",
										});
									}
								}}
								onDelete={async () => {
									try {
										await deleteMutation.mutateAsync(record.publicId);
										notifications.show({
											title: "Entry deleted",
											message: `"${record.game.title}" has been removed.`,
											color: "green",
										});
									} catch (err) {
										notifications.show({
											title: "Delete failed",
											message: err instanceof Error ? err.message : "An unexpected error occurred",
											color: "red",
										});
									}
								}}
								isPending={updateMutation.isPending || deleteMutation.isPending}
							/>
						),
					}}
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

// ---------------------------------------------------------------------------
// Expanded row editor
// ---------------------------------------------------------------------------

interface ExpandedRowProps {
	entry: LibraryEntry;
	onUpdate: (data: { status?: LibraryStatus; notes?: string }) => Promise<void>;
	onDelete: () => Promise<void>;
	isPending: boolean;
}

function ExpandedRow({ entry, onUpdate, onDelete, isPending }: ExpandedRowProps) {
	const [editStatus, setEditStatus] = useState<string | null>(entry.status);
	const [editNotes, setEditNotes] = useState(entry.notes ?? "");

	return (
		<Stack p="md" gap="sm">
			<Group>
				<Select
					label="Status"
					data={STATUS_OPTIONS}
					value={editStatus}
					onChange={setEditStatus}
					w={200}
				/>
			</Group>
			<Textarea
				label="Notes"
				value={editNotes}
				onChange={(e) => setEditNotes(e.currentTarget.value)}
				autosize
				minRows={2}
				maxRows={4}
			/>
			<Group>
				<Button
					size="xs"
					loading={isPending}
					onClick={() =>
						onUpdate({
							status: (editStatus as LibraryStatus) ?? undefined,
							notes: editNotes.trim() || undefined,
						})
					}
				>
					Save
				</Button>
				<Button size="xs" color="red" variant="light" loading={isPending} onClick={onDelete}>
					Delete
				</Button>
			</Group>
		</Stack>
	);
}
