import { BASE_URL } from "@dl/shared/api";

// ---------------------------------------------------------------------------
// Social login (OAuth) helpers.
//
// The OAuth flow is driven entirely by full-page browser navigations to the
// API: a click sends the browser to `/v1/auth/oauth/{provider}/start`, the API
// redirects to the provider and back to its own callback, then 302s the browser
// to the web success URL (`/oauth/callback`) on success or to
// `/login?error=<reason>` on failure. No JSON/fetch is involved on the client
// for the start of the flow — see SocialLoginButtons / OAuthCallbackPage.
// ---------------------------------------------------------------------------

/** Provider identifiers understood by both the API and the UI. */
export type OAuthProvider = "google" | "twitch";

interface OAuthProviderMeta {
	provider: OAuthProvider;
	/** User-facing button label, e.g. "Google". */
	label: string;
}

// Known providers, keyed by their API identifier. Only these can be enabled.
const KNOWN_PROVIDERS: Record<OAuthProvider, OAuthProviderMeta> = {
	google: { provider: "google", label: "Google" },
	twitch: { provider: "twitch", label: "Twitch" },
};

const DEFAULT_PROVIDERS = "google,twitch";

/** Build the full-page navigation URL that begins the OAuth flow. */
export function oauthStartUrl(provider: string): string {
	return `${BASE_URL}/v1/auth/oauth/${provider}/start`;
}

function isKnownProvider(value: string): value is OAuthProvider {
	return value === "google" || value === "twitch";
}

/**
 * Resolve which OAuth providers are enabled from `VITE_OAUTH_PROVIDERS`
 * (comma-separated). Defaults to "google,twitch" when unset; an explicit empty
 * string disables social login entirely. Only known providers are returned, and
 * order follows the env list.
 */
export function enabledOAuthProviders(): OAuthProviderMeta[] {
	const configured: string | undefined =
		typeof import.meta !== "undefined" ? import.meta.env?.VITE_OAUTH_PROVIDERS : undefined;
	const raw = configured ?? DEFAULT_PROVIDERS;

	return raw
		.split(",")
		.map((part) => part.trim().toLowerCase())
		.filter(isKnownProvider)
		.map((provider) => KNOWN_PROVIDERS[provider]);
}

// ---------------------------------------------------------------------------
// Error-reason → human message mapping. The API redirects to
// `/login?error=<reason>` on a failed flow; the LoginPage surfaces these.
// ---------------------------------------------------------------------------

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
	invalid_state: "Your sign-in session expired or was invalid. Please try again.",
	provider_unavailable: "That sign-in provider is currently unavailable. Please try again later.",
	oauth_failed: "We couldn't sign you in with that provider. Please try again.",
	account_exists:
		"An account with this email already exists. Log in with your password, then link this provider in settings.",
};

const OAUTH_ERROR_FALLBACK = "We couldn't sign you in. Please try again.";

/** Map an OAuth failure reason to a user-facing message. */
export function oauthErrorMessage(reason: string | null | undefined): string {
	if (!reason) return OAUTH_ERROR_FALLBACK;
	return OAUTH_ERROR_MESSAGES[reason] ?? OAUTH_ERROR_FALLBACK;
}
