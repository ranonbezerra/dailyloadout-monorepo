import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { ChangePasswordPage } from "./ChangePasswordPage";

vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: vi.fn(),
	AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

const mockUseAuthContext = useAuthContext as Mock;

const defaultAuth = {
	changePassword: vi.fn(),
	isChangePasswordPending: false,
};

function renderPage() {
	return render(
		<MantineProvider>
			<ChangePasswordPage />
		</MantineProvider>,
	);
}

function fillForm(current: string, next: string, confirm: string) {
	fireEvent.change(screen.getByPlaceholderText("Your current password"), {
		target: { value: current },
	});
	fireEvent.change(screen.getByPlaceholderText("Choose a new password"), {
		target: { value: next },
	});
	fireEvent.change(screen.getByPlaceholderText("Repeat the new password"), {
		target: { value: confirm },
	});
}

function submit() {
	const form = screen.getByRole("button", { name: /update password/i }).closest("form");
	if (!form) throw new Error("form not found");
	fireEvent.submit(form);
}

describe("ChangePasswordPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth });
	});

	it("renders the three password fields", () => {
		renderPage();
		expect(screen.getByPlaceholderText("Your current password")).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Choose a new password")).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Repeat the new password")).toBeInTheDocument();
	});

	it("rejects a weak new password", async () => {
		const changeFn = vi.fn();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, changePassword: changeFn });
		renderPage();

		fillForm("OldPass123", "weak", "weak");
		submit();

		await waitFor(() => {
			expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument();
		});
		expect(changeFn).not.toHaveBeenCalled();
	});

	it("rejects mismatched confirmation", async () => {
		const changeFn = vi.fn();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, changePassword: changeFn });
		renderPage();

		fillForm("OldPass123", "NewPass123", "Other9999");
		submit();

		await waitFor(() => {
			expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
		});
		expect(changeFn).not.toHaveBeenCalled();
	});

	it("calls changePassword and shows a success notification", async () => {
		const changeFn = vi.fn().mockResolvedValueOnce(undefined);
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, changePassword: changeFn });
		renderPage();

		fillForm("OldPass123", "NewPass123", "NewPass123");
		submit();

		await waitFor(() => {
			expect(changeFn).toHaveBeenCalledWith("OldPass123", "NewPass123");
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Password changed", color: "green" }),
			);
		});
	});

	it("shows an error notification when the change fails", async () => {
		const changeFn = vi.fn().mockRejectedValueOnce(new Error("Current password is incorrect"));
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, changePassword: changeFn });
		renderPage();

		fillForm("WrongPass1", "NewPass123", "NewPass123");
		submit();

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Couldn't change password",
					message: "Current password is incorrect",
					color: "red",
				}),
			);
		});
	});
});
