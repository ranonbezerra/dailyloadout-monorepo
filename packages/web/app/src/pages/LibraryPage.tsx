import {
	Anchor,
	Badge,
	Button,
	Card,
	Divider,
	Group,
	MultiSelect,
	Select,
	Skeleton,
	Stack,
	Text,
	Textarea,
	Title,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { IconHistory, IconPlus } from "@tabler/icons-react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { DataTable } from "mantine-datatable";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorState } from "../components/ErrorState";
import { QuickAddMenu } from "../components/QuickAddMenu";
import {
	useAddToLibrary,
	useDeleteEntry,
	useLibrary,
	usePlatforms,
	useUpdateEntry,
} from "../hooks/useLibrary";
import { useActiveMission } from "../hooks/useMission";
import type {
	Game,
	LibraryEntry,
	LibraryGameGroup,
	LibraryPlatformState,
	LibraryStatus,
} from "../types/library";
import type { Mission } from "../types/mission";
import { AddGameModal } from "./AddGameModal";
import { CapturePhotoModal } from "./CapturePhotoModal";
import { CaptureReviewModal } from "./CaptureReviewModal";
import { CaptureTextModal } from "./CaptureTextModal";
import { CaptureVoiceModal } from "./CaptureVoiceModal";
import { ImageSourceModal } from "./ImageSourceModal";
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

/**
 * Build a flat LibraryEntry (the shape the rest of the app — missions,
 * briefings — speaks) from a grouped game plus one of its platform states.
 * This is a per-platform projection, NOT aggregation: each entry maps 1:1 to a
 * library row the backend already gave us.
 */
function toEntry(game: Game, state: LibraryPlatformState): LibraryEntry {
	return {
		publicId: state.publicId,
		game,
		platform: state.platform,
		status: state.status,
		acquiredAt: state.acquiredAt,
		lastPlayedAt: state.lastPlayedAt,
		missionNextAction: state.missionNextAction,
		notes: state.notes,
		createdAt: state.createdAt,
		updatedAt: state.updatedAt,
	};
}

export function LibraryPage() {
	const navigate = useNavigate();
	const [statusFilter, setStatusFilter] = useState("all");
	// How many pages (of PAGE_SIZE) to request; bumped by "Load more".
	const [pageCount, setPageCount] = useState(1);
	const [expandedIds, setExpandedIds] = useState<string[]>([]);
	const [manualModalOpened, setManualModalOpened] = useState(false);
	const [textModalOpened, setTextModalOpened] = useState(false);
	const [voiceModalOpened, setVoiceModalOpened] = useState(false);
	const [photoModalOpened, setPhotoModalOpened] = useState(false);
	const [imageChooserOpened, setImageChooserOpened] = useState(false);
	const [reviewCaptureId, setReviewCaptureId] = useState<string | null>(null);

	// View mode: viewing an existing mission's briefing
	const [briefingMission, setBriefingMission] = useState<Mission | null>(null);
	// Preview mode: starting a mission for a specific platform entry. The
	// briefing is fetched inside the modal after the user picks quick vs deep.
	const [previewEntry, setPreviewEntry] = useState<LibraryEntry | null>(null);

	const [debriefMission, setDebriefMission] = useState<Mission | null>(null);

	const queryParams = {
		status: statusFilter === "all" ? undefined : statusFilter,
		limit: PAGE_SIZE * pageCount,
		offset: 0,
	};

	const { data, isLoading, isError, error, refetch } = useLibrary(queryParams);
	const { data: activeMission } = useActiveMission();
	const updateMutation = useUpdateEntry();
	const deleteMutation = useDeleteEntry();

	const groups = data?.items ?? [];
	const total = data?.total ?? 0;
	const hasMore = groups.length < total;

	const selectStatus = (value: string) => {
		setStatusFilter(value);
		setPageCount(1);
	};

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
					onManual={() => setManualModalOpened(true)}
					onText={() => setTextModalOpened(true)}
					onVoice={() => setVoiceModalOpened(true)}
					onImage={() => setImageChooserOpened(true)}
				/>
			</Group>

			<Group gap="xs">
				{STATUS_TABS.map((tab) => (
					<Button
						key={tab.value}
						variant={statusFilter === tab.value ? "filled" : "default"}
						size="xs"
						onClick={() => selectStatus(tab.value)}
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

			{isError ? (
				<ErrorState title="Couldn't load your library" error={error} onRetry={() => refetch()} />
			) : groups.length === 0 ? (
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
					records={groups}
					idAccessor="game.publicId"
					columns={[
						{
							accessor: "game.title",
							title: "Game",
							render: (group: LibraryGameGroup) => (
								<Text size="sm" fw={500}>
									{group.game.title}
								</Text>
							),
						},
						{
							accessor: "platforms",
							title: "Platforms",
							render: (group: LibraryGameGroup) => (
								<Group gap={4}>
									{group.platforms.map((state) => (
										<Badge
											key={state.publicId}
											color={STATUS_COLORS[state.status] ?? "gray"}
											variant="light"
											size="sm"
										>
											{state.platform.label}: {state.status}
										</Badge>
									))}
								</Group>
							),
						},
						{
							accessor: "game.createdAt",
							title: "Added",
							render: (group: LibraryGameGroup) => (
								<Text size="xs">{dayjs(group.game.createdAt).format("MMM D, YYYY")}</Text>
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
							<ExpandedGameRow
								group={record}
								onUpdate={async (entryPublicId, entryData) => {
									try {
										await updateMutation.mutateAsync({
											publicId: entryPublicId,
											data: entryData,
										});
										notifications.show({
											title: "Entry updated",
											message: `"${record.game.title}" has been updated.`,
											color: "green",
										});
									} catch (err) {
										notifications.show({
											title: "Update failed",
											message: err instanceof Error ? err.message : "An unexpected error occurred",
											color: "red",
										});
									}
								}}
								onDelete={async (entryPublicId) => {
									try {
										await deleteMutation.mutateAsync(entryPublicId);
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
								onStartMission={(state) => setPreviewEntry(toEntry(record.game, state))}
								isPending={updateMutation.isPending || deleteMutation.isPending}
							/>
						),
					}}
				/>
			)}

			{!isError && hasMore && (
				<Group justify="center">
					<Button variant="default" loading={isLoading} onClick={() => setPageCount((c) => c + 1)}>
						Load more ({groups.length} of {total})
					</Button>
				</Group>
			)}

			<AddGameModal opened={manualModalOpened} onClose={() => setManualModalOpened(false)} />

			<ImageSourceModal
				opened={imageChooserOpened}
				onClose={() => setImageChooserOpened(false)}
				onPhoto={() => setPhotoModalOpened(true)}
				onScreenshots={() => navigate("/library/import")}
			/>

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
// Expanded game row: one block per owned platform + an "add platform" form
// ---------------------------------------------------------------------------

interface ExpandedGameRowProps {
	group: LibraryGameGroup;
	onUpdate: (
		entryPublicId: string,
		data: { status?: LibraryStatus; notes?: string },
	) => Promise<void>;
	onDelete: (entryPublicId: string) => Promise<void>;
	onStartMission: (state: LibraryPlatformState) => void;
	isPending: boolean;
}

function ExpandedGameRow({
	group,
	onUpdate,
	onDelete,
	onStartMission,
	isPending,
}: ExpandedGameRowProps) {
	return (
		<Stack p="md" gap="md">
			{group.game.genres && group.game.genres.length > 0 && (
				<div>
					<Text size="sm" fw={500} mb={4}>
						Genres
					</Text>
					<Group gap="xs">
						{group.game.genres.map((g) => (
							<Badge key={g} variant="light" size="sm">
								{g}
							</Badge>
						))}
					</Group>
				</div>
			)}

			{group.platforms.map((state) => (
				<PlatformRow
					key={state.publicId}
					game={group.game}
					state={state}
					onUpdate={onUpdate}
					onDelete={onDelete}
					onStartMission={onStartMission}
					isPending={isPending}
				/>
			))}

			<Divider />

			<AddPlatformRow group={group} />
		</Stack>
	);
}

// ---------------------------------------------------------------------------
// Per-platform editor (status, notes, start mission, remove)
// ---------------------------------------------------------------------------

interface PlatformRowProps {
	game: Game;
	state: LibraryPlatformState;
	onUpdate: (
		entryPublicId: string,
		data: { status?: LibraryStatus; notes?: string },
	) => Promise<void>;
	onDelete: (entryPublicId: string) => Promise<void>;
	onStartMission: (state: LibraryPlatformState) => void;
	isPending: boolean;
}

function PlatformRow({
	game,
	state,
	onUpdate,
	onDelete,
	onStartMission,
	isPending,
}: PlatformRowProps) {
	const [editStatus, setEditStatus] = useState<string | null>(state.status);
	const [editNotes, setEditNotes] = useState(state.notes ?? "");
	const { data: activeMission } = useActiveMission();

	const hasActiveMission = activeMission != null;
	const isThisEntryActive = activeMission?.libraryEntry.publicId === state.publicId;

	const handleSave = async () => {
		// Game metadata (title/genres) is immutable — it's a cache of IGDB.
		// Only this platform entry's own fields are editable here.
		await onUpdate(state.publicId, {
			status: (editStatus as LibraryStatus) ?? undefined,
			notes: editNotes.trim() || undefined,
		});
	};

	const confirmDelete = () => {
		modals.openConfirmModal({
			title: "Delete library entry",
			centered: true,
			children: (
				<Text size="sm">
					Permanently remove "{game.title}" on {state.platform.label} from your library? This can't
					be undone.
				</Text>
			),
			labels: { confirm: "Delete entry", cancel: "Cancel" },
			confirmProps: { color: "red" },
			onConfirm: () => {
				void onDelete(state.publicId);
			},
		});
	};

	return (
		<Card withBorder p="sm" radius="sm">
			<Stack gap="sm">
				<Group gap="xs">
					<Badge variant="filled">{state.platform.label}</Badge>
					{state.missionNextAction && (
						<Text size="sm" c="dimmed">
							Next objective: {state.missionNextAction}
						</Text>
					)}
				</Group>
				<Group align="flex-start">
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
					<Button size="xs" loading={isPending} onClick={handleSave}>
						Save
					</Button>
					<Button
						size="xs"
						color="teal"
						disabled={hasActiveMission}
						onClick={() => onStartMission(state)}
					>
						{isThisEntryActive ? "Mission active" : "Start Mission"}
					</Button>
					<Button
						size="xs"
						color="red"
						variant="light"
						loading={isPending}
						onClick={confirmDelete}
					>
						Remove
					</Button>
				</Group>
			</Stack>
		</Card>
	);
}

// ---------------------------------------------------------------------------
// Add-platform affordance: own this game on an additional platform
// ---------------------------------------------------------------------------

function AddPlatformRow({ group }: { group: LibraryGameGroup }) {
	const { data: platforms = [] } = usePlatforms();
	const addMutation = useAddToLibrary();
	const [selectedIds, setSelectedIds] = useState<string[]>([]);

	const ownedIds = useMemo(
		() => new Set(group.platforms.map((p) => p.platform.id)),
		[group.platforms],
	);

	const options = useMemo(
		() =>
			platforms
				.filter((p) => !ownedIds.has(p.id))
				.map((p) => ({ value: String(p.id), label: p.label })),
		[platforms, ownedIds],
	);

	if (options.length === 0) {
		return (
			<Text size="xs" c="dimmed">
				Owned on every available platform.
			</Text>
		);
	}

	const handleAdd = async () => {
		if (selectedIds.length === 0) {
			notifications.show({
				title: "No platform selected",
				message: "Pick at least one platform to add.",
				color: "red",
			});
			return;
		}
		try {
			await addMutation.mutateAsync({
				gamePublicId: group.game.publicId,
				platformIds: selectedIds.map(Number),
			});
			notifications.show({
				title: "Platform added",
				message: `"${group.game.title}" is now in your library on more platforms.`,
				color: "green",
			});
			setSelectedIds([]);
		} catch (err) {
			notifications.show({
				title: "Failed to add platform",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Group align="flex-end" gap="sm">
			<MultiSelect
				label="Add platform"
				placeholder="Pick platforms you also own"
				data={options}
				value={selectedIds}
				onChange={setSelectedIds}
				searchable
				w={280}
			/>
			<Button
				size="xs"
				variant="light"
				leftSection={<IconPlus size={14} />}
				loading={addMutation.isPending}
				onClick={handleAdd}
			>
				Add
			</Button>
		</Group>
	);
}
