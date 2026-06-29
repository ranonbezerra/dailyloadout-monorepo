import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { ResetPasswordPage } from "./ResetPasswordPage";

vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: vi.fn(),
	AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

const mockUseAuthContext = useAuthContext as Mock;

const defaultAuth = {
	resetPassword: vi.fn(),
	isResetPasswordPending: false,
};

function renderPage(entry = "/reset-password?token=tok-123") {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={[entry]}>
				<Routes>
					<Route path="/reset-password" element={<ResetPasswordPage />} />
					<Route path="/login" element={<div data-testid="login-page">Login</div>} />
					<Route path="/forgot-password" element={<div data-testid="forgot-page">Forgot</div>} />
				</Routes>
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("ResetPasswordPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth });
	});

	it("shows a missing-token state when no token is present", () => {
		renderPage("/reset-password");
		expect(screen.getByText(/Missing token/i)).toBeInTheDocument();
		expect(screen.queryByPlaceholderText("Choose a new password")).not.toBeInTheDocument();
	});

	it("renders the password fields when a token is present", () => {
		renderPage();
		expect(screen.getByPlaceholderText("Choose a new password")).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Repeat the new password")).toBeInTheDocument();
	});

	it("validates complexity before submitting", async () => {
		const resetFn = vi.fn();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, resetPassword: resetFn });
		renderPage();

		fireEvent.change(screen.getByPlaceholderText("Choose a new password"), {
			target: { value: "weak" },
		});
		fireEvent.change(screen.getByPlaceholderText("Repeat the new password"), {
			target: { value: "weak" },
		});
		const form = screen.getByRole("button", { name: /reset password/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument();
		});
		expect(resetFn).not.toHaveBeenCalled();
	});

	it("rejects mismatched confirmation", async () => {
		const resetFn = vi.fn();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, resetPassword: resetFn });
		renderPage();

		fireEvent.change(screen.getByPlaceholderText("Choose a new password"), {
			target: { value: "NewPass123" },
		});
		fireEvent.change(screen.getByPlaceholderText("Repeat the new password"), {
			target: { value: "Other9999" },
		});
		const form = screen.getByRole("button", { name: /reset password/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
		});
		expect(resetFn).not.toHaveBeenCalled();
	});

	it("resets and navigates to login on success", async () => {
		const resetFn = vi.fn().mockResolvedValueOnce(undefined);
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, resetPassword: resetFn });
		renderPage();

		fireEvent.change(screen.getByPlaceholderText("Choose a new password"), {
			target: { value: "NewPass123" },
		});
		fireEvent.change(screen.getByPlaceholderText("Repeat the new password"), {
			target: { value: "NewPass123" },
		});
		const form = screen.getByRole("button", { name: /reset password/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(resetFn).toHaveBeenCalledWith("tok-123", "NewPass123");
			expect(screen.getByTestId("login-page")).toBeInTheDocument();
		});
	});

	it("shows an error notification when the reset fails", async () => {
		const resetFn = vi.fn().mockRejectedValueOnce(new Error("Invalid or expired reset token"));
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, resetPassword: resetFn });
		renderPage();

		fireEvent.change(screen.getByPlaceholderText("Choose a new password"), {
			target: { value: "NewPass123" },
		});
		fireEvent.change(screen.getByPlaceholderText("Repeat the new password"), {
			target: { value: "NewPass123" },
		});
		const form = screen.getByRole("button", { name: /reset password/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Reset failed",
					message: "Invalid or expired reset token",
					color: "red",
				}),
			);
		});
	});
});
