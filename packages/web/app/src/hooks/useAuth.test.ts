import {
	apiFetch,
	authFetch,
	clearTokens,
	getAccessToken,
	refreshSession,
	saveTokens,
} from "@slate/shared/api";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	changePassword,
	forgotPassword,
	resendVerification,
	resetPassword,
	verifyEmail,
} from "../lib/auth-api";
import { mfaLogin } from "../lib/mfa-api";
import { createWrapper } from "../test/wrapper";
import { useAuth } from "./useAuth";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@slate/shared/api", () => ({
	apiFetch: vi.fn(),
	authFetch: vi.fn(),
	getAccessToken: vi.fn(() => null),
	refreshSession: vi.fn(async () => false),
	saveTokens: vi.fn(),
	clearTokens: vi.fn(),
	TURNSTILE_HEADER: "cf-turnstile-response",
}));

vi.mock("../lib/auth-api", () => ({
	verifyEmail: vi.fn(),
	resendVerification: vi.fn(),
	forgotPassword: vi.fn(),
	resetPassword: vi.fn(),
	changePassword: vi.fn(),
}));

vi.mock("../lib/mfa-api", () => ({
	mfaLogin: vi.fn(),
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

// The auth/me query normalizes the API's snake_case `email_verified` into a
// camel-case `emailVerified` mirror, so the in-app `user` carries both.
const normalizedUser = { ...fakeUser, emailVerified: true };

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
			expect(result.current.user).toEqual(normalizedUser);
		});

		expect(result.current.isAuthenticated).toBe(true);
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/me");
	});

	it("does not call refresh during bootstrap when a token is already present", async () => {
		mockedGetAccessToken.mockReturnValue("acc-123");
		mockedApiFetch.mockResolvedValueOnce(fakeUser);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.user).toEqual(normalizedUser);
		});

		expect(mockedRefreshSession).not.toHaveBeenCalled();
	});

	it("login calls authFetch /v1/auth/login and saves only the access token", async () => {
		mockedAuthFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.login("player@test.com", "secret123");
		});

		expect(mockedAuthFetch).toHaveBeenCalledWith(
			"/v1/auth/login",
			{
				email: "player@test.com",
				password: "secret123", // pragma: allowlist secret
			},
			undefined,
		);
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-123");
	});

	it("login forwards a Turnstile token as the cf-turnstile-response header", async () => {
		mockedAuthFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.login("player@test.com", "secret123", "tok-abc");
		});

		expect(mockedAuthFetch).toHaveBeenCalledWith(
			"/v1/auth/login",
			expect.objectContaining({ email: "player@test.com" }),
			{ "cf-turnstile-response": "tok-abc" },
		);
	});

	it("login with MFA enabled returns a challenge and saves no tokens", async () => {
		mockedAuthFetch.mockResolvedValueOnce({
			access_token: "",
			refresh_token: "",
			token_type: "bearer",
			mfa_required: true,
			mfa_token: "challenge-123",
		});

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		let outcome: { mfaRequired: boolean; mfaToken: string } | undefined;
		await act(async () => {
			outcome = await result.current.login("player@test.com", "secret123");
		});

		expect(outcome).toEqual({ mfaRequired: true, mfaToken: "challenge-123" });
		expect(mockedSaveTokens).not.toHaveBeenCalled();
	});

	it("completeMfaLogin exchanges the challenge and saves the access token", async () => {
		vi.mocked(mfaLogin).mockResolvedValueOnce({
			access_token: "acc-mfa",
			refresh_token: "",
			token_type: "bearer",
			mfa_required: false,
			mfa_token: "",
		});

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.completeMfaLogin("challenge-123", "123456");
		});

		expect(mfaLogin).toHaveBeenCalledWith("challenge-123", "123456");
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-mfa");
	});

	it("register calls authFetch /v1/auth/register (no token header) and saves only the access token", async () => {
		mockedAuthFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.register("player@test.com", "secret123", "Player");
		});

		// No Turnstile token → no extra headers (third arg undefined).
		expect(mockedAuthFetch).toHaveBeenCalledWith(
			"/v1/auth/register",
			{
				email: "player@test.com",
				password: "secret123", // pragma: allowlist secret
				display_name: "Player",
			},
			undefined,
		);
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-123");
	});

	it("register forwards the Turnstile token as the cf-turnstile-response header", async () => {
		mockedAuthFetch.mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.register("player@test.com", "secret123", "Player", "tok-xyz");
		});

		expect(mockedAuthFetch).toHaveBeenCalledWith(
			"/v1/auth/register",
			{
				email: "player@test.com",
				password: "secret123", // pragma: allowlist secret
				display_name: "Player",
			},
			{ "cf-turnstile-response": "tok-xyz" },
		);
	});

	it("verify calls verifyEmail and resolves", async () => {
		vi.mocked(verifyEmail).mockResolvedValueOnce({ message: "ok" });

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.verify("verify-token");
		});

		expect(verifyEmail).toHaveBeenCalledWith("verify-token");
	});

	it("resendVerification calls the resend API", async () => {
		vi.mocked(resendVerification).mockResolvedValueOnce({ message: "sent" });

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.resendVerification();
		});

		expect(resendVerification).toHaveBeenCalledOnce();
	});

	it("forgotPassword calls the forgot-password API with the email", async () => {
		vi.mocked(forgotPassword).mockResolvedValueOnce({ message: "sent" });

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.forgotPassword("player@test.com");
		});

		expect(forgotPassword).toHaveBeenCalledWith("player@test.com");
	});

	it("resetPassword calls the reset-password API with token + password", async () => {
		vi.mocked(resetPassword).mockResolvedValueOnce({ message: "reset" });

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.resetPassword("tok-1", "NewPass123");
		});

		expect(resetPassword).toHaveBeenCalledWith("tok-1", "NewPass123");
	});

	it("changePassword saves the reissued access token", async () => {
		vi.mocked(changePassword).mockResolvedValueOnce(fakeTokens);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.changePassword("OldPass123", "NewPass123");
		});

		expect(changePassword).toHaveBeenCalledWith("OldPass123", "NewPass123");
		expect(mockedSaveTokens).toHaveBeenCalledWith("acc-123");
	});

	it("normalizes email_verified into a camel-case emailVerified field", async () => {
		mockedGetAccessToken.mockReturnValue("acc-123");
		mockedApiFetch.mockResolvedValueOnce({ ...fakeUser, email_verified: false });

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.user?.email).toBe("player@test.com");
		});

		expect(result.current.user?.emailVerified).toBe(false);
		expect(result.current.emailVerified).toBe(false);
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

		expect(result.current.user).toEqual(normalizedUser);
	});
});
