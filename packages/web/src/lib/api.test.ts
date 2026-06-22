import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	apiFetch,
	BASE_URL,
	clearTokens,
	getAccessToken,
	getRefreshToken,
	saveTokens,
} from "./api";

// ---------------------------------------------------------------------------
// localStorage mock (simple in-memory implementation)
// ---------------------------------------------------------------------------

function createLocalStorageMock(): Storage {
	let store: Record<string, string> = {};
	return {
		getItem: vi.fn((key: string) => store[key] ?? null),
		setItem: vi.fn((key: string, value: string) => {
			store[key] = value;
		}),
		removeItem: vi.fn((key: string) => {
			delete store[key];
		}),
		clear: vi.fn(() => {
			store = {};
		}),
		get length() {
			return Object.keys(store).length;
		},
		key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
	};
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const mockFetch = vi.fn<(...args: unknown[]) => Promise<Response>>();
let storageMock: Storage;

beforeEach(() => {
	vi.stubGlobal("fetch", mockFetch);
	storageMock = createLocalStorageMock();
	vi.stubGlobal("localStorage", storageMock);
	mockFetch.mockReset();
});

// ---------------------------------------------------------------------------
// Token helpers
// ---------------------------------------------------------------------------

describe("Token helpers", () => {
	it("getAccessToken returns null when no token is stored", () => {
		expect(getAccessToken()).toBeNull();
	});

	it("getRefreshToken returns null when no token is stored", () => {
		expect(getRefreshToken()).toBeNull();
	});

	it("saveTokens persists both tokens to localStorage", () => {
		saveTokens("access-123", "refresh-456");
		expect(storageMock.setItem).toHaveBeenCalledWith("dl_access_token", "access-123");
		expect(storageMock.setItem).toHaveBeenCalledWith("dl_refresh_token", "refresh-456");
	});

	it("getAccessToken returns the saved access token", () => {
		saveTokens("access-123", "refresh-456");
		expect(getAccessToken()).toBe("access-123");
	});

	it("getRefreshToken returns the saved refresh token", () => {
		saveTokens("access-123", "refresh-456");
		expect(getRefreshToken()).toBe("refresh-456");
	});

	it("clearTokens removes both tokens from localStorage", () => {
		saveTokens("access-123", "refresh-456");
		clearTokens();
		expect(getAccessToken()).toBeNull();
		expect(getRefreshToken()).toBeNull();
		expect(storageMock.removeItem).toHaveBeenCalledWith("dl_access_token");
		expect(storageMock.removeItem).toHaveBeenCalledWith("dl_refresh_token");
	});
});

// ---------------------------------------------------------------------------
// apiFetch
// ---------------------------------------------------------------------------

describe("apiFetch", () => {
	// Helper to create a minimal Response-like object for mockFetch
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

	// -- Authorization header ------------------------------------------------

	it("sets Authorization header when an access token exists", async () => {
		saveTokens("my-token", "my-refresh");
		mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

		await apiFetch("/v1/items");

		const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
		const headers = new Headers(init.headers);
		expect(headers.get("Authorization")).toBe("Bearer my-token");
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
		saveTokens("tok", "ref");
		mockFetch.mockResolvedValueOnce(jsonResponse({ id: 1 }));

		await apiFetch("/v1/items", {
			method: "POST",
			body: JSON.stringify({ name: "Sword" }),
		});

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

	it("throws with status code when error response is not JSON", async () => {
		mockFetch.mockResolvedValueOnce(textResponse("Internal error", 500));

		await expect(apiFetch("/v1/items")).rejects.toThrow("Request failed: 500");
	});

	// -- 401 refresh flow ----------------------------------------------------

	describe("401 token refresh", () => {
		it("refreshes the token and retries the original request on 401", async () => {
			saveTokens("expired-token", "valid-refresh");

			// 1st call: original request returns 401
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));

			// 2nd call: refresh endpoint succeeds
			mockFetch.mockResolvedValueOnce(
				jsonResponse({
					access_token: "new-access",
					refresh_token: "new-refresh",
				}),
			);

			// 3rd call: retry of the original request succeeds
			const retryPayload = { id: 1, name: "Sword" };
			mockFetch.mockResolvedValueOnce(jsonResponse(retryPayload));

			const result = await apiFetch("/v1/items/1");

			expect(result).toEqual(retryPayload);
			expect(mockFetch).toHaveBeenCalledTimes(3);

			// Verify the refresh call was made correctly
			const [refreshUrl, refreshInit] = mockFetch.mock.calls[1] as [string, RequestInit];
			expect(refreshUrl).toBe(`${BASE_URL}/v1/auth/refresh`);
			expect(JSON.parse(refreshInit.body as string)).toEqual({
				refresh_token: "valid-refresh",
			});

			// Verify the retry used the new token
			const [, retryInit] = mockFetch.mock.calls[2] as [string, RequestInit];
			const retryHeaders = new Headers(retryInit.headers);
			expect(retryHeaders.get("Authorization")).toBe("Bearer new-access");

			// Verify tokens were updated in storage
			expect(getAccessToken()).toBe("new-access");
			expect(getRefreshToken()).toBe("new-refresh");
		});

		it("clears tokens and throws when refresh fails with non-ok status", async () => {
			saveTokens("expired-token", "bad-refresh");

			// 1st call: original 401
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));

			// 2nd call: refresh returns 401 (invalid refresh token)
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));

			await expect(apiFetch("/v1/items")).rejects.toThrow("Session expired. Please log in again.");

			expect(getAccessToken()).toBeNull();
			expect(getRefreshToken()).toBeNull();
		});

		it("clears tokens and throws when refresh request throws a network error", async () => {
			saveTokens("expired-token", "valid-refresh");

			// 1st call: original 401
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));

			// 2nd call: refresh throws network error
			mockFetch.mockRejectedValueOnce(new Error("Network error"));

			await expect(apiFetch("/v1/items")).rejects.toThrow("Session expired. Please log in again.");

			expect(getAccessToken()).toBeNull();
			expect(getRefreshToken()).toBeNull();
		});

		it("does not attempt refresh when there is no refresh token", async () => {
			saveTokens("expired-token", "valid-refresh");
			// Remove only the refresh token
			localStorage.removeItem("dl_refresh_token");

			mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Unauthorized" }, 401));

			await expect(apiFetch("/v1/items")).rejects.toThrow("Unauthorized");

			// Should not have called the refresh endpoint
			expect(mockFetch).toHaveBeenCalledTimes(1);
		});

		it("retried request 204 returns undefined", async () => {
			saveTokens("expired-token", "valid-refresh");

			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));
			mockFetch.mockResolvedValueOnce(
				jsonResponse({
					access_token: "new-access",
					refresh_token: "new-refresh",
				}),
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
			saveTokens("expired-token", "valid-refresh");

			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401));
			mockFetch.mockResolvedValueOnce(
				jsonResponse({
					access_token: "new-access",
					refresh_token: "new-refresh",
				}),
			);
			// Retry also fails
			mockFetch.mockResolvedValueOnce(textResponse("Forbidden", 403));

			await expect(apiFetch("/v1/admin/secret")).rejects.toThrow("Forbidden");
		});

		// -- Concurrent 401 deduplication ------------------------------------

		it("deduplicates concurrent refresh calls into a single request", async () => {
			saveTokens("expired-token", "valid-refresh");

			// Both initial requests return 401
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401)); // call A
			mockFetch.mockResolvedValueOnce(jsonResponse({}, 401)); // call B

			// Single refresh call
			mockFetch.mockResolvedValueOnce(
				jsonResponse({
					access_token: "new-access",
					refresh_token: "new-refresh",
				}),
			);

			// Retry for call A
			mockFetch.mockResolvedValueOnce(jsonResponse({ id: 1 }));
			// Retry for call B
			mockFetch.mockResolvedValueOnce(jsonResponse({ id: 2 }));

			const [resultA, resultB] = await Promise.all([
				apiFetch("/v1/items/1"),
				apiFetch("/v1/items/2"),
			]);

			expect(resultA).toEqual({ id: 1 });
			expect(resultB).toEqual({ id: 2 });

			// 2 original + 1 refresh + 2 retries = 5 calls total
			expect(mockFetch).toHaveBeenCalledTimes(5);

			// Verify only ONE call went to the refresh endpoint
			const refreshCalls = mockFetch.mock.calls.filter(
				(call) => (call[0] as string) === `${BASE_URL}/v1/auth/refresh`,
			);
			expect(refreshCalls).toHaveLength(1);
		});
	});
});
