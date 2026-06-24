import {
	Anchor,
	Badge,
	Button,
	Card,
	Group,
	Select,
	Skeleton,
	Stack,
	TagsInput,
	Text,
	Textarea,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconHistory } from "@tabler/icons-react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { DataTable } from "mantine-datatable";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { QuickAddMenu } from "../components/QuickAddMenu";
import {
	useDeleteEntry,
	useGameGenres,
	useLibrary,
	useUpdateEntry,
	useUpdateGame,
} from "../hooks/useLibrary";
import { useActiveMission } from "../hooks/useMission";
import type { LibraryEntry, LibraryStatus } from "../types/library";
import type { Mission } from "../types/mission";
import { CapturePhotoModal } from "./CapturePhotoModal";
import { CaptureReviewModal } from "./CaptureReviewModal";
import { CaptureTextModal } from "./CaptureTextModal";
import { CaptureVoiceModal } from "./CaptureVoiceModal";
import { MissionBriefingModal } from "./MissionBriefingModal";
import { MissionDebriefModal } from "./MissionDebriefModal";

dayjs.extend(relativeTime);

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
	const navigate = useNavigate();
	const [statusFilter, setStatusFilter] = useState("all");
	const [expandedIds, setExpandedIds] = useState<string[]>([]);
	const [textModalOpened, setTextModalOpened] = useState(false);
	const [voiceModalOpened, setVoiceModalOpened] = useState(false);
	const [photoModalOpened, setPhotoModalOpened] = useState(false);
	const [reviewCaptureId, setReviewCaptureId] = useState<string | null>(null);

	// View mode: viewing an existing mission's briefing
	const [briefingMission, setBriefingMission] = useState<Mission | null>(null);
	// Preview mode: starting a mission (briefing is fetched inside the modal,
	// after the user picks quick vs deep — no pre-fetch here).
	const [previewEntry, setPreviewEntry] = useState<LibraryEntry | null>(null);

	const [debriefMission, setDebriefMission] = useState<Mission | null>(null);

	const queryParams = {
		status: statusFilter === "all" ? undefined : statusFilter,
		limit: PAGE_SIZE,
		offset: 0,
	};

	const { data, isLoading } = useLibrary(queryParams);
	const { data: activeMission } = useActiveMission();
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
				<Group gap="md" align="baseline">
					<Title order={2}>Library</Title>
					<Anchor
						size="sm"
						c="dimmed"
						onClick={() => navigate("/captures")}
						style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
					>
						<IconHistory size={14} />
						Capture History
					</Anchor>
				</Group>
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

			{activeMission && (
				<Card withBorder p="sm" radius="md">
					<Group justify="space-between">
						<Group gap="sm">
							<Badge color="teal" variant="dot" size="lg">
								Mission active
							</Badge>
							<Text fw={500}>{activeMission.libraryEntry.game.title}</Text>
							<Text size="sm" c="dimmed">
								{activeMission.libraryEntry.platform.label}
							</Text>
							<Text size="sm" c="dimmed">
								started {dayjs(activeMission.startedAt).fromNow()}
							</Text>
						</Group>
						<Group gap="xs">
							{activeMission.briefingText && (
								<Button
									size="xs"
									variant="light"
									onClick={() => setBriefingMission(activeMission)}
								>
									View briefing
								</Button>
							)}
							<Button size="xs" color="teal" onClick={() => setDebriefMission(activeMission)}>
								End mission
							</Button>
						</Group>
					</Group>
				</Card>
			)}

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
								onStartMission={() => setPreviewEntry(record)}
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

			{/* Preview mode: choosing briefing mode, then reviewing before starting */}
			{previewEntry && (
				<MissionBriefingModal
					mode="preview"
					libraryEntry={previewEntry}
					libraryEntryPublicId={previewEntry.publicId}
					onConfirm={() => setPreviewEntry(null)}
					onClose={() => setPreviewEntry(null)}
				/>
			)}

			{/* View mode: viewing an existing mission's briefing */}
			{briefingMission && (
				<MissionBriefingModal
					mode="view"
					mission={briefingMission}
					onClose={() => setBriefingMission(null)}
					onMissionUpdated={(updated) => setBriefingMission(updated)}
				/>
			)}

			<MissionDebriefModal mission={debriefMission} onClose={() => setDebriefMission(null)} />
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
	onStartMission: () => void;
	isPending: boolean;
}

function ExpandedRow({ entry, onUpdate, onDelete, onStartMission, isPending }: ExpandedRowProps) {
	const [editStatus, setEditStatus] = useState<string | null>(entry.status);
	const [editNotes, setEditNotes] = useState(entry.notes ?? "");
	const [editGenres, setEditGenres] = useState<string[]>(entry.game.genres ?? []);
	const { data: activeMission } = useActiveMission();
	const updateGameMutation = useUpdateGame();
	const { data: genreOptions = [] } = useGameGenres();

	const hasActiveMission = activeMission != null;
	const isThisEntryActive = activeMission?.libraryEntry.publicId === entry.publicId;

	const handleSave = async () => {
		// Update game genres if changed
		const prev = [...(entry.game.genres ?? [])].sort();
		const next = [...editGenres].sort();
		if (JSON.stringify(prev) !== JSON.stringify(next)) {
			await updateGameMutation.mutateAsync({
				publicId: entry.game.publicId,
				data: { genres: editGenres },
			});
		}
		// Update library entry fields
		await onUpdate({
			status: (editStatus as LibraryStatus) ?? undefined,
			notes: editNotes.trim() || undefined,
		});
	};

	return (
		<Stack p="md" gap="sm">
			{entry.missionNextAction && (
				<Text size="sm" c="dimmed">
					Next objective: {entry.missionNextAction}
				</Text>
			)}
			<Group>
				<Select
					label="Status"
					data={STATUS_OPTIONS}
					value={editStatus}
					onChange={setEditStatus}
					w={200}
				/>
			</Group>
			<TagsInput
				label="Genres"
				placeholder="Type a genre and press Enter"
				data={genreOptions}
				value={editGenres}
				onChange={setEditGenres}
			/>
			<Textarea
				label="Notes"
				value={editNotes}
				onChange={(e) => setEditNotes(e.currentTarget.value)}
				autosize
				minRows={2}
				maxRows={4}
			/>
			<Group>
				<Button size="xs" loading={isPending || updateGameMutation.isPending} onClick={handleSave}>
					Save
				</Button>
				<Button size="xs" color="teal" disabled={hasActiveMission} onClick={onStartMission}>
					{isThisEntryActive ? "Mission active" : "Start Mission"}
				</Button>
				<Button size="xs" color="red" variant="light" loading={isPending} onClick={onDelete}>
					Delete
				</Button>
			</Group>
		</Stack>
	);
}
