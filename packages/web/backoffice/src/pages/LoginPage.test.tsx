import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";

const notifyShow = vi.fn();
vi.mock("@mantine/notifications", () => ({
	notifications: { show: (a: unknown) => notifyShow(a) },
}));

const mockAuth = vi.fn();
vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: () => mockAuth(),
}));

function renderLogin(auth: Partial<ReturnType<typeof mockAuth>> = {}) {
	mockAuth.mockReturnValue({
		login: vi.fn().mockResolvedValue(undefined),
		isAuthenticated: false,
		isLoading: false,
		...auth,
	});
	return render(
		<MantineProvider>
			<MemoryRouter>
				<LoginPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("LoginPage", () => {
	it("renders the backoffice branding", () => {
		renderLogin();
		expect(screen.getByText("BACKOFFICE")).toBeInTheDocument();
		expect(screen.getByText("Sign in with an admin account")).toBeInTheDocument();
	});

	it("submits valid credentials to login()", async () => {
		const login = vi.fn().mockResolvedValue(undefined);
		renderLogin({ login });
		fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
			target: { value: "a@b.com" },
		});
		fireEvent.change(screen.getByPlaceholderText("Your password"), {
			target: { value: "secret123" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
		await waitFor(() => expect(login).toHaveBeenCalledWith("a@b.com", "secret123"));
	});

	it("toasts on login failure", async () => {
		const login = vi.fn().mockRejectedValue(new Error("Invalid credentials"));
		renderLogin({ login });
		fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
			target: { value: "a@b.com" },
		});
		fireEvent.change(screen.getByPlaceholderText("Your password"), {
			target: { value: "secret123" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
		await waitFor(() =>
			expect(notifyShow).toHaveBeenCalledWith(
				expect.objectContaining({ color: "red", message: "Invalid credentials" }),
			),
		);
	});
});
