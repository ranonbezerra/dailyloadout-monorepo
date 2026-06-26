import { Button, Card, Stack, Text } from "@mantine/core";
import { IconAlertTriangle, IconRefresh } from "@tabler/icons-react";

interface ErrorStateProps {
	title?: string;
	error?: unknown;
	onRetry: () => void;
}

/**
 * Inline error surface for failed list/detail queries, with a retry button.
 * Used instead of silently rendering an empty state when a fetch fails.
 */
export function ErrorState({ title = "Something went wrong", error, onRetry }: ErrorStateProps) {
	const message = error instanceof Error ? error.message : "Please try again.";
	return (
		<Card withBorder p="xl" radius="md">
			<Stack align="center" gap="sm">
				<IconAlertTriangle size={28} color="var(--mantine-color-red-6)" />
				<Text fw={600}>{title}</Text>
				<Text c="dimmed" size="sm" ta="center">
					{message}
				</Text>
				<Button variant="light" leftSection={<IconRefresh size={16} />} onClick={onRetry}>
					Retry
				</Button>
			</Stack>
		</Card>
	);
}
