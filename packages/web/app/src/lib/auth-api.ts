import { apiFetch } from "@dl/shared/api";
import type { MessageResponse } from "../types/auth";

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
