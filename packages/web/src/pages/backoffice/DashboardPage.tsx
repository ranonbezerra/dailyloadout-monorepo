import {
	Alert,
	Badge,
	Card,
	Center,
	Group,
	Loader,
	SimpleGrid,
	Stack,
	Table,
	Text,
	ThemeIcon,
	Title,
} from "@mantine/core";
import type { Icon } from "@tabler/icons-react";
import {
	IconAlertTriangle,
	IconBan,
	IconDeviceGamepad2,
	IconMailExclamation,
	IconSettingsBolt,
	IconShieldCheck,
	IconUsers,
} from "@tabler/icons-react";
import { useDashboard } from "../../hooks/useBackoffice";
import { ActionLabel, relativeTime } from "./shared";

interface StatProps {
	label: string;
	value: number;
	icon: Icon;
	color: string;
	hint?: string;
}

function Stat({ label, value, icon: IconCmp, color, hint }: StatProps) {
	return (
		<Card padding="lg">
			<Group justify="space-between" align="flex-start">
				<Stack gap={2}>
					<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
						{label}
					</Text>
					<Text fz={32} fw={800} lh={1}>
						{value}
					</Text>
					{hint && (
						<Text size="xs" c="dimmed">
							{hint}
						</Text>
					)}
				</Stack>
				<ThemeIcon size={42} radius="md" variant="light" color={color}>
					<IconCmp size={22} />
				</ThemeIcon>
			</Group>
		</Card>
	);
}

export function DashboardPage() {
	const { data, isLoading, isError } = useDashboard();

	if (isLoading) {
		return (
			<Center py="xl">
				<Loader color="violet" />
			</Center>
		);
	}

	if (isError || !data) {
		return (
			<Alert color="red" icon={<IconAlertTriangle size={18} />} title="Couldn't load dashboard">
				The backoffice metrics endpoint failed to respond.
			</Alert>
		);
	}

	return (
		<Stack gap="lg">
			<div>
				<Title order={2}>Dashboard</Title>
				<Text c="dimmed" size="sm">
					Operational snapshot across the platform.
				</Text>
			</div>

			<SimpleGrid cols={{ base: 1, xs: 2, md: 4 }}>
				<Stat label="Users" value={data.usersTotal} icon={IconUsers} color="violet" />
				<Stat label="Banned" value={data.usersBanned} icon={IconBan} color="red" />
				<Stat
					label="Unverified"
					value={data.usersUnverified}
					icon={IconMailExclamation}
					color="yellow"
				/>
				<Stat label="Admins" value={data.admins} icon={IconShieldCheck} color="green" />
				<Stat
					label="Active missions"
					value={data.missionsActive}
					icon={IconDeviceGamepad2}
					color="coral"
				/>
				<Stat
					label="Catalogue"
					value={data.catalogueSize}
					icon={IconDeviceGamepad2}
					color="violet"
					hint="shared games"
				/>
				<Stat
					label="Config overrides"
					value={data.configOverrides}
					icon={IconSettingsBolt}
					color="violet"
					hint="of 9 knobs"
				/>
			</SimpleGrid>

			<Card padding="lg">
				<Group justify="space-between" mb="sm">
					<Title order={4}>Recent admin actions</Title>
					<Badge color="violet" variant="light" radius="sm">
						audit log
					</Badge>
				</Group>
				{data.recentActions.length === 0 ? (
					<Text c="dimmed" size="sm">
						No admin actions recorded yet.
					</Text>
				) : (
					<Table.ScrollContainer minWidth={520}>
						<Table verticalSpacing="xs" highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>Action</Table.Th>
									<Table.Th>By</Table.Th>
									<Table.Th>Target</Table.Th>
									<Table.Th>When</Table.Th>
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{data.recentActions.map((a) => (
									<Table.Tr key={`${a.createdAt}-${a.action}-${a.targetEmail ?? ""}`}>
										<Table.Td>
											<ActionLabel action={a.action} />
										</Table.Td>
										<Table.Td>
											<Text size="sm">{a.adminEmail ?? "—"}</Text>
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{a.targetEmail ?? a.detail ?? "—"}
											</Text>
										</Table.Td>
										<Table.Td>
											<Text size="sm" c="dimmed">
												{relativeTime(a.createdAt)}
											</Text>
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>
					</Table.ScrollContainer>
				)}
			</Card>
		</Stack>
	);
}
