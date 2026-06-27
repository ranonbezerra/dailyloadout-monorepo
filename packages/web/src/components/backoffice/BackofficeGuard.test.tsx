import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, type Mock, vi } from "vitest";
import { useAdminMe } from "../../hooks/useBackoffice";
import { BackofficeGuard } from "./BackofficeGuard";

vi.mock("../../hooks/useBackoffice", () => ({
	useAdminMe: vi.fn(),
}));

const mockUseAdminMe = useAdminMe as Mock;

function renderGuard() {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<BackofficeGuard>
					<div>secret admin content</div>
				</BackofficeGuard>
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("BackofficeGuard", () => {
	it("shows a loader while checking admin rights", () => {
		mockUseAdminMe.mockReturnValue({ isLoading: true, isError: false });
		renderGuard();
		expect(screen.queryByText("secret admin content")).not.toBeInTheDocument();
	});

	it("blocks non-admins with an access screen", () => {
		mockUseAdminMe.mockReturnValue({ isLoading: false, isError: true });
		renderGuard();
		expect(screen.getByText("Backoffice access required")).toBeInTheDocument();
		expect(screen.queryByText("secret admin content")).not.toBeInTheDocument();
	});

	it("renders children for an admin", () => {
		mockUseAdminMe.mockReturnValue({ isLoading: false, isError: false });
		renderGuard();
		expect(screen.getByText("secret admin content")).toBeInTheDocument();
	});
});
