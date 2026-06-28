import { ActionIcon, Button, Group, Modal, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconMicrophone, IconPlayerStop } from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSubmitTextCapture, useTranscribeAudio } from "../hooks/useCapture";

interface CaptureVoiceModalProps {
	opened: boolean;
	onClose: () => void;
	onSuccess: (capturePublicId: string) => void;
}

const MAX_DURATION_SECONDS = 60;

export function CaptureVoiceModal({ opened, onClose, onSuccess }: CaptureVoiceModalProps) {
	const [isRecording, setIsRecording] = useState(false);
	const [secondsElapsed, setSecondsElapsed] = useState(0);
	const [transcribedText, setTranscribedText] = useState("");
	const [hasTranscription, setHasTranscription] = useState(false);

	const mediaRecorderRef = useRef<MediaRecorder | null>(null);
	const chunksRef = useRef<Blob[]>([]);
	const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const streamRef = useRef<MediaStream | null>(null);

	const transcribeMutation = useTranscribeAudio();
	const submitMutation = useSubmitTextCapture();

	const stopRecording = useCallback(() => {
		if (timerRef.current) {
			clearInterval(timerRef.current);
			timerRef.current = null;
		}
		if (mediaRecorderRef.current?.state === "recording") {
			mediaRecorderRef.current.stop();
		}
		setIsRecording(false);
	}, []);

	// Auto-stop at max duration.
	useEffect(() => {
		if (isRecording && secondsElapsed >= MAX_DURATION_SECONDS) {
			stopRecording();
		}
	}, [isRecording, secondsElapsed, stopRecording]);

	// Clean up on unmount or close.
	useEffect(() => {
		return () => {
			if (timerRef.current) clearInterval(timerRef.current);
			if (streamRef.current) {
				for (const track of streamRef.current.getTracks()) track.stop();
			}
		};
	}, []);

	const startRecording = async () => {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			streamRef.current = stream;

			const mediaRecorder = new MediaRecorder(stream);
			mediaRecorderRef.current = mediaRecorder;
			chunksRef.current = [];

			mediaRecorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunksRef.current.push(e.data);
			};

			mediaRecorder.onstop = async () => {
				// Stop all tracks to release the mic.
				for (const track of stream.getTracks()) track.stop();
				streamRef.current = null;

				const blob = new Blob(chunksRef.current, { type: "audio/webm" });
				chunksRef.current = [];

				try {
					const result = await transcribeMutation.mutateAsync(blob);
					setTranscribedText(result.text);
					setHasTranscription(true);
				} catch (err) {
					notifications.show({
						title: "Transcription failed",
						message: err instanceof Error ? err.message : "An unexpected error occurred",
						color: "red",
					});
				}
			};

			mediaRecorder.start();
			setIsRecording(true);
			setSecondsElapsed(0);
			setHasTranscription(false);
			setTranscribedText("");

			timerRef.current = setInterval(() => {
				setSecondsElapsed((prev) => prev + 1);
			}, 1000);
		} catch {
			notifications.show({
				title: "Microphone access denied",
				message: "Please allow microphone access to use voice capture.",
				color: "red",
			});
		}
	};

	const handleSubmit = async () => {
		const trimmed = transcribedText.trim();
		if (trimmed.length < 3) {
			notifications.show({
				title: "Input too short",
				message: "Please enter at least 3 characters.",
				color: "red",
			});
			return;
		}

		try {
			const capture = await submitMutation.mutateAsync({
				rawText: trimmed,
				inputType: "voice",
			});
			notifications.show({
				title: "Capture submitted",
				message: `Found ${capture.candidates.length} candidate(s). Review them now.`,
				color: "green",
			});
			resetState();
			onSuccess(capture.publicId);
		} catch (err) {
			notifications.show({
				title: "Capture failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const resetState = () => {
		setIsRecording(false);
		setSecondsElapsed(0);
		setTranscribedText("");
		setHasTranscription(false);
	};

	const handleClose = () => {
		stopRecording();
		resetState();
		onClose();
	};

	const handleRecordAgain = () => {
		setHasTranscription(false);
		setTranscribedText("");
		setSecondsElapsed(0);
	};

	const formatDuration = (seconds: number) => {
		const m = Math.floor(seconds / 60)
			.toString()
			.padStart(2, "0");
		const s = (seconds % 60).toString().padStart(2, "0");
		return `${m}:${s}`;
	};

	return (
		<Modal opened={opened} onClose={handleClose} title="Voice Capture" size="lg">
			<Stack>
				<Text size="sm" c="dimmed">
					Record yourself describing the games you want to add. The audio will be transcribed and
					you can review or edit the text before submitting.
				</Text>

				{!hasTranscription ? (
					<Stack align="center" gap="md" py="xl">
						<Text size="xl" fw={600} ff="monospace">
							{formatDuration(secondsElapsed)}
						</Text>

						<Text size="sm" c="dimmed">
							{isRecording
								? `Recording... (max ${MAX_DURATION_SECONDS}s)`
								: "Tap the mic to start recording"}
						</Text>

						<ActionIcon
							size={80}
							radius="xl"
							variant="filled"
							color={isRecording ? "red" : "blue"}
							onClick={isRecording ? stopRecording : startRecording}
							loading={transcribeMutation.isPending}
							disabled={transcribeMutation.isPending}
						>
							{isRecording ? <IconPlayerStop size={36} /> : <IconMicrophone size={36} />}
						</ActionIcon>

						<Text size="xs" c="dimmed">
							{isRecording ? "Tap to stop" : "Tap to record"}
						</Text>
					</Stack>
				) : (
					<Stack>
						<Group gap="xs">
							<Text size="sm" fw={600}>
								Transcription ready
							</Text>
						</Group>

						<Text size="xs" c="dimmed">
							Review and edit the text below, then submit to extract your games.
						</Text>

						<Textarea
							value={transcribedText}
							onChange={(e) => setTranscribedText(e.currentTarget.value)}
							autosize
							minRows={4}
							maxRows={10}
						/>

						<Group grow>
							<Button
								variant="default"
								onClick={handleRecordAgain}
								leftSection={<IconMicrophone size={16} />}
							>
								Record Again
							</Button>
							<Button
								onClick={handleSubmit}
								loading={submitMutation.isPending}
								disabled={transcribedText.trim().length < 3}
							>
								Submit
							</Button>
						</Group>
					</Stack>
				)}
			</Stack>
		</Modal>
	);
}
