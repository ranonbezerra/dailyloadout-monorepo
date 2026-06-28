import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { RegisterPage } from "./RegisterPage";

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

// Stand in for the real Turnstile widget: when a site key is "configured" it
// hands a solved token up via onToken and exposes a reset() through the ref.
const turnstileReset = vi.fn();
vi.mock("../components/TurnstileWidget", () => ({
	TurnstileWidget: ({
		onToken,
		ref,
	}: {
		onToken: (t: string | null) => void;
		ref?: React.Ref<{ reset: () => void }>;
	}) => {
		if (ref && typeof ref === "object") {
			(ref as { current: { reset: () => void } | null }).current = { reset: turnstileReset };
		}
		return (
			<button type="button" data-testid="solve-turnstile" onClick={() => onToken("test-token")}>
				solve
			</button>
		);
	},
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

function renderRegisterPage() {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={["/register"]}>
				<Routes>
					<Route path="/register" element={<RegisterPage />} />
					<Route path="/library" element={<div data-testid="library-page">Library</div>} />
				</Routes>
			</MemoryRouter>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("RegisterPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUseAuthContext.mockReturnValue({ ...defaultAuth });
	});

	it("renders display name, email, and password inputs and a create-account button", () => {
		renderRegisterPage();

		expect(screen.getByRole("textbox", { name: /display name/i })).toBeInTheDocument();
		expect(screen.getByRole("textbox", { name: /email/i })).toBeInTheDocument();
		expect(screen.getByPlaceholderText("Choose a password")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
	});

	it("has a link to the login page", () => {
		renderRegisterPage();

		const signInLink = screen.getByRole("link", { name: /sign in/i });
		expect(signInLink).toBeInTheDocument();
		expect(signInLink).toHaveAttribute("href", "/login");
	});

	it("redirects to /library when authenticated", () => {
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, isAuthenticated: true });

		renderRegisterPage();

		expect(screen.getByTestId("library-page")).toBeInTheDocument();
		expect(screen.queryByRole("button", { name: /create account/i })).not.toBeInTheDocument();
	});

	it("does not redirect when still loading", () => {
		mockUseAuthContext.mockReturnValue({
			...defaultAuth,
			isLoading: true,
			isAuthenticated: false,
		});

		renderRegisterPage();

		expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
	});

	it("shows validation error for short display name on submit", async () => {
		renderRegisterPage();

		const displayName = screen.getByRole("textbox", { name: /display name/i });
		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Choose a password");

		fireEvent.change(displayName, { target: { value: "A" } });
		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Display name must be at least 2 characters")).toBeInTheDocument();
		});
	});

	it("shows validation error for invalid email on submit", async () => {
		renderRegisterPage();

		const displayName = screen.getByRole("textbox", { name: /display name/i });
		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Choose a password");

		fireEvent.change(displayName, { target: { value: "John Doe" } });
		fireEvent.change(email, { target: { value: "not-an-email" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Invalid email")).toBeInTheDocument();
		});
	});

	it("shows validation error for short password on submit", async () => {
		renderRegisterPage();

		const displayName = screen.getByRole("textbox", { name: /display name/i });
		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Choose a password");

		fireEvent.change(displayName, { target: { value: "John Doe" } });
		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "short" } });

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument();
		});
	});

	it("calls register on valid form submission", async () => {
		const registerFn = vi.fn().mockResolvedValueOnce(undefined);
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, register: registerFn });

		renderRegisterPage();

		const displayName = screen.getByRole("textbox", { name: /display name/i });
		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Choose a password");

		fireEvent.change(displayName, { target: { value: "John Doe" } });
		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			// No Turnstile solved → token arg is undefined.
			expect(registerFn).toHaveBeenCalledWith(
				"test@test.com",
				"password123",
				"John Doe",
				undefined,
			);
		});
	});

	it("passes the solved Turnstile token to register", async () => {
		const registerFn = vi.fn().mockResolvedValueOnce(undefined);
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, register: registerFn });

		renderRegisterPage();

		fireEvent.change(screen.getByRole("textbox", { name: /display name/i }), {
			target: { value: "John Doe" },
		});
		fireEvent.change(screen.getByRole("textbox", { name: /email/i }), {
			target: { value: "test@test.com" },
		});
		fireEvent.change(screen.getByPlaceholderText("Choose a password"), {
			target: { value: "password123" },
		});

		// Simulate Cloudflare solving the challenge before submit.
		fireEvent.click(screen.getByTestId("solve-turnstile"));

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(registerFn).toHaveBeenCalledWith(
				"test@test.com",
				"password123",
				"John Doe",
				"test-token",
			);
		});
	});

	it("resets the Turnstile widget when registration fails", async () => {
		const registerFn = vi.fn().mockRejectedValueOnce(new Error("Email already exists"));
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, register: registerFn });

		renderRegisterPage();

		fireEvent.change(screen.getByRole("textbox", { name: /display name/i }), {
			target: { value: "John Doe" },
		});
		fireEvent.change(screen.getByRole("textbox", { name: /email/i }), {
			target: { value: "test@test.com" },
		});
		fireEvent.change(screen.getByPlaceholderText("Choose a password"), {
			target: { value: "password123" },
		});
		fireEvent.click(screen.getByTestId("solve-turnstile"));

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(turnstileReset).toHaveBeenCalled();
		});
	});

	it("shows error notification when registration fails with Error", async () => {
		const registerFn = vi.fn().mockRejectedValueOnce(new Error("Email already exists"));
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, register: registerFn });

		renderRegisterPage();

		const displayName = screen.getByRole("textbox", { name: /display name/i });
		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Choose a password");

		fireEvent.change(displayName, { target: { value: "John Doe" } });
		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Registration failed",
					message: "Email already exists",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when registration fails with non-Error", async () => {
		const registerFn = vi.fn().mockRejectedValueOnce("something went wrong");
		mockUseAuthContext.mockReturnValue({ ...defaultAuth, register: registerFn });

		renderRegisterPage();

		const displayName = screen.getByRole("textbox", { name: /display name/i });
		const email = screen.getByRole("textbox", { name: /email/i });
		const password = screen.getByPlaceholderText("Choose a password");

		fireEvent.change(displayName, { target: { value: "John Doe" } });
		fireEvent.change(email, { target: { value: "test@test.com" } });
		fireEvent.change(password, { target: { value: "password123" } });

		const form = screen.getByRole("button", { name: /create account/i }).closest("form");
		if (!form) throw new Error("form not found");
		fireEvent.submit(form);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Registration failed",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});
});
