import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	apiFetch,
	authFetch,
	clearTokens,
	getAccessToken,
	refreshSession,
	saveTokens,
} from "../lib/api";
import { createWrapper } from "../test/wrapper";
import { useAuth } from "./useAuth";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../lib/api", () => ({
	apiFetch: vi.fn(),
	authFetch: vi.fn(),
	getAccessToken: vi.fn(() => null),
	refreshSession: vi.fn(async () => false),
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
const mockedAuthFetch = vi.mocked(authFetch);
const mockedGetAccessToken = vi.mocked(getAccessToken);
const mockedRefreshSession = vi.mocked(refreshSession);
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
	refresh_token: "",
	token_type: "bearer",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useAuth", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockedGetAccessToken.mockReturnValue(null);
		mockedRefreshSession.mockResolvedValue(false);
	});

	it("bootstraps via silent refresh; user=null when refresh fails", async () => {
		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isLoading).toBe(false);
		});

		expect(mockedRefreshSession).toHaveBeenCalledOnce();
		expect(result.current.user).toBeNull();
		expect(result.current.isAuthenticated).toBe(false);
	});

	it("restores the session when bootstrap refresh succeeds", async () => {
		// Refresh succeeds and populates the in-memory token.
		mockedRefreshSession.mockImplementation(async () => {
			mockedGetAccessToken.mockReturnValue("acc-123");
			return true;
		});
		mockedApiFetch.mockResolvedValueOnce(fakeUser);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.user).toEqual(fakeUser);
		});

		expect(result.current.isAuthenticated).toBe(true);
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/me");
	});

	it("does not call refresh during bootstrap when a token is already present", async () => {
		mockedGetAccessToken.mockReturnValue("acc-123");
		mockedApiFetch.mockResolvedValueOnce(fakeUser);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.user).toEqual(fakeUser);
		});

		expect(mockedRefreshSession).not.toHaveBeenCalled();
	});

	it("login calls authFetch /v1/auth/login and saves only the access token", async () => {
		mockedAuthFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.login("player@test.com", "secret123");
		});

		expect(mockedAuthFetch).toHaveBeenCalledWith("/v1/auth/login", {
			email: "player@test.com",
			password: "secret123",
		});
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-123");
	});

	it("register calls authFetch /v1/auth/register and saves only the access token", async () => {
		mockedAuthFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.register("player@test.com", "secret123", "Player");
		});

		expect(mockedAuthFetch).toHaveBeenCalledWith("/v1/auth/register", {
			email: "player@test.com",
			password: "secret123",
			display_name: "Player",
		});
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-123");
	});

	it("logout calls authFetch /v1/auth/logout (clears the cookie) and clearTokens", async () => {
		mockedAuthFetch.mockResolvedValueOnce(undefined);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.logout();
		});

		expect(mockedAuthFetch).toHaveBeenCalledWith("/v1/auth/logout", {});
		expect(mockedClearTokens).toHaveBeenCalledOnce();
	});

	it("logout still clears the in-memory token if the API call fails", async () => {
		mockedAuthFetch.mockRejectedValueOnce(new Error("Network error"));

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.logout();
		});

		expect(mockedClearTokens).toHaveBeenCalledOnce();
	});

	it("isAuthenticated is true when user data is available", async () => {
		mockedGetAccessToken.mockReturnValue("acc-123");
		mockedApiFetch.mockResolvedValueOnce(fakeUser);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isAuthenticated).toBe(true);
		});

		expect(result.current.user).toEqual(fakeUser);
	});
});
