// ---------------------------------------------------------------------------
// Error helpers.
//
// `apiFetch` rejects with `new Error(detail)`, where `detail` is the API's
// `{ detail }` string. Cost-bearing routes return 403 with the exact detail
// "Email not verified" until the user verifies, so we match on that message to
// drive the defensive global toast.
// ---------------------------------------------------------------------------

const EMAIL_NOT_VERIFIED = "email not verified";

export function isEmailNotVerifiedError(error: unknown): boolean {
	if (!(error instanceof Error)) return false;
	return error.message.toLowerCase().includes(EMAIL_NOT_VERIFIED);
}
