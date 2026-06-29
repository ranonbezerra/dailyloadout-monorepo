import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useEndPlaySession, useSubmitWrapUp } from "../hooks/usePlaySession";
import type { PlaySession } from "../types/play-session";

interface PlaySessionWrapUpModalProps {
	playSession: PlaySession | null;
	onClose: () => void;
}

export function PlaySessionWrapUpModal({ playSession, onClose }: PlaySessionWrapUpModalProps) {
	const [wrapUpText, setWrapUpText] = useState("");
	const submitWrapUp = useSubmitWrapUp();
	const endPlaySession = useEndPlaySession();

	if (!playSession) return null;

	const handleWrapUp = async () => {
		try {
			await submitWrapUp.mutateAsync({
				publicId: playSession.publicId,
				wrapUpText,
			});
			notifications.show({
				title: "Session complete",
				message: "Your wrap-up has been saved. See you next session!",
				color: "green",
			});
			setWrapUpText("");
			onClose();
		} catch (err) {
			notifications.show({
				title: "Couldn't save your wrap-up",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const handleEndWithoutWrapUp = async () => {
		try {
			await endPlaySession.mutateAsync({ publicId: playSession.publicId });
			notifications.show({
				title: "Session ended",
				message: "Session ended without a wrap-up.",
				color: "yellow",
			});
			setWrapUpText("");
			onClose();
		} catch (err) {
			notifications.show({
				title: "Couldn't end session",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Modal
			opened={!!playSession}
			onClose={onClose}
			title={<Title order={4}>End session: {playSession.libraryEntry.game.title}</Title>}
			size="lg"
		>
			<Stack gap="md">
				<Text size="sm">
					What happened this session? Jot a quick wrap-up so your next recap knows where you left
					off.
				</Text>

				<Textarea
					placeholder="Beat the Mantis Lords. Got the cloak. Heading to Greenpath next..."
					value={wrapUpText}
					onChange={(e) => setWrapUpText(e.currentTarget.value)}
					autosize
					minRows={4}
					maxRows={8}
				/>

				<Group justify="space-between">
					<Button
						variant="subtle"
						color="gray"
						onClick={handleEndWithoutWrapUp}
						loading={endPlaySession.isPending}
					>
						Skip wrap-up
					</Button>
					<Button
						onClick={handleWrapUp}
						loading={submitWrapUp.isPending}
						disabled={wrapUpText.trim().length < 3}
					>
						Save wrap-up
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}
