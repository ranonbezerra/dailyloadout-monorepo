import {
	Badge,
	Button,
	Card,
	Checkbox,
	Group,
	Image,
	Select,
	SimpleGrid,
	Stack,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconArrowLeft, IconPhotoUp, IconX } from "@tabler/icons-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
	useBulkConfirmCandidates,
	useCandidateDuplicates,
	useSubmitLibraryImport,
} from "../hooks/useCapture";
import { usePlatforms } from "../hooks/useLibrary";
import { safeImageUrl } from "../lib/safe-image";
import type { Capture } from "../types/capture";
import type { LibraryStatus, Platform } from "../types/library";

// ---------------------------------------------------------------------------
// Platform picker config + hint copy (verbatim)
// ---------------------------------------------------------------------------

interface PlatformPicker {
	key: string;
	label: string;
	/** Token used to match against platform slug/label for the default Select. */
	matchToken: string;
	hint: string;
}

const PLATFORM_PICKERS: PlatformPicker[] = [
	{
		key: "steam",
		label: "Steam",
		matchToken: "steam",
		hint: "Open your Steam Library and switch to **List view** (the left rail shows titles as text). Screenshot that list.",
	},
	{
		key: "xbox",
		label: "Xbox",
		matchToken: "xbox",
		hint: "Open My games & apps → Full library and switch to List / Details view so titles render as text rows.",
	},
	{
		key: "gog",
		label: "GOG",
		matchToken: "gog",
		hint: "In GOG Galaxy, switch to List view, or use your web library list.",
	},
	{
		key: "playstation",
		label: "PlayStation",
		matchToken: "ps",
		hint: "Open your Game Library, or the PS App list on your phone (the web/app account list is cleanest).",
	},
	{
		key: "epic",
		label: "Epic",
		matchToken: "epic",
		hint: "The Epic launcher is grid-only — open Account → Transactions on the web for a clean text list.",
	},
	{
		key: "switch",
		label: "Nintendo Switch",
		matchToken: "switch",
		hint: "The console is an icon grid — open Nintendo Account → Purchase history on the web for text.",
	},
];

const STATUS_OPTIONS: { value: LibraryStatus; label: string }[] = [
	{ value: "backlog", label: "Backlog" },
	{ value: "playing", label: "Playing" },
	{ value: "paused", label: "Paused" },
	{ value: "completed", label: "Completed" },
	{ value: "dropped", label: "Dropped" },
];

/**
 * Pick the platform whose slug or label (lowercased) contains the picker token;
 * fall back to the first platform.
 */
export function matchDefaultPlatform(
	platforms: Platform[],
	matchToken: string,
): Platform | undefined {
	const token = matchToken.toLowerCase();
	const matched = platforms.find(
		(p) => p.slug.toLowerCase().includes(token) || p.label.toLowerCase().includes(token),
	);
	return matched ?? platforms[0];
}

type Step = "platform" | "hint" | "confirm";

export function LibraryImportPage() {
	const navigate = useNavigate();
	const { data: platforms = [] } = usePlatforms();
	const importMutation = useSubmitLibraryImport();
	const bulkConfirmMutation = useBulkConfirmCandidates();

	const [step, setStep] = useState<Step>("platform");
	const [picker, setPicker] = useState<PlatformPicker | null>(null);
	const [files, setFiles] = useState<File[]>([]);
	const [isDragging, setIsDragging] = useState(false);
	const [capture, setCapture] = useState<Capture | null>(null);
	const [checkedIds, setCheckedIds] = useState<string[]>([]);
	const [titles, setTitles] = useState<Record<string, string>>({});
	const [platformId, setPlatformId] = useState<string | null>(null);
	const [status, setStatus] = useState<string>("backlog");
	const fileInputRef = useRef<HTMLInputElement>(null);

	const { data: duplicateIds = [] } = useCandidateDuplicates(
		step === "confirm" ? (capture?.publicId ?? null) : null,
		platformId != null ? Number(platformId) : null,
	);

	const platformOptions = useMemo(
		() => platforms.map((p) => ({ value: String(p.id), label: p.label })),
		[platforms],
	);

	// A candidate whose title the user edited is treated as a new game, so its
	// "already in library" warning (computed from the original title) no longer
	// applies.
	const isEdited = (cand: { publicId: string; title: string }) =>
		(titles[cand.publicId] ?? cand.title).trim() !== cand.title;
	const isDuplicate = (cand: { publicId: string; title: string }) =>
		duplicateIds.includes(cand.publicId) && !isEdited(cand);

	// Default-uncheck duplicates when the platform (and thus the warning) changes.
	useEffect(() => {
		if (step !== "confirm" || !capture) return;
		setCheckedIds(
			capture.candidates.filter((c) => !duplicateIds.includes(c.publicId)).map((c) => c.publicId),
		);
	}, [step, capture, duplicateIds]);

	const handlePickPlatform = (p: PlatformPicker) => {
		setPicker(p);
		const def = matchDefaultPlatform(platforms, p.matchToken);
		setPlatformId(def ? String(def.id) : null);
		setStep("hint");
	};

	/** Append image files, de-duping by name+size so re-drops don't pile up. */
	const addFiles = useCallback((incoming: File[]) => {
		const images = incoming.filter((f) => f.type.startsWith("image/"));
		setFiles((prev) => {
			const seen = new Set(prev.map((f) => `${f.name}:${f.size}`));
			return [...prev, ...images.filter((f) => !seen.has(`${f.name}:${f.size}`))];
		});
	}, []);

	// While picking screenshots, allow pasting an image straight from the clipboard.
	useEffect(() => {
		if (step !== "hint") return;
		const onPaste = (e: ClipboardEvent) => {
			const pasted = e.clipboardData?.files;
			if (pasted && pasted.length > 0) addFiles(Array.from(pasted));
		};
		document.addEventListener("paste", onPaste);
		return () => document.removeEventListener("paste", onPaste);
	}, [step, addFiles]);

	const handleFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		addFiles(e.target.files ? Array.from(e.target.files) : []);
		e.target.value = ""; // allow re-selecting the same file
	};

	const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
		e.preventDefault();
		setIsDragging(false);
		addFiles(Array.from(e.dataTransfer.files));
	};

	const removeFile = (name: string, size: number) => {
		setFiles((prev) => prev.filter((f) => !(f.name === name && f.size === size)));
	};

	const handleUpload = async () => {
		if (files.length === 0) return;
		try {
			const result = await importMutation.mutateAsync(files);
			setCapture(result);
			setCheckedIds(result.candidates.map((c) => c.publicId));
			setTitles(Object.fromEntries(result.candidates.map((c) => [c.publicId, c.title])));
			setStep("confirm");
		} catch (err) {
			notifications.show({
				title: "Import failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const toggleChecked = (id: string, checked: boolean) => {
		setCheckedIds((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)));
	};

	const handleConfirm = async () => {
		if (!capture || checkedIds.length === 0 || !platformId) return;
		// Send only the titles the user actually changed.
		const checkedSet = new Set(checkedIds);
		const titleOverrides: Record<string, string> = {};
		for (const cand of capture.candidates) {
			const edited = (titles[cand.publicId] ?? cand.title).trim();
			if (checkedSet.has(cand.publicId) && edited && edited !== cand.title) {
				titleOverrides[cand.publicId] = edited;
			}
		}
		try {
			await bulkConfirmMutation.mutateAsync({
				captureId: capture.publicId,
				confirmPublicIds: checkedIds,
				platformId: Number(platformId),
				status: status as LibraryStatus,
				titleOverrides,
			});
			notifications.show({
				title: "Library import",
				message: `Imported ${checkedIds.length} games`,
				color: "green",
			});
			navigate("/library");
		} catch (err) {
			notifications.show({
				title: "Import failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Stack>
			<Group justify="space-between">
				<Title order={2}>Import from screenshots</Title>
				<Button
					variant="subtle"
					color="gray"
					leftSection={<IconArrowLeft size={16} />}
					onClick={() => navigate("/library")}
				>
					Back to Library
				</Button>
			</Group>

			{step === "platform" && (
				<Stack>
					<Text c="dimmed">Pick the platform you want to import games from.</Text>
					<SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
						{PLATFORM_PICKERS.map((p) => (
							<Card
								key={p.key}
								withBorder
								radius="md"
								padding="lg"
								style={{ cursor: "pointer" }}
								onClick={() => handlePickPlatform(p)}
								data-testid={`platform-card-${p.key}`}
							>
								<Text fw={600}>{p.label}</Text>
							</Card>
						))}
					</SimpleGrid>
				</Stack>
			)}

			{step === "hint" && picker && (
				<Stack>
					<Button
						variant="subtle"
						color="gray"
						leftSection={<IconArrowLeft size={16} />}
						onClick={() => setStep("platform")}
						w="fit-content"
					>
						Change platform
					</Button>
					<Card withBorder radius="md" padding="lg">
						<Stack gap="xs">
							<Title order={4}>{picker.label}</Title>
							<Text>{picker.hint}</Text>
						</Stack>
					</Card>

					{/* Hidden native input — the styled dropzone drives it. */}
					<input
						ref={fileInputRef}
						type="file"
						multiple
						accept="image/*"
						onChange={handleFilesChange}
						data-testid="import-file-input"
						aria-label="Select screenshots"
						style={{ display: "none" }}
					/>

					<Card
						withBorder
						radius="md"
						padding="xl"
						onClick={() => fileInputRef.current?.click()}
						onDragOver={(e) => {
							e.preventDefault();
							setIsDragging(true);
						}}
						onDragLeave={() => setIsDragging(false)}
						onDrop={handleDrop}
						data-testid="import-dropzone"
						style={{
							cursor: "pointer",
							borderStyle: "dashed",
							borderWidth: 2,
							borderColor: isDragging ? "var(--mantine-primary-color-filled)" : undefined,
							backgroundColor: isDragging ? "var(--mantine-primary-color-light)" : undefined,
							transition: "border-color 120ms ease, background-color 120ms ease",
						}}
					>
						<Stack align="center" gap={6} py="md">
							<IconPhotoUp size={36} opacity={0.7} />
							<Text fw={600}>Drop screenshots here</Text>
							<Text size="sm" c="dimmed">
								or click to browse, or paste (⌘/Ctrl+V) — PNG or JPG, add as many as you like
							</Text>
						</Stack>
					</Card>

					{files.length > 0 && (
						<Stack gap={6}>
							<Group justify="space-between">
								<Text size="sm" fw={500}>
									{files.length} screenshot{files.length === 1 ? "" : "s"} selected
								</Text>
								<Button
									variant="subtle"
									size="compact-xs"
									color="gray"
									onClick={() => setFiles([])}
								>
									Clear all
								</Button>
							</Group>
							{files.map((f) => (
								<Card key={`${f.name}:${f.size}`} withBorder radius="sm" padding="xs">
									<Group justify="space-between" wrap="nowrap">
										<Text size="sm" truncate>
											{f.name}
										</Text>
										<Button
											variant="subtle"
											color="gray"
											size="compact-xs"
											onClick={() => removeFile(f.name, f.size)}
											aria-label={`Remove ${f.name}`}
										>
											<IconX size={14} />
										</Button>
									</Group>
								</Card>
							))}
						</Stack>
					)}

					<Button
						onClick={handleUpload}
						disabled={files.length === 0}
						loading={importMutation.isPending}
						w="fit-content"
					>
						{files.length === 0
							? "Import screenshots"
							: `Import ${files.length} screenshot${files.length === 1 ? "" : "s"}`}
					</Button>
				</Stack>
			)}

			{step === "confirm" && capture && (
				<Stack>
					<Text c="dimmed">
						Review the detected games, fix any wrong titles, and choose which to add. Games already
						in your library for the selected platform are flagged.
					</Text>

					<Group>
						<Select
							label="Platform"
							data={platformOptions}
							value={platformId}
							onChange={setPlatformId}
							w={220}
						/>
						<Select
							label="Status"
							data={STATUS_OPTIONS}
							value={status}
							onChange={(v) => setStatus(v ?? "backlog")}
							w={220}
						/>
					</Group>

					<Stack gap="xs">
						{capture.candidates.map((cand) => {
							const duplicate = isDuplicate(cand);
							return (
								<Card key={cand.publicId} withBorder radius="md" padding="sm">
									<Group wrap="nowrap" align="center">
										<Checkbox
											checked={checkedIds.includes(cand.publicId)}
											onChange={(e) => toggleChecked(cand.publicId, e.currentTarget.checked)}
											aria-label={`Select ${cand.title}`}
										/>
										{safeImageUrl(cand.igdbCoverUrl) && !isEdited(cand) && (
											<Image
												src={safeImageUrl(cand.igdbCoverUrl)}
												alt={cand.title}
												w={40}
												h={56}
												radius="sm"
											/>
										)}
										<TextInput
											value={titles[cand.publicId] ?? cand.title}
											onChange={(e) => {
												const value = e.currentTarget.value;
												setTitles((prev) => ({ ...prev, [cand.publicId]: value }));
											}}
											aria-label={`Title for ${cand.title}`}
											style={{ flex: 1 }}
										/>
										{cand.matchedGame && !isEdited(cand) && (
											<Badge color="green" variant="light">
												IGDB
											</Badge>
										)}
										{duplicate && (
											<Badge
												color="orange"
												variant="light"
												leftSection={<IconAlertTriangle size={12} />}
											>
												In library
											</Badge>
										)}
									</Group>
								</Card>
							);
						})}
					</Stack>

					<Button
						onClick={handleConfirm}
						disabled={checkedIds.length === 0 || !platformId}
						loading={bulkConfirmMutation.isPending}
						w="fit-content"
					>
						Add {checkedIds.length} games
					</Button>
				</Stack>
			)}
		</Stack>
	);
}
