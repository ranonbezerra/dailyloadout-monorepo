import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { LoginPage } from "./LoginPage";

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

const defaultAuth = {
	user: null,
	isLoading: false,
	isAuthenticated: false,
	login: vi.fn(),
	logout: vi.fn(),
	register: vi.fn(),
	loginError: null,
	registerError: null,
	isLoginPending: false,
	isRegisterPending: false,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderLoginPage(initialEntry = "/login") {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={[initialEntry]}>
				<Routes>
					<Route path="/login" element={<LoginPage />} />
					<Route path="/library" element={<div data-testid="library-page">Library</div>} />
				</Routes>
			</MemoryRouter>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LoginPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth });
	});

	it("renders email and password inputs and a sign-in button", () => {
		renderLoginPage();

		expect(screen.getByRole("textbox", { name: /email/i })).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Your password")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
	});

	it("has a link to the register page", () => {
		renderLoginPage();

		const registerLink = screen.getByRole("link", { name: /register/i });
		expect(registerLink).toBeInTheDocument();
		expect(registerLink).toHaveAttribute("href", "/register");
	});

	it("redirects to /library when authenticated", () => {
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, isAuthenticated: true });

		renderLoginPage();

		expect(screen.getByTestId("library-page")).toBeInTheDocument();
		expect(screen.queryByRole("button", { name: /sign in/i })).not.toBeInTheDocument();
	});

	it("does not redirect when still loading", () => {
		mockUseAuthContext.mockReturnValue({
			...defaultAuth,
			isLoading: true,
			isAuthenticated: false,
		});

		renderLoginPage();

		// Should still show login form while loading
		expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
	});

	it("shows validation error for invalid email on submit", async () => {
		renderLoginPage();

		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Your password");

		fireEvent.change(email, { target: { value: "not-an-email" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /sign in/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Invalid email")).toBeInTheDocument();
		});
	});

	it("shows validation error for short password on submit", async () => {
		renderLoginPage();

		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Your password");

		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "abc" } });

		const form = screen.getByRole("button", { name: /sign in/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Password must be at least 6 characters")).toBeInTheDocument();
		});
	});

	it("calls login on valid form submission", async () => {
		const loginFn = vi.fn().mockResolvedValueOnce(undefined);
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, login: loginFn });

		renderLoginPage();

		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Your password");

		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /sign in/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(loginFn).toHaveBeenCalledWith("test@test.com", "password123");
		});
	});

	it("shows error notification when login fails with Error", async () => {
		const loginFn = vi.fn().mockRejectedValueOnce(new Error("Invalid credentials"));
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, login: loginFn });

		renderLoginPage();

		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Your password");

		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /sign in/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Login failed",
					message: "Invalid credentials",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when login fails with non-Error", async () => {
		const loginFn = vi.fn().mockRejectedValueOnce("something went wrong");
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, login: loginFn });

		renderLoginPage();

		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Your password");

		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /sign in/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Login failed",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});

	it("renders the social login buttons", () => {
		renderLoginPage();

		expect(screen.getByRole("button", { name: /continue with google/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /continue with twitch/i })).toBeInTheDocument();
	});

	it("toasts a mapped message when an oauth ?error= param is present", async () => {
		renderLoginPage("/login?error=account_exists");

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Sign-in failed",
					message: expect.stringContaining("An account with this email already exists"),
					color: "red",
				}),
			);
		});
	});
});
