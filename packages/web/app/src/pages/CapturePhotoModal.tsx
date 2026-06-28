import { Button, Group, Image, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCamera, IconPhoto, IconRefresh } from "@tabler/icons-react";
import { useRef, useState } from "react";
import { useSubmitPhotoCapture } from "../hooks/useCapture";

interface CapturePhotoModalProps {
	opened: boolean;
	onClose: () => void;
	onSuccess: (capturePublicId: string) => void;
}

export function CapturePhotoModal({ opened, onClose, onSuccess }: CapturePhotoModalProps) {
	const [selectedFile, setSelectedFile] = useState<File | null>(null);
	const [previewUrl, setPreviewUrl] = useState<string | null>(null);

	const fileInputRef = useRef<HTMLInputElement | null>(null);
	const cameraInputRef = useRef<HTMLInputElement | null>(null);

	const submitMutation = useSubmitPhotoCapture();

	const handleFileChange = (file: File | null) => {
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
		}

		if (file) {
			setSelectedFile(file);
			setPreviewUrl(URL.createObjectURL(file));
		} else {
			setSelectedFile(null);
			setPreviewUrl(null);
		}
	};

	const resetState = () => {
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
		}
		setSelectedFile(null);
		setPreviewUrl(null);
	};

	const handleClose = () => {
		resetState();
		onClose();
	};

	const handleSubmit = async () => {
		if (!selectedFile) return;

		try {
			const capture = await submitMutation.mutateAsync(selectedFile);
			notifications.show({
				title: "Photo capture submitted",
				message: `Found ${capture.candidates.length} candidate(s). Review them now.`,
				color: "green",
			});
			resetState();
			onSuccess(capture.publicId);
		} catch (err) {
			notifications.show({
				title: "Photo capture failed",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Modal opened={opened} onClose={handleClose} title="Photo Capture" size="lg">
			<Stack>
				<Text size="sm" c="dimmed">
					Take a photo of a game cover or your shelf, or choose an image from your gallery. The AI
					will analyze the image to extract game titles.
				</Text>

				{/* Hidden file inputs */}
				<input
					ref={fileInputRef}
					type="file"
					accept="image/*"
					style={{ display: "none" }}
					onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
				/>
				<input
					ref={cameraInputRef}
					type="file"
					accept="image/*"
					capture="environment"
					style={{ display: "none" }}
					onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
				/>

				{previewUrl ? (
					<Stack>
						<Image
							src={previewUrl}
							alt="Selected image preview"
							radius="sm"
							mah={400}
							fit="contain"
						/>

						<Text size="xs" c="dimmed" ta="center">
							{selectedFile?.name}
						</Text>

						<Group grow>
							<Button
								variant="default"
								onClick={resetState}
								leftSection={<IconRefresh size={16} />}
							>
								Choose Different Image
							</Button>
							<Button
								onClick={handleSubmit}
								loading={submitMutation.isPending}
								disabled={!selectedFile}
							>
								Submit
							</Button>
						</Group>
					</Stack>
				) : (
					<Stack align="center" gap="md" py="xl">
						<Group grow w="100%">
							<Button
								variant="default"
								size="lg"
								leftSection={<IconPhoto size={20} />}
								onClick={() => fileInputRef.current?.click()}
							>
								Choose File
							</Button>
							<Button
								variant="default"
								size="lg"
								leftSection={<IconCamera size={20} />}
								onClick={() => cameraInputRef.current?.click()}
							>
								Take Photo
							</Button>
						</Group>

						<Text size="xs" c="dimmed">
							Supports JPG, PNG, WebP, and other image formats
						</Text>
					</Stack>
				)}
			</Stack>
		</Modal>
	);
}
