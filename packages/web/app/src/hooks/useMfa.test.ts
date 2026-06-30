import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { createElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	confirmMfa,
	disableMfa,
	enrollMfa,
	getMfaStatus,
	regenerateRecoveryCodes,
} from "../lib/mfa-api";
import { useMfa } from "./useMfa";

vi.mock("../lib/mfa-api", () => ({
	getMfaStatus: vi.fn(),
	enrollMfa: vi.fn(),
	confirmMfa: vi.fn(),
	regenerateRecoveryCodes: vi.fn(),
	disableMfa: vi.fn(),
}));

function wrapper({ children }: { children: ReactNode }) {
	const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return createElement(QueryClientProvider, { client: qc }, children);
}

describe("useMfa", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.mocked(getMfaStatus).mockResolvedValue({ enabled: false, recovery_codes_remaining: 0 });
	});

	it("loads MFA status", async () => {
		vi.mocked(getMfaStatus).mockResolvedValueOnce({
			enabled: true,
			recovery_codes_remaining: 5,
		});
		const { result } = renderHook(() => useMfa(), { wrapper });
		await waitFor(() => expect(result.current.status?.enabled).toBe(true));
		expect(result.current.status?.recovery_codes_remaining).toBe(5);
	});

	it("enroll calls the enroll API", async () => {
		vi.mocked(enrollMfa).mockResolvedValueOnce({ secret: "S", otpauth_uri: "otpauth://x" });
		const { result } = renderHook(() => useMfa(), { wrapper });
		await act(async () => {
			await result.current.enroll();
		});
		expect(enrollMfa).toHaveBeenCalledOnce();
	});

	it("confirm calls the confirm API with the code", async () => {
		vi.mocked(confirmMfa).mockResolvedValueOnce({ recovery_codes: ["a"] });
		const { result } = renderHook(() => useMfa(), { wrapper });
		await act(async () => {
			await result.current.confirm("123456");
		});
		expect(confirmMfa).toHaveBeenCalledWith("123456");
	});

	it("regenerate calls the regenerate API", async () => {
		vi.mocked(regenerateRecoveryCodes).mockResolvedValueOnce({ recovery_codes: ["a", "b"] });
		const { result } = renderHook(() => useMfa(), { wrapper });
		await act(async () => {
			await result.current.regenerate("123456");
		});
		expect(regenerateRecoveryCodes).toHaveBeenCalledWith("123456");
	});

	it("disable calls the disable API", async () => {
		vi.mocked(disableMfa).mockResolvedValueOnce({ message: "MFA disabled" });
		const { result } = renderHook(() => useMfa(), { wrapper });
		await act(async () => {
			await result.current.disable("123456");
		});
		expect(disableMfa).toHaveBeenCalledWith("123456");
	});
});
