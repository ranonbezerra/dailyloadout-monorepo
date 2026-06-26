import { MantineProvider } from "@mantine/core";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAcceptLoadout, useCreateLoadout, useRejectLoadout } from "../hooks/useLoadout";
import { usePreviewBriefing } from "../hooks/useMission";
import type { Loadout } from "../types/loadout";
import { LoadoutPage } from "./LoadoutPage";

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

vi.mock("../hooks/useLoadout", () => ({
	useCreateLoadout: vi.fn(),
	useAcceptLoadout: vi.fn(),
	useRejectLoadout: vi.fn(),
	useLoadouts: vi.fn(() => ({ data: null, isLoading: false })),
	useLatestLoadout: vi.fn(() => ({ data: null, isLoading: false })),
}));

vi.mock("../hooks/useMission", () => ({
	usePreviewBriefing: vi.fn(),
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

function makeMockLoadout(overrides?: Partial<Loadout>): Loadout {
	return {
		publicId: "lo-1",
		libraryEntry: {
			publicId: "le-1",
			game: {
				publicId: "g-1",
				slug: "hollow-knight",
				title: "Hollow Knight",
				coverUrl: "https://images.igdb.com/igdb/image/upload/t_cover_big/hk.jpg",
				genres: ["Metroidvania", "Platformer"],
				metadataSource: "igdb",
				createdAt: "2024-01-01T00:00:00Z",
			},
			platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
			status: "playing",
			createdAt: "2024-01-01T00:00:00Z",
			updatedAt: "2024-01-01T00:00:00Z",
		},
		mood: "chill",
		availableMinutes: 60,
		mentalEnergy: "medium",
		context: null,
		reasoning: "A great choice for a chill session",
		action: null,
		createdAt: "2024-06-01T00:00:00Z",
		updatedAt: "2024-06-01T00:00:00Z",
		...overrides,
	};
}

function makeMockLoadout2(): Loadout {
	return makeMockLoadout({
		publicId: "lo-2",
		libraryEntry: {
			publicId: "le-2",
			game: {
				publicId: "g-2",
				slug: "celeste",
				title: "Celeste",
				coverUrl: "https://images.igdb.com/igdb/image/upload/t_cover_big/celeste.jpg",
				genres: ["Platformer"],
				metadataSource: "igdb",
				createdAt: "2024-01-01T00:00:00Z",
			},
			platform: { id: 2, slug: "switch", label: "Nintendo Switch", family: "console" },
			status: "backlog",
			createdAt: "2024-01-01T00:00:00Z",
			updatedAt: "2024-01-01T00:00:00Z",
		},
		reasoning: "A challenging but rewarding platformer",
	});
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setDefaultMutationMocks() {
	(useCreateLoadout as Mock).mockReturnValue({
		mutate: vi.fn(),
		mutateAsync: vi.fn(),
		isPending: false,
		isError: false,
		error: null,
	});
	(useAcceptLoadout as Mock).mockReturnValue({
		mutate: vi.fn(),
		mutateAsync: vi.fn(),
		isPending: false,
	});
	(useRejectLoadout as Mock).mockReturnValue({
		mutate: vi.fn(),
		mutateAsync: vi.fn(),
		isPending: false,
	});
	(usePreviewBriefing as Mock).mockReturnValue({
		mutate: vi.fn(),
		mutateAsync: vi.fn(),
		isPending: false,
		variables: undefined,
	});
}

function renderPage() {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<LoadoutPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

/**
 * Helper: sets up mocks so that createLoadout.mutate captures the onSuccess
 * callback, and returns the mockMutate fn for assertions.
 */
function setupCreateMockWithCapture() {
	const mockMutate = vi.fn();
	(useCreateLoadout as Mock).mockReturnValue({
		mutate: mockMutate,
		mutateAsync: vi.fn(),
		isPending: false,
		isError: false,
		error: null,
	});
	(useAcceptLoadout as Mock).mockReturnValue({
		mutate: vi.fn(),
		mutateAsync: vi.fn(),
		isPending: false,
	});
	(useRejectLoadout as Mock).mockReturnValue({
		mutate: vi.fn(),
		mutateAsync: vi.fn(),
		isPending: false,
	});
	(usePreviewBriefing as Mock).mockReturnValue({
		mutate: vi.fn(),
		mutateAsync: vi.fn(),
		isPending: false,
		variables: undefined,
	});
	return mockMutate;
}

/**
 * Helper: clicks "Roll the dice", then invokes the captured onSuccess
 * with the provided data, causing results to render.
 */
function rollAndSetResults(mockMutate: ReturnType<typeof vi.fn>, data: Loadout[]) {
	fireEvent.click(screen.getByRole("button", { name: /Roll the dice/i }));
	const onSuccess = mockMutate.mock.calls[0][1].onSuccess;
	act(() => {
		onSuccess(data);
	});
}

// ---------------------------------------------------------------------------
// Tests - Form rendering
// ---------------------------------------------------------------------------

describe("LoadoutPage", () => {
	beforeEach(() => {
		mockNavigate.mockClear();
	});

	it("renders title 'Daily Loadout'", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByText("Daily Loadout")).toBeInTheDocument();
	});

	it("renders subtitle description text", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(
			screen.getByText(/Answer a few questions and we'll pick the perfect game/),
		).toBeInTheDocument();
	});

	it("renders mood question and options", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByText("What's your mood?")).toBeInTheDocument();
		expect(screen.getByText("Chill")).toBeInTheDocument();
		expect(screen.getByText("Focused")).toBeInTheDocument();
		expect(screen.getByText("Energetic")).toBeInTheDocument();
		expect(screen.getByText("Adventurous")).toBeInTheDocument();
	});

	it("renders time question", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByText("How much time do you have?")).toBeInTheDocument();
	});

	it("renders energy question and options", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByText("Mental energy level?")).toBeInTheDocument();
		expect(screen.getByText("Low")).toBeInTheDocument();
		expect(screen.getByText("Medium")).toBeInTheDocument();
		expect(screen.getByText("High")).toBeInTheDocument();
	});

	it("renders the optional context text input", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByText("Anything else? (optional)")).toBeInTheDocument();
		expect(screen.getByPlaceholderText(/feeling nostalgic/)).toBeInTheDocument();
	});

	it("renders multi-mode switch", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByText("Show multiple suggestions (up to 3)")).toBeInTheDocument();
	});

	it("renders 'Roll the dice' button", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByRole("button", { name: /Roll the dice/i })).toBeInTheDocument();
	});

	it("shows 'Picking...' text when createLoadout is pending", () => {
		(useCreateLoadout as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: true,
			isError: false,
			error: null,
		});
		(useAcceptLoadout as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
		});
		(useRejectLoadout as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
		});
		(usePreviewBriefing as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
			variables: undefined,
		});

		renderPage();

		expect(screen.getByRole("button", { name: /Picking/i })).toBeInTheDocument();
	});

	it("shows error text when createLoadout has an error", () => {
		(useCreateLoadout as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
			isError: true,
			error: new Error("No games in your library"),
		});
		(useAcceptLoadout as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
		});
		(useRejectLoadout as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
		});
		(usePreviewBriefing as Mock).mockReturnValue({
			mutate: vi.fn(),
			mutateAsync: vi.fn(),
			isPending: false,
			variables: undefined,
		});

		renderPage();

		expect(screen.getByText("No games in your library")).toBeInTheDocument();
	});

	it("shows character count for context input", () => {
		setDefaultMutationMocks();
		renderPage();

		// Default is empty so 0/120
		expect(screen.getByText("0/120")).toBeInTheDocument();
	});

	it("renders time slider marks", () => {
		setDefaultMutationMocks();
		renderPage();

		expect(screen.getByText("30m")).toBeInTheDocument();
		expect(screen.getByText("1h")).toBeInTheDocument();
		expect(screen.getByText("2h")).toBeInTheDocument();
		expect(screen.getByText("4h")).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Tests - handleRoll (mutate call)
// ---------------------------------------------------------------------------

describe("LoadoutPage - handleRoll", () => {
	beforeEach(() => {
		mockNavigate.mockClear();
	});

	it("calls createLoadout.mutate with default params when clicking Roll", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		fireEvent.click(screen.getByRole("button", { name: /Roll the dice/i }));

		expect(mockMutate).toHaveBeenCalledTimes(1);
		const [args] = mockMutate.mock.calls[0];
		expect(args).toEqual({
			mood: "chill",
			availableMinutes: 60,
			mentalEnergy: "medium",
			context: undefined,
			count: 1,
		});
	});

	it("passes changed mood and energy when user selects different options", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		// Change mood from default "chill" to "focused"
		fireEvent.click(screen.getByLabelText("Focused"));
		// Change energy from default "medium" to "high"
		fireEvent.click(screen.getByLabelText("High"));

		fireEvent.click(screen.getByRole("button", { name: /Roll the dice/i }));

		const [args] = mockMutate.mock.calls[0];
		expect(args.mood).toBe("focused");
		expect(args.mentalEnergy).toBe("high");
	});

	it("passes count=3 when multi-mode switch is toggled on", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		// Toggle multi-mode on via its label
		const switchEl = screen.getByLabelText("Show multiple suggestions (up to 3)");
		fireEvent.click(switchEl);

		fireEvent.click(screen.getByRole("button", { name: /Roll the dice/i }));

		const [args] = mockMutate.mock.calls[0];
		expect(args.count).toBe(3);
	});

	it("includes trimmed context when provided", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		const input = screen.getByPlaceholderText(/feeling nostalgic/);
		fireEvent.change(input, { target: { value: "  want something story-driven  " } });

		fireEvent.click(screen.getByRole("button", { name: /Roll the dice/i }));

		const [args] = mockMutate.mock.calls[0];
		expect(args.context).toBe("want something story-driven");
	});
});

// ---------------------------------------------------------------------------
// Tests - LoadoutResultCard rendering
// ---------------------------------------------------------------------------

describe("LoadoutPage - result cards", () => {
	beforeEach(() => {
		mockNavigate.mockClear();
	});

	it("shows result card with game title, platform, and reasoning after roll", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		rollAndSetResults(mockMutate, [makeMockLoadout()]);

		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getByText("PC")).toBeInTheDocument();
		expect(screen.getByText("playing")).toBeInTheDocument();
		expect(screen.getByText("A great choice for a chill session")).toBeInTheDocument();
	});

	it("shows cover image when coverUrl is present", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		rollAndSetResults(mockMutate, [makeMockLoadout()]);

		const img = screen.getByAltText("Hollow Knight");
		expect(img).toBeInTheDocument();
		expect(img).toHaveAttribute(
			"src",
			"https://images.igdb.com/igdb/image/upload/t_cover_big/hk.jpg",
		);
	});

	it("renders genre badges", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		rollAndSetResults(mockMutate, [makeMockLoadout()]);

		expect(screen.getByText("Metroidvania")).toBeInTheDocument();
		expect(screen.getByText("Platformer")).toBeInTheDocument();
	});

	it("shows Accept and Reject buttons when action is null", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		rollAndSetResults(mockMutate, [makeMockLoadout()]);

		expect(screen.getByRole("button", { name: /Just play/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Quick briefing/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Deep briefing/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Reject/i })).toBeInTheDocument();
	});

	it("shows 'Mission started! Redirecting...' when action is accepted", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		// Use two results: one accepted, one still pending (action: null)
		// so allActioned is false and result cards remain visible.
		rollAndSetResults(mockMutate, [makeMockLoadout({ action: "accepted" }), makeMockLoadout2()]);

		expect(screen.getByText("Mission started! Redirecting...")).toBeInTheDocument();
	});

	it("shows 'Rejected' when action is rejected", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		// Use two results: one rejected, one still pending (action: null)
		// so allActioned is false and result cards remain visible.
		rollAndSetResults(mockMutate, [makeMockLoadout({ action: "rejected" }), makeMockLoadout2()]);

		expect(screen.getByText("Rejected")).toBeInTheDocument();
	});

	it("does NOT show rank badge when there is a single result", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		rollAndSetResults(mockMutate, [makeMockLoadout()]);

		expect(screen.queryByText("Best Match")).not.toBeInTheDocument();
		expect(screen.queryByText("Great Alternative")).not.toBeInTheDocument();
	});

	it("shows rank badges when there are multiple results", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		rollAndSetResults(mockMutate, [makeMockLoadout(), makeMockLoadout2()]);

		expect(screen.getByText("Best Match")).toBeInTheDocument();
		expect(screen.getByText("Great Alternative")).toBeInTheDocument();
	});

	it("hides result cards and shows form again when all results are actioned", () => {
		const mockMutate = setupCreateMockWithCapture();
		renderPage();

		// Single result that is already actioned
		rollAndSetResults(mockMutate, [makeMockLoadout({ action: "rejected" })]);

		// The form should reappear since all results have an action
		expect(screen.getByText("What's your mood?")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Roll the dice/i })).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Tests - handleAccept and handleReject
// ---------------------------------------------------------------------------

describe("LoadoutPage - accept and reject actions", () => {
	beforeEach(() => {
		vi.useFakeTimers();
		mockNavigate.mockClear();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it("calls acceptLoadout.mutate when Accept button is clicked", () => {
		const createMutate = setupCreateMockWithCapture();
		const acceptMutate = vi.fn();
		(useAcceptLoadout as Mock).mockReturnValue({
			mutate: acceptMutate,
			mutateAsync: vi.fn(),
			isPending: false,
		});

		renderPage();
		rollAndSetResults(createMutate, [makeMockLoadout()]);

		fireEvent.click(screen.getByRole("button", { name: /Just play/i }));

		expect(acceptMutate).toHaveBeenCalledTimes(1);
		expect(acceptMutate.mock.calls[0][0]).toEqual({
			publicId: "lo-1",
			briefingText: undefined,
		});
	});

	it("updates result to accepted and navigates to /play after accept", () => {
		const createMutate = setupCreateMockWithCapture();
		const acceptMutate = vi.fn();
		(useAcceptLoadout as Mock).mockReturnValue({
			mutate: acceptMutate,
			mutateAsync: vi.fn(),
			isPending: false,
		});

		renderPage();
		// Use two results so allActioned stays false after accepting one
		rollAndSetResults(createMutate, [makeMockLoadout(), makeMockLoadout2()]);

		// Click Accept on the first card (there are two Accept buttons)
		const acceptButtons = screen.getAllByRole("button", { name: /Just play/i });
		fireEvent.click(acceptButtons[0]);

		// Simulate accept onSuccess callback
		const onSuccess = acceptMutate.mock.calls[0][1].onSuccess;
		act(() => {
			onSuccess(makeMockLoadout({ action: "accepted" }));
		});

		expect(screen.getByText("Mission started! Redirecting...")).toBeInTheDocument();

		// Fast-forward the setTimeout(600) for navigation
		act(() => {
			vi.advanceTimersByTime(600);
		});
		expect(mockNavigate).toHaveBeenCalledWith("/play");
	});

	it("calls rejectLoadout.mutate when Reject button is clicked", () => {
		const createMutate = setupCreateMockWithCapture();
		const rejectMutate = vi.fn();
		(useRejectLoadout as Mock).mockReturnValue({
			mutate: rejectMutate,
			mutateAsync: vi.fn(),
			isPending: false,
		});

		renderPage();
		rollAndSetResults(createMutate, [makeMockLoadout()]);

		fireEvent.click(screen.getByRole("button", { name: /Reject/i }));

		expect(rejectMutate).toHaveBeenCalledTimes(1);
		expect(rejectMutate.mock.calls[0][0]).toBe("lo-1");
	});

	it("updates result to rejected after reject callback", () => {
		const createMutate = setupCreateMockWithCapture();
		const rejectMutate = vi.fn();
		(useRejectLoadout as Mock).mockReturnValue({
			mutate: rejectMutate,
			mutateAsync: vi.fn(),
			isPending: false,
		});

		renderPage();
		rollAndSetResults(createMutate, [makeMockLoadout()]);

		fireEvent.click(screen.getByRole("button", { name: /Reject/i }));

		// Simulate reject onSuccess
		const onSuccess = rejectMutate.mock.calls[0][1].onSuccess;
		act(() => {
			onSuccess(makeMockLoadout({ action: "rejected" }));
		});

		// Since all results are now actioned, form should reappear
		expect(screen.getByText("What's your mood?")).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Tests - briefing flow
// ---------------------------------------------------------------------------

describe("LoadoutPage - briefing flow", () => {
	beforeEach(() => {
		mockNavigate.mockClear();
	});

	it("previews a quick briefing when 'Quick briefing' is clicked", () => {
		const createMutate = setupCreateMockWithCapture();
		const previewMutate = vi.fn();
		(usePreviewBriefing as Mock).mockReturnValue({
			mutate: previewMutate,
			mutateAsync: vi.fn(),
			isPending: false,
			variables: undefined,
		});

		renderPage();
		rollAndSetResults(createMutate, [makeMockLoadout()]);

		fireEvent.click(screen.getByRole("button", { name: /Quick briefing/i }));

		expect(previewMutate).toHaveBeenCalledTimes(1);
		expect(previewMutate.mock.calls[0][0]).toEqual({
			libraryEntryPublicId: "le-1",
			mode: "quick",
		});
	});

	it("previews a deep briefing when 'Deep briefing' is clicked", () => {
		const createMutate = setupCreateMockWithCapture();
		const previewMutate = vi.fn();
		(usePreviewBriefing as Mock).mockReturnValue({
			mutate: previewMutate,
			mutateAsync: vi.fn(),
			isPending: false,
			variables: undefined,
		});

		renderPage();
		rollAndSetResults(createMutate, [makeMockLoadout()]);

		fireEvent.click(screen.getByRole("button", { name: /Deep briefing/i }));

		expect(previewMutate.mock.calls[0][0]).toEqual({
			libraryEntryPublicId: "le-1",
			mode: "deep",
		});
	});

	it("shows the briefing sub-card and 'Start with briefing' button once a briefing is fetched", () => {
		const createMutate = setupCreateMockWithCapture();
		const previewMutate = vi.fn();
		(usePreviewBriefing as Mock).mockReturnValue({
			mutate: previewMutate,
			mutateAsync: vi.fn(),
			isPending: false,
			variables: undefined,
		});

		renderPage();
		rollAndSetResults(createMutate, [makeMockLoadout()]);

		fireEvent.click(screen.getByRole("button", { name: /Quick briefing/i }));

		// Simulate the preview onSuccess callback with a briefing text.
		const onSuccess = previewMutate.mock.calls[0][1].onSuccess;
		act(() => {
			onSuccess({ briefingText: "Focus on collecting charms early." });
		});

		expect(screen.getByText("Briefing")).toBeInTheDocument();
		expect(screen.getByText("Focus on collecting charms early.")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Start with briefing/i })).toBeInTheDocument();
		// The pre-briefing buttons should no longer be visible.
		expect(screen.queryByRole("button", { name: /Just play/i })).not.toBeInTheDocument();
		expect(screen.queryByRole("button", { name: /Quick briefing/i })).not.toBeInTheDocument();
	});

	it("accepts with the fetched briefing text when 'Start with briefing' is clicked", () => {
		const createMutate = setupCreateMockWithCapture();
		const previewMutate = vi.fn();
		const acceptMutate = vi.fn();
		(usePreviewBriefing as Mock).mockReturnValue({
			mutate: previewMutate,
			mutateAsync: vi.fn(),
			isPending: false,
			variables: undefined,
		});
		(useAcceptLoadout as Mock).mockReturnValue({
			mutate: acceptMutate,
			mutateAsync: vi.fn(),
			isPending: false,
		});

		renderPage();
		rollAndSetResults(createMutate, [makeMockLoadout()]);

		fireEvent.click(screen.getByRole("button", { name: /Quick briefing/i }));
		const onSuccess = previewMutate.mock.calls[0][1].onSuccess;
		act(() => {
			onSuccess({ briefingText: "Focus on collecting charms early." });
		});

		fireEvent.click(screen.getByRole("button", { name: /Start with briefing/i }));

		expect(acceptMutate).toHaveBeenCalledTimes(1);
		expect(acceptMutate.mock.calls[0][0]).toEqual({
			publicId: "lo-1",
			briefingText: "Focus on collecting charms early.",
		});
	});
});
