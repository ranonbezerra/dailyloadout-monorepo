import { Button, Divider, Stack } from "@mantine/core";
import { enabledOAuthProviders, oauthStartUrl } from "../lib/oauth";

interface SocialLoginButtonsProps {
	/** Divider label shown above the buttons. */
	label?: string;
}

// ---------------------------------------------------------------------------
// Presentational social-login buttons. One full-width Mantine button per
// enabled provider; a click navigates the whole page to the API's OAuth start
// URL (the flow is browser-redirect based, not fetch based). Renders nothing
// — not even the divider — when no providers are enabled.
// ---------------------------------------------------------------------------

export function SocialLoginButtons({ label = "or continue with" }: SocialLoginButtonsProps) {
	const providers = enabledOAuthProviders();
	if (providers.length === 0) {
		return null;
	}

	return (
		<>
			<Divider my="md" label={label} />
			<Stack>
				{providers.map(({ provider, label: providerLabel }) => (
					<Button
						key={provider}
						variant="default"
						fullWidth
						onClick={() => {
							window.location.href = oauthStartUrl(provider);
						}}
					>
						Continue with {providerLabel}
					</Button>
				))}
			</Stack>
		</>
	);
}
