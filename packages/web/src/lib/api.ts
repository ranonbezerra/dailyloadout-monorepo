export const BASE_URL =
	(typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "http://localhost:8100";

const ACCESS_TOKEN_KEY = "dl_access_token";
const REFRESH_TOKEN_KEY = "dl_refresh_token";

// ---------------------------------------------------------------------------
// Token helpers
// ---------------------------------------------------------------------------

export function getAccessToken(): string | null {
	return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
	return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function saveTokens(access: string, refresh: string): void {
	localStorage.setItem(ACCESS_TOKEN_KEY, access);
	localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
	localStorage.removeItem(ACCESS_TOKEN_KEY);
	localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// Refresh logic (single in-flight promise to avoid races)
// ---------------------------------------------------------------------------

let refreshPromise: Promise<boolean> | null = null;

async function attemptRefresh(): Promise<boolean> {
	const refreshToken = getRefreshToken();
	if (!refreshToken) return false;

	try {
		const res = await fetch(`${BASE_URL}/v1/auth/refresh`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ refresh_token: refreshToken }),
		});

		if (!res.ok) {
			clearTokens();
			return false;
		}

		const data = (await res.json()) as {
			access_token: string;
			refresh_token: string;
		};
		saveTokens(data.access_token, data.refresh_token);
		return true;
	} catch {
		clearTokens();
		return false;
	}
}

// ---------------------------------------------------------------------------
// apiFetch – thin wrapper around fetch
// ---------------------------------------------------------------------------

export async function apiFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
	const headers = new Headers(options.headers);

	if (!headers.has("Content-Type") && options.body) {
		headers.set("Content-Type", "application/json");
	}

	const accessToken = getAccessToken();
	if (accessToken) {
		headers.set("Authorization", `Bearer ${accessToken}`);
	}

	const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

	// -- Handle 401: try refresh once, then retry the original request --------
	if (res.status === 401 && getRefreshToken()) {
		// Deduplicate concurrent refresh calls
		if (!refreshPromise) {
			refreshPromise = attemptRefresh().finally(() => {
				refreshPromise = null;
			});
		}

		const refreshed = await refreshPromise;

		if (refreshed) {
			const retryHeaders = new Headers(options.headers);
			if (!retryHeaders.has("Content-Type") && options.body) {
				retryHeaders.set("Content-Type", "application/json");
			}
			const newToken = getAccessToken();
			if (newToken) {
				retryHeaders.set("Authorization", `Bearer ${newToken}`);
			}

			const retryRes = await fetch(`${BASE_URL}${path}`, {
				...options,
				headers: retryHeaders,
			});

			if (!retryRes.ok) {
				const errBody = await retryRes.text();
				throw new Error(errBody || `Request failed: ${retryRes.status}`);
			}

			if (retryRes.status === 204) {
				return undefined as T;
			}

			return retryRes.json() as Promise<T>;
		}

		// Refresh failed – clear and throw
		clearTokens();
		throw new Error("Session expired. Please log in again.");
	}

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
// Helpers
// ---------------------------------------------------------------------------

async function retryParseError(res: Response): Promise<string> {
	try {
		const body = await res.json();
		if (typeof body === "object" && body !== null && "detail" in body) {
			return String((body as { detail: unknown }).detail);
		}
		return JSON.stringify(body);
	} catch {
		return `Request failed: ${res.status}`;
	}
}
