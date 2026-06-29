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
vi.mock("./pages/PickPage", () => ({ PickPage: () => <div>PickPage</div> }));
vi.mock("./pages/PlaySessionsPage", () => ({
	PlaySessionsPage: () => <div>PlaySessionsPage</div>,
}));
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
		user: { public_id: "u1", email: "test@test.com", display_name: "Test", emailVerified: true },
		isLoading: false,
		isAuthenticated: true,
		emailVerified: true,
		login: vi.fn(),
		logout: logoutFn ?? vi.fn(),
		register: vi.fn(),
		resendVerification: vi.fn(),
		loginError: null,
		registerError: null,
		isLoginPending: false,
		isRegisterPending: false,
		isResendPending: false,
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
		expect(screen.getByText("Sign in to Slate")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
	});

	it("renders RegisterPage at the /register route", () => {
		renderApp(["/register"]);
		expect(screen.getByText("Create an account")).toBeInTheDocument();
		expect(screen.getByText("Join Slate")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
	});
});

describe("App - authenticated layout", () => {
	beforeEach(() => {
		setAuthenticated();
	});

	it("redirects authenticated user on '/' to /play", async () => {
		renderApp(["/"]);
		expect(await screen.findByText("PlayPage")).toBeInTheDocument();
	});

	it("displays the Slate brand text in the navbar", () => {
		renderApp(["/play"]);
		expect(screen.getByText("Slate")).toBeInTheDocument();
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

	it("renders PlayPage at /play", async () => {
		renderApp(["/play"]);
		expect(await screen.findByText("PlayPage")).toBeInTheDocument();
	});

	it("renders PickPage at /play/pick", async () => {
		renderApp(["/play/pick"]);
		expect(await screen.findByText("PickPage")).toBeInTheDocument();
	});

	it("renders PlaySessionsPage (Session history) at /history", async () => {
		renderApp(["/history"]);
		expect(await screen.findByText("PlaySessionsPage")).toBeInTheDocument();
	});

	it("redirects the old /pick route to /play/pick", async () => {
		renderApp(["/pick"]);
		expect(await screen.findByText("PickPage")).toBeInTheDocument();
	});

	it("redirects the old /play-sessions route to /history", async () => {
		renderApp(["/play-sessions"]);
		expect(await screen.findByText("PlaySessionsPage")).toBeInTheDocument();
	});

	it("redirects the old /play/play-sessions route to /history", async () => {
		renderApp(["/play/play-sessions"]);
		expect(await screen.findByText("PlaySessionsPage")).toBeInTheDocument();
	});

	it("renders CapturesPage at /captures", async () => {
		renderApp(["/captures"]);
		expect(await screen.findByText("CapturesPage")).toBeInTheDocument();
	});

	it("renders AnalyticsPage at /analytics", async () => {
		renderApp(["/analytics"]);
		expect(await screen.findByText("AnalyticsPage")).toBeInTheDocument();
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
		expect(await screen.findByText("LibraryPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Play"));

		await waitFor(() => {
			expect(screen.getByText("PlayPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Library' NavLink navigates to /library and shows LibraryPage", async () => {
		renderApp(["/play"]);

		// Verify we start at PlayPage
		expect(await screen.findByText("PlayPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Library"));

		await waitFor(() => {
			expect(screen.getByText("LibraryPage")).toBeInTheDocument();
		});
	});

	it("clicking 'History' NavLink navigates to /history and shows the playSession history", async () => {
		renderApp(["/play"]);

		expect(await screen.findByText("PlayPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("History"));

		await waitFor(() => {
			expect(screen.getByText("PlaySessionsPage")).toBeInTheDocument();
		});
	});

	it("clicking 'Stats' NavLink navigates to /analytics and shows AnalyticsPage", async () => {
		renderApp(["/play"]);

		expect(await screen.findByText("PlayPage")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Stats"));

		await waitFor(() => {
			expect(screen.getByText("AnalyticsPage")).toBeInTheDocument();
		});
	});
});
