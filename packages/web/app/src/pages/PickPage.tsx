import {
	Badge,
	Button,
	Card,
	Group,
	Image,
	Loader,
	SegmentedControl,
	Slider,
	Stack,
	Switch,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import { IconBolt, IconCheck, IconDice3, IconSearch, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAcceptPick, useCreatePick, useRejectPick } from "../hooks/usePick";
import { usePreviewRecap } from "../hooks/usePlaySession";
import type { RecapMode } from "../lib/play-session-api";
import { safeImageUrl } from "../lib/safe-image";
import type { MentalEnergy, Pick, PickMood } from "../types/pick";

const MOOD_OPTIONS: { value: PickMood; label: string }[] = [
	{ value: "chill", label: "Chill" },
	{ value: "focused", label: "Focused" },
	{ value: "energetic", label: "Energetic" },
	{ value: "adventurous", label: "Adventurous" },
];

const ENERGY_OPTIONS: { value: MentalEnergy; label: string }[] = [
	{ value: "low", label: "Low" },
	{ value: "medium", label: "Medium" },
	{ value: "high", label: "High" },
];

const TIME_MARKS = [
	{ value: 30, label: "30m" },
	{ value: 60, label: "1h" },
	{ value: 120, label: "2h" },
	{ value: 240, label: "4h" },
];

const RANK_LABELS = ["Best Match", "Great Alternative", "Worth Considering"] as const;

const RANK_COLORS = ["green", "blue", "gray"] as const;

function PickResultCard({
	pick,
	rank,
	totalResults,
	recapText,
	isPreviewing,
	onGetRecap,
	onAccept,
	onReject,
	isActioning,
}: {
	pick: Pick;
	rank: number;
	totalResults: number;
	recapText?: string;
	isPreviewing: boolean;
	onGetRecap: (mode: RecapMode) => void;
	onAccept: (recapText?: string) => void;
	onReject: () => void;
	isActioning: boolean;
}) {
	return (
		<Card withBorder p="lg">
			<Stack gap="md">
				{totalResults > 1 && (
					<Badge color={RANK_COLORS[rank]} variant="filled" size="lg">
						{RANK_LABELS[rank]}
					</Badge>
				)}

				<Group align="flex-start" gap="md">
					{safeImageUrl(pick.libraryEntry?.game.coverUrl) && (
						<Image
							src={safeImageUrl(pick.libraryEntry?.game.coverUrl)}
							alt={pick.libraryEntry?.game.title}
							w={120}
							radius="sm"
						/>
					)}
					<Stack gap="xs" style={{ flex: 1 }}>
						<Title order={3}>{pick.libraryEntry?.game.title}</Title>
						<Group gap="xs">
							<Badge variant="light">{pick.libraryEntry?.platform.label}</Badge>
							<Badge variant="light" color="gray">
								{pick.libraryEntry?.status}
							</Badge>
						</Group>
						{pick.libraryEntry?.game.genres && pick.libraryEntry.game.genres.length > 0 && (
							<Group gap={4}>
								{pick.libraryEntry.game.genres.map((g) => (
									<Badge key={g} size="xs" variant="outline">
										{g}
									</Badge>
								))}
							</Group>
						)}
					</Stack>
				</Group>

				{pick.reasoning && (
					<Card withBorder p="sm">
						<Text size="sm" fs="italic" c="dimmed">
							{pick.reasoning}
						</Text>
					</Card>
				)}

				{pick.action === "accepted" ? (
					<Text c="green" fw={500}>
						Session started! Redirecting...
					</Text>
				) : pick.action === "rejected" ? (
					<Text c="dimmed" fw={500}>
						Rejected
					</Text>
				) : (
					<Stack gap="sm">
						{recapText && (
							<Card withBorder p="sm" radius="sm">
								<Text size="sm" fw={500} mb={4}>
									Recap
								</Text>
								<Text size="sm" c="dimmed">
									{recapText}
								</Text>
							</Card>
						)}
						{recapText ? (
							<Group grow>
								<Button
									color="green"
									leftSection={<IconCheck size={18} />}
									onClick={() => onAccept(recapText)}
									loading={isActioning}
								>
									Start with recap
								</Button>
								<Button
									variant="outline"
									color="red"
									leftSection={<IconX size={18} />}
									onClick={onReject}
									loading={isActioning}
								>
									Reject
								</Button>
							</Group>
						) : (
							<Stack gap="sm">
								<Group grow>
									<Button
										variant="light"
										leftSection={<IconBolt size={18} />}
										onClick={() => onGetRecap("quick")}
										loading={isPreviewing}
										disabled={isActioning || !pick.libraryEntry}
									>
										Quick recap
									</Button>
									<Button
										variant="light"
										leftSection={<IconSearch size={18} />}
										onClick={() => onGetRecap("deep")}
										loading={isPreviewing}
										disabled={isActioning || !pick.libraryEntry}
									>
										Deep recap
									</Button>
								</Group>
								<Group grow>
									<Button
										color="green"
										leftSection={<IconCheck size={18} />}
										onClick={() => onAccept()}
										loading={isActioning}
									>
										Just play
									</Button>
									<Button
										variant="outline"
										color="red"
										leftSection={<IconX size={18} />}
										onClick={onReject}
										loading={isActioning}
									>
										Reject
									</Button>
								</Group>
							</Stack>
						)}
					</Stack>
				)}
			</Stack>
		</Card>
	);
}

const CONTEXT_MAX_LENGTH = 120;

export function PickPage() {
	const navigate = useNavigate();
	const [mood, setMood] = useState<PickMood>("chill");
	const [minutes, setMinutes] = useState(60);
	const [energy, setEnergy] = useState<MentalEnergy>("medium");
	const [context, setContext] = useState("");
	const [multiMode, setMultiMode] = useState(false);
	const [results, setResults] = useState<Pick[]>([]);
	const [recaps, setRecaps] = useState<Record<string, string>>({});

	const createPick = useCreatePick();
	const acceptPick = useAcceptPick();
	const rejectPick = useRejectPick();
	const previewRecap = usePreviewRecap();

	const handleRoll = () => {
		setResults([]);
		setRecaps({});
		createPick.mutate(
			{
				mood,
				availableMinutes: minutes,
				mentalEnergy: energy,
				context: context.trim() || undefined,
				count: multiMode ? 3 : 1,
			},
			{ onSuccess: (data) => setResults(data) },
		);
	};

	const handleGetRecap = (pick: Pick, mode: RecapMode) => {
		const entryId = pick.libraryEntry?.publicId;
		if (!entryId) return;
		previewRecap.mutate(
			{ libraryEntryPublicId: entryId, mode },
			{
				onSuccess: (preview) => {
					if (preview.recapText) {
						setRecaps((prev) => ({
							...prev,
							[pick.publicId]: preview.recapText as string,
						}));
					}
				},
			},
		);
	};

	const handleAccept = (publicId: string, recapText?: string) => {
		acceptPick.mutate(
			{ publicId, recapText },
			{
				onSuccess: (data) => {
					setResults((prev) => prev.map((r) => (r.publicId === data.publicId ? data : r)));
					setTimeout(() => navigate("/play"), 600);
				},
			},
		);
	};

	const handleReject = (publicId: string) => {
		rejectPick.mutate(publicId, {
			onSuccess: (data) => {
				setResults((prev) => prev.map((r) => (r.publicId === data.publicId ? data : r)));
			},
		});
	};

	const allActioned = results.length > 0 && results.every((r) => r.action !== null);
	const isLoading = createPick.isPending;
	const isActioning = acceptPick.isPending || rejectPick.isPending;

	return (
		<Stack maw={600} mx="auto" mt="md">
			<Title order={2}>Daily Pick</Title>
			<Text c="dimmed" size="sm">
				Answer a few questions and we'll pick the perfect game for your session.
			</Text>

			{/* Step 1: Questions */}
			{(results.length === 0 || allActioned) && (
				<Card withBorder p="lg">
					<Stack gap="lg">
						<div>
							<Text fw={500} mb="xs">
								What's your mood?
							</Text>
							<SegmentedControl
								fullWidth
								data={MOOD_OPTIONS}
								value={mood}
								onChange={(v) => setMood(v as PickMood)}
							/>
						</div>

						<div>
							<Text fw={500} mb="xs">
								How much time do you have?
							</Text>
							<Slider
								min={10}
								max={480}
								step={10}
								marks={TIME_MARKS}
								value={minutes}
								onChange={setMinutes}
								label={(v) =>
									v >= 60 ? `${Math.floor(v / 60)}h${v % 60 > 0 ? ` ${v % 60}m` : ""}` : `${v}m`
								}
								mb="md"
							/>
						</div>

						<div>
							<Text fw={500} mb="xs">
								Mental energy level?
							</Text>
							<SegmentedControl
								fullWidth
								data={ENERGY_OPTIONS}
								value={energy}
								onChange={(v) => setEnergy(v as MentalEnergy)}
							/>
						</div>

						<TextInput
							label="Anything else? (optional)"
							placeholder="e.g. feeling nostalgic, want something story-driven..."
							value={context}
							onChange={(e) => setContext(e.currentTarget.value.slice(0, CONTEXT_MAX_LENGTH))}
							maxLength={CONTEXT_MAX_LENGTH}
							description={`${context.length}/${CONTEXT_MAX_LENGTH}`}
						/>

						<Switch
							label="Show multiple suggestions (up to 3)"
							checked={multiMode}
							onChange={(e) => setMultiMode(e.currentTarget.checked)}
						/>

						<Button
							size="lg"
							leftSection={
								isLoading ? <Loader size={18} color="white" /> : <IconDice3 size={20} />
							}
							onClick={handleRoll}
							disabled={isLoading}
						>
							{isLoading ? "Picking..." : "Roll the dice"}
						</Button>

						{createPick.isError && (
							<Text c="red" size="sm">
								{(createPick.error as Error).message || "Failed to pick a game. Try again."}
							</Text>
						)}
					</Stack>
				</Card>
			)}

			{/* Step 2: Results */}
			{results.length > 0 &&
				!allActioned &&
				results.map((pick, index) => (
					<PickResultCard
						key={pick.publicId}
						pick={pick}
						rank={index}
						totalResults={results.length}
						recapText={recaps[pick.publicId]}
						isPreviewing={
							previewRecap.isPending &&
							previewRecap.variables?.libraryEntryPublicId === pick.libraryEntry?.publicId
						}
						onGetRecap={(mode) => handleGetRecap(pick, mode)}
						onAccept={(recapText) => handleAccept(pick.publicId, recapText)}
						onReject={() => handleReject(pick.publicId)}
						isActioning={isActioning}
					/>
				))}
		</Stack>
	);
}
