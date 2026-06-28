import {
	ActionIcon,
	Badge,
	Button,
	Card,
	Center,
	Code,
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
	IconCamera,
	IconEye,
	IconRefresh,
	IconSearch,
	IconSearchOff,
	IconTrash,
} from "@tabler/icons-react";
import { useState } from "react";
import { useCapture, useCaptureActions, useCaptures } from "../hooks/useBackoffice";
import type { AdminCaptureSummary } from "../types/backoffice";
import { relativeTime } from "./shared";

const PAGE_SIZE = 20;

// The capture lifecycle (mirrors the API's CaptureStatus literal).
const STATUSES = [
	"queued",
	"processing",
	"review",
	"committed",
	"partially_committed",
	"failed",
	"cancelled",
] as const;

const STATUS_COLOR: Record<string, string> = {
	queued: "gray",
	processing: "blue",
	review: "yellow",
	committed: "green",
	partially_committed: "teal",
	failed: "red",
	cancelled: "gray",
};

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

function CaptureStat({ label, value }: { label: string; value: number }) {
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

export function CapturesPage() {
	const [search, setSearch] = useState("");
	const [debounced] = useDebouncedValue(search, 300);
	const [status, setStatus] = useState<string | null>(null);
	const [page, setPage] = useState(1);
	const [viewing, setViewing] = useState<string | null>(null);
	const [purging, setPurging] = useState<AdminCaptureSummary | null>(null);

	const { data, isLoading, isError } = useCaptures({
		q: debounced || undefined,
		status: status ?? undefined,
		limit: PAGE_SIZE,
		offset: (page - 1) * PAGE_SIZE,
	});

	const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
	const tallies = data?.statusCounts ?? [];

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Captures</Title>
				<Text c="dimmed" size="sm">
					Browse, reprocess, and purge captures across all users.
				</Text>
			</div>

			{tallies.length > 0 && (
				<SimpleGrid cols={{ base: 2, xs: 3, md: tallies.length > 4 ? 5 : tallies.length }}>
					{tallies.map((t) => (
						<CaptureStat key={t.status} label={t.status} value={t.count} />
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
						<Text c="red">Failed to load captures.</Text>
					</Center>
				) : !data || data.items.length === 0 ? (
					<Center py="xl">
						<Stack align="center" gap={4}>
							<IconSearchOff size={28} color="var(--mantine-color-dimmed)" />
							<Text c="dimmed">No captures match.</Text>
						</Stack>
					</Center>
				) : (
					<Table.ScrollContainer minWidth={720}>
						<Table verticalSpacing="sm" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>Owner</Table.Th>
									<Table.Th>Type</Table.Th>
									<Table.Th>Status</Table.Th>
									<Table.Th>Candidates</Table.Th>
									<Table.Th>Created</Table.Th>
									<Table.Th />
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{data.items.map((c) => (
									<Table.Tr key={c.publicId}>
										<Table.Td>
											<Group gap="sm" wrap="nowrap">
												<IconCamera size={18} color="var(--mantine-color-dimmed)" />
												<Text size="sm" lineClamp={1}>
													{c.userEmail ?? "—"}
												</Text>
											</Group>
										</Table.Td>
										<Table.Td>
											<Badge variant="outline" color="gray" radius="sm" size="sm">
												{c.inputType}
											</Badge>
										</Table.Td>
										<Table.Td>
											<StatusBadge status={c.status} />
										</Table.Td>
										<Table.Td>
											<Text size="sm">{c.candidateCount}</Text>
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{relativeTime(c.createdAt)}
											</Text>
										</Table.Td>
										<Table.Td>
											<RowActions
												onView={() => setViewing(c.publicId)}
												onPurge={() => setPurging(c)}
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
						{data.total} captures
					</Text>
					<Pagination color="violet" value={page} onChange={setPage} total={totalPages} />
				</Group>
			)}

			<CaptureDrawer publicId={viewing} onClose={() => setViewing(null)} />
			<PurgeModal capture={purging} onClose={() => setPurging(null)} />
		</Stack>
	);
}

function RowActions({ onView, onPurge }: { onView: () => void; onPurge: () => void }) {
	return (
		<Group gap={4} justify="flex-end" wrap="nowrap">
			<Tooltip label="View detail">
				<ActionIcon variant="subtle" color="violet" onClick={onView} aria-label="View">
					<IconEye size={18} />
				</ActionIcon>
			</Tooltip>
			<Tooltip label="Purge">
				<ActionIcon variant="subtle" color="red" onClick={onPurge} aria-label="Purge capture">
					<IconTrash size={18} />
				</ActionIcon>
			</Tooltip>
		</Group>
	);
}

function CaptureDrawer({ publicId, onClose }: { publicId: string | null; onClose: () => void }) {
	const { data, isLoading } = useCapture(publicId);
	const { reprocess } = useCaptureActions();

	return (
		<Drawer
			opened={!!publicId}
			onClose={onClose}
			position="right"
			size="md"
			title="Capture detail"
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
							{data.inputType}
						</Badge>
					</Group>
					<div>
						<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
							Owner
						</Text>
						<Text size="sm">{data.userEmail ?? "—"}</Text>
					</div>
					{data.errorMessage && (
						<div>
							<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
								Error
							</Text>
							<Text size="sm" c="red">
								{data.errorMessage}
							</Text>
						</div>
					)}
					{data.rawText && (
						<div>
							<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
								Raw text
							</Text>
							<Code block>{data.rawText}</Code>
						</div>
					)}
					<div>
						<Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={4}>
							Candidates ({data.candidates.length})
						</Text>
						<Stack gap={4}>
							{data.candidates.length === 0 ? (
								<Text size="sm" c="dimmed">
									None
								</Text>
							) : (
								data.candidates.map((cand) => (
									<Group key={cand.publicId} justify="space-between" wrap="nowrap">
										<Text size="sm" lineClamp={1}>
											{cand.title}
										</Text>
										<Badge variant="light" color="gray" radius="sm" size="xs">
											{cand.status}
										</Badge>
									</Group>
								))
							)}
						</Stack>
					</div>
					<Tooltip
						label="Only text captures can be reprocessed"
						disabled={data.reprocessable}
						withinPortal
					>
						<Button
							leftSection={<IconRefresh size={16} />}
							color="cyan"
							variant="light"
							disabled={!data.reprocessable}
							loading={reprocess.isPending}
							onClick={() =>
								reprocess.mutate(data.publicId, {
									onSuccess: () => notify("Capture reprocessed", "cyan"),
									onError: (e) => notify((e as Error).message, "red"),
								})
							}
						>
							Reprocess
						</Button>
					</Tooltip>
				</Stack>
			)}
		</Drawer>
	);
}

function PurgeModal({
	capture,
	onClose,
}: {
	capture: AdminCaptureSummary | null;
	onClose: () => void;
}) {
	const { purge } = useCaptureActions();

	return (
		<Modal opened={!!capture} onClose={onClose} title="Purge capture" centered>
			<Stack>
				<Text size="sm">
					Permanently delete this capture and its candidates? This cannot be undone.
				</Text>
				{capture && (
					<Text size="sm" c="dimmed">
						{capture.userEmail ?? "—"} · {capture.inputType} · {capture.status}
					</Text>
				)}
				<Group justify="flex-end">
					<Button variant="default" onClick={onClose}>
						Cancel
					</Button>
					<Button
						color="red"
						loading={purge.isPending}
						onClick={() => {
							if (!capture) return;
							purge.mutate(capture.publicId, {
								onSuccess: () => {
									notify("Capture purged", "red");
									onClose();
								},
								onError: (e) => notify((e as Error).message, "red"),
							});
						}}
					>
						Purge
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}
