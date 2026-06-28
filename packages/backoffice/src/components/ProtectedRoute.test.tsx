import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "./ProtectedRoute";

const mockAuth = vi.fn();
vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: () => mockAuth(),
}));

function renderAt(authValue: { isAuthenticated: boolean; isLoading: boolean }) {
	mockAuth.mockReturnValue(authValue);
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={["/"]}>
				<Routes>
					<Route
						path="/"
						element={
							<ProtectedRoute>
								<div>protected</div>
							</ProtectedRoute>
						}
					/>
					<Route path="/login" element={<div>login screen</div>} />
				</Routes>
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("ProtectedRoute", () => {
	it("renders children when authenticated", () => {
		renderAt({ isAuthenticated: true, isLoading: false });
		expect(screen.getByText("protected")).toBeInTheDocument();
	});

	it("redirects to /login when unauthenticated", () => {
		renderAt({ isAuthenticated: false, isLoading: false });
		expect(screen.getByText("login screen")).toBeInTheDocument();
	});

	it("shows a loader while bootstrapping", () => {
		renderAt({ isAuthenticated: false, isLoading: true });
		expect(screen.queryByText("protected")).not.toBeInTheDocument();
		expect(screen.queryByText("login screen")).not.toBeInTheDocument();
	});
});
