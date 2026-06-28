import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { makeAuthContext } from "../test/wrapper";
import { VerifyEmailBanner } from "./VerifyEmailBanner";

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

function renderBanner() {
	return render(
		<MantineProvider>
			<VerifyEmailBanner />
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("VerifyEmailBanner", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		sessionStorage.clear();
	});

	it("shows when the user is authenticated but not verified", () => {
		mockUseAuthContext.mockReturnValue(
			makeAuthContext({ isAuthenticated: true, emailVerified: false }),
		);

		renderBanner();

		expect(screen.getByText("Verify your email")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /resend verification/i })).toBeInTheDocument();
	});

	it("is hidden when the user is verified", () => {
		mockUseAuthContext.mockReturnValue(
			makeAuthContext({ isAuthenticated: true, emailVerified: true }),
		);

		renderBanner();

		expect(screen.queryByText("Verify your email")).not.toBeInTheDocument();
	});

	it("is hidden when the user is not authenticated", () => {
		mockUseAuthContext.mockReturnValue(
			makeAuthContext({ isAuthenticated: false, emailVerified: false }),
		);

		renderBanner();

		expect(screen.queryByText("Verify your email")).not.toBeInTheDocument();
	});

	it("Resend triggers resendVerification and a success toast", async () => {
		const resendVerification = vi.fn().mockResolvedValue(undefined);
		mockUseAuthContext.mockReturnValue(
			makeAuthContext({ isAuthenticated: true, emailVerified: false, resendVerification }),
		);

		renderBanner();

		fireEvent.click(screen.getByRole("button", { name: /resend verification/i }));

		await waitFor(() => {
			expect(resendVerification).toHaveBeenCalled();
		});
		expect(notifications.show).toHaveBeenCalledWith(expect.objectContaining({ color: "green" }));
	});

	it("can be dismissed for the session", () => {
		mockUseAuthContext.mockReturnValue(
			makeAuthContext({ isAuthenticated: true, emailVerified: false }),
		);

		renderBanner();

		fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));

		expect(screen.queryByText("Verify your email")).not.toBeInTheDocument();
		expect(sessionStorage.getItem("dl.verifyEmailBanner.dismissed")).toBe("1");
	});

	it("stays hidden after a session-scoped dismissal across remounts", () => {
		sessionStorage.setItem("dl.verifyEmailBanner.dismissed", "1");
		mockUseAuthContext.mockReturnValue(
			makeAuthContext({ isAuthenticated: true, emailVerified: false }),
		);

		renderBanner();

		expect(screen.queryByText("Verify your email")).not.toBeInTheDocument();
	});
});
