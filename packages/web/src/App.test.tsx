import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import App from "./App";
import { useAuthContext } from "./contexts/AuthContext";

vi.mock("./contexts/AuthContext", () => ({
	useAuthContext: vi.fn(() => ({
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
	})),
	AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("./pages/LibraryPage", () => ({ LibraryPage: () => <div>LibraryPage</div> }));
vi.mock("./pages/LoadoutPage", () => ({ LoadoutPage: () => <div>LoadoutPage</div> }));
vi.mock("./pages/MissionsPage", () => ({ MissionsPage: () => <div>MissionsPage</div> }));
vi.mock("./pages/CapturesPage", () => ({ CapturesPage: () => <div>CapturesPage</div> }));
vi.mock("./pages/AnalyticsPage", () => ({ AnalyticsPage: () => <div>AnalyticsPage</div> }));

const mockUseAuthContext = useAuthContext as Mock;

function makeQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
}

function renderApp(initialEntries: string[] = ["/"]) {
	return render(
		<QueryClientProvider client={makeQueryClient()}>
			<MantineProvider>
				<MemoryRouter initialEntries={initialEntries}>
					<App />
				</MemoryRouter>
			</MantineProvider>
		</QueryClientProvider>,
	);
}

function setUnauthenticated() {
	mockUseAuthContext.mockReturnValue({
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
	});
}

function setAuthenticated(logoutFn?: ReturnType<typeof vi.fn>) {
	mockUseAuthContext.mockReturnValue({
		user: { public_id: "u1", email: "test@test.com", display_name: "Test" },
		isLoading: false,
		isAuthenticated: true,
		login: vi.fn(),
		logout: logoutFn ?? vi.fn(),
		register: vi.fn(),
		loginError: null,
		registerError: null,
		isLoginPending: false,
		isRegisterPending: false,
	});
}

describe("App - unauthenticated routes", () => {
	beforeEach(() => {
		setUnauthenticated();
	});

	it("redirects an unauthenticated user on '/' to the login page", () => {
		renderApp(["/"]);
		expect(screen.getByText("Welcome back")).toBeInTheDocument();
	});

	it("renders LoginPage at the /login route", () => {
		renderApp(["/login"]);
		expect(screen.getByText("Sign in to DailyLoadout")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
	});

	it("renders RegisterPage at the /register route", () => {
		renderApp(["/register"]);
		expect(screen.getByText("Create an account")).toBeInTheDocument();
		expect(screen.getByText("Join DailyLoadout")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
	});
});

describe("App - authenticated layout", () => {
	beforeEach(() => {
		setAuthenticated();
	});

	it("redirects authenticated user on '/' to /library", () => {
		renderApp(["/"]);
		expect(screen.getByText("LibraryPage")).toBeInTheDocument();
	});

	it("displays the DailyLoadout brand text in the navbar", () => {
		renderApp(["/library"]);
		expect(screen.getByText("DailyLoadout")).toBeInTheDocument();
	});

	it("renders all five nav links", () => {
		renderApp(["/library"]);
		expect(screen.getByText("Library")).toBeInTheDocument();
		expect(screen.getByText("Daily Loadout")).toBeInTheDocument();
		expect(screen.getByText("Missions")).toBeInTheDocument();
		expect(screen.getByText("Capture History")).toBeInTheDocument();
		expect(screen.getByText("Analytics")).toBeInTheDocument();
	});

	it("renders the Sign out button", () => {
		renderApp(["/library"]);
		expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
	});

	it("renders LoadoutPage at /loadout", () => {
		renderApp(["/loadout"]);
		expect(screen.getByText("LoadoutPage")).toBeInTheDocument();
	});

	it("renders MissionsPage at /missions", () => {
		renderApp(["/missions"]);
		expect(screen.getByText("MissionsPage")).toBeInTheDocument();
	});

	it("renders CapturesPage at /captures", () => {
		renderApp(["/captures"]);
		expect(screen.getByText("CapturesPage")).toBeInTheDocument();
	});

	it("renders AnalyticsPage at /analytics", () => {
		renderApp(["/analytics"]);
		expect(screen.getByText("AnalyticsPage")).toBeInTheDocument();
	});

	it("calls logout when Sign out button is clicked", () => {
		const logoutFn = vi.fn();
		setAuthenticated(logoutFn);

		renderApp(["/library"]);

		const signOutButton = screen.getByRole("button", { name: /sign out/i });
		fireEvent.click(signOutButton);

		expect(logoutFn).toHaveBeenCalledTimes(1);
	});
});

// ---------------------------------------------------------------------------
// NavLink navigation tests - clicking NavLinks navigates to correct pages
// ---------------------------------------------------------------------------

describe("App - NavLink navigation", () => {
	beforeEach(() => {
		setAuthenticated();
	});

	it("clicking 'Library' NavLink navigates to /library and shows LibraryPage", async () => {
		renderApp(["/loadout"]);

		// Verify we start at LoadoutPage
		expect(screen.getByText("LoadoutPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Library"));

		await waitFor(() => {
			expect(screen.getByText("LibraryPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Daily Loadout' NavLink navigates to /loadout and shows LoadoutPage", async () => {
		renderApp(["/library"]);

		// Verify we start at LibraryPage
		expect(screen.getByText("LibraryPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Daily Loadout"));

		await waitFor(() => {
			expect(screen.getByText("LoadoutPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Missions' NavLink navigates to /missions and shows MissionsPage", async () => {
		renderApp(["/library"]);

		expect(screen.getByText("LibraryPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Missions"));

		await waitFor(() => {
			expect(screen.getByText("MissionsPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Capture History' NavLink navigates to /captures and shows CapturesPage", async () => {
		renderApp(["/library"]);

		expect(screen.getByText("LibraryPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Capture History"));

		await waitFor(() => {
			expect(screen.getByText("CapturesPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Analytics' NavLink navigates to /analytics and shows AnalyticsPage", async () => {
		renderApp(["/library"]);

		expect(screen.getByText("LibraryPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Analytics"));

		await waitFor(() => {
			expect(screen.getByText("AnalyticsPage")).toBeInTheDocument();
		});
	});
});
