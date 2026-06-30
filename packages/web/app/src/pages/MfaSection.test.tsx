import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useMfa } from "../hooks/useMfa";
import { MfaSection } from "./MfaSection";

vi.mock("../hooks/useMfa", () => ({ useMfa: vi.fn() }));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));
vi.mock("qrcode.react", () => ({ QRCodeSVG: () => <svg data-testid="qr" aria-label="qr" /> }));

const mockUseMfa = vi.mocked(useMfa);

function makeMfa(overrides: Partial<ReturnType<typeof useMfa>> = {}): ReturnType<typeof useMfa> {
	return {
		status: { enabled: false, recovery_codes_remaining: 0 },
		isStatusLoading: false,
		enroll: vi.fn().mockResolvedValue({ secret: "ABC123", otpauth_uri: "otpauth://totp/x" }),
		confirm: vi.fn().mockResolvedValue({ recovery_codes: ["aaa-bbb", "ccc-ddd"] }),
		regenerate: vi.fn().mockResolvedValue({ recovery_codes: ["eee-fff"] }),
		disable: vi.fn().mockResolvedValue({ message: "MFA disabled" }),
		isEnrolling: false,
		isConfirming: false,
		isRegenerating: false,
		isDisabling: false,
		...overrides,
	};
}

function renderSection() {
	return render(
		<MantineProvider>
			<MfaSection />
		</MantineProvider>,
	);
}

describe("MfaSection", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseMfa.mockReturnValue(makeMfa());
	});

	it("shows the disabled state with an enable button", () => {
		renderSection();
		expect(screen.getByText("Off")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /enable two-factor/i })).toBeInTheDocument();
	});

	it("starts enrollment and shows the QR + confirm form", async () => {
		const enroll = vi.fn().mockResolvedValue({ secret: "KEY99", otpauth_uri: "otpauth://totp/x" });
		mockUseMfa.mockReturnValue(makeMfa({ enroll }));

		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /enable two-factor/i }));

		await waitFor(() => expect(screen.getByTestId("qr")).toBeInTheDocument());
		expect(enroll).toHaveBeenCalledOnce();
		expect(screen.getByText("KEY99")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
	});

	it("confirms enrollment and shows recovery codes", async () => {
		const confirm = vi.fn().mockResolvedValue({ recovery_codes: ["aaa-bbb", "ccc-ddd"] });
		mockUseMfa.mockReturnValue(makeMfa({ confirm }));

		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /enable two-factor/i }));

		const codeInput = await screen.findByPlaceholderText("123456");
		fireEvent.change(codeInput, { target: { value: "123456" } });
		const form = screen.getByRole("button", { name: /confirm/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(confirm).toHaveBeenCalledWith("123456");
			expect(screen.getByText("aaa-bbb")).toBeInTheDocument();
			expect(screen.getByText("ccc-ddd")).toBeInTheDocument();
		});
	});

	it("shows the enabled state with remaining codes", () => {
		mockUseMfa.mockReturnValue(
			makeMfa({ status: { enabled: true, recovery_codes_remaining: 4 } }),
		);
		renderSection();
		expect(screen.getByText("On")).toBeInTheDocument();
		expect(screen.getByText(/4 recovery code/i)).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /disable/i })).toBeInTheDocument();
	});

	it("disables MFA with a code", async () => {
		const disable = vi.fn().mockResolvedValue({ message: "MFA disabled" });
		mockUseMfa.mockReturnValue(
			makeMfa({ status: { enabled: true, recovery_codes_remaining: 4 }, disable }),
		);
		renderSection();

		fireEvent.change(screen.getByPlaceholderText("123456"), { target: { value: "654321" } });
		fireEvent.click(screen.getByRole("button", { name: /disable/i }));

		await waitFor(() => expect(disable).toHaveBeenCalledWith("654321"));
	});

	it("regenerates recovery codes with a code", async () => {
		const regenerate = vi.fn().mockResolvedValue({ recovery_codes: ["eee-fff"] });
		mockUseMfa.mockReturnValue(
			makeMfa({ status: { enabled: true, recovery_codes_remaining: 4 }, regenerate }),
		);
		renderSection();

		fireEvent.change(screen.getByPlaceholderText("123456"), { target: { value: "654321" } });
		fireEvent.click(screen.getByRole("button", { name: /regenerate codes/i }));

		await waitFor(() => {
			expect(regenerate).toHaveBeenCalledWith("654321");
			expect(screen.getByText("eee-fff")).toBeInTheDocument();
		});
	});

	it("validates the code before disabling", async () => {
		const disable = vi.fn();
		mockUseMfa.mockReturnValue(
			makeMfa({ status: { enabled: true, recovery_codes_remaining: 4 }, disable }),
		);
		renderSection();

		// No code entered → the action is blocked by validation.
		fireEvent.click(screen.getByRole("button", { name: /disable/i }));
		await waitFor(() => expect(screen.getByText("Enter a current code")).toBeInTheDocument());
		expect(disable).not.toHaveBeenCalled();
	});
});
