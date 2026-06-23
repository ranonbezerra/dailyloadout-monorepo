import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, clearTokens, getAccessToken, getRefreshToken, saveTokens } from "../lib/api";
import { createWrapper } from "../test/wrapper";
import { useAuth } from "./useAuth";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../lib/api", () => ({
	apiFetch: vi.fn(),
	getAccessToken: vi.fn(() => null),
	getRefreshToken: vi.fn(() => null),
	saveTokens: vi.fn(),
	clearTokens: vi.fn(),
}));

// AuthProvider inside createWrapper uses useAuth internally -- we need to
// mock AuthContext so the wrapper does not create a second useAuth instance
// that interferes with our test.
vi.mock("../contexts/AuthContext", () => ({
	AuthProvider: ({ children }: { children: React.ReactNode }) => children,
	useAuthContext: vi.fn(),
}));

const mockedApiFetch = vi.mocked(apiFetch);
const mockedGetAccessToken = vi.mocked(getAccessToken);
const mockedGetRefreshToken = vi.mocked(getRefreshToken);
const mockedSaveTokens = vi.mocked(saveTokens);
const mockedClearTokens = vi.mocked(clearTokens);

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const fakeUser = {
	public_id: "u-001",
	email: "player@test.com",
	display_name: "Player",
	avatar_url: null,
	email_verified: true,
	locale: "en",
	timezone: "UTC",
	created_at: "2024-01-01T00:00:00Z",
};

const fakeTokens = {
	access_token: "acc-123",
	refresh_token: "ref-456",
	token_type: "bearer",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useAuth", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockedGetAccessToken.mockReturnValue(null);
		mockedGetRefreshToken.mockReturnValue(null);
	});

	it("returns user=null and isAuthenticated=false when no access token", async () => {
		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(result.current.isLoading).toBe(false);
		});

		expect(result.current.user).toBeNull();
		expect(result.current.isAuthenticated).toBe(false);
	});

	it("fetches user when access token is present", async () => {
		mockedGetAccessToken.mockReturnValue("acc-123");
		mockedApiFetch.mockResolvedValueOnce(fakeUser);

		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(result.current.user).toEqual(fakeUser);
		});

		expect(result.current.isAuthenticated).toBe(true);
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/me");
	});

	it("login calls apiFetch POST /v1/auth/login and saveTokens", async () => {
		mockedApiFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await act(async () => {
			await result.current.login("player@test.com", "secret123");
		});

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/login", {
			method: "POST",
			body: JSON.stringify({
				email: "player@test.com",
				password: "secret123",
			}),
		});
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-123", "ref-456");
	});

	it("register calls apiFetch POST /v1/auth/register and saveTokens", async () => {
		mockedApiFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await act(async () => {
			await result.current.register("player@test.com", "secret123", "Player");
		});

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/register", {
			method: "POST",
			body: JSON.stringify({
				email: "player@test.com",
				password: "secret123",
				display_name: "Player",
			}),
		});
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-123", "ref-456");
	});

	it("logout calls apiFetch POST /v1/auth/logout and clearTokens", async () => {
		mockedGetRefreshToken.mockReturnValue("ref-456");
		mockedApiFetch.mockResolvedValueOnce(undefined);

		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await act(async () => {
			await result.current.logout();
		});

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/logout", {
			method: "POST",
			body: JSON.stringify({ refresh_token: "ref-456" }),
		});
		expect(mockedClearTokens).toHaveBeenCalledOnce();
	});

	it("logout still clears tokens if API call fails", async () => {
		mockedGetRefreshToken.mockReturnValue("ref-456");
		mockedApiFetch.mockRejectedValueOnce(new Error("Network error"));

		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await act(async () => {
			await result.current.logout();
		});

		// Even though the API call failed, clearTokens should still be called
		expect(mockedClearTokens).toHaveBeenCalledOnce();
	});

	it("logout skips API call when no refresh token", async () => {
		mockedGetRefreshToken.mockReturnValue(null);

		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await act(async () => {
			await result.current.logout();
		});

		// apiFetch should NOT have been called for /v1/auth/logout
		expect(mockedApiFetch).not.toHaveBeenCalledWith("/v1/auth/logout", expect.anything());
		expect(mockedClearTokens).toHaveBeenCalledOnce();
	});

	it("isAuthenticated is true when user data is available", async () => {
		mockedGetAccessToken.mockReturnValue("acc-123");
		mockedApiFetch.mockResolvedValueOnce(fakeUser);

		const { result } = renderHook(() => useAuth(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(result.current.isAuthenticated).toBe(true);
		});

		expect(result.current.user).toEqual(fakeUser);
	});
});
