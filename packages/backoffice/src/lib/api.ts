export const BASE_URL =
	(typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "http://localhost:8100";

// Web auth contract: the API stores the refresh token in an httpOnly cookie
// (opt-in via the `X-Auth-Mode: cookie` header). The access token is kept ONLY
// in memory, so an XSS payload cannot exfiltrate a
// long-lived credential. On page reload the in-memory token is gone and the
// session is restored via a silent `/refresh` using the cookie (see useAuth
// bootstrap). All requests send `credentials: "include"` so the cookie rides
// along.
const AUTH_MODE_HEADER = "X-Auth-Mode";
const AUTH_MODE_VALUE = "cookie";

// Cloudflare Turnstile passes its solved-challenge token to the server via this
// header (the server also accepts a JSON body field of the same name). When the
// server's TURNSTILE_SECRET is unset the header is a no-op, so the client must
// keep working when no token is available.
export const TURNSTILE_HEADER = "cf-turnstile-response";

// ---------------------------------------------------------------------------
// Token helpers — access token lives in a module-level variable (in memory).
// ---------------------------------------------------------------------------

let accessToken: string | null = null;

export function getAccessToken(): string | null {
	return accessToken;
}

/**
 * Store the access token in memory. The refresh token is no longer handled by
 * JS (it is an httpOnly cookie managed by the browser), so the second argument
 * is accepted for backwards compatibility but ignored.
 */
export function saveTokens(access: string, _refresh?: string): void {
	accessToken = access;
}

export function clearTokens(): void {
	accessToken = null;
}

// ---------------------------------------------------------------------------
// Refresh logic (single in-flight promise to avoid races)
// ---------------------------------------------------------------------------

let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt a cookie-based silent refresh: POST /v1/auth/refresh with no body,
 * the cookie-mode header, and credentials so the httpOnly refresh cookie is
 * sent. On success the new access token is stored in memory; on failure the
 * in-memory token is cleared.
 */
export async function attemptRefresh(): Promise<boolean> {
	try {
		const res = await fetch(`${BASE_URL}/v1/auth/refresh`, {
			method: "POST",
			headers: { [AUTH_MODE_HEADER]: AUTH_MODE_VALUE },
			credentials: "include",
		});

		if (!res.ok) {
			clearTokens();
			return false;
		}

		const data = (await res.json()) as { access_token: string; refresh_token: string };
		saveTokens(data.access_token);
		return true;
	} catch {
		clearTokens();
		return false;
	}
}

/**
 * Deduplicated silent refresh: concurrent callers share a single in-flight
 * request. Used by both the 401 retry path and the app-load bootstrap.
 */
export function refreshSession(): Promise<boolean> {
	if (!refreshPromise) {
		refreshPromise = attemptRefresh().finally(() => {
			refreshPromise = null;
		});
	}
	return refreshPromise;
}

// ---------------------------------------------------------------------------
// fetchWithAuthRetry – attaches the access token, and on a 401 performs a
// single-flight refresh and retries the request once. Shared by both JSON
// callers (apiFetch) and raw multipart/SSE callers so every request benefits
// from transparent token refresh. It never forces a Content-Type header: the
// caller (or the browser, for FormData) decides that. `credentials: "include"`
// is always set so the refresh cookie is sent.
// ---------------------------------------------------------------------------

export async function fetchWithAuthRetry(
	path: string,
	options: RequestInit = {},
): Promise<Response> {
	const headers = new Headers(options.headers);

	if (accessToken) {
		headers.set("Authorization", `Bearer ${accessToken}`);
	}

	const res = await fetch(`${BASE_URL}${path}`, {
		...options,
		headers,
		credentials: "include",
	});

	// -- Handle 401: try refresh once, then retry the original request --------
	if (res.status === 401) {
		const refreshed = await refreshSession();

		if (refreshed) {
			const retryHeaders = new Headers(options.headers);
			if (accessToken) {
				retryHeaders.set("Authorization", `Bearer ${accessToken}`);
			}

			return fetch(`${BASE_URL}${path}`, {
				...options,
				headers: retryHeaders,
				credentials: "include",
			});
		}

		// Refresh failed – clear and throw
		clearTokens();
		throw new Error("Session expired. Please log in again.");
	}

	return res;
}

// ---------------------------------------------------------------------------
// apiFetch – thin JSON wrapper around fetchWithAuthRetry
// ---------------------------------------------------------------------------

export async function apiFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
	const headers = new Headers(options.headers);

	if (!headers.has("Content-Type") && options.body) {
		headers.set("Content-Type", "application/json");
	}

	const res = await fetchWithAuthRetry(path, { ...options, headers });

	if (!res.ok) {
		const errBody = await retryParseError(res);
		throw new Error(errBody);
	}

	// Handle 204 No Content (and other responses with no body).
	if (res.status === 204) {
		return undefined as T;
	}

	return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// authFetch – like apiFetch but for the auth endpoints (login/register/logout).
// Adds the cookie-mode header + credentials so the server sets/clears the
// httpOnly refresh cookie. Does NOT go through the 401-refresh retry loop.
// ---------------------------------------------------------------------------

export async function authFetch<T = unknown>(
	path: string,
	body: unknown,
	extraHeaders?: Record<string, string>,
): Promise<T> {
	const res = await fetch(`${BASE_URL}${path}`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			[AUTH_MODE_HEADER]: AUTH_MODE_VALUE,
			...extraHeaders,
		},
		credentials: "include",
		body: JSON.stringify(body),
	});

	if (!res.ok) {
		const errBody = await retryParseError(res);
		throw new Error(errBody);
	}

	if (res.status === 204) {
		return undefined as T;
	}

	return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function retryParseError(res: Response): Promise<string> {
	let text: string;
	try {
		text = await res.text();
	} catch {
		return `Request failed: ${res.status}`;
	}

	if (!text) {
		return `Request failed: ${res.status}`;
	}

	try {
		const body = JSON.parse(text);
		if (typeof body === "object" && body !== null && "detail" in body) {
			return String((body as { detail: unknown }).detail);
		}
		return JSON.stringify(body);
	} catch {
		// Not JSON — surface the raw body text.
		return text;
	}
}
