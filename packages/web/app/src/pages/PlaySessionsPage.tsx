import { Badge, Card, Group, Stack, Text, Title } from "@mantine/core";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { DataTable } from "mantine-datatable";
import { ErrorState } from "../components/ErrorState";
import { usePlaySessions } from "../hooks/usePlaySession";
import type { PlaySessionListItem } from "../types/play-session";

dayjs.extend(relativeTime);

const ENDED_VIA_LABELS: Record<string, { label: string; color: string }> = {
	wrap_up_completed: { label: "Wrapped", color: "green" },
	paused_app: { label: "Paused", color: "yellow" },
	auto_clamp: { label: "Auto-closed", color: "gray" },
	retroactive: { label: "Retroactive", color: "grape" },
};

function getEndedViaBadge(endedVia: string | null) {
	if (!endedVia) {
		return <Badge color="blue">Active</Badge>;
	}
	const info = ENDED_VIA_LABELS[endedVia] ?? { label: endedVia, color: "gray" };
	return <Badge color={info.color}>{info.label}</Badge>;
}

function formatDuration(startedAt: string, endedAt: string | null): string {
	const start = dayjs(startedAt);
	const end = endedAt ? dayjs(endedAt) : dayjs();
	const diffMinutes = end.diff(start, "minute");

	if (diffMinutes < 60) return `${diffMinutes}m`;
	const hours = Math.floor(diffMinutes / 60);
	const mins = diffMinutes % 60;
	return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

export function PlaySessionsPage() {
	const { data, isLoading, isError, error, refetch } = usePlaySessions({ limit: 50 });
	const playSessions = data?.items ?? [];

	return (
		<Stack>
			<Group justify="space-between">
				<Title order={2}>Session history</Title>
				{data && (
					<Text c="dimmed" size="sm">
						{data.total} session{data.total !== 1 ? "s" : ""} total
					</Text>
				)}
			</Group>

			{isError ? (
				<ErrorState title="Couldn't load sessions" error={error} onRetry={() => refetch()} />
			) : !isLoading && playSessions.length === 0 ? (
				<Card withBorder p="xl">
					<Text c="dimmed" ta="center">
						No sessions yet. Start one from the Play page.
					</Text>
				</Card>
			) : (
				<DataTable
					fetching={isLoading}
					records={playSessions}
					idAccessor="publicId"
					columns={[
						{
							accessor: "libraryEntry.game.title",
							title: "Game",
							render: (playSession: PlaySessionListItem) => (
								<Text fw={500}>{playSession.libraryEntry.game.title}</Text>
							),
						},
						{
							accessor: "libraryEntry.platform.label",
							title: "Platform",
							render: (playSession: PlaySessionListItem) => (
								<Text size="sm">{playSession.libraryEntry.platform.label}</Text>
							),
						},
						{
							accessor: "endedVia",
							title: "Status",
							render: (playSession: PlaySessionListItem) => getEndedViaBadge(playSession.endedVia),
						},
						{
							accessor: "duration",
							title: "Duration",
							render: (playSession: PlaySessionListItem) => (
								<Text size="sm">{formatDuration(playSession.startedAt, playSession.endedAt)}</Text>
							),
						},
						{
							accessor: "startedAt",
							title: "Started",
							render: (playSession: PlaySessionListItem) => (
								<Text size="xs" c="dimmed">
									{dayjs(playSession.startedAt).format("MMM D, YYYY h:mm A")}
								</Text>
							),
						},
					]}
				/>
			)}
		</Stack>
	);
}
