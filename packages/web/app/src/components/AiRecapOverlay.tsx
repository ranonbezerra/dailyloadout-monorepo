import { Box, Button, Loader, Modal, Stack, Text } from "@mantine/core";
import { IconBrain } from "@tabler/icons-react";

interface AiRecapOverlayProps {
	opened: boolean;
	gameTitle?: string;
	/** When set, the overlay describes a slower web-researched (deep) recap. */
	deep?: boolean;
	/** When set, a Cancel button is shown that aborts the in-flight request. */
	onCancel?: () => void;
}

export function AiRecapOverlay({ opened, gameTitle, deep, onCancel }: AiRecapOverlayProps) {
	return (
		<Modal
			opened={opened}
			onClose={() => {}}
			withCloseButton={false}
			closeOnClickOutside={false}
			closeOnEscape={false}
			centered
			size="sm"
			overlayProps={{ backgroundOpacity: 0.6, blur: 2 }}
			styles={{
				content: {
					backgroundColor: "var(--mantine-color-dark-7)",
					border: "1px solid var(--mantine-color-dark-4)",
				},
			}}
		>
			<Stack align="center" gap="lg" py="md">
				{/* Spinner with brain icon */}
				<Box
					pos="relative"
					style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
				>
					<Loader size={56} color="teal" type="oval" />
					<Box
						pos="absolute"
						style={{
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							width: 32,
							height: 32,
							borderRadius: "50%",
							backgroundColor: "var(--mantine-color-teal-9)",
						}}
					>
						<IconBrain size={18} color="var(--mantine-color-teal-4)" />
					</Box>
				</Box>

				{/* Text */}
				<Stack align="center" gap={4}>
					<Text fw={600} size="sm">
						{deep ? "Researching the web for your recap" : "Preparing your recap"}
					</Text>
					<Text size="sm" c="dimmed" ta="center">
						{deep
							? `Searching the web and your past sessions${gameTitle ? ` in ${gameTitle}` : ""} for spoiler-free next steps. This can take up to a minute.`
							: gameTitle
								? `Analyzing your previous sessions in ${gameTitle} to craft a personalized recap.`
								: "Analyzing your previous sessions to craft a personalized recap."}
					</Text>
				</Stack>

				{/* Shimmer progress bar */}
				<Box
					w="100%"
					h={4}
					style={{
						borderRadius: "var(--mantine-radius-xl)",
						backgroundColor: "var(--mantine-color-teal-9)",
						overflow: "hidden",
					}}
				>
					<Box
						h="100%"
						w="50%"
						style={{
							borderRadius: "var(--mantine-radius-xl)",
							backgroundColor: "var(--mantine-color-teal-5)",
							animation: "shimmer 1.5s ease-in-out infinite",
						}}
					/>
				</Box>

				{onCancel && (
					<Button variant="subtle" color="gray" size="xs" onClick={onCancel}>
						Cancel
					</Button>
				)}
			</Stack>
		</Modal>
	);
}
