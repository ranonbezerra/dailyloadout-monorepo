// Frontend password rules — mirror the API's `RegisterRequest`/reset schemas
// (min 8 chars, at least one upper, one lower, and one digit) so the user gets
// instant feedback instead of a round-trip 422. The server stays the source of
// truth; this is a UX nicety, not the enforcement boundary.

/** Return a validation error string, or `null` when the password is acceptable. */
export function validatePasswordComplexity(value: string): string | null {
	if (value.length < 8) return "Password must be at least 8 characters";
	if (!/[A-Z]/.test(value)) return "Password must contain an uppercase letter";
	if (!/[a-z]/.test(value)) return "Password must contain a lowercase letter";
	if (!/\d/.test(value)) return "Password must contain a digit";
	return null;
}

/** Return an error when *confirm* does not match *password*, else `null`. */
export function validatePasswordMatch(password: string, confirm: string): string | null {
	return confirm === password ? null : "Passwords do not match";
}
