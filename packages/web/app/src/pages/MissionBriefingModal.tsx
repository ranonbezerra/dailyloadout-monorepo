import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useRef, useState } from "react";
import { AiBriefingOverlay } from "../components/AiBriefingOverlay";
import {
	usePreviewBriefing,
	useRegenerateBriefing,
	useRetroactiveDebrief,
	useStartMission,
} from "../hooks/useMission";
import type { BriefingMode } from "../lib/mission-api";
import type { LibraryEntry } from "../types/library";
import type { Mission } from "../types/mission";

// ---------------------------------------------------------------------------
// Preview mode: user picks a briefing mode, then reviews it before starting.
// The briefing is fetched on demand (after the mode choice), not pre-fetched.
// ---------------------------------------------------------------------------

interface PreviewModeProps {
	mode: "preview";
	libraryEntry: LibraryEntry;
	libraryEntryPublicId: string;
	onConfirm: (mission: Mission) => void;
	onClose: () => void;
}

// ---------------------------------------------------------------------------
// View mode: user is viewing a briefing of an already-started mission
// ---------------------------------------------------------------------------

interface ViewModeProps {
	mode: "view";
	mission: Mission;
	onClose: () => void;
	onMissionUpdated?: (mission: Mission) => void;
}

type MissionBriefingModalProps = PreviewModeProps | ViewModeProps;

// "chooseMode" → pick quick vs deep; "update" → pick which fix to apply.
type ModalStep = "chooseMode" | "briefing" | "update" | "correct" | "retroactive";

export function MissionBriefingModal(props: MissionBriefingModalProps) {
	const isPreview = props.mode === "preview";

	const gameTitle = isPreview
		? props.libraryEntry.game.title
		: props.mission.libraryEntry.game.title;
	const platformLabel = isPreview
		? props.libraryEntry.platform.label
		: props.mission.libraryEntry.platform.label;
	// In view mode the briefing is already on the mission; in preview it's fetched.
	const baseBriefing = isPreview ? null : props.mission.briefingText;

	const [step, setStep] = useState<ModalStep>(isPreview ? "chooseMode" : "briefing");
	const [correction, setCorrection] = useState("");
	const [retroactiveText, setRetroactiveText] = useState("");
	const [currentBriefing, setCurrentBriefing] = useState<string | null>(null);
	const [deepLoading, setDeepLoading] = useState(false);
	const deepAbortRef = useRef<AbortController | null>(null);

	// Preview mode hooks
	const previewMutation = usePreviewBriefing();
	const startMission = useStartMission();
	const retroactiveMutation = useRetroactiveDebrief();

	// View mode hook
	const regenerate = useRegenerateBriefing();

	// Reset state when the modal content changes.
	const contentKey = isPreview
		? `preview-${props.libraryEntryPublicId}`
		: `view-${props.mission.publicId}`;
	const [prevKey, setPrevKey] = useState<string | null>(null);
	if (contentKey !== prevKey) {
		setPrevKey(contentKey);
		setStep(isPreview ? "chooseMode" : "briefing");
		setCorrection("");
		setRetroactiveText("");
		setCurrentBriefing(null);
		setDeepLoading(false);
		deepAbortRef.current?.abort();
		deepAbortRef.current = null;
	}

	const displayBriefing = currentBriefing ?? baseBriefing;

	// -- Mode choice ----------------------------------------------------------

	const handleChooseMode = async (next: BriefingMode) => {
		if (!isPreview) return;
		deepAbortRef.current?.abort();
		deepAbortRef.current = null;
		setStep("briefing");

		if (next === "quick") {
			setDeepLoading(false);
			try {
				const updated = await previewMutation.mutateAsync({
					libraryEntryPublicId: props.libraryEntryPublicId,
					mode: "quick",
				});
				setCurrentBriefing(updated.briefingText);
			} catch (err) {
				notifications.show({
					title: "Couldn't load briefing",
					message: err instanceof Error ? err.message : "An unexpected error occurred",
					color: "red",
				});
			}
			return;
		}

		const controller = new AbortController();
		deepAbortRef.current = controller;
		setDeepLoading(true);
		try {
			const updated = await previewMutation.mutateAsync({
				libraryEntryPublicId: props.libraryEntryPublicId,
				mode: "deep",
				signal: controller.signal,
			});
			if (!controller.signal.aborted) setCurrentBriefing(updated.briefingText);
		} catch (err) {
			if (controller.signal.aborted) return; // user cancelled — stay silent
			notifications.show({
				title: "Deep briefing unavailable",
				message: err instanceof Error ? err.message : "Try the quick briefing instead",
				color: "yellow",
			});
		} finally {
			if (deepAbortRef.current === controller) {
				deepAbortRef.current = null;
				setDeepLoading(false);
			}
		}
	};

	const handleCancelDeep = () => {
		deepAbortRef.current?.abort();
		deepAbortRef.current = null;
		setDeepLoading(false);
		setStep("chooseMode"); // nothing loaded yet — let them pick again
	};

	// -- Briefing corrections -------------------------------------------------

	const handleCorrection = async () => {
		if (!correction.trim()) return;
		try {
			if (isPreview) {
				const updated = await previewMutation.mutateAsync({
					libraryEntryPublicId: props.libraryEntryPublicId,
					positionOverride: correction.trim(),
				});
				setCurrentBriefing(updated.briefingText);
				setStep("briefing");
			} else {
				const updated = await regenerate.mutateAsync({
					publicId: props.mission.publicId,
					currentPosition: correction.trim(),
				});
				props.onMissionUpdated?.(updated);
				setStep("briefing");
			}
		} catch (err) {
			notifications.show({
				title: "Regeneration failed",
				message: err instanceof Error ? err.message : "Could not regenerate briefing",
				color: "red",
			});
		}
	};

	const handleRetroactiveSubmit = async () => {
		if (!isPreview || !retroactiveText.trim()) return;
		try {
			const updatedPreview = await retroactiveMutation.mutateAsync({
				libraryEntryPublicId: props.libraryEntryPublicId,
				debriefText: retroactiveText.trim(),
			});
			setCurrentBriefing(updatedPreview.briefingText);
			setRetroactiveText("");
			setStep("briefing");
			notifications.show({
				title: "Session recorded",
				message: "Your unregistered session has been saved. The briefing has been updated.",
				color: "teal",
			});
		} catch (err) {
			notifications.show({
				title: "Failed to record session",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const handleConfirmStart = async () => {
		if (!isPreview) return;
		try {
			const mission = await startMission.mutateAsync({
				libraryEntryPublicId: props.libraryEntryPublicId,
				briefingText: displayBriefing ?? undefined,
			});
			props.onConfirm(mission);
		} catch (err) {
			notifications.show({
				title: "Cannot start mission",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const handleSkipBriefing = async () => {
		if (!isPreview) return;
		try {
			const mission = await startMission.mutateAsync({
				libraryEntryPublicId: props.libraryEntryPublicId,
				skipBriefing: true,
			});
			props.onConfirm(mission);
		} catch (err) {
			notifications.show({
				title: "Cannot start mission",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const isRegenerating = isPreview
		? previewMutation.isPending && !deepLoading
		: regenerate.isPending;

	const choiceButtonStyles = {
		root: { height: "auto" },
		inner: { justifyContent: "flex-start" },
		label: { whiteSpace: "normal" as const, textAlign: "left" as const },
	};

	return (
		<Modal
			opened
			onClose={props.onClose}
			title={<Title order={4}>Mission Briefing: {gameTitle}</Title>}
			size="lg"
		>
			<Stack gap="md">
				<Text size="sm" c="dimmed">
					{platformLabel}
				</Text>

				{step === "chooseMode" && isPreview && (
					<>
						<Text size="sm">How should we prepare your briefing?</Text>
						<Button
							variant="default"
							fullWidth
							justify="flex-start"
							py="md"
							styles={choiceButtonStyles}
							onClick={() => handleChooseMode("quick")}
						>
							<Stack gap={2} align="flex-start">
								<Text fw={600}>⚡ Quick briefing</Text>
								<Text size="sm" c="dimmed">
									Instant — built from your own past sessions. Recommended.
								</Text>
							</Stack>
						</Button>
						<Button
							variant="default"
							fullWidth
							justify="flex-start"
							py="md"
							styles={choiceButtonStyles}
							onClick={() => handleChooseMode("deep")}
						>
							<Stack gap={2} align="flex-start">
								<Text fw={600}>🔎 Deep briefing (web)</Text>
								<Text size="sm" c="dimmed">
									Searches the web for spoiler-free next steps. Takes up to a minute.
								</Text>
							</Stack>
						</Button>
						<Button
							variant="default"
							fullWidth
							justify="flex-start"
							py="md"
							styles={choiceButtonStyles}
							onClick={handleSkipBriefing}
							loading={startMission.isPending}
						>
							<Stack gap={2} align="flex-start">
								<Text fw={600}>▶️ Just play</Text>
								<Text size="sm" c="dimmed">
									Skip the briefing and start the mission right away.
								</Text>
							</Stack>
						</Button>
					</>
				)}

				{step === "correct" && (
					<>
						<Text size="sm">Tell us where you actually are so we can adjust the briefing:</Text>
						<Textarea
							placeholder="e.g. I'm actually in City of Tears now, working on the Soul Master fight"
							value={correction}
							onChange={(e) => setCorrection(e.currentTarget.value)}
							autosize
							minRows={2}
							maxRows={4}
						/>
						<Group justify="flex-end">
							<Button variant="subtle" onClick={() => setStep(isPreview ? "update" : "briefing")}>
								Back
							</Button>
							<Button
								loading={isRegenerating}
								disabled={!correction.trim()}
								onClick={handleCorrection}
							>
								Update & regenerate
							</Button>
						</Group>
					</>
				)}

				{step === "retroactive" && isPreview && (
					<>
						<Text size="sm">
							Tell us what happened in that unregistered session so we can update your briefing:
						</Text>
						<Textarea
							placeholder="e.g. I played for a couple hours, beat the Soul Master and explored the City of Tears. Got the Elegant Key."
							value={retroactiveText}
							onChange={(e) => setRetroactiveText(e.currentTarget.value)}
							autosize
							minRows={3}
							maxRows={6}
						/>
						<Group justify="flex-end">
							<Button variant="subtle" onClick={() => setStep("update")}>
								Back
							</Button>
							<Button
								loading={retroactiveMutation.isPending}
								disabled={!retroactiveText.trim()}
								onClick={handleRetroactiveSubmit}
							>
								Record session & update briefing
							</Button>
						</Group>
					</>
				)}

				{step === "update" && isPreview && (
					<>
						<Text size="sm">What would you like to fix?</Text>
						<Button variant="default" justify="flex-start" onClick={() => setStep("correct")}>
							Correct my current position
						</Button>
						<Button variant="default" justify="flex-start" onClick={() => setStep("retroactive")}>
							Log a session I didn't register
						</Button>
						<Group justify="flex-end">
							<Button variant="subtle" onClick={() => setStep("briefing")}>
								Back
							</Button>
						</Group>
					</>
				)}

				{step === "briefing" && (
					<>
						{displayBriefing ? (
							<Text style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{displayBriefing}</Text>
						) : (
							<Text c="dimmed" fs="italic">
								No briefing available for this session. This is your first mission for this game —
								enjoy the adventure!
							</Text>
						)}
						<Group justify="flex-end" wrap="wrap">
							{isPreview ? (
								<>
									<Button variant="subtle" onClick={() => setStep("update")}>
										Update this briefing
									</Button>
									<Button
										color="teal"
										loading={startMission.isPending}
										onClick={handleConfirmStart}
									>
										Got it, let's go
									</Button>
								</>
							) : (
								<>
									<Button variant="subtle" onClick={() => setStep("correct")}>
										That's not right
									</Button>
									<Button onClick={props.onClose}>Got it, let's go</Button>
								</>
							)}
						</Group>
					</>
				)}
			</Stack>

			<AiBriefingOverlay
				opened={isRegenerating || retroactiveMutation.isPending}
				gameTitle={gameTitle}
			/>

			<AiBriefingOverlay
				opened={deepLoading}
				gameTitle={gameTitle}
				deep
				onCancel={handleCancelDeep}
			/>
		</Modal>
	);
}
