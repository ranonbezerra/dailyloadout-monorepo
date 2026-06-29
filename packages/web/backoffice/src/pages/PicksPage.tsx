import {
	ActionIcon,
	Badge,
	Card,
	Center,
	Drawer,
	Group,
	Loader,
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
import { IconBolt, IconEye, IconSearch, IconSearchOff } from "@tabler/icons-react";
import { useState } from "react";
import { usePick, usePicks } from "../hooks/useBackoffice";
import type { PickAction } from "../types/backoffice";
import { relativeTime } from "./shared";

const PAGE_SIZE = 20;
const ACTIONS: PickAction[] = ["pending", "accepted", "rejected", "ignored"];
const ACTION_COLOR: Record<string, string> = {
	pending: "blue",
	accepted: "green",
	rejected: "red",
	ignored: "gray",
};

function ActionBadge({ action }: { action: string }) {
	return (
		<Badge color={ACTION_COLOR[action] ?? "gray"} variant="light" radius="sm" size="sm">
			{action}
		</Badge>
	);
}

function PickStat({ label, value }: { label: string; value: number }) {
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

export function PicksPage() {
	const [search, setSearch] = useState("");
	const [debounced] = useDebouncedValue(search, 300);
	const [action, setAction] = useState<string | null>(null);
	const [page, setPage] = useState(1);
	const [viewing, setViewing] = useState<string | null>(null);

	const { data, isLoading, isError } = usePicks({
		q: debounced || undefined,
		action: (action as PickAction) ?? undefined,
		limit: PAGE_SIZE,
		offset: (page - 1) * PAGE_SIZE,
	});

	const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
	const tallies = data?.actionCounts ?? [];

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Picks</Title>
				<Text c="dimmed" size="sm">
					Browse pick suggestions across all users (read-only).
				</Text>
			</div>

			{tallies.length > 0 && (
				<SimpleGrid cols={{ base: 2, xs: tallies.length > 4 ? 4 : tallies.length }}>
					{tallies.map((t) => (
						<PickStat key={t.action} label={t.action} value={t.count} />
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
					placeholder="All actions"
					clearable
					value={action}
					onChange={(v) => {
						setAction(v);
						setPage(1);
					}}
					data={ACTIONS.map((a) => ({ value: a, label: a }))}
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
						<Text c="red">Failed to load picks.</Text>
					</Center>
				) : !data || data.items.length === 0 ? (
					<Center py="xl">
						<Stack align="center" gap={4}>
							<IconSearchOff size={28} color="var(--mantine-color-dimmed)" />
							<Text c="dimmed">No picks match.</Text>
						</Stack>
					</Center>
				) : (
					<Table.ScrollContainer minWidth={760}>
						<Table verticalSpacing="sm" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>Owner</Table.Th>
									<Table.Th>Game</Table.Th>
									<Table.Th>Mood</Table.Th>
									<Table.Th>Action</Table.Th>
									<Table.Th>Created</Table.Th>
									<Table.Th />
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{data.items.map((l) => (
									<Table.Tr key={l.publicId}>
										<Table.Td>
											<Group gap="sm" wrap="nowrap">
												<IconBolt size={18} color="var(--mantine-color-dimmed)" />
												<Text size="sm" lineClamp={1}>
													{l.userEmail ?? "—"}
												</Text>
											</Group>
										</Table.Td>
										<Table.Td>
											<Text size="sm" lineClamp={1}>
												{l.gameTitle ?? "—"}
											</Text>
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{l.mood} · {l.availableMinutes}m
											</Text>
										</Table.Td>
										<Table.Td>
											<ActionBadge action={l.action} />
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{relativeTime(l.createdAt)}
											</Text>
										</Table.Td>
										<Table.Td>
											<Group justify="flex-end">
												<Tooltip label="View detail">
													<ActionIcon
														variant="subtle"
														color="violet"
														onClick={() => setViewing(l.publicId)}
														aria-label="View"
													>
														<IconEye size={18} />
													</ActionIcon>
												</Tooltip>
											</Group>
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
						{data.total} picks
					</Text>
					<Pagination color="violet" value={page} onChange={setPage} total={totalPages} />
				</Group>
			)}

			<PickDrawer publicId={viewing} onClose={() => setViewing(null)} />
		</Stack>
	);
}

function PickDrawer({ publicId, onClose }: { publicId: string | null; onClose: () => void }) {
	const { data, isLoading } = usePick(publicId);

	return (
		<Drawer opened={!!publicId} onClose={onClose} position="right" size="md" title="Pick detail">
			{isLoading || !data ? (
				<Center py="xl">
					<Loader color="violet" />
				</Center>
			) : (
				<Stack gap="md">
					<Group justify="space-between">
						<ActionBadge action={data.action} />
						{data.ledToPlaySession && (
							<Badge color="violet" variant="light" radius="sm" size="sm">
								led to session
							</Badge>
						)}
					</Group>
					<Field label="Owner" value={data.userEmail ?? "—"} />
					<Field label="Game" value={data.gameTitle ?? "—"} />
					<Field label="Platform" value={data.platformLabel ?? "—"} />
					<Field
						label="Inputs"
						value={`${data.mood} · ${data.mentalEnergy} energy · ${data.availableMinutes}m`}
					/>
					{data.context && <Field label="Context" value={data.context} />}
					{data.reasoning && <Field label="Reasoning" value={data.reasoning} />}
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
