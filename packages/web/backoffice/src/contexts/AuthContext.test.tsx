import { render, renderHook, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuthContext } from "./AuthContext";

vi.mock("../hooks/useAuth", () => ({
	useAuth: () => ({ isAuthenticated: true, isLoading: false, login: vi.fn(), logout: vi.fn() }),
}));

describe("AuthContext", () => {
	it("provides the auth value to children", () => {
		function Consumer() {
			const { isAuthenticated } = useAuthContext();
			return <div>auth: {String(isAuthenticated)}</div>;
		}
		render(
			<AuthProvider>
				<Consumer />
			</AuthProvider>,
		);
		expect(screen.getByText("auth: true")).toBeInTheDocument();
	});

	it("throws when used outside an AuthProvider", () => {
		expect(() => renderHook(() => useAuthContext())).toThrow(/AuthProvider/);
	});
});
