import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { makeAuthContext } from "../test/wrapper";
import { OAuthCallbackPage } from "./OAuthCallbackPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
	return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../contexts/AuthContext", () => ({
	useAuthContext: vi.fn(),
	AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockUseAuthContext = useAuthContext as Mock;

function renderCallback() {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={["/oauth/callback"]}>
				<OAuthCallbackPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OAuthCallbackPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("shows the signing-in loader while completing", () => {
		const completeOAuth = vi.fn().mockReturnValue(new Promise(() => {}));
		mockUseAuthContext.mockReturnValue(makeAuthContext({ completeOAuth }));

		renderCallback();

		expect(screen.getByText(/signing you in/i)).toBeInTheDocument();
	});

	it("navigates to /library on a successful completion", async () => {
		const completeOAuth = vi.fn().mockResolvedValue(true);
		mockUseAuthContext.mockReturnValue(makeAuthContext({ completeOAuth }));

		renderCallback();

		await waitFor(() => {
			expect(mockNavigate).toHaveBeenCalledWith("/library", { replace: true });
		});
		expect(completeOAuth).toHaveBeenCalled();
	});

	it("navigates to /login with an error on a failed completion", async () => {
		const completeOAuth = vi.fn().mockResolvedValue(false);
		mockUseAuthContext.mockReturnValue(makeAuthContext({ completeOAuth }));

		renderCallback();

		await waitFor(() => {
			expect(mockNavigate).toHaveBeenCalledWith("/login?error=oauth_failed", { replace: true });
		});
	});
});
