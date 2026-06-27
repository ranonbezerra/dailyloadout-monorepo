import {
	ActionIcon,
	Badge,
	Button,
	Card,
	Center,
	Drawer,
	Group,
	Loader,
	Pagination,
	SegmentedControl,
	Stack,
	Table,
	Text,
	TextInput,
	Title,
	Tooltip,
} from "@mantine/core";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
	IconBan,
	IconCheck,
	IconMailCheck,
	IconSearchOff,
	IconUserCheck,
	IconUserSearch,
} from "@tabler/icons-react";
import { useState } from "react";
import { useUser, useUserActions, useUsers } from "../../hooks/useBackoffice";
import type { AdminUserSummary } from "../../types/backoffice";
import { relativeTime } from "./shared";

const PAGE_SIZE = 20;
type Filter = "all" | "banned" | "unverified";

function StatusBadges({ user }: { user: { isBanned: boolean; emailVerified: boolean } }) {
	return (
		<Group gap={6}>
			{user.isBanned && (
				<Badge color="red" variant="light" radius="sm" size="sm">
					banned
				</Badge>
			)}
			{!user.emailVerified && (
				<Badge color="yellow" variant="light" radius="sm" size="sm">
					unverified
				</Badge>
			)}
			{!user.isBanned && user.emailVerified && (
				<Badge color="green" variant="light" radius="sm" size="sm">
					active
				</Badge>
			)}
		</Group>
	);
}

export function UsersPage() {
	const [search, setSearch] = useState("");
	const [debounced] = useDebouncedValue(search, 300);
	const [filter, setFilter] = useState<Filter>("all");
	const [page, setPage] = useState(1);
	const [selected, setSelected] = useState<string | null>(null);
	const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);

	const { data, isLoading, isError } = useUsers({
		q: debounced || undefined,
		banned: filter === "banned" ? true : undefined,
		verified: filter === "unverified" ? false : undefined,
		limit: PAGE_SIZE,
		offset: (page - 1) * PAGE_SIZE,
	});

	const openUser = (publicId: string) => {
		setSelected(publicId);
		openDrawer();
	};

	const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Users</Title>
				<Text c="dimmed" size="sm">
					Search, inspect, and moderate accounts.
				</Text>
			</div>

			<Group justify="space-between" wrap="wrap">
				<TextInput
					placeholder="Search email or name…"
					leftSection={<IconUserSearch size={16} />}
					value={search}
					onChange={(e) => {
						setSearch(e.currentTarget.value);
						setPage(1);
					}}
					w={{ base: "100%", sm: 320 }}
				/>
				<SegmentedControl
					color="violet"
					value={filter}
					onChange={(v) => {
						setFilter(v as Filter);
						setPage(1);
					}}
					data={[
						{ label: "All", value: "all" },
						{ label: "Banned", value: "banned" },
						{ label: "Unverified", value: "unverified" },
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
						<Text c="red">Failed to load users.</Text>
					</Center>
				) : !data || data.items.length === 0 ? (
					<Center py="xl">
						<Stack align="center" gap={4}>
							<IconSearchOff size={28} color="var(--mantine-color-dimmed)" />
							<Text c="dimmed">No users match.</Text>
						</Stack>
					</Center>
				) : (
					<Table.ScrollContainer minWidth={640}>
						<Table verticalSpacing="sm" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>User</Table.Th>
									<Table.Th>Status</Table.Th>
									<Table.Th>Joined</Table.Th>
									<Table.Th />
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{data.items.map((u) => (
									<Table.Tr
										key={u.publicId}
										style={{ cursor: "pointer" }}
										onClick={() => openUser(u.publicId)}
									>
										<Table.Td>
											<Text fw={600} size="sm">
												{u.displayName}
											</Text>
											<Text size="xs" c="dimmed">
												{u.email}
											</Text>
										</Table.Td>
										<Table.Td>
											<StatusBadges user={u} />
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{relativeTime(u.createdAt)}
											</Text>
										</Table.Td>
										<Table.Td onClick={(e) => e.stopPropagation()}>
											<RowActions user={u} />
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
						{data.total} users
					</Text>
					<Pagination color="violet" value={page} onChange={setPage} total={totalPages} />
				</Group>
			)}

			<Drawer
				opened={drawerOpened}
				onClose={closeDrawer}
				position="right"
				title="User detail"
				size="md"
			>
				{selected && <UserDetail publicId={selected} />}
			</Drawer>
		</Stack>
	);
}

function RowActions({ user }: { user: AdminUserSummary }) {
	const { ban, unban, verify } = useUserActions();
	const notify = (msg: string) => notifications.show({ message: msg, color: "violet" });

	return (
		<Group gap={4} justify="flex-end" wrap="nowrap">
			{!user.emailVerified && (
				<Tooltip label="Force-verify email">
					<ActionIcon
						variant="subtle"
						color="blue"
						loading={verify.isPending}
						onClick={() => verify.mutate(user.publicId, { onSuccess: () => notify("Verified") })}
						aria-label="Verify"
					>
						<IconMailCheck size={18} />
					</ActionIcon>
				</Tooltip>
			)}
			{user.isBanned ? (
				<Tooltip label="Unban">
					<ActionIcon
						variant="subtle"
						color="green"
						loading={unban.isPending}
						onClick={() => unban.mutate(user.publicId, { onSuccess: () => notify("Unbanned") })}
						aria-label="Unban"
					>
						<IconUserCheck size={18} />
					</ActionIcon>
				</Tooltip>
			) : (
				<Tooltip label="Ban">
					<ActionIcon
						variant="subtle"
						color="red"
						loading={ban.isPending}
						onClick={() =>
							ban.mutate(
								{ publicId: user.publicId },
								{
									onSuccess: () => notify("Banned"),
									onError: (e) =>
										notifications.show({ message: (e as Error).message, color: "red" }),
								},
							)
						}
						aria-label="Ban"
					>
						<IconBan size={18} />
					</ActionIcon>
				</Tooltip>
			)}
		</Group>
	);
}

function UserDetail({ publicId }: { publicId: string }) {
	const { data, isLoading } = useUser(publicId);

	if (isLoading || !data) {
		return (
			<Center py="xl">
				<Loader color="violet" />
			</Center>
		);
	}

	const rows: [string, string][] = [
		["Email", data.email],
		["Name", data.displayName],
		["Locale", data.locale],
		["Timezone", data.timezone],
		["Sign-in", data.hasPassword ? "Password" : "Social only"],
		["Active sessions", String(data.activeSessions)],
		["Joined", new Date(data.createdAt).toLocaleString()],
	];

	return (
		<Stack gap="md">
			<Group gap="xs">
				<StatusBadges user={data} />
				{data.isAdmin && (
					<Badge color="violet" variant="filled" radius="sm" size="sm">
						admin
					</Badge>
				)}
			</Group>

			<Table withRowBorders={false} verticalSpacing={6}>
				<Table.Tbody>
					{rows.map(([k, v]) => (
						<Table.Tr key={k}>
							<Table.Td>
								<Text size="sm" c="dimmed">
									{k}
								</Text>
							</Table.Td>
							<Table.Td>
								<Text size="sm">{v}</Text>
							</Table.Td>
						</Table.Tr>
					))}
				</Table.Tbody>
			</Table>

			<DetailActions user={data} />
		</Stack>
	);
}

function DetailActions({ user }: { user: AdminUserSummary & { isAdmin: boolean } }) {
	const { ban, unban, verify } = useUserActions();
	const notify = (msg: string, color = "violet") => notifications.show({ message: msg, color });

	if (user.isAdmin) {
		return (
			<Text size="xs" c="dimmed">
				Admins can't be moderated here — revoke the admin grant first.
			</Text>
		);
	}

	return (
		<Group>
			{!user.emailVerified && (
				<Button
					size="xs"
					variant="light"
					color="blue"
					leftSection={<IconCheck size={14} />}
					loading={verify.isPending}
					onClick={() => verify.mutate(user.publicId, { onSuccess: () => notify("Verified") })}
				>
					Verify email
				</Button>
			)}
			{user.isBanned ? (
				<Button
					size="xs"
					variant="light"
					color="green"
					loading={unban.isPending}
					onClick={() => unban.mutate(user.publicId, { onSuccess: () => notify("Unbanned") })}
				>
					Unban
				</Button>
			) : (
				<Button
					size="xs"
					variant="light"
					color="red"
					leftSection={<IconBan size={14} />}
					loading={ban.isPending}
					onClick={() =>
						ban.mutate(
							{ publicId: user.publicId },
							{
								onSuccess: () => notify("Banned"),
								onError: (e) => notify((e as Error).message, "red"),
							},
						)
					}
				>
					Ban user
				</Button>
			)}
		</Group>
	);
}
