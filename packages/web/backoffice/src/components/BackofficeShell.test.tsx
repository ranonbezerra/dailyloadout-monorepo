import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { BackofficeShell } from "./BackofficeShell";

const logout = vi.fn();
vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: () => ({ logout }),
}));
vi.mock("../hooks/useBackoffice", () => ({
	useAdminMe: () => ({ data: { email: "boss@example.com" } }),
}));

function renderShell() {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={["/"]}>
				<BackofficeShell>
					<div>page body</div>
				</BackofficeShell>
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("BackofficeShell", () => {
	it("renders the nav, admin email, and children", () => {
		renderShell();
		expect(screen.getByText("Dashboard")).toBeInTheDocument();
		expect(screen.getByText("Catalogue")).toBeInTheDocument();
		expect(screen.getByText("boss@example.com")).toBeInTheDocument();
		expect(screen.getByText("page body")).toBeInTheDocument();
	});

	it("signs out via the auth context", () => {
		renderShell();
		fireEvent.click(screen.getByText("Sign out"));
		expect(logout).toHaveBeenCalled();
	});
});
