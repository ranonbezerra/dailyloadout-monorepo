import { apiFetch, authFetch } from "@slate/shared/api";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	confirmMfa,
	disableMfa,
	enrollMfa,
	getMfaStatus,
	mfaLogin,
	regenerateRecoveryCodes,
} from "./mfa-api";

vi.mock("@slate/shared/api", () => ({
	apiFetch: vi.fn(),
	authFetch: vi.fn(),
}));

const mockedApiFetch = vi.mocked(apiFetch);
const mockedAuthFetch = vi.mocked(authFetch);

describe("mfa-api", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("mfaLogin posts the challenge token + code via authFetch", async () => {
		mockedAuthFetch.mockResolvedValueOnce({ access_token: "a1", mfa_required: false });
		await mfaLogin("tok", "123456");
		expect(mockedAuthFetch).toHaveBeenCalledWith("/v1/auth/mfa/login", {
			mfa_token: "tok",
			code: "123456",
		});
	});

	it("getMfaStatus GETs the status endpoint", async () => {
		mockedApiFetch.mockResolvedValueOnce({ enabled: true, recovery_codes_remaining: 7 });
		const res = await getMfaStatus();
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/mfa/status");
		expect(res).toEqual({ enabled: true, recovery_codes_remaining: 7 });
	});

	it("enrollMfa POSTs to the enroll endpoint", async () => {
		mockedApiFetch.mockResolvedValueOnce({ secret: "S", otpauth_uri: "otpauth://x" });
		await enrollMfa();
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/mfa/enroll", { method: "POST" });
	});

	it("confirmMfa POSTs the code", async () => {
		mockedApiFetch.mockResolvedValueOnce({ recovery_codes: ["a"] });
		await confirmMfa("123456");
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/mfa/confirm", {
			method: "POST",
			body: JSON.stringify({ code: "123456" }),
		});
	});

	it("regenerateRecoveryCodes POSTs the code", async () => {
		mockedApiFetch.mockResolvedValueOnce({ recovery_codes: ["a", "b"] });
		await regenerateRecoveryCodes("123456");
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/mfa/recovery-codes", {
			method: "POST",
			body: JSON.stringify({ code: "123456" }),
		});
	});

	it("disableMfa POSTs the code", async () => {
		mockedApiFetch.mockResolvedValueOnce({ message: "MFA disabled" });
		await disableMfa("123456");
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/mfa/disable", {
			method: "POST",
			body: JSON.stringify({ code: "123456" }),
		});
	});
});
