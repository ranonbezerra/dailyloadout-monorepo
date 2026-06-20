import { Badge, Button, Card, Group, Stack, Text, Title } from "@mantine/core";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { DataTable } from "mantine-datatable";
import { useState } from "react";
import { useActiveMission, useMissions } from "../hooks/useMission";
import type { Mission, MissionListItem } from "../types/mission";
import { MissionBriefingModal } from "./MissionBriefingModal";
import { MissionDebriefModal } from "./MissionDebriefModal";

dayjs.extend(relativeTime);

const ENDED_VIA_LABELS: Record<string, { label: string; color: string }> = {
	debrief_completed: { label: "Debriefed", color: "green" },
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

export function MissionsPage() {
	const { data, isLoading } = useMissions({ limit: 50 });
	const { data: activeMission } = useActiveMission();
	const missions = data?.items ?? [];

	const [briefingMission, setBriefingMission] = useState<Mission | null>(null);
	const [debriefMission, setDebriefMission] = useState<Mission | null>(null);

	return (
		<Stack>
			<Group justify="space-between">
				<Title order={2}>Mission Timeline</Title>
				{data && (
					<Text c="dimmed" size="sm">
						{data.total} mission{data.total !== 1 ? "s" : ""} total
					</Text>
				)}
			</Group>

			{!isLoading && missions.length === 0 ? (
				<Card withBorder p="xl">
					<Text c="dimmed" ta="center">
						No missions yet. Start a mission from a game in your library.
					</Text>
				</Card>
			) : (
				<DataTable
					fetching={isLoading}
					records={missions}
					idAccessor="publicId"
					columns={[
						{
							accessor: "libraryEntry.game.title",
							title: "Game",
							render: (mission: MissionListItem) => (
								<Text fw={500}>{mission.libraryEntry.game.title}</Text>
							),
						},
						{
							accessor: "libraryEntry.platform.label",
							title: "Platform",
							render: (mission: MissionListItem) => (
								<Text size="sm">{mission.libraryEntry.platform.label}</Text>
							),
						},
						{
							accessor: "endedVia",
							title: "Status",
							render: (mission: MissionListItem) => getEndedViaBadge(mission.endedVia),
						},
						{
							accessor: "duration",
							title: "Duration",
							render: (mission: MissionListItem) => (
								<Text size="sm">{formatDuration(mission.startedAt, mission.endedAt)}</Text>
							),
						},
						{
							accessor: "startedAt",
							title: "Started",
							render: (mission: MissionListItem) => (
								<Text size="xs" c="dimmed">
									{dayjs(mission.startedAt).format("MMM D, YYYY h:mm A")}
								</Text>
							),
						},
						{
							accessor: "actions",
							title: "",
							render: (mission: MissionListItem) => {
								if (mission.endedVia !== null) return null;
								return (
									<Group gap="xs" wrap="nowrap">
										{activeMission?.briefingText && (
											<Button
												size="xs"
												variant="light"
												onClick={() => setBriefingMission(activeMission)}
											>
												Briefing
											</Button>
										)}
										<Button
											size="xs"
											color="teal"
											onClick={() => {
												if (activeMission) setDebriefMission(activeMission);
											}}
										>
											End mission
										</Button>
									</Group>
								);
							},
						},
					]}
				/>
			)}

			{briefingMission && (
				<MissionBriefingModal
					mode="view"
					mission={briefingMission}
					onClose={() => setBriefingMission(null)}
					onMissionUpdated={(updated) => setBriefingMission(updated)}
				/>
			)}
			<MissionDebriefModal mission={debriefMission} onClose={() => setDebriefMission(null)} />
		</Stack>
	);
}
