import {
	ActionIcon,
	Badge,
	Button,
	Card,
	Center,
	Drawer,
	Group,
	Loader,
	Modal,
	Pagination,
	Select,
	SimpleGrid,
	Stack,
	Table,
	Text,
	TextInput,
	Title,
	Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
	IconEye,
	IconPlayerStopFilled,
	IconSearch,
	IconSearchOff,
	IconTargetArrow,
} from "@tabler/icons-react";
import { useState } from "react";
import { usePlaySession, usePlaySessionActions, usePlaySessions } from "../hooks/useBackoffice";
import type { AdminPlaySessionSummary, PlaySessionStatus } from "../types/backoffice";
import { relativeTime } from "./shared";

const PAGE_SIZE = 20;
const STATUSES: PlaySessionStatus[] = ["active", "ended"];
const STATUS_COLOR: Record<string, string> = { active: "green", ended: "gray" };

function notify(msg: string, color = "violet") {
	notifications.show({ message: msg, color });
}

function StatusBadge({ status }: { status: string }) {
	return (
		<Badge color={STATUS_COLOR[status] ?? "gray"} variant="light" radius="sm" size="sm">
			{status}
		</Badge>
	);
}

function PlaySessionStat({ label, value }: { label: string; value: number }) {
	return (
		<Card padding="md">
			<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
				{label}
			</Text>
			<Text fz={28} fw={800} lh={1.2}>
				{value}
			</Text>
		</Card>
	);
}

export function PlaySessionsPage() {
	const [search, setSearch] = useState("");
	const [debounced] = useDebouncedValue(search, 300);
	const [status, setStatus] = useState<string | null>(null);
	const [page, setPage] = useState(1);
	const [viewing, setViewing] = useState<string | null>(null);
	const [clamping, setClamping] = useState<AdminPlaySessionSummary | null>(null);

	const { data, isLoading, isError } = usePlaySessions({
		q: debounced || undefined,
		status: (status as PlaySessionStatus) ?? undefined,
		limit: PAGE_SIZE,
		offset: (page - 1) * PAGE_SIZE,
	});

	const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
	const tallies = data?.statusCounts ?? [];

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Sessions</Title>
				<Text c="dimmed" size="sm">
					Browse sessions across all users and force-clamp stuck ones.
				</Text>
			</div>

			{tallies.length > 0 && (
				<SimpleGrid cols={{ base: 2, xs: tallies.length }}>
					{tallies.map((t) => (
						<PlaySessionStat key={t.status} label={t.status} value={t.count} />
					))}
				</SimpleGrid>
			)}

			<Group justify="space-between" wrap="wrap">
				<TextInput
					placeholder="Search by owner email…"
					leftSection={<IconSearch size={16} />}
					value={search}
					onChange={(e) => {
						setSearch(e.currentTarget.value);
						setPage(1);
					}}
					w={{ base: "100%", sm: 320 }}
				/>
				<Select
					placeholder="All statuses"
					clearable
					value={status}
					onChange={(v) => {
						setStatus(v);
						setPage(1);
					}}
					data={STATUSES.map((s) => ({ value: s, label: s }))}
					w={{ base: "100%", sm: 220 }}
				/>
			</Group>

			<Card padding={0}>
				{isLoading ? (
					<Center py="xl">
						<Loader color="violet" />
					</Center>
				) : isError ? (
					<Center py="xl">
						<Text c="red">Failed to load sessions.</Text>
					</Center>
				) : !data || data.items.length === 0 ? (
					<Center py="xl">
						<Stack align="center" gap={4}>
							<IconSearchOff size={28} color="var(--mantine-color-dimmed)" />
							<Text c="dimmed">No sessions match.</Text>
						</Stack>
					</Center>
				) : (
					<Table.ScrollContainer minWidth={720}>
						<Table verticalSpacing="sm" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>Owner</Table.Th>
									<Table.Th>Game</Table.Th>
									<Table.Th>Status</Table.Th>
									<Table.Th>Started</Table.Th>
									<Table.Th />
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{data.items.map((m) => (
									<Table.Tr key={m.publicId}>
										<Table.Td>
											<Group gap="sm" wrap="nowrap">
												<IconTargetArrow size={18} color="var(--mantine-color-dimmed)" />
												<Text size="sm" lineClamp={1}>
													{m.userEmail ?? "—"}
												</Text>
											</Group>
										</Table.Td>
										<Table.Td>
											<Text size="sm" lineClamp={1}>
												{m.gameTitle ?? "—"}
											</Text>
										</Table.Td>
										<Table.Td>
											<StatusBadge status={m.status} />
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{relativeTime(m.startedAt)}
											</Text>
										</Table.Td>
										<Table.Td>
											<RowActions
												playSession={m}
												onView={() => setViewing(m.publicId)}
												onClamp={() => setClamping(m)}
											/>
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>
					</Table.ScrollContainer>
				)}
			</Card>

			{data && data.total > PAGE_SIZE && (
				<Group justify="space-between">
					<Text size="xs" c="dimmed">
						{data.total} playSessions
					</Text>
					<Pagination color="violet" value={page} onChange={setPage} total={totalPages} />
				</Group>
			)}

			<PlaySessionDrawer publicId={viewing} onClose={() => setViewing(null)} />
			<ClampModal playSession={clamping} onClose={() => setClamping(null)} />
		</Stack>
	);
}

function RowActions({
	playSession,
	onView,
	onClamp,
}: {
	playSession: AdminPlaySessionSummary;
	onView: () => void;
	onClamp: () => void;
}) {
	return (
		<Group gap={4} justify="flex-end" wrap="nowrap">
			<Tooltip label="View detail">
				<ActionIcon variant="subtle" color="violet" onClick={onView} aria-label="View">
					<IconEye size={18} />
				</ActionIcon>
			</Tooltip>
			{playSession.status === "active" && (
				<Tooltip label="Force-clamp (end now)">
					<ActionIcon
						variant="subtle"
						color="orange"
						onClick={onClamp}
						aria-label="Clamp playSession"
					>
						<IconPlayerStopFilled size={18} />
					</ActionIcon>
				</Tooltip>
			)}
		</Group>
	);
}

function PlaySessionDrawer({
	publicId,
	onClose,
}: {
	publicId: string | null;
	onClose: () => void;
}) {
	const { data, isLoading } = usePlaySession(publicId);

	return (
		<Drawer
			opened={!!publicId}
			onClose={onClose}
			position="right"
			size="md"
			title="PlaySession detail"
		>
			{isLoading || !data ? (
				<Center py="xl">
					<Loader color="violet" />
				</Center>
			) : (
				<Stack gap="md">
					<Group justify="space-between">
						<StatusBadge status={data.status} />
						<Badge variant="outline" color="gray" radius="sm" size="sm">
							{data.playSessionType}
						</Badge>
					</Group>
					<Field label="Owner" value={data.userEmail ?? "—"} />
					<Field label="Game" value={data.gameTitle ?? "—"} />
					<Field label="Platform" value={data.platformLabel ?? "—"} />
					{data.endedVia && <Field label="Ended via" value={data.endedVia} />}
					{data.recapText && <Field label="Recap" value={data.recapText} />}
					{data.wrapUpText && <Field label="WrapUp" value={data.wrapUpText} />}
					<Field label="WrapUp extracted" value={data.hasExtractedState ? "yes" : "no"} />
				</Stack>
			)}
		</Drawer>
	);
}

function Field({ label, value }: { label: string; value: string }) {
	return (
		<div>
			<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
				{label}
			</Text>
			<Text size="sm">{value}</Text>
		</div>
	);
}

function ClampModal({
	playSession,
	onClose,
}: {
	playSession: AdminPlaySessionSummary | null;
	onClose: () => void;
}) {
	const { clamp } = usePlaySessionActions();

	return (
		<Modal opened={!!playSession} onClose={onClose} title="Force-clamp playSession" centered>
			<Stack>
				<Text size="sm">
					End this active playSession now? It will be closed with <code>admin_clamp</code> and the
					owner's stats recomputed.
				</Text>
				{playSession && (
					<Text size="sm" c="dimmed">
						{playSession.userEmail ?? "—"} · {playSession.gameTitle ?? "—"}
					</Text>
				)}
				<Group justify="flex-end">
					<Button variant="default" onClick={onClose}>
						Cancel
					</Button>
					<Button
						color="orange"
						loading={clamp.isPending}
						onClick={() => {
							if (!playSession) return;
							clamp.mutate(playSession.publicId, {
								onSuccess: () => {
									notify("PlaySession clamped", "orange");
									onClose();
								},
								onError: (e) => notify((e as Error).message, "red"),
							});
						}}
					>
						Clamp
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}
