import { Anchor, Button, Center, Loader, Stack, Text, Title } from "@mantine/core";
import { IconLock } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useAdminMe } from "../../hooks/useBackoffice";

interface BackofficeGuardProps {
	children: ReactNode;
}

/**
 * Gate the backoffice on a successful `/internal/v1/me`. The outer
 * `ProtectedRoute` already guarantees an authenticated session; this adds the
 * admin check — a non-admin (or single-user mode) gets a 403 and a polite
 * "no access" screen rather than a broken panel.
 */
export function BackofficeGuard({ children }: BackofficeGuardProps) {
	const navigate = useNavigate();
	const { isLoading, isError } = useAdminMe();

	if (isLoading) {
		return (
			<Center h="100vh">
				<Loader size="lg" color="violet" />
			</Center>
		);
	}

	if (isError) {
		return (
			<Center h="100vh" px="md">
				<Stack align="center" gap="sm" maw={420}>
					<IconLock size={48} color="var(--mantine-color-violet-5)" />
					<Title order={3}>Backoffice access required</Title>
					<Text c="dimmed" ta="center">
						Your account doesn't have admin rights for this area. If you believe this is a mistake,
						contact another administrator.
					</Text>
					<Button variant="light" color="violet" onClick={() => navigate("/play")}>
						Back to DailyLoadout
					</Button>
					<Anchor size="xs" c="dimmed" onClick={() => navigate("/play")}>
						Return to the app
					</Anchor>
				</Stack>
			</Center>
		);
	}

	return <>{children}</>;
}
