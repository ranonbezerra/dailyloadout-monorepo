import { Box, Loader, Modal, Stack, Text } from "@mantine/core";
import { IconBrain } from "@tabler/icons-react";

interface AiBriefingOverlayProps {
	opened: boolean;
	gameTitle?: string;
}

const shimmerKeyframes = `
@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}
`;

export function AiBriefingOverlay({ opened, gameTitle }: AiBriefingOverlayProps) {
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
			{/* biome-ignore lint/security/noDangerouslySetInnerHtml: keyframe injection */}
			<style dangerouslySetInnerHTML={{ __html: shimmerKeyframes }} />

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
						AI is preparing your briefing
					</Text>
					<Text size="sm" c="dimmed" ta="center">
						{gameTitle
							? `Analyzing your previous sessions in ${gameTitle} to craft a personalized briefing.`
							: "Analyzing your previous sessions to craft a personalized briefing."}
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
			</Stack>
		</Modal>
	);
}
