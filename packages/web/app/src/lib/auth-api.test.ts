import { apiFetch } from "@dl/shared/api";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { resendVerification, verifyEmail } from "./auth-api";

vi.mock("@dl/shared/api", () => ({
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
});
