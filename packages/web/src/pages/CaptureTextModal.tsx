import { Button, Modal, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useSubmitTextCapture } from "../hooks/useCapture";

interface CaptureTextModalProps {
	opened: boolean;
	onClose: () => void;
	onSuccess: (capturePublicId: string) => void;
}

export function CaptureTextModal({ opened, onClose, onSuccess }: CaptureTextModalProps) {
	const [rawText, setRawText] = useState("");
	const submitMutation = useSubmitTextCapture();

	const resetForm = () => {
		setRawText("");
	};

	const handleClose = () => {
		resetForm();
		onClose();
	};

	const handleSubmit = async () => {
		const trimmed = rawText.trim();
		if (trimmed.length < 3) {
			notifications.show({
				title: "Input too short",
				message: "Please enter at least 3 characters.",
				color: "red",
			});
			return;
		}

		try {
			const capture = await submitMutation.mutateAsync({ rawText: trimmed });
			notifications.show({
				title: "Capture submitted",
				message: `Found ${capture.candidates.length} candidate(s). Review them now.`,
				color: "green",
			});
			resetForm();
			onSuccess(capture.publicId);
		} catch (err) {
			notifications.show({
				title: "Capture failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Modal opened={opened} onClose={handleClose} title="New Text Capture" size="lg">
			<Stack>
				<Text size="sm" c="dimmed">
					Paste or type the games you want to capture. You can list multiple games, include
					platform names, or paste text from any source. The AI will extract game titles and match
					them.
				</Text>

				<Textarea
					label="Raw text"
					placeholder="e.g. Elden Ring on PS5, Zelda TOTK, Hollow Knight..."
					value={rawText}
					onChange={(e) => setRawText(e.currentTarget.value)}
					autosize
					minRows={4}
					maxRows={10}
					required
				/>

				<Button
					fullWidth
					onClick={handleSubmit}
					loading={submitMutation.isPending}
					disabled={rawText.trim().length < 3}
				>
					Submit Capture
				</Button>
			</Stack>
		</Modal>
	);
}
