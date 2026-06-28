import { Card, Modal, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { IconDeviceDesktop, IconPhoto } from "@tabler/icons-react";

interface ImageSourceModalProps {
	opened: boolean;
	onClose: () => void;
	/** A real photo of a shelf / covers — read by the vision model (~12 games). */
	onPhoto: () => void;
	/** A library list-view screenshot — OCR + catalog match (50–100 games). */
	onScreenshots: () => void;
}

/**
 * Disambiguates the two image-based add flows, which look similar but route to
 * very different pipelines (vision vs OCR). Asking up front avoids sending a
 * shelf photo through the screenshot path, or vice versa.
 */
export function ImageSourceModal({
	opened,
	onClose,
	onPhoto,
	onScreenshots,
}: ImageSourceModalProps) {
	const choose = (handler: () => void) => () => {
		onClose();
		handler();
	};

	return (
		<Modal opened={opened} onClose={onClose} title="Photo or screenshot?" centered size="lg">
			<SimpleGrid cols={{ base: 1, sm: 2 }}>
				<Card
					withBorder
					radius="md"
					p="lg"
					onClick={choose(onPhoto)}
					style={{ cursor: "pointer", height: "100%" }}
					data-testid="image-source-photo"
				>
					<Stack gap="sm" align="flex-start">
						<IconPhoto size={28} />
						<Title order={4}>Photo of my shelf</Title>
						<Text size="sm" c="dimmed">
							Snap your shelf or a few covers — we read up to ~12 games.
						</Text>
					</Stack>
				</Card>

				<Card
					withBorder
					radius="md"
					p="lg"
					onClick={choose(onScreenshots)}
					style={{ cursor: "pointer", height: "100%" }}
					data-testid="image-source-screenshots"
				>
					<Stack gap="sm" align="flex-start">
						<IconDeviceDesktop size={28} />
						<Title order={4}>Library screenshot</Title>
						<Text size="sm" c="dimmed">
							A list view from Steam, Xbox, PSN… — import 50–100 games at once.
						</Text>
					</Stack>
				</Card>
			</SimpleGrid>
		</Modal>
	);
}
