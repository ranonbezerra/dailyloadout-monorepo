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

vi.mock("./pages/PlayPage", () => ({ PlayPage: () => <div>PlayPage</div> }));
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

	it("redirects authenticated user on '/' to /play", () => {
		renderApp(["/"]);
		expect(screen.getByText("PlayPage")).toBeInTheDocument();
	});

	it("displays the DailyLoadout brand text in the navbar", () => {
		renderApp(["/play"]);
		expect(screen.getByText("DailyLoadout")).toBeInTheDocument();
	});

	it("renders the primary nav links", () => {
		renderApp(["/play"]);
		expect(screen.getByText("Play")).toBeInTheDocument();
		expect(screen.getByText("Library")).toBeInTheDocument();
		expect(screen.getByText("History")).toBeInTheDocument();
		expect(screen.getByText("Stats")).toBeInTheDocument();
	});

	it("renders the Sign out button", () => {
		renderApp(["/play"]);
		expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
	});

	it("renders the IGDB attribution credit", () => {
		renderApp(["/play"]);
		const credit = screen.getByRole("link", { name: /igdb\.com/i });
		expect(credit).toHaveAttribute("href", "https://www.igdb.com");
	});

	it("renders PlayPage at /play", () => {
		renderApp(["/play"]);
		expect(screen.getByText("PlayPage")).toBeInTheDocument();
	});

	it("renders LoadoutPage at /play/loadout", () => {
		renderApp(["/play/loadout"]);
		expect(screen.getByText("LoadoutPage")).toBeInTheDocument();
	});

	it("renders MissionsPage (Mission History) at /history", () => {
		renderApp(["/history"]);
		expect(screen.getByText("MissionsPage")).toBeInTheDocument();
	});

	it("redirects the old /loadout route to /play/loadout", () => {
		renderApp(["/loadout"]);
		expect(screen.getByText("LoadoutPage")).toBeInTheDocument();
	});

	it("redirects the old /missions route to /history", () => {
		renderApp(["/missions"]);
		expect(screen.getByText("MissionsPage")).toBeInTheDocument();
	});

	it("redirects the old /play/missions route to /history", () => {
		renderApp(["/play/missions"]);
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

		renderApp(["/play"]);

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

	it("clicking 'Play' NavLink navigates to /play and shows PlayPage", async () => {
		renderApp(["/library"]);

		// Verify we start at LibraryPage
		expect(screen.getByText("LibraryPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Play"));

		await waitFor(() => {
			expect(screen.getByText("PlayPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Library' NavLink navigates to /library and shows LibraryPage", async () => {
		renderApp(["/play"]);

		// Verify we start at PlayPage
		expect(screen.getByText("PlayPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Library"));

		await waitFor(() => {
			expect(screen.getByText("LibraryPage")).toBeInTheDocument();
		});
	});

	it("clicking 'History' NavLink navigates to /history and shows the mission history", async () => {
		renderApp(["/play"]);

		expect(screen.getByText("PlayPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("History"));

		await waitFor(() => {
			expect(screen.getByText("MissionsPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Stats' NavLink navigates to /analytics and shows AnalyticsPage", async () => {
		renderApp(["/play"]);

		expect(screen.getByText("PlayPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Stats"));

		await waitFor(() => {
			expect(screen.getByText("AnalyticsPage")).toBeInTheDocument();
		});
	});
});
