import { apiFetch } from "@slate/shared/api";
import type { AuthTokens, MessageResponse } from "../types/auth";

// Web auth contract: the API keeps the refresh token in an httpOnly cookie when
// the request carries `X-Auth-Mode: cookie`. change-password reissues tokens, so
// it must opt into cookie mode (like login/register) to refresh that cookie.
const COOKIE_MODE_HEADER = { "X-Auth-Mode": "cookie" } as const;

// ---------------------------------------------------------------------------
// Email-verification API (anti-abuse Phase 1).
//
// `verifyEmail` is hit from the link in the verification email and works
// whether or not the visitor is logged in — the token in the body is the
// credential. `resendVerification` is hit from the in-app banner by an
// authenticated-but-unverified user; `apiFetch` attaches the in-memory access
// token (and transparently refreshes on 401). Both return a neutral
// `{ message }`.
// ---------------------------------------------------------------------------

/** POST /v1/auth/verify — flips the user's `email_verified` flag. */
export function verifyEmail(token: string): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/verify", {
		method: "POST",
		body: JSON.stringify({ token }),
	});
}

/** POST /v1/auth/resend-verification — rate-limited, neutral response. */
export function resendVerification(): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/resend-verification", {
		method: "POST",
		body: JSON.stringify({}),
	});
}

// ---------------------------------------------------------------------------
// Password recovery (Phase 1 auth hardening).
//
// `forgotPassword` and `resetPassword` are unauthenticated: the first is hit
// from the "forgot password?" link and is neutral (no account oracle); the
// second is hit from the emailed reset link, where the token is the credential.
// `changePassword` is for a signed-in user; it opts into cookie mode so the
// server rotates the refresh cookie and returns a fresh access token, keeping
// this device signed in while every other session is cut off.
// ---------------------------------------------------------------------------

/** POST /v1/auth/forgot-password — rate-limited, neutral response. */
export function forgotPassword(email: string): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/forgot-password", {
		method: "POST",
		body: JSON.stringify({ email }),
	});
}

/** POST /v1/auth/reset-password — set a new password from an emailed token. */
export function resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/reset-password", {
		method: "POST",
		body: JSON.stringify({ token, new_password: newPassword }),
	});
}

/** POST /v1/auth/change-password — verify current, set new, reissue tokens. */
export function changePassword(currentPassword: string, newPassword: string): Promise<AuthTokens> {
	return apiFetch<AuthTokens>("/v1/auth/change-password", {
		method: "POST",
		headers: COOKIE_MODE_HEADER,
		body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
	});
}
