import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useEndMission, useSubmitDebrief } from "../hooks/useMission";
import type { Mission } from "../types/mission";

interface MissionDebriefModalProps {
	mission: Mission | null;
	onClose: () => void;
}

export function MissionDebriefModal({ mission, onClose }: MissionDebriefModalProps) {
	const [debriefText, setDebriefText] = useState("");
	const submitDebrief = useSubmitDebrief();
	const endMission = useEndMission();

	if (!mission) return null;

	const handleDebrief = async () => {
		try {
			await submitDebrief.mutateAsync({
				publicId: mission.publicId,
				debriefText,
			});
			notifications.show({
				title: "Mission complete",
				message: "Your debrief has been saved. See you next session!",
				color: "green",
			});
			setDebriefText("");
			onClose();
		} catch (err) {
			notifications.show({
				title: "Debrief failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const handleEndWithoutDebrief = async () => {
		try {
			await endMission.mutateAsync({ publicId: mission.publicId });
			notifications.show({
				title: "Mission ended",
				message: "Mission ended without debrief.",
				color: "yellow",
			});
			setDebriefText("");
			onClose();
		} catch (err) {
			notifications.show({
				title: "End mission failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Modal
			opened={!!mission}
			onClose={onClose}
			title={<Title order={4}>End Mission: {mission.libraryEntry.game.title}</Title>}
			size="lg"
		>
			<Stack gap="md">
				<Text size="sm">
					What happened this session? Write a quick debrief so your next briefing knows where you
					left off.
				</Text>

				<Textarea
					placeholder="Beat the Mantis Lords. Got the cloak. Heading to Greenpath next..."
					value={debriefText}
					onChange={(e) => setDebriefText(e.currentTarget.value)}
					autosize
					minRows={4}
					maxRows={8}
				/>

				<Group justify="space-between">
					<Button
						variant="subtle"
						color="gray"
						onClick={handleEndWithoutDebrief}
						loading={endMission.isPending}
					>
						Skip debrief
					</Button>
					<Button
						onClick={handleDebrief}
						loading={submitDebrief.isPending}
						disabled={debriefText.trim().length < 3}
					>
						Submit debrief
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}
