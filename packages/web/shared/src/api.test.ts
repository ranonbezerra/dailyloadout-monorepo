import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	apiFetch,
	authFetch,
	BASE_URL,
	clearTokens,
	getAccessToken,
	refreshSession,
	saveTokens,
} from "./api";

// ---------------------------------------------------------------------------
// Setup — the access token now lives in a module-level variable (in memory),
// and the refresh token is an httpOnly cookie the browser manages.
// ---------------------------------------------------------------------------

const mockFetch = vi.fn<(...args: unknown[]) => Promise<Response>>();

beforeEach(() => {
	vi.stubGlobal("fetch", mockFetch);
	mockFetch.mockReset();
	clearTokens();
});

// ---------------------------------------------------------------------------
// Token helpers
// ---------------------------------------------------------------------------

describe("Token helpers", () => {
	it("getAccessToken returns null when no token is stored", () => {
		expect(getAccessToken()).toBeNull();
	});

	it("saveTokens stores the access token in memory (refresh arg ignored)", () => {
		saveTokens("access-123", "refresh-456");
		expect(getAccessToken()).toBe("access-123");
	});

	it("saveTokens works with only the access token", () => {
		saveTokens("access-only");
		expect(getAccessToken()).toBe("access-only");
	});

	it("clearTokens removes the in-memory access token", () => {
		saveTokens("access-123");
		clearTokens();
		expect(getAccessToken()).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Response helpers
// ---------------------------------------------------------------------------

function jsonResponse(body: unknown, status = 200): Response {
	return {
		ok: status >= 200 && status < 300,
		status,
		json: () => Promise.resolve(body),
		text: () => Promise.resolve(JSON.stringify(body)),
		headers: new Headers(),
	} as unknown as Response;
}

function textResponse(text: string, status: number): Response {
	return {
		ok: status >= 200 && status < 300,
		status,
		json: () => Promise.reject(new Error("not json")),
		text: () => Promise.resolve(text),
		headers: new Headers(),
	} as unknown as Response;
}

// ---------------------------------------------------------------------------
// refreshSession (cookie-based silent refresh)
// ---------------------------------------------------------------------------

describe("refreshSession", () => {
	it("POSTs /v1/auth/refresh with cookie-mode header, credentials, no body", async () => {
		mockFetch.mockResolvedValueOnce(
			jsonResponse({ access_token: "new-access", refresh_token: "" }),
		);

		const ok = await refreshSession();

		expect(ok).toBe(true);
		expect(getAccessToken()).toBe("new-access");

		const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		expect(url).toBe(`${BASE_URL}/v1/auth/refresh`);
		expect(init.method).toBe("POST");
		expect(init.credentials).toBe("include");
		expect(init.body).toBeUndefined();
		const headers = new Headers(init.headers);
		expect(headers.get("X-Auth-Mode")).toBe("cookie");
	});

	it("clears the token and returns false when refresh is not ok", async () => {
		saveTokens("stale");
		mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));

		const ok = await refreshSession();

		expect(ok).toBe(false);
		expect(getAccessToken()).toBeNull();
	});

	it("clears the token and returns false on a network error", async () => {
		saveTokens("stale");
		mockFetch.mockRejectedValueOnce(new Error("network"));

		const ok = await refreshSession();

		expect(ok).toBe(false);
		expect(getAccessToken()).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// authFetch (login / register / logout)
// ---------------------------------------------------------------------------

describe("authFetch", () => {
	it("sends cookie-mode header + credentials and returns parsed JSON", async () => {
		mockFetch.mockResolvedValueOnce(
			jsonResponse({ access_token: "a", refresh_token: "", token_type: "bearer" }),
		);

		const data = await authFetch("/v1/auth/login", { email: "x@y.z", password: "p" });

		expect(data).toEqual({ access_token: "a", refresh_token: "", token_type: "bearer" });
		const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		expect(url).toBe(`${BASE_URL}/v1/auth/login`);
		expect(init.credentials).toBe("include");
		const headers = new Headers(init.headers);
		expect(headers.get("X-Auth-Mode")).toBe("cookie");
		expect(headers.get("Content-Type")).toBe("application/json");
		expect(JSON.parse(init.body as string)).toEqual({ email: "x@y.z", password: "p" });
	});

	it("forwards extra headers (e.g. the Turnstile token)", async () => {
		mockFetch.mockResolvedValueOnce(
			jsonResponse({ access_token: "a", refresh_token: "", token_type: "bearer" }),
		);

		await authFetch(
			"/v1/auth/register",
			{ email: "x@y.z", password: "p", display_name: "X" },
			{ "cf-turnstile-response": "captcha-token" },
		);

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = new Headers(init.headers);
		expect(headers.get("cf-turnstile-response")).toBe("captcha-token");
		// Still sends the standard auth headers.
		expect(headers.get("X-Auth-Mode")).toBe("cookie");
	});

	it("returns undefined for a 204 logout", async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 204,
			json: () => Promise.reject(new Error("no body")),
			text: () => Promise.resolve(""),
			headers: new Headers(),
		} as unknown as Response);

		const data = await authFetch("/v1/auth/logout", {});
		expect(data).toBeUndefined();
	});

	it("throws the error detail on a non-ok response", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Invalid credentials" }, 401));

		await expect(authFetch("/v1/auth/login", {})).rejects.toThrow("Invalid credentials");
	});
});

// ---------------------------------------------------------------------------
// apiFetch
// ---------------------------------------------------------------------------

describe("apiFetch", () => {
	// -- Authorization header ------------------------------------------------

	it("sets Authorization header when an access token exists", async () => {
		saveTokens("my-token");
		mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

		await apiFetch("/v1/items");

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = new Headers(init.headers);
		expect(headers.get("Authorization")).toBe("Bearer my-token");
	});

	it("includes credentials so the cookie rides along", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

		await apiFetch("/v1/items");

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		expect(init.credentials).toBe("include");
	});

	it("does not set Authorization header when no access token exists", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

		await apiFetch("/v1/items");

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = new Headers(init.headers);
		expect(headers.get("Authorization")).toBeNull();
	});

	// -- Content-Type --------------------------------------------------------

	it("sets Content-Type to application/json when a body is provided", async () => {
		saveTokens("tok");
		mockFetch.mockResolvedValueOnce(jsonResponse({ id: 1 }));

		await apiFetch("/v1/items", { method: "POST", body: JSON.stringify({ name: "Sword" }) });

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = new Headers(init.headers);
		expect(headers.get("Content-Type")).toBe("application/json");
	});

	it("does not set Content-Type when no body is provided", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ id: 1 }));

		await apiFetch("/v1/items");

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = new Headers(init.headers);
		expect(headers.get("Content-Type")).toBeNull();
	});

	it("does not override an existing Content-Type header", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

		await apiFetch("/v1/upload", {
			method: "POST",
			headers: { "Content-Type": "multipart/form-data" },
			body: "binary-data",
		});

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = new Headers(init.headers);
		expect(headers.get("Content-Type")).toBe("multipart/form-data");
	});

	// -- URL construction ----------------------------------------------------

	it("prepends BASE_URL to the path", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

		await apiFetch("/v1/items");

		const [url] = mockFetch.mock.calls[0] as [string];
		expect(url).toBe(`${BASE_URL}/v1/items`);
	});

	// -- 204 No Content ------------------------------------------------------

	it("returns undefined for 204 No Content responses", async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 204,
			json: () => Promise.reject(new Error("no body")),
			text: () => Promise.resolve(""),
			headers: new Headers(),
		} as unknown as Response);

		const result = await apiFetch("/v1/items/1", { method: "DELETE" });
		expect(result).toBeUndefined();
	});

	// -- Successful JSON response --------------------------------------------

	it("returns parsed JSON for a successful response", async () => {
		const payload = { id: 1, name: "Sword" };
		mockFetch.mockResolvedValueOnce(jsonResponse(payload));

		const result = await apiFetch("/v1/items/1");
		expect(result).toEqual(payload);
	});

	// -- Error responses -----------------------------------------------------

	it("throws with the detail field from a JSON error response", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Not found" }, 404));

		await expect(apiFetch("/v1/items/999")).rejects.toThrow("Not found");
	});

	it("throws with stringified body when error JSON has no detail field", async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ message: "bad request" }, 400));

		await expect(apiFetch("/v1/items")).rejects.toThrow(
			JSON.stringify({ message: "bad request" }),
		);
	});

	it("surfaces the raw body when the error response is not JSON", async () => {
		mockFetch.mockResolvedValueOnce(textResponse("Internal error", 500));

		await expect(apiFetch("/v1/items")).rejects.toThrow("Internal error");
	});

	it("throws with status code when error response has an empty body", async () => {
		mockFetch.mockResolvedValueOnce(textResponse("", 500));

		await expect(apiFetch("/v1/items")).rejects.toThrow("Request failed: 500");
	});

	// -- 401 cookie-refresh flow ---------------------------------------------

	describe("401 token refresh", () => {
		it("refreshes via the cookie and retries the original request on 401", async () => {
			saveTokens("expired-token");

			// 1st call: original request returns 401
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));
			// 2nd call: refresh endpoint succeeds (cookie-based, empty refresh body)
			mockFetch.mockResolvedValueOnce(
				jsonResponse({ access_token: "new-access", refresh_token: "" }),
			);
			// 3rd call: retry of the original request succeeds
			const retryPayload = { id: 1, name: "Sword" };
			mockFetch.mockResolvedValueOnce(jsonResponse(retryPayload));

			const result = await apiFetch("/v1/items/1");

			expect(result).toEqual(retryPayload);
			expect(mockFetch).toHaveBeenCalledTimes(3);

			// The refresh call: no body, cookie-mode header, credentials included.
			const [refreshUrl, refreshInit] = mockFetch.mock.calls[1] as [string, RequestInit];
			expect(refreshUrl).toBe(`${BASE_URL}/v1/auth/refresh`);
			expect(refreshInit.body).toBeUndefined();
			expect(refreshInit.credentials).toBe("include");
			expect(new Headers(refreshInit.headers).get("X-Auth-Mode")).toBe("cookie");

			// The retry used the new in-memory token.
			const [, retryInit] = mockFetch.mock.calls[2] as [string, RequestInit];
			expect(new Headers(retryInit.headers).get("Authorization")).toBe("Bearer new-access");
			expect(getAccessToken()).toBe("new-access");
		});

		it("clears the token and throws when refresh fails with non-ok status", async () => {
			saveTokens("expired-token");

			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));

			await expect(apiFetch("/v1/items")).rejects.toThrow("Session expired. Please log in again.");

			expect(getAccessToken()).toBeNull();
		});

		it("clears the token and throws when the refresh request throws", async () => {
			saveTokens("expired-token");

			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));
			mockFetch.mockRejectedValueOnce(new Error("Network error"));

			await expect(apiFetch("/v1/items")).rejects.toThrow("Session expired. Please log in again.");

			expect(getAccessToken()).toBeNull();
		});

		it("attempts a cookie refresh even when there is no in-memory token", async () => {
			// No access token yet (e.g. cookie present but memory empty): a 401
			// still triggers a refresh attempt because the cookie may be valid.
			mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Unauthorized" }, 401));
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401)); // refresh also 401

			await expect(apiFetch("/v1/items")).rejects.toThrow("Session expired. Please log in again.");
			// original + refresh attempt = 2 calls
			expect(mockFetch).toHaveBeenCalledTimes(2);
		});

		it("retried request 204 returns undefined", async () => {
			saveTokens("expired-token");

			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));
			mockFetch.mockResolvedValueOnce(
				jsonResponse({ access_token: "new-access", refresh_token: "" }),
			);
			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 204,
				json: () => Promise.reject(new Error("no body")),
				text: () => Promise.resolve(""),
				headers: new Headers(),
			} as unknown as Response);

			const result = await apiFetch("/v1/items/1", { method: "DELETE" });
			expect(result).toBeUndefined();
		});

		it("throws when retried request after successful refresh still fails", async () => {
			saveTokens("expired-token");

			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));
			mockFetch.mockResolvedValueOnce(
				jsonResponse({ access_token: "new-access", refresh_token: "" }),
			);
			mockFetch.mockResolvedValueOnce(textResponse("Forbidden", 403));

			await expect(apiFetch("/v1/admin/secret")).rejects.toThrow("Forbidden");
		});

		// -- Concurrent 401 deduplication ------------------------------------

		it("deduplicates concurrent refresh calls into a single request", async () => {
			saveTokens("expired-token");

			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401)); // call A
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401)); // call B
			mockFetch.mockResolvedValueOnce(
				jsonResponse({ access_token: "new-access", refresh_token: "" }),
			);
			mockFetch.mockResolvedValueOnce(jsonResponse({ id: 1 })); // retry A
			mockFetch.mockResolvedValueOnce(jsonResponse({ id: 2 })); // retry B

			const [resultA, resultB] = await Promise.all([
				apiFetch("/v1/items/1"),
				apiFetch("/v1/items/2"),
			]);

			expect(resultA).toEqual({ id: 1 });
			expect(resultB).toEqual({ id: 2 });
			expect(mockFetch).toHaveBeenCalledTimes(5);

			const refreshCalls = mockFetch.mock.calls.filter(
				(call) => (call[0] as string) === `${BASE_URL}/v1/auth/refresh`,
			);
			expect(refreshCalls).toHaveLength(1);
		});
	});
});
