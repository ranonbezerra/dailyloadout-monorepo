import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useRegenerateBriefing } from "../hooks/useMission";
import type { Mission } from "../types/mission";

interface MissionBriefingModalProps {
	mission: Mission | null;
	onClose: () => void;
	onMissionUpdated?: (mission: Mission) => void;
}

type ModalStep = "confirm" | "correct" | "briefing";

export function MissionBriefingModal({
	mission,
	onClose,
	onMissionUpdated,
}: MissionBriefingModalProps) {
	const ctx = mission?.lastSessionContext;
	const hasContext = ctx && (ctx.location || ctx.nextAction || ctx.currentQuest);

	const [step, setStep] = useState<ModalStep>(hasContext ? "confirm" : "briefing");
	const [correction, setCorrection] = useState("");
	const regenerate = useRegenerateBriefing();

	// Reset state when mission changes.
	const currentMissionId = mission?.publicId ?? null;
	const [prevMissionId, setPrevMissionId] = useState<string | null>(null);
	if (currentMissionId !== prevMissionId) {
		setPrevMissionId(currentMissionId);
		setStep(hasContext ? "confirm" : "briefing");
		setCorrection("");
	}

	if (!mission) return null;

	const handleCorrection = async () => {
		if (!correction.trim()) return;
		try {
			const updated = await regenerate.mutateAsync({
				publicId: mission.publicId,
				currentPosition: correction.trim(),
			});
			onMissionUpdated?.(updated);
			setStep("briefing");
		} catch (err) {
			notifications.show({
				title: "Regeneration failed",
				message: err instanceof Error ? err.message : "Could not regenerate briefing",
				color: "red",
			});
		}
	};

	return (
		<Modal
			opened={!!mission}
			onClose={onClose}
			title={<Title order={4}>Mission Briefing: {mission.libraryEntry.game.title}</Title>}
			size="lg"
		>
			<Stack gap="md">
				<Text size="sm" c="dimmed">
					{mission.libraryEntry.platform.label}
				</Text>

				{step === "confirm" && ctx && (
					<>
						<Text fw={500}>Before we begin — are you still here?</Text>
						<Stack
							gap="xs"
							p="sm"
							style={{
								backgroundColor: "var(--mantine-color-dark-6)",
								borderRadius: "var(--mantine-radius-sm)",
							}}
						>
							{ctx.location && (
								<Text size="sm">
									<Text span fw={500}>
										Location:
									</Text>{" "}
									{ctx.location}
								</Text>
							)}
							{ctx.currentQuest && (
								<Text size="sm">
									<Text span fw={500}>
										Quest:
									</Text>{" "}
									{ctx.currentQuest}
								</Text>
							)}
							{ctx.nextAction && (
								<Text size="sm">
									<Text span fw={500}>
										Next action:
									</Text>{" "}
									{ctx.nextAction}
								</Text>
							)}
							{ctx.level && (
								<Text size="sm">
									<Text span fw={500}>
										Progress:
									</Text>{" "}
									{ctx.level}
								</Text>
							)}
						</Stack>
						<Group justify="flex-end">
							<Button variant="subtle" onClick={() => setStep("correct")}>
								Not quite — let me update
							</Button>
							<Button onClick={() => setStep("briefing")}>Yes, that's right</Button>
						</Group>
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
							<Button variant="subtle" onClick={() => setStep("confirm")}>
								Back
							</Button>
							<Button
								loading={regenerate.isPending}
								disabled={!correction.trim()}
								onClick={handleCorrection}
							>
								Update & regenerate
							</Button>
						</Group>
					</>
				)}

				{step === "briefing" && (
					<>
						{mission.briefingText ? (
							<Text
								style={{
									whiteSpace: "pre-wrap",
									lineHeight: 1.6,
								}}
							>
								{mission.briefingText}
							</Text>
						) : (
							<Text c="dimmed" fs="italic">
								No briefing available for this session. This is your first mission for this game —
								enjoy the adventure!
							</Text>
						)}
						<Group justify="flex-end">
							<Button onClick={onClose}>Got it, let's go</Button>
						</Group>
					</>
				)}
			</Stack>
		</Modal>
	);
}
