export interface AuthTokens {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

export interface User {
	public_id: string;
	email: string;
	display_name: string;
	avatar_url: string | null;
	/** Snake_case as returned by the API (`UserResponse.email_verified`). */
	email_verified: boolean;
	/**
	 * Camel-case mirror of `email_verified`, normalized in the auth/me query so
	 * UI code can read a single, idiomatic field. Cost-bearing API routes return
	 * 403 "Email not verified" until this flips to `true`.
	 */
	emailVerified: boolean;
	locale: string;
	timezone: string;
	created_at: string;
}

/** Generic `{ message }` envelope returned by verify / resend endpoints. */
export interface MessageResponse {
	message: string;
}

export interface LoginRequest {
	email: string;
	password: string;
}

export interface RegisterRequest {
	email: string;
	password: string;
	display_name: string;
}
