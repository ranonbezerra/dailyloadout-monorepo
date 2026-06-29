import { apiFetch } from "@slate/shared/api";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	changePassword,
	forgotPassword,
	resendVerification,
	resetPassword,
	verifyEmail,
} from "./auth-api";

vi.mock("@slate/shared/api", () => ({
	apiFetch: vi.fn(),
}));

const mockedApiFetch = vi.mocked(apiFetch);

describe("auth-api", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("verifyEmail POSTs the token to /v1/auth/verify", async () => {
		mockedApiFetch.mockResolvedValueOnce({ message: "ok" });

		const res = await verifyEmail("tok-123");

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/verify", {
			method: "POST",
			body: JSON.stringify({ token: "tok-123" }),
		});
		expect(res).toEqual({ message: "ok" });
	});

	it("resendVerification POSTs to /v1/auth/resend-verification", async () => {
		mockedApiFetch.mockResolvedValueOnce({ message: "sent" });

		const res = await resendVerification();

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/resend-verification", {
			method: "POST",
			body: JSON.stringify({}),
		});
		expect(res).toEqual({ message: "sent" });
	});

	it("forgotPassword POSTs the email to /v1/auth/forgot-password", async () => {
		mockedApiFetch.mockResolvedValueOnce({ message: "sent" });

		const res = await forgotPassword("a@b.com");

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/forgot-password", {
			method: "POST",
			body: JSON.stringify({ email: "a@b.com" }),
		});
		expect(res).toEqual({ message: "sent" });
	});

	it("resetPassword POSTs token + new_password to /v1/auth/reset-password", async () => {
		mockedApiFetch.mockResolvedValueOnce({ message: "reset" });

		const res = await resetPassword("tok-9", "NewPass123");

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/reset-password", {
			method: "POST",
			body: JSON.stringify({ token: "tok-9", new_password: "NewPass123" }),
		});
		expect(res).toEqual({ message: "reset" });
	});

	it("changePassword POSTs in cookie mode and returns tokens", async () => {
		mockedApiFetch.mockResolvedValueOnce({ access_token: "a1", refresh_token: "" });

		const res = await changePassword("OldPass123", "NewPass123");

		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/change-password", {
			method: "POST",
			headers: { "X-Auth-Mode": "cookie" },
			body: JSON.stringify({ current_password: "OldPass123", new_password: "NewPass123" }),
		});
		expect(res).toEqual({ access_token: "a1", refresh_token: "" });
	});
});
