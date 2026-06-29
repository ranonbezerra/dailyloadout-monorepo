import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useActivePlaySession } from "../hooks/usePlaySession";
import type { PlaySession } from "../types/play-session";
import { PlayPage } from "./PlayPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useNavigate: () => mockNavigate,
	};
});

vi.mock("../hooks/usePlaySession", () => ({
	useActivePlaySession: vi.fn(),
}));

// Force the concierge feature OFF so door-card assertions are deterministic
// regardless of the ambient VITE_ENABLE_CONCIERGE value.
vi.mock("../lib/features", () => ({
	FEATURES: { backlogConcierge: false },
}));

// The recap/wrapUp modals are rendered inline on the page now. They pull
// in their own data hooks; stub them out so this suite stays focused on the
// PlayPage behavior and does not need a QueryClient provider.
vi.mock("./PlaySessionRecapModal", () => ({
	PlaySessionRecapModal: ({ mode }: { mode: string }) => (
		<div data-testid="recap-modal">{mode}</div>
	),
}));
vi.mock("./PlaySessionWrapUpModal", () => ({
	PlaySessionWrapUpModal: ({ playSession }: { playSession: unknown }) =>
		playSession ? <div data-testid="wrapUp-modal" /> : null,
}));

function renderPage() {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<PlayPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

function makePlaySession(overrides: Partial<PlaySession> = {}): PlaySession {
	return {
		publicId: "playSession-1",
		libraryEntry: {
			publicId: "entry-1",
			game: {
				publicId: "game-1",
				slug: "hollow-knight",
				title: "Hollow Knight",
				summary: null,
				coverUrl: null,
				genres: null,
				metadataSource: "igdb",
				createdAt: "2024-01-01T00:00:00Z",
			},
			platform: { id: 1, slug: "pc", label: "PC", family: "pc" },
			status: "playing",
			playSessionNextAction: null,
			notes: null,
			createdAt: "2024-06-01T00:00:00Z",
			updatedAt: "2024-06-02T00:00:00Z",
		},
		playSessionType: "regular",
		recapText: "Your next adventure awaits",
		wrapUpText: null,
		extractedState: null,
		endedVia: null,
		startedAt: "2024-06-02T10:00:00Z",
		endedAt: null,
		createdAt: "2024-06-02T10:00:00Z",
		updatedAt: "2024-06-02T10:00:00Z",
		lastSessionContext: null,
		...overrides,
	};
}

beforeEach(() => {
	vi.clearAllMocks();
	(useActivePlaySession as Mock).mockReturnValue({ data: null });
});

describe("PlayPage", () => {
	it("renders the Play title", () => {
		renderPage();
		expect(screen.getByText("Play")).toBeInTheDocument();
	});

	it("shows an empty hint when there is no active playSession", () => {
		renderPage();
		expect(screen.getByText(/No active session/)).toBeInTheDocument();
	});

	it("renders the two non-concierge door cards in order", () => {
		renderPage();
		expect(screen.getByText("What's the move?")).toBeInTheDocument();
		expect(screen.getByText("I'll choose")).toBeInTheDocument();
		// Concierge feature is off by default, so the Ask door is hidden.
		expect(screen.queryByText("Ask")).not.toBeInTheDocument();
	});

	it("navigates to /play/pick from the 'What's the move?' door", () => {
		renderPage();
		fireEvent.click(screen.getByText("What's the move?"));
		expect(mockNavigate).toHaveBeenCalledWith("/play/pick");
	});

	it("navigates to /library from the 'I'll choose' door", () => {
		renderPage();
		fireEvent.click(screen.getByText("I'll choose"));
		expect(mockNavigate).toHaveBeenCalledWith("/library");
	});

	it("shows the active playSession card with the game title and recap", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderPage();
		expect(screen.getByText("Session active")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getByText("Your next adventure awaits")).toBeInTheDocument();
	});

	it("shows 'Recap' and 'Wrap up' buttons on the active playSession card", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderPage();
		expect(screen.getByRole("button", { name: /recap/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /wrap up/i })).toBeInTheDocument();
		// No Resume button anymore.
		expect(screen.queryByRole("button", { name: /resume/i })).not.toBeInTheDocument();
	});

	it("opens the recap modal in view mode from the 'Recap' button", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderPage();
		expect(screen.queryByTestId("recap-modal")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: /recap/i }));
		const modal = screen.getByTestId("recap-modal");
		expect(modal).toBeInTheDocument();
		expect(modal).toHaveTextContent("view");
		// Opening the recap does not navigate.
		expect(mockNavigate).not.toHaveBeenCalled();
	});

	it("opens the wrapUp modal from the 'Wrap up' button", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderPage();
		expect(screen.queryByTestId("wrapUp-modal")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: /wrap up/i }));
		expect(screen.getByTestId("wrapUp-modal")).toBeInTheDocument();
		// Ending/wrapping up does not navigate.
		expect(mockNavigate).not.toHaveBeenCalled();
	});

	it("disables the start doors and does not navigate when a playSession is active", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderPage();

		fireEvent.click(screen.getByText("What's the move?"));
		fireEvent.click(screen.getByText("I'll choose"));

		expect(mockNavigate).not.toHaveBeenCalled();
	});
});
