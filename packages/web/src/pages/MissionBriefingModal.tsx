import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { AiBriefingOverlay } from "../components/AiBriefingOverlay";
import {
	usePreviewBriefing,
	useRegenerateBriefing,
	useRetroactiveDebrief,
	useStartMission,
} from "../hooks/useMission";
import type { BriefingPreview, Mission } from "../types/mission";

// ---------------------------------------------------------------------------
// Preview mode: user is reviewing a briefing before starting a mission
// ---------------------------------------------------------------------------

interface PreviewModeProps {
	mode: "preview";
	preview: BriefingPreview;
	libraryEntryPublicId: string;
	onConfirm: (mission: Mission) => void;
	onPreviewUpdated?: (preview: BriefingPreview) => void;
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

type ModalStep = "correct" | "retroactive" | "briefing";

export function MissionBriefingModal(props: MissionBriefingModalProps) {
	const isPreview = props.mode === "preview";

	const gameTitle = isPreview
		? props.preview.libraryEntry.game.title
		: props.mission.libraryEntry.game.title;
	const platformLabel = isPreview
		? props.preview.libraryEntry.platform.label
		: props.mission.libraryEntry.platform.label;
	const briefingText = isPreview ? props.preview.briefingText : props.mission.briefingText;

	const [step, setStep] = useState<ModalStep>("briefing");
	const [correction, setCorrection] = useState("");
	const [retroactiveText, setRetroactiveText] = useState("");
	const [currentBriefing, setCurrentBriefing] = useState<string | null>(null);

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
		setStep("briefing");
		setCorrection("");
		setRetroactiveText("");
		setCurrentBriefing(null);
	}

	const displayBriefing = currentBriefing ?? briefingText;

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
			props.onPreviewUpdated?.(updatedPreview);
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

	const isRegenerating = isPreview ? previewMutation.isPending : regenerate.isPending;

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
							<Button variant="subtle" onClick={() => setStep("briefing")}>
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
							<Button variant="subtle" onClick={() => setStep("briefing")}>
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

				{step === "briefing" && (
					<>
						{displayBriefing ? (
							<Text
								style={{
									whiteSpace: "pre-wrap",
									lineHeight: 1.6,
								}}
							>
								{displayBriefing}
							</Text>
						) : (
							<Text c="dimmed" fs="italic">
								No briefing available for this session. This is your first mission for this game —
								enjoy the adventure!
							</Text>
						)}
						<Group justify="flex-end" wrap="wrap">
							{isPreview && (
								<Button variant="subtle" onClick={() => setStep("retroactive")}>
									I played without registering
								</Button>
							)}
							<Button variant="subtle" onClick={() => setStep("correct")}>
								That's not right
							</Button>
							{isPreview ? (
								<>
									<Button variant="subtle" onClick={props.onClose}>
										Cancel
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
								<Button onClick={props.onClose}>Got it, let's go</Button>
							)}
						</Group>
					</>
				)}
			</Stack>

			<AiBriefingOverlay
				opened={isRegenerating || retroactiveMutation.isPending}
				gameTitle={gameTitle}
			/>
		</Modal>
	);
}
