import {
	ActionIcon,
	Avatar,
	Badge,
	Button,
	Card,
	Center,
	Group,
	Loader,
	Modal,
	Pagination,
	SegmentedControl,
	SimpleGrid,
	Stack,
	Table,
	Text,
	Textarea,
	TextInput,
	ThemeIcon,
	Title,
	Tooltip,
} from "@mantine/core";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
	IconArrowDown,
	IconArrowUp,
	IconDeviceGamepad2,
	IconEdit,
	IconSearchOff,
	IconUsers,
	IconWorld,
} from "@tabler/icons-react";
import { useState } from "react";
import { useGameActions, useGames } from "../hooks/useBackoffice";
import type { AdminGameSummary } from "../types/backoffice";
import { relativeTime } from "./shared";

const PAGE_SIZE = 20;
type SourceFilter = "all" | "igdb" | "manual";

function notify(msg: string, color = "violet") {
	notifications.show({ message: msg, color });
}

function CatalogueStat({ label, value }: { label: string; value: number }) {
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

export function GamesPage() {
	const [search, setSearch] = useState("");
	const [debounced] = useDebouncedValue(search, 300);
	const [source, setSource] = useState<SourceFilter>("all");
	const [page, setPage] = useState(1);
	const [editing, setEditing] = useState<AdminGameSummary | null>(null);

	const { data, isLoading, isError } = useGames({
		q: debounced || undefined,
		source: source === "all" ? undefined : source,
		limit: PAGE_SIZE,
		offset: (page - 1) * PAGE_SIZE,
	});

	const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Catalogue</Title>
				<Text c="dimmed" size="sm">
					Browse and moderate the shared game catalogue.
				</Text>
			</div>

			{data && (
				<SimpleGrid cols={{ base: 1, xs: 3 }}>
					<CatalogueStat label="Total games" value={data.catalogueTotal} />
					<CatalogueStat label="IGDB" value={data.catalogueIgdb} />
					<CatalogueStat label="Manual" value={data.catalogueManual} />
				</SimpleGrid>
			)}

			<Group justify="space-between" wrap="wrap">
				<TextInput
					placeholder="Search title or slug…"
					leftSection={<IconDeviceGamepad2 size={16} />}
					value={search}
					onChange={(e) => {
						setSearch(e.currentTarget.value);
						setPage(1);
					}}
					w={{ base: "100%", sm: 320 }}
				/>
				<SegmentedControl
					color="violet"
					value={source}
					onChange={(v) => {
						setSource(v as SourceFilter);
						setPage(1);
					}}
					data={[
						{ label: "All", value: "all" },
						{ label: "IGDB", value: "igdb" },
						{ label: "Manual", value: "manual" },
					]}
				/>
			</Group>

			<Card padding={0}>
				{isLoading ? (
					<Center py="xl">
						<Loader color="violet" />
					</Center>
				) : isError ? (
					<Center py="xl">
						<Text c="red">Failed to load the catalogue.</Text>
					</Center>
				) : !data || data.items.length === 0 ? (
					<Center py="xl">
						<Stack align="center" gap={4}>
							<IconSearchOff size={28} color="var(--mantine-color-dimmed)" />
							<Text c="dimmed">No games match.</Text>
						</Stack>
					</Center>
				) : (
					<Table.ScrollContainer minWidth={680}>
						<Table verticalSpacing="sm" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>Game</Table.Th>
									<Table.Th>Source</Table.Th>
									<Table.Th>Visibility</Table.Th>
									<Table.Th>Owners</Table.Th>
									<Table.Th>Added</Table.Th>
									<Table.Th />
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{data.items.map((g) => (
									<Table.Tr key={g.publicId}>
										<Table.Td>
											<Group gap="sm" wrap="nowrap">
												<Avatar src={g.coverUrl} size={36} radius="sm">
													<IconDeviceGamepad2 size={18} />
												</Avatar>
												<div>
													<Text fw={600} size="sm" lineClamp={1}>
														{g.title}
													</Text>
													<Text size="xs" c="dimmed" ff="monospace">
														{g.slug}
													</Text>
												</div>
											</Group>
										</Table.Td>
										<Table.Td>
											<Badge
												color={g.source === "igdb" ? "blue" : "grape"}
												variant="light"
												radius="sm"
												size="sm"
											>
												{g.source}
											</Badge>
										</Table.Td>
										<Table.Td>
											{g.isShared ? (
												<Badge color="green" variant="light" radius="sm" size="sm">
													shared
												</Badge>
											) : (
												<Badge color="gray" variant="light" radius="sm" size="sm">
													private
												</Badge>
											)}
										</Table.Td>
										<Table.Td>
											<Group gap={4}>
												<IconUsers size={14} color="var(--mantine-color-dimmed)" />
												<Text size="sm">{g.ownerCount}</Text>
											</Group>
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{relativeTime(g.createdAt)}
											</Text>
										</Table.Td>
										<Table.Td>
											<RowActions game={g} onEdit={() => setEditing(g)} />
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
						{data.total} games
					</Text>
					<Pagination color="violet" value={page} onChange={setPage} total={totalPages} />
				</Group>
			)}

			<EditGameModal game={editing} onClose={() => setEditing(null)} />
		</Stack>
	);
}

function RowActions({ game, onEdit }: { game: AdminGameSummary; onEdit: () => void }) {
	const { demote, promote } = useGameActions();

	return (
		<Group gap={4} justify="flex-end" wrap="nowrap">
			<Tooltip label="Edit metadata">
				<ActionIcon variant="subtle" color="violet" onClick={onEdit} aria-label="Edit">
					<IconEdit size={18} />
				</ActionIcon>
			</Tooltip>
			{game.isShared ? (
				<Tooltip label="Demote to private">
					<ActionIcon
						variant="subtle"
						color="orange"
						loading={demote.isPending}
						onClick={() =>
							demote.mutate(game.publicId, { onSuccess: () => notify("Demoted to private") })
						}
						aria-label="Demote"
					>
						<IconArrowDown size={18} />
					</ActionIcon>
				</Tooltip>
			) : (
				<Tooltip label="Promote to shared">
					<ActionIcon
						variant="subtle"
						color="green"
						loading={promote.isPending}
						onClick={() =>
							promote.mutate(game.publicId, { onSuccess: () => notify("Promoted to shared") })
						}
						aria-label="Promote"
					>
						<IconArrowUp size={18} />
					</ActionIcon>
				</Tooltip>
			)}
		</Group>
	);
}

function EditGameModal({ game, onClose }: { game: AdminGameSummary | null; onClose: () => void }) {
	const { edit } = useGameActions();
	const [opened, { open, close }] = useDisclosure(false);
	const [title, setTitle] = useState("");
	const [summary, setSummary] = useState("");
	const [current, setCurrent] = useState<string | null>(null);

	// Sync local fields when a new game is selected.
	if (game && game.publicId !== current) {
		setCurrent(game.publicId);
		setTitle(game.title);
		setSummary("");
		open();
	}

	const handleClose = () => {
		close();
		setCurrent(null);
		onClose();
	};

	const save = () => {
		if (!game) return;
		edit.mutate(
			{ publicId: game.publicId, edit: { title, summary: summary || undefined } },
			{
				onSuccess: () => {
					notify("Catalogue updated");
					handleClose();
				},
				onError: (e) => notify((e as Error).message, "red"),
			},
		);
	};

	return (
		<Modal opened={opened} onClose={handleClose} title="Edit game" centered>
			<Stack>
				<Group gap="sm">
					<ThemeIcon variant="light" color="violet" radius="sm">
						<IconWorld size={16} />
					</ThemeIcon>
					<Text size="sm" c="dimmed" ff="monospace">
						{game?.slug}
					</Text>
				</Group>
				<TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
				<Textarea
					label="Summary"
					placeholder="Leave blank to keep the current summary"
					autosize
					minRows={3}
					value={summary}
					onChange={(e) => setSummary(e.currentTarget.value)}
				/>
				<Group justify="flex-end">
					<Button variant="default" onClick={handleClose}>
						Cancel
					</Button>
					<Button color="violet" loading={edit.isPending} onClick={save}>
						Save
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}
