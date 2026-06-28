import { Button, Center, Loader, Stack, Text, Title } from "@mantine/core";
import { IconLock } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useAuthContext } from "../contexts/AuthContext";
import { useAdminMe } from "../hooks/useBackoffice";

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
	const { logout } = useAuthContext();
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
						This account doesn't have admin rights. If you believe this is a mistake, contact
						another administrator — or sign in with an admin account.
					</Text>
					<Button variant="light" color="violet" onClick={() => logout()}>
						Sign out
					</Button>
				</Stack>
			</Center>
		);
	}

	return <>{children}</>;
}
