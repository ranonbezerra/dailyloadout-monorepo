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
	email_verified: boolean;
	locale: string;
	timezone: string;
	created_at: string;
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
