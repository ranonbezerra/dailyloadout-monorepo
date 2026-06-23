import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuthContext } from "./AuthContext";

function makeQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
}

function TestWrapper({ children }: { children: React.ReactNode }) {
	return (
		<QueryClientProvider client={makeQueryClient()}>
			<MemoryRouter>
				<AuthProvider>{children}</AuthProvider>
			</MemoryRouter>
		</QueryClientProvider>
	);
}

describe("AuthContext", () => {
	it("AuthProvider renders its children", () => {
		render(
			<TestWrapper>
				<div data-testid="child">Hello</div>
			</TestWrapper>,
		);

		expect(screen.getByTestId("child")).toBeInTheDocument();
		expect(screen.getByText("Hello")).toBeInTheDocument();
	});

	it("useAuthContext throws when used outside AuthProvider", () => {
		// Suppress React error boundary / console.error noise
		const spy = vi.spyOn(console, "error").mockImplementation(() => {});

		// Call the hook directly outside of any provider context
		// React context returns null, and useAuthContext throws.
		function BadComponent() {
			useAuthContext();
			return <div>should not render</div>;
		}

		expect(() => {
			render(
				<QueryClientProvider client={makeQueryClient()}>
					<MemoryRouter>
						<BadComponent />
					</MemoryRouter>
				</QueryClientProvider>,
			);
		}).toThrow("useAuthContext must be used within an AuthProvider");

		spy.mockRestore();
	});
});
