import { Alert, Button, Card, Center, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCircleCheck, IconMailExclamation } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";

type Status = "verifying" | "success" | "error" | "missing";

// ---------------------------------------------------------------------------
// /verify-email — landing page for the link in the verification email.
//
// Reads `?token=`, POSTs it to /v1/auth/verify, and shows a success or an
// error (invalid/expired) state. On success it refetches /me so the verified
// flag clears the in-app banner, then offers a link back into the app. The
// error state offers a Resend action (for signed-in users).
// ---------------------------------------------------------------------------

export function VerifyEmailPage() {
	const [searchParams] = useSearchParams();
	const token = searchParams.get("token");
	const { verify, resendVerification, isResendPending, refetchUser } = useAuthContext();

	const [status, setStatus] = useState<Status>(token ? "verifying" : "missing");
	// Guard against double-invocation under React StrictMode / re-renders so we
	// only POST the (single-use) token once.
	const attemptedRef = useRef(false);

	useEffect(() => {
		if (!token || attemptedRef.current) return;
		attemptedRef.current = true;

		verify(token)
			.then(() => {
				setStatus("success");
				refetchUser();
			})
			.catch(() => {
				setStatus("error");
			});
	}, [token, verify, refetchUser]);

	const handleResend = async () => {
		try {
			await resendVerification();
			notifications.show({
				title: "Verification email sent",
				message: "Check your inbox for a fresh verification link.",
				color: "green",
			});
		} catch {
			notifications.show({
				title: "Couldn't resend",
				message: "Please try again in a moment.",
				color: "red",
			});
		}
	};

	return (
		<Center h="100vh">
			<Card shadow="md" padding="xl" radius="md" w={460}>
				<Stack>
					<Title order={2} ta="center">
						Email verification
					</Title>

					{status === "verifying" && (
						<Group justify="center" py="md">
							<Loader />
							<Text c="dimmed">Verifying your email…</Text>
						</Group>
					)}

					{status === "missing" && (
						<Alert color="yellow" icon={<IconMailExclamation size={18} />} title="Missing token">
							This link is missing its verification token. Open the most recent link from your
							email, or resend a new one.
						</Alert>
					)}

					{status === "success" && (
						<Alert color="green" icon={<IconCircleCheck size={18} />} title="All set">
							Email verified — you're all set.
						</Alert>
					)}

					{status === "error" && (
						<Alert
							color="red"
							icon={<IconMailExclamation size={18} />}
							title="Verification failed"
						>
							This verification link is invalid or has expired. Request a new one below.
						</Alert>
					)}

					{status === "success" ? (
						<Button component={Link} to="/play" fullWidth>
							Continue to DailyLoadout
						</Button>
					) : (
						status !== "verifying" && (
							<Button variant="light" fullWidth loading={isResendPending} onClick={handleResend}>
								Resend verification email
							</Button>
						)
					)}

					<Text ta="center" size="sm">
						<Link to="/play">Back to the app</Link>
					</Text>
				</Stack>
			</Card>
		</Center>
	);
}
