import {
	AppShell,
	Badge,
	Box,
	Burger,
	Button,
	Code,
	Group,
	NavLink,
	Stack,
	Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
	IconChartBar,
	IconExternalLink,
	IconHistory,
	IconLayoutDashboard,
	IconSettings,
	IconShieldLock,
	IconUsers,
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAdminMe } from "../../hooks/useBackoffice";

const NAV = [
	{ path: "/backoffice", label: "Dashboard", icon: IconLayoutDashboard, exact: true },
	{ path: "/backoffice/users", label: "Users", icon: IconUsers },
	{ path: "/backoffice/config", label: "Config", icon: IconSettings },
	{ path: "/backoffice/audit", label: "Audit log", icon: IconHistory },
];

/**
 * The backoffice chrome — deliberately distinct from the player app: a violet
 * accent (vs. the app's coral), a shield wordmark, and a persistent INTERNAL
 * badge so it always reads as an admin tool, not a user-facing screen.
 */
export function BackofficeShell({ children }: { children: ReactNode }) {
	const location = useLocation();
	const navigate = useNavigate();
	const [opened, { toggle, close }] = useDisclosure();
	const { data: me } = useAdminMe();

	const go = (path: string) => {
		navigate(path);
		close();
	};

	const isActive = (path: string, exact?: boolean) =>
		exact ? location.pathname === path : location.pathname.startsWith(path);

	return (
		<AppShell
			header={{ height: 56 }}
			navbar={{ width: 260, breakpoint: "sm", collapsed: { mobile: !opened } }}
			padding="md"
		>
			<AppShell.Header bg="dark.8">
				<Group h="100%" px="md" gap="sm" justify="space-between">
					<Group gap="sm">
						<Burger
							opened={opened}
							onClick={toggle}
							hiddenFrom="sm"
							size="sm"
							aria-label="Toggle navigation"
						/>
						<IconShieldLock size={22} color="var(--mantine-color-violet-4)" />
						<Group gap={6} align="baseline">
							<Text fw={800} ff="monospace" style={{ letterSpacing: "0.04em" }}>
								BACKOFFICE
							</Text>
							<Text size="xs" c="dimmed">
								DailyLoadout
							</Text>
						</Group>
						<Badge color="violet" variant="light" size="xs" radius="sm">
							INTERNAL
						</Badge>
					</Group>
					{me && (
						<Code c="dimmed" bg="dark.6" visibleFrom="xs">
							{me.email}
						</Code>
					)}
				</Group>
			</AppShell.Header>

			<AppShell.Navbar p="md" bg="dark.8">
				<Stack justify="space-between" h="100%">
					<Stack gap="xs">
						{NAV.map((item) => (
							<NavLink
								key={item.path}
								label={item.label}
								color="violet"
								variant="light"
								leftSection={<item.icon size={18} />}
								active={isActive(item.path, item.exact)}
								onClick={() => go(item.path)}
							/>
						))}
					</Stack>
					<Stack gap="xs">
						<Box>
							<Text size="xs" c="dimmed" mb={4}>
								Coming soon
							</Text>
							<NavLink
								label="Games"
								color="violet"
								leftSection={<IconChartBar size={18} />}
								disabled
							/>
						</Box>
						<Button
							variant="subtle"
							color="gray"
							leftSection={<IconExternalLink size={16} />}
							justify="flex-start"
							onClick={() => navigate("/play")}
						>
							Exit to app
						</Button>
					</Stack>
				</Stack>
			</AppShell.Navbar>

			<AppShell.Main>{children}</AppShell.Main>
		</AppShell>
	);
}
