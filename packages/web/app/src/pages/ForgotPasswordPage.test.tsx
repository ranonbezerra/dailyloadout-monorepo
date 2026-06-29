import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { ForgotPasswordPage } from "./ForgotPasswordPage";

vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: vi.fn(),
	AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockUseAuthContext = useAuthContext as Mock;

const defaultAuth = {
	forgotPassword: vi.fn(),
	isForgotPasswordPending: false,
};

function renderPage() {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={["/forgot-password"]}>
				<ForgotPasswordPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("ForgotPasswordPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth });
	});

	it("renders the email field and submit button", () => {
		renderPage();
		expect(screen.getByRole("textbox", { name: /email/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /send reset link/i })).toBeInTheDocument();
	});

	it("validates the email before submitting", async () => {
		const forgotFn = vi.fn();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, forgotPassword: forgotFn });
		renderPage();

		fireEvent.change(screen.getByRole("textbox", { name: /email/i }), {
			target: { value: "not-an-email" },
		});
		const form = screen.getByRole("button", { name: /send reset link/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Invalid email")).toBeInTheDocument();
		});
		expect(forgotFn).not.toHaveBeenCalled();
	});

	it("calls forgotPassword and shows the neutral confirmation on submit", async () => {
		const forgotFn = vi.fn().mockResolvedValueOnce(undefined);
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, forgotPassword: forgotFn });
		renderPage();

		fireEvent.change(screen.getByRole("textbox", { name: /email/i }), {
			target: { value: "user@example.com" },
		});
		const form = screen.getByRole("button", { name: /send reset link/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(forgotFn).toHaveBeenCalledWith("user@example.com");
			expect(screen.getByText(/Check your inbox/i)).toBeInTheDocument();
		});
	});

	it("still shows the confirmation even if the request rejects (neutral)", async () => {
		const forgotFn = vi.fn().mockRejectedValueOnce(new Error("boom"));
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, forgotPassword: forgotFn });
		renderPage();

		fireEvent.change(screen.getByRole("textbox", { name: /email/i }), {
			target: { value: "user@example.com" },
		});
		const form = screen.getByRole("button", { name: /send reset link/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText(/Check your inbox/i)).toBeInTheDocument();
		});
	});
});
