import { apiFetch, authFetch } from "@slate/shared/api";
import type {
	LoginResponse,
	MessageResponse,
	MfaEnroll,
	MfaRecoveryCodes,
	MfaStatus,
} from "../types/auth";

// ---------------------------------------------------------------------------
// MFA (TOTP) API.
//
// `mfaLogin` is the public second step of a two-factor sign-in: it goes through
// `authFetch` (cookie-mode) so the server rotates the refresh cookie and returns
// a fresh access token. The management calls are authenticated (`apiFetch`
// attaches the access token); the server gates them per-user.
// ---------------------------------------------------------------------------

/** POST /v1/auth/mfa/login — exchange a challenge token + code for session tokens. */
export function mfaLogin(mfaToken: string, code: string): Promise<LoginResponse> {
	return authFetch<LoginResponse>("/v1/auth/mfa/login", { mfa_token: mfaToken, code });
}

/** GET /v1/auth/mfa/status — whether MFA is enabled and recovery codes left. */
export function getMfaStatus(): Promise<MfaStatus> {
	return apiFetch<MfaStatus>("/v1/auth/mfa/status");
}

/** POST /v1/auth/mfa/enroll — start enrollment; returns the secret + otpauth URI. */
export function enrollMfa(): Promise<MfaEnroll> {
	return apiFetch<MfaEnroll>("/v1/auth/mfa/enroll", { method: "POST" });
}

/** POST /v1/auth/mfa/confirm — activate MFA with a code; returns recovery codes. */
export function confirmMfa(code: string): Promise<MfaRecoveryCodes> {
	return apiFetch<MfaRecoveryCodes>("/v1/auth/mfa/confirm", {
		method: "POST",
		body: JSON.stringify({ code }),
	});
}

/** POST /v1/auth/mfa/recovery-codes — replace the recovery-code set. */
export function regenerateRecoveryCodes(code: string): Promise<MfaRecoveryCodes> {
	return apiFetch<MfaRecoveryCodes>("/v1/auth/mfa/recovery-codes", {
		method: "POST",
		body: JSON.stringify({ code }),
	});
}

/** POST /v1/auth/mfa/disable — turn MFA off after verifying a current code. */
export function disableMfa(code: string): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/mfa/disable", {
		method: "POST",
		body: JSON.stringify({ code }),
	});
}
