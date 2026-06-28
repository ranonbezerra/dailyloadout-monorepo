import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { createWrapper } from "../test/wrapper";

vi.mock("@dl/shared/api", () => ({
	authFetch: vi.fn(),
	clearTokens: vi.fn(),
	getAccessToken: vi.fn(),
	refreshSession: vi.fn(),
	saveTokens: vi.fn(),
}));

import {
	authFetch,
	clearTokens,
	getAccessToken,
	refreshSession,
	saveTokens,
} from "@dl/shared/api";
import { useAuth } from "./useAuth";

beforeEach(() => {
	vi.clearAllMocks();
});

describe("useAuth", () => {
	it("bootstraps via silent refresh when no token is in memory", async () => {
		(getAccessToken as Mock).mockReturnValue(null);
		(refreshSession as Mock).mockResolvedValue(true);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });
		await waitFor(() => expect(result.current.isLoading).toBe(false));
		expect(refreshSession).toHaveBeenCalled();
	});

	it("login stores the access token", async () => {
		(getAccessToken as Mock).mockReturnValue(null);
		(refreshSession as Mock).mockResolvedValue(false);
		(authFetch as Mock).mockResolvedValue({ access_token: "tok" });

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });
		await result.current.login("a@b.com", "secret123");
		expect(authFetch).toHaveBeenCalledWith("/v1/auth/login", {
			email: "a@b.com",
			password: "secret123", // pragma: allowlist secret
		});
		expect(saveTokens).toHaveBeenCalledWith("tok");
	});

	it("logout hits the endpoint and clears tokens", async () => {
		(getAccessToken as Mock).mockReturnValue("tok");
		(refreshSession as Mock).mockResolvedValue(true);
		(authFetch as Mock).mockResolvedValue(undefined);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });
		await result.current.logout();
		expect(authFetch).toHaveBeenCalledWith("/v1/auth/logout", {});
		expect(clearTokens).toHaveBeenCalled();
	});

	it("logout still clears tokens when the endpoint throws", async () => {
		(getAccessToken as Mock).mockReturnValue("tok");
		(refreshSession as Mock).mockResolvedValue(true);
		(authFetch as Mock).mockRejectedValue(new Error("network"));

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });
		await result.current.logout();
		expect(clearTokens).toHaveBeenCalled();
	});
});
