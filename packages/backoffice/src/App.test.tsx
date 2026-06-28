import { MantineProvider } from "@mantine/core";
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { makeQueryClient } from "./test/wrapper";

const mockAuth = vi.fn();
vi.mock("./contexts/AuthContext", () => ({
	useAuthContext: () => mockAuth(),
}));
// The admin-gated area's heavy children aren't under test here; stub the guard.
vi.mock("./components/BackofficeGuard", () => ({
	BackofficeGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("./components/BackofficeShell", () => ({
	BackofficeShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("./pages/DashboardPage", () => ({ DashboardPage: () => <div>dashboard body</div> }));

function renderApp(path: string, auth: { isAuthenticated: boolean; isLoading: boolean }) {
	mockAuth.mockReturnValue(auth);
	return render(
		<QueryClientProvider client={makeQueryClient()}>
			<MantineProvider>
				<MemoryRouter initialEntries={[path]}>
					<App />
				</MemoryRouter>
			</MantineProvider>
		</QueryClientProvider>,
	);
}

describe("App routing", () => {
	it("shows the login page at /login", () => {
		renderApp("/login", { isAuthenticated: false, isLoading: false });
		expect(screen.getByText("BACKOFFICE")).toBeInTheDocument();
	});

	it("renders the dashboard at / when authenticated", () => {
		renderApp("/", { isAuthenticated: true, isLoading: false });
		expect(screen.getByText("dashboard body")).toBeInTheDocument();
	});

	it("redirects to /login at / when unauthenticated", () => {
		renderApp("/", { isAuthenticated: false, isLoading: false });
		expect(screen.getByText("BACKOFFICE")).toBeInTheDocument();
	});
});
