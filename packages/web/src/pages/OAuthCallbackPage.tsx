import { Card, Center, Loader, Stack, Text } from "@mantine/core";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";

// ---------------------------------------------------------------------------
// /oauth/callback — the web success URL the API redirects to after a social
// login. At this point the browser holds only the httpOnly refresh cookie and
// the app has no access token, so we trigger a silent cookie→session bootstrap
// (completeOAuth) and then route the user into the app — or back to /login on
// failure. The cancelled-guard prevents a navigate after unmount.
// ---------------------------------------------------------------------------

export function OAuthCallbackPage() {
	const { completeOAuth } = useAuthContext();
	const navigate = useNavigate();

	useEffect(() => {
		let cancelled = false;

		completeOAuth().then((ok) => {
			if (cancelled) return;
			if (ok) {
				navigate("/library", { replace: true });
			} else {
				navigate("/login?error=oauth_failed", { replace: true });
			}
		});

		return () => {
			cancelled = true;
		};
	}, [completeOAuth, navigate]);

	return (
		<Center h="100vh">
			<Card shadow="md" padding="xl" radius="md" w={420}>
				<Stack align="center">
					<Loader />
					<Text c="dimmed">Signing you in…</Text>
				</Stack>
			</Card>
		</Center>
	);
}
