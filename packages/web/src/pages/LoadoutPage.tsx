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
import { useAcceptLoadout, useCreateLoadout, useRejectLoadout } from "../hooks/useLoadout";
import { usePreviewBriefing } from "../hooks/useMission";
import type { BriefingMode } from "../lib/mission-api";
import { safeImageUrl } from "../lib/safe-image";
import type { Loadout, LoadoutMood, MentalEnergy } from "../types/loadout";

const MOOD_OPTIONS: { value: LoadoutMood; label: string }[] = [
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

function LoadoutResultCard({
	loadout,
	rank,
	totalResults,
	briefingText,
	isPreviewing,
	onGetBriefing,
	onAccept,
	onReject,
	isActioning,
}: {
	loadout: Loadout;
	rank: number;
	totalResults: number;
	briefingText?: string;
	isPreviewing: boolean;
	onGetBriefing: (mode: BriefingMode) => void;
	onAccept: (briefingText?: string) => void;
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
					{safeImageUrl(loadout.libraryEntry?.game.coverUrl) && (
						<Image
							src={safeImageUrl(loadout.libraryEntry?.game.coverUrl)}
							alt={loadout.libraryEntry?.game.title}
							w={120}
							radius="sm"
						/>
					)}
					<Stack gap="xs" style={{ flex: 1 }}>
						<Title order={3}>{loadout.libraryEntry?.game.title}</Title>
						<Group gap="xs">
							<Badge variant="light">{loadout.libraryEntry?.platform.label}</Badge>
							<Badge variant="light" color="gray">
								{loadout.libraryEntry?.status}
							</Badge>
						</Group>
						{loadout.libraryEntry?.game.genres && loadout.libraryEntry.game.genres.length > 0 && (
							<Group gap={4}>
								{loadout.libraryEntry.game.genres.map((g) => (
									<Badge key={g} size="xs" variant="outline">
										{g}
									</Badge>
								))}
							</Group>
						)}
					</Stack>
				</Group>

				{loadout.reasoning && (
					<Card withBorder p="sm">
						<Text size="sm" fs="italic" c="dimmed">
							{loadout.reasoning}
						</Text>
					</Card>
				)}

				{loadout.action === "accepted" ? (
					<Text c="green" fw={500}>
						Mission started! Redirecting...
					</Text>
				) : loadout.action === "rejected" ? (
					<Text c="dimmed" fw={500}>
						Rejected
					</Text>
				) : (
					<Stack gap="sm">
						{briefingText && (
							<Card withBorder p="sm" radius="sm">
								<Text size="sm" fw={500} mb={4}>
									Briefing
								</Text>
								<Text size="sm" c="dimmed">
									{briefingText}
								</Text>
							</Card>
						)}
						{briefingText ? (
							<Group grow>
								<Button
									color="green"
									leftSection={<IconCheck size={18} />}
									onClick={() => onAccept(briefingText)}
									loading={isActioning}
								>
									Start with briefing
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
										onClick={() => onGetBriefing("quick")}
										loading={isPreviewing}
										disabled={isActioning || !loadout.libraryEntry}
									>
										Quick briefing
									</Button>
									<Button
										variant="light"
										leftSection={<IconSearch size={18} />}
										onClick={() => onGetBriefing("deep")}
										loading={isPreviewing}
										disabled={isActioning || !loadout.libraryEntry}
									>
										Deep briefing
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

export function LoadoutPage() {
	const navigate = useNavigate();
	const [mood, setMood] = useState<LoadoutMood>("chill");
	const [minutes, setMinutes] = useState(60);
	const [energy, setEnergy] = useState<MentalEnergy>("medium");
	const [context, setContext] = useState("");
	const [multiMode, setMultiMode] = useState(false);
	const [results, setResults] = useState<Loadout[]>([]);
	const [briefings, setBriefings] = useState<Record<string, string>>({});

	const createLoadout = useCreateLoadout();
	const acceptLoadout = useAcceptLoadout();
	const rejectLoadout = useRejectLoadout();
	const previewBriefing = usePreviewBriefing();

	const handleRoll = () => {
		setResults([]);
		setBriefings({});
		createLoadout.mutate(
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

	const handleGetBriefing = (loadout: Loadout, mode: BriefingMode) => {
		const entryId = loadout.libraryEntry?.publicId;
		if (!entryId) return;
		previewBriefing.mutate(
			{ libraryEntryPublicId: entryId, mode },
			{
				onSuccess: (preview) => {
					if (preview.briefingText) {
						setBriefings((prev) => ({
							...prev,
							[loadout.publicId]: preview.briefingText as string,
						}));
					}
				},
			},
		);
	};

	const handleAccept = (publicId: string, briefingText?: string) => {
		acceptLoadout.mutate(
			{ publicId, briefingText },
			{
				onSuccess: (data) => {
					setResults((prev) => prev.map((r) => (r.publicId === data.publicId ? data : r)));
					setTimeout(() => navigate("/play"), 600);
				},
			},
		);
	};

	const handleReject = (publicId: string) => {
		rejectLoadout.mutate(publicId, {
			onSuccess: (data) => {
				setResults((prev) => prev.map((r) => (r.publicId === data.publicId ? data : r)));
			},
		});
	};

	const allActioned = results.length > 0 && results.every((r) => r.action !== null);
	const isLoading = createLoadout.isPending;
	const isActioning = acceptLoadout.isPending || rejectLoadout.isPending;

	return (
		<Stack maw={600} mx="auto" mt="md">
			<Title order={2}>Daily Loadout</Title>
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
								onChange={(v) => setMood(v as LoadoutMood)}
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

						{createLoadout.isError && (
							<Text c="red" size="sm">
								{(createLoadout.error as Error).message || "Failed to pick a game. Try again."}
							</Text>
						)}
					</Stack>
				</Card>
			)}

			{/* Step 2: Results */}
			{results.length > 0 &&
				!allActioned &&
				results.map((loadout, index) => (
					<LoadoutResultCard
						key={loadout.publicId}
						loadout={loadout}
						rank={index}
						totalResults={results.length}
						briefingText={briefings[loadout.publicId]}
						isPreviewing={
							previewBriefing.isPending &&
							previewBriefing.variables?.libraryEntryPublicId === loadout.libraryEntry?.publicId
						}
						onGetBriefing={(mode) => handleGetBriefing(loadout, mode)}
						onAccept={(briefingText) => handleAccept(loadout.publicId, briefingText)}
						onReject={() => handleReject(loadout.publicId)}
						isActioning={isActioning}
					/>
				))}
		</Stack>
	);
}
