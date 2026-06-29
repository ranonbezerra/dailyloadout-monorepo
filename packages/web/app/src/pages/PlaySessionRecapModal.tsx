import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useRef, useState } from "react";
import { AiRecapOverlay } from "../components/AiRecapOverlay";
import {
	usePreviewRecap,
	useRegenerateRecap,
	useRetroactiveWrapUp,
	useStartPlaySession,
} from "../hooks/usePlaySession";
import type { RecapMode } from "../lib/play-session-api";
import type { LibraryEntry } from "../types/library";
import type { PlaySession } from "../types/play-session";

// ---------------------------------------------------------------------------
// Preview mode: user picks a recap mode, then reviews it before starting.
// The recap is fetched on demand (after the mode choice), not pre-fetched.
// ---------------------------------------------------------------------------

interface PreviewModeProps {
	mode: "preview";
	libraryEntry: LibraryEntry;
	libraryEntryPublicId: string;
	onConfirm: (playSession: PlaySession) => void;
	onClose: () => void;
}

// ---------------------------------------------------------------------------
// View mode: user is viewing a recap of an already-started playSession
// ---------------------------------------------------------------------------

interface ViewModeProps {
	mode: "view";
	playSession: PlaySession;
	onClose: () => void;
	onPlaySessionUpdated?: (playSession: PlaySession) => void;
}

type PlaySessionRecapModalProps = PreviewModeProps | ViewModeProps;

// "chooseMode" → pick quick vs deep; "update" → pick which fix to apply.
type ModalStep = "chooseMode" | "recap" | "update" | "correct" | "retroactive";

export function PlaySessionRecapModal(props: PlaySessionRecapModalProps) {
	const isPreview = props.mode === "preview";

	const gameTitle = isPreview
		? props.libraryEntry.game.title
		: props.playSession.libraryEntry.game.title;
	const platformLabel = isPreview
		? props.libraryEntry.platform.label
		: props.playSession.libraryEntry.platform.label;
	// In view mode the recap is already on the playSession; in preview it's fetched.
	const baseRecap = isPreview ? null : props.playSession.recapText;

	const [step, setStep] = useState<ModalStep>(isPreview ? "chooseMode" : "recap");
	const [correction, setCorrection] = useState("");
	const [retroactiveText, setRetroactiveText] = useState("");
	const [currentRecap, setCurrentRecap] = useState<string | null>(null);
	const [deepLoading, setDeepLoading] = useState(false);
	const deepAbortRef = useRef<AbortController | null>(null);

	// Preview mode hooks
	const previewMutation = usePreviewRecap();
	const startPlaySession = useStartPlaySession();
	const retroactiveMutation = useRetroactiveWrapUp();

	// View mode hook
	const regenerate = useRegenerateRecap();

	// Reset state when the modal content changes.
	const contentKey = isPreview
		? `preview-${props.libraryEntryPublicId}`
		: `view-${props.playSession.publicId}`;
	const [prevKey, setPrevKey] = useState<string | null>(null);
	if (contentKey !== prevKey) {
		setPrevKey(contentKey);
		setStep(isPreview ? "chooseMode" : "recap");
		setCorrection("");
		setRetroactiveText("");
		setCurrentRecap(null);
		setDeepLoading(false);
		deepAbortRef.current?.abort();
		deepAbortRef.current = null;
	}

	const displayRecap = currentRecap ?? baseRecap;

	// -- Mode choice ----------------------------------------------------------

	const handleChooseMode = async (next: RecapMode) => {
		if (!isPreview) return;
		deepAbortRef.current?.abort();
		deepAbortRef.current = null;
		setStep("recap");

		if (next === "quick") {
			setDeepLoading(false);
			try {
				const updated = await previewMutation.mutateAsync({
					libraryEntryPublicId: props.libraryEntryPublicId,
					mode: "quick",
				});
				setCurrentRecap(updated.recapText);
			} catch (err) {
				notifications.show({
					title: "Couldn't load recap",
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
			if (!controller.signal.aborted) setCurrentRecap(updated.recapText);
		} catch (err) {
			if (controller.signal.aborted) return; // user cancelled — stay silent
			notifications.show({
				title: "Deep recap unavailable",
				message: err instanceof Error ? err.message : "Try the quick recap instead",
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

	// -- Recap corrections -------------------------------------------------

	const handleCorrection = async () => {
		if (!correction.trim()) return;
		try {
			if (isPreview) {
				const updated = await previewMutation.mutateAsync({
					libraryEntryPublicId: props.libraryEntryPublicId,
					positionOverride: correction.trim(),
				});
				setCurrentRecap(updated.recapText);
				setStep("recap");
			} else {
				const updated = await regenerate.mutateAsync({
					publicId: props.playSession.publicId,
					currentPosition: correction.trim(),
				});
				props.onPlaySessionUpdated?.(updated);
				setStep("recap");
			}
		} catch (err) {
			notifications.show({
				title: "Regeneration failed",
				message: err instanceof Error ? err.message : "Couldn't regenerate recap",
				color: "red",
			});
		}
	};

	const handleRetroactiveSubmit = async () => {
		if (!isPreview || !retroactiveText.trim()) return;
		try {
			const updatedPreview = await retroactiveMutation.mutateAsync({
				libraryEntryPublicId: props.libraryEntryPublicId,
				wrapUpText: retroactiveText.trim(),
			});
			setCurrentRecap(updatedPreview.recapText);
			setRetroactiveText("");
			setStep("recap");
			notifications.show({
				title: "Session recorded",
				message: "Your unregistered session has been saved. The recap has been updated.",
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
			const playSession = await startPlaySession.mutateAsync({
				libraryEntryPublicId: props.libraryEntryPublicId,
				recapText: displayRecap ?? undefined,
			});
			props.onConfirm(playSession);
		} catch (err) {
			notifications.show({
				title: "Couldn't start session",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const handleSkipRecap = async () => {
		if (!isPreview) return;
		try {
			const playSession = await startPlaySession.mutateAsync({
				libraryEntryPublicId: props.libraryEntryPublicId,
				skipRecap: true,
			});
			props.onConfirm(playSession);
		} catch (err) {
			notifications.show({
				title: "Couldn't start session",
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
			title={<Title order={4}>Recap: {gameTitle}</Title>}
			size="lg"
		>
			<Stack gap="md">
				<Text size="sm" c="dimmed">
					{platformLabel}
				</Text>

				{step === "chooseMode" && isPreview && (
					<>
						<Text size="sm">How should we prepare your recap?</Text>
						<Button
							variant="default"
							fullWidth
							justify="flex-start"
							py="md"
							styles={choiceButtonStyles}
							onClick={() => handleChooseMode("quick")}
						>
							<Stack gap={2} align="flex-start">
								<Text fw={600}>⚡ Quick recap</Text>
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
								<Text fw={600}>🔎 Deep recap (web)</Text>
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
							onClick={handleSkipRecap}
							loading={startPlaySession.isPending}
						>
							<Stack gap={2} align="flex-start">
								<Text fw={600}>▶️ Just play</Text>
								<Text size="sm" c="dimmed">
									Skip the recap and start your session right away.
								</Text>
							</Stack>
						</Button>
					</>
				)}

				{step === "correct" && (
					<>
						<Text size="sm">Tell us where you actually are so we can adjust the recap:</Text>
						<Textarea
							placeholder="e.g. I'm actually in City of Tears now, working on the Soul Master fight"
							value={correction}
							onChange={(e) => setCorrection(e.currentTarget.value)}
							autosize
							minRows={2}
							maxRows={4}
						/>
						<Group justify="flex-end">
							<Button variant="subtle" onClick={() => setStep(isPreview ? "update" : "recap")}>
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
							Tell us what happened in that unregistered session so we can update your recap:
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
								Record session & update recap
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
							<Button variant="subtle" onClick={() => setStep("recap")}>
								Back
							</Button>
						</Group>
					</>
				)}

				{step === "recap" && (
					<>
						{displayRecap ? (
							<Text style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{displayRecap}</Text>
						) : (
							<Text c="dimmed" fs="italic">
								No recap available for this session. This is your first session for this game —
								enjoy the adventure!
							</Text>
						)}
						<Group justify="flex-end" wrap="wrap">
							{isPreview ? (
								<>
									<Button variant="subtle" onClick={() => setStep("update")}>
										Update this recap
									</Button>
									<Button
										color="teal"
										loading={startPlaySession.isPending}
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

			<AiRecapOverlay
				opened={isRegenerating || retroactiveMutation.isPending}
				gameTitle={gameTitle}
			/>

			<AiRecapOverlay
				opened={deepLoading}
				gameTitle={gameTitle}
				deep
				onCancel={handleCancelDeep}
			/>
		</Modal>
	);
}
