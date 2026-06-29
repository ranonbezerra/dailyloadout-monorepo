import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { makeAuthContext } from "../test/wrapper";
import { VerifyEmailPage } from "./VerifyEmailPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: vi.fn(),
	AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

const mockUseAuthContext = useAuthContext as Mock;

function renderVerifyPage(initialEntry: string) {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={[initialEntry]}>
				<Routes>
					<Route path="/verify-email" element={<VerifyEmailPage />} />
					<Route path="/play" element={<div data-testid="play-page">Play</div>} />
				</Routes>
			</MemoryRouter>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("VerifyEmailPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("verifies the token and shows the success state, refetching the user", async () => {
		const verify = vi.fn().mockResolvedValue(undefined);
		const refetchUser = vi.fn();
		mockUseAuthContext.mockReturnValue(makeAuthContext({ verify, refetchUser }));

		renderVerifyPage("/verify-email?token=good-token");

		await waitFor(() => {
			expect(screen.getByText("Email verified — you're all set.")).toBeInTheDocument();
		});
		expect(verify).toHaveBeenCalledWith("good-token");
		expect(refetchUser).toHaveBeenCalled();
		// Success offers a way back into the app; no Resend.
		expect(screen.getByRole("link", { name: /continue to slate/i })).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /resend verification email/i }),
		).not.toBeInTheDocument();
	});

	it("shows the expired/invalid error state with a Resend button", async () => {
		const verify = vi.fn().mockRejectedValue(new Error("invalid or expired token"));
		mockUseAuthContext.mockReturnValue(makeAuthContext({ verify }));

		renderVerifyPage("/verify-email?token=expired-token");

		await waitFor(() => {
			expect(screen.getByText(/invalid or has expired/i)).toBeInTheDocument();
		});
		expect(screen.getByRole("button", { name: /resend verification email/i })).toBeInTheDocument();
	});

	it("clicking Resend on the error state calls resendVerification and toasts success", async () => {
		const verify = vi.fn().mockRejectedValue(new Error("expired"));
		const resendVerification = vi.fn().mockResolvedValue(undefined);
		mockUseAuthContext.mockReturnValue(makeAuthContext({ verify, resendVerification }));

		renderVerifyPage("/verify-email?token=expired-token");

		const resendBtn = await screen.findByRole("button", {
			name: /resend verification email/i,
		});
		resendBtn.click();

		await waitFor(() => {
			expect(resendVerification).toHaveBeenCalled();
		});
		expect(notifications.show).toHaveBeenCalledWith(expect.objectContaining({ color: "green" }));
	});

	it("shows the missing-token state when no token is present", () => {
		mockUseAuthContext.mockReturnValue(makeAuthContext());

		renderVerifyPage("/verify-email");

		expect(screen.getByText(/missing its verification token/i)).toBeInTheDocument();
	});
});
