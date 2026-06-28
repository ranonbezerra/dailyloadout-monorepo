import {
	Badge,
	Button,
	Divider,
	Group,
	Loader,
	Modal,
	MultiSelect,
	Select,
	Stack,
	Switch,
	TagsInput,
	Text,
	Textarea,
	TextInput,
	UnstyledButton,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import {
	useAddToLibrary,
	useCreateGame,
	useGameGenres,
	usePlatforms,
	useSearchGames,
} from "../hooks/useLibrary";
import type { Game, LibraryStatus } from "../types/library";

interface AddGameModalProps {
	opened: boolean;
	onClose: () => void;
}

const STATUS_OPTIONS: { value: LibraryStatus; label: string }[] = [
	{ value: "backlog", label: "Backlog" },
	{ value: "playing", label: "Playing" },
	{ value: "paused", label: "Paused" },
	{ value: "completed", label: "Completed" },
	{ value: "dropped", label: "Dropped" },
];

export function AddGameModal({ opened, onClose }: AddGameModalProps) {
	// -- Search state --
	const [searchInput, setSearchInput] = useState("");
	const [debouncedSearch] = useDebouncedValue(searchInput, 300);
	const [selectedGame, setSelectedGame] = useState<Game | null>(null);

	// -- Manual creation toggle --
	const [manualMode, setManualMode] = useState(false);
	const [manualTitle, setManualTitle] = useState("");
	const [manualSlug, setManualSlug] = useState("");
	const [manualGenres, setManualGenres] = useState<string[]>([]);

	// -- Common fields --
	const [platformIds, setPlatformIds] = useState<string[]>([]);
	const [status, setStatus] = useState<string | null>("backlog");
	const [notes, setNotes] = useState("");

	// -- Queries & mutations --
	const { data: platforms = [] } = usePlatforms();
	const { data: searchResults = [], isFetching: isSearching } = useSearchGames(debouncedSearch);
	const { data: genreOptions = [] } = useGameGenres();
	const addMutation = useAddToLibrary();
	const createGameMutation = useCreateGame();

	const platformOptions = platforms.map((p) => ({
		value: String(p.id),
		label: p.label,
	}));

	const resetForm = () => {
		setSearchInput("");
		setSelectedGame(null);
		setManualMode(false);
		setManualTitle("");
		setManualSlug("");
		setManualGenres([]);
		setPlatformIds([]);
		setStatus("backlog");
		setNotes("");
	};

	const handleClose = () => {
		resetForm();
		onClose();
	};

	const handleSubmit = async () => {
		if (platformIds.length === 0) {
			notifications.show({
				title: "Missing platform",
				message: "Please select at least one platform.",
				color: "red",
			});
			return;
		}

		try {
			let gamePublicId: string;

			if (manualMode) {
				if (!manualTitle.trim() || !manualSlug.trim()) {
					notifications.show({
						title: "Missing fields",
						message: "Title and slug are required.",
						color: "red",
					});
					return;
				}
				const created = await createGameMutation.mutateAsync({
					title: manualTitle.trim(),
					slug: manualSlug.trim(),
					genres: manualGenres.length > 0 ? manualGenres : undefined,
				});
				gamePublicId = created.publicId;
			} else {
				if (!selectedGame) {
					notifications.show({
						title: "No game selected",
						message: "Search for and select a game first.",
						color: "red",
					});
					return;
				}
				gamePublicId = selectedGame.publicId;
			}

			await addMutation.mutateAsync({
				gamePublicId,
				platformIds: platformIds.map(Number),
				status: (status as LibraryStatus) ?? "backlog",
				notes: notes.trim() || undefined,
			});

			notifications.show({
				title: "Added to library",
				message: manualMode
					? `"${manualTitle}" has been added to your library.`
					: `"${selectedGame?.title}" has been added to your library.`,
				color: "green",
			});

			handleClose();
		} catch (err) {
			notifications.show({
				title: "Failed to add game",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const isPending = addMutation.isPending || createGameMutation.isPending;

	return (
		<Modal opened={opened} onClose={handleClose} title="Add Game to Library" size="lg">
			<Stack>
				<Group justify="space-between">
					<Text size="sm" fw={500}>
						{manualMode ? "Create game manually" : "Search existing games"}
					</Text>
					<Switch
						label="Create manually"
						checked={manualMode}
						onChange={(e) => {
							setManualMode(e.currentTarget.checked);
							setSelectedGame(null);
							setSearchInput("");
						}}
					/>
				</Group>

				{manualMode ? (
					<>
						<TextInput
							label="Title"
							placeholder="Game title"
							required
							value={manualTitle}
							onChange={(e) => setManualTitle(e.currentTarget.value)}
						/>
						<TextInput
							label="Slug"
							placeholder="game-slug"
							required
							value={manualSlug}
							onChange={(e) => setManualSlug(e.currentTarget.value)}
						/>
						<TagsInput
							label="Genres"
							placeholder="Type a genre and press Enter"
							data={genreOptions}
							value={manualGenres}
							onChange={setManualGenres}
						/>
					</>
				) : (
					<>
						<TextInput
							label="Search games"
							placeholder="Type at least 2 characters..."
							value={searchInput}
							onChange={(e) => {
								setSearchInput(e.currentTarget.value);
								setSelectedGame(null);
							}}
							rightSection={isSearching ? <Loader size="xs" /> : null}
						/>

						{selectedGame ? (
							<Badge
								size="lg"
								variant="light"
								rightSection={
									<UnstyledButton
										onClick={() => setSelectedGame(null)}
										ml={4}
										style={{ lineHeight: 1 }}
									>
										x
									</UnstyledButton>
								}
							>
								{selectedGame.title}
							</Badge>
						) : (
							searchResults.length > 0 && (
								<Stack gap="xs">
									{searchResults.map((game) => (
										<UnstyledButton
											key={game.publicId}
											onClick={() => {
												setSelectedGame(game);
												setSearchInput(game.title);
											}}
											p="xs"
											style={(theme) => ({
												borderRadius: theme.radius.sm,
												border: `1px solid ${theme.colors.gray[3]}`,
											})}
										>
											<Text size="sm" fw={500}>
												{game.title}
											</Text>
											{game.summary && (
												<Text size="xs" c="dimmed" lineClamp={1}>
													{game.summary}
												</Text>
											)}
										</UnstyledButton>
									))}
								</Stack>
							)
						)}
					</>
				)}

				<Divider />

				<MultiSelect
					label="Platforms"
					placeholder="Select one or more platforms"
					data={platformOptions}
					required
					value={platformIds}
					onChange={setPlatformIds}
					searchable
				/>

				<Select label="Status" data={STATUS_OPTIONS} value={status} onChange={setStatus} />

				<Textarea
					label="Notes"
					placeholder="Optional notes..."
					value={notes}
					onChange={(e) => setNotes(e.currentTarget.value)}
					autosize
					minRows={2}
					maxRows={4}
				/>

				<Button fullWidth onClick={handleSubmit} loading={isPending}>
					Add to Library
				</Button>
			</Stack>
		</Modal>
	);
}
