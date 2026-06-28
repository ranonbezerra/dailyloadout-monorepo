import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { makeAuthContext } from "../test/wrapper";
import type { User } from "../types/auth";
import { ProtectedRoute } from "./ProtectedRoute";

vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: vi.fn(),
}));

import { useAuthContext } from "../contexts/AuthContext";

const mockedUseAuthContext = vi.mocked(useAuthContext);

function renderProtected(initialEntries: string[] = ["/"]) {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={initialEntries}>
				<ProtectedRoute>
					<div data-testid="protected-child">Secret content</div>
				</ProtectedRoute>
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("ProtectedRoute", () => {
	it("shows a loader when isLoading is true", () => {
		mockedUseAuthContext.mockReturnValue(makeAuthContext({ isLoading: true }));

		const { container } = renderProtected();

		// The children must NOT be rendered while loading
		expect(screen.queryByTestId("protected-child")).not.toBeInTheDocument();
		// Mantine Loader renders a span with role="presentation" or a visible
		// loading element. Verify the loader container is present.
		const loader = container.querySelector(".mantine-Loader-root");
		expect(loader).toBeInTheDocument();
	});

	it("redirects to /login when the user is not authenticated", () => {
		mockedUseAuthContext.mockReturnValue(makeAuthContext({ isAuthenticated: false }));

		renderProtected();

		// Navigate component renders nothing visible; the child must not appear
		expect(screen.queryByTestId("protected-child")).not.toBeInTheDocument();
	});

	it("renders children when the user is authenticated", () => {
		mockedUseAuthContext.mockReturnValue(
			makeAuthContext({
				user: { email: "test@test.com", display_name: "Test" } as User,
				isAuthenticated: true,
			}),
		);

		renderProtected();

		expect(screen.getByTestId("protected-child")).toBeInTheDocument();
		expect(screen.getByText("Secret content")).toBeInTheDocument();
	});
});
