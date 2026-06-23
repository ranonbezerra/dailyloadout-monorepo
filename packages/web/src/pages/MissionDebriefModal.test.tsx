import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useEndMission, useSubmitDebrief } from "../hooks/useMission";
import type { Mission } from "../types/mission";
import { MissionDebriefModal } from "./MissionDebriefModal";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../hooks/useMission", () => ({
	useEndMission: vi.fn(),
	useSubmitDebrief: vi.fn(),
	useMissions: vi.fn(() => ({ data: null, isLoading: false })),
	useActiveMission: vi.fn(() => ({ data: null })),
	useMission: vi.fn(() => ({ data: null, isLoading: false })),
	useStartMission: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	usePreviewBriefing: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useRegenerateBriefing: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useRetroactiveDebrief: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

// Mock only Modal to avoid portal issues in jsdom; keep real Textarea
vi.mock("@mantine/core", async () => {
	const actual = await vi.importActual("@mantine/core");
	return {
		...actual,
		Modal: ({
			opened,
			children,
			title,
			onClose,
		}: {
			opened: boolean;
			children?: ReactNode;
			title?: ReactNode;
			onClose?: () => void;
			size?: string;
		}) =>
			opened ? (
				<div data-testid="mock-modal">
					{title && <div>{title}</div>}
					<button type="button" data-testid="mock-modal-close" onClick={onClose}>
						Close
					</button>
					{children}
				</div>
			) : null,
	};
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMission(overrides: Partial<Mission> = {}): Mission {
	return {
		publicId: "mis-001",
		libraryEntry: {
			publicId: "le-001",
			game: {
				publicId: "game-001",
				slug: "hollow-knight",
				title: "Hollow Knight",
				metadataSource: "igdb",
				createdAt: "2024-01-01T00:00:00Z",
			},
			platform: {
				id: 1,
				slug: "pc",
				label: "PC",
				family: "pc",
			},
			status: "playing",
			createdAt: "2024-01-01T00:00:00Z",
			updatedAt: "2024-01-01T00:00:00Z",
		},
		missionType: "regular",
		briefingText: "Welcome back to Hollow Knight...",
		debriefText: null,
		extractedState: null,
		endedVia: null,
		startedAt: "2024-06-01T10:00:00Z",
		endedAt: null,
		createdAt: "2024-06-01T10:00:00Z",
		updatedAt: "2024-06-01T10:00:00Z",
		lastSessionContext: null,
		...overrides,
	};
}

const defaultOnClose = vi.fn();

function renderModal(mission: Mission | null, onClose = defaultOnClose) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<MissionDebriefModal mission={mission} onClose={onClose} />
			</MemoryRouter>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MissionDebriefModal", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		(useEndMission as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: false,
		});
		(useSubmitDebrief as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: false,
		});
	});

	it("returns null and renders nothing when mission is null", () => {
		renderModal(null);

		expect(screen.queryByText(/End Mission/)).not.toBeInTheDocument();
		expect(screen.queryByTestId("mock-modal")).not.toBeInTheDocument();
	});

	it("renders modal title with the game name", () => {
		renderModal(makeMission());

		expect(screen.getByText(/End Mission: Hollow Knight/)).toBeInTheDocument();
	});

	it("renders title with different game name", () => {
		const mission = makeMission({
			libraryEntry: {
				publicId: "le-002",
				game: {
					publicId: "game-002",
					slug: "elden-ring",
					title: "Elden Ring",
					metadataSource: "igdb",
					createdAt: "2024-01-01T00:00:00Z",
				},
				platform: {
					id: 2,
					slug: "ps5",
					label: "PS5",
					family: "playstation",
				},
				status: "playing",
				createdAt: "2024-01-01T00:00:00Z",
				updatedAt: "2024-01-01T00:00:00Z",
			},
		});

		renderModal(mission);

		expect(screen.getByText(/End Mission: Elden Ring/)).toBeInTheDocument();
	});

	it("renders the debrief description text", () => {
		renderModal(makeMission());

		expect(screen.getByText(/What happened this session/)).toBeInTheDocument();
	});

	it("renders the textarea with correct placeholder", () => {
		renderModal(makeMission());

		expect(screen.getByPlaceholderText(/Beat the Mantis Lords/)).toBeInTheDocument();
	});

	it("renders 'Skip debrief' and 'Submit debrief' buttons", () => {
		renderModal(makeMission());

		expect(screen.getByRole("button", { name: /Skip debrief/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Submit debrief/i })).toBeInTheDocument();
	});

	it("submit debrief button is disabled when text is shorter than 3 characters", () => {
		renderModal(makeMission());

		const submitButton = screen.getByRole("button", { name: /Submit debrief/i });
		expect(submitButton).toBeDisabled();
	});

	it("submit debrief button becomes enabled when text is 3+ characters", () => {
		renderModal(makeMission());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Got the cloak" } });

		const submitButton = screen.getByRole("button", { name: /Submit debrief/i });
		expect(submitButton).not.toBeDisabled();
	});

	it("submit debrief stays disabled with only whitespace", () => {
		renderModal(makeMission());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "   " } });

		const submitButton = screen.getByRole("button", { name: /Submit debrief/i });
		expect(submitButton).toBeDisabled();
	});

	it("skip debrief button is not disabled even without text", () => {
		renderModal(makeMission());

		const skipButton = screen.getByRole("button", { name: /Skip debrief/i });
		expect(skipButton).not.toBeDisabled();
	});

	it("shows loading state on skip button when endMission is pending", () => {
		(useEndMission as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: true,
		});

		renderModal(makeMission());

		const skipButton = screen.getByRole("button", { name: /Skip debrief/i });
		expect(skipButton).toHaveAttribute("data-loading");
	});

	it("shows loading state on submit button when submitDebrief is pending", () => {
		(useSubmitDebrief as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: true,
		});

		renderModal(makeMission());

		const submitButton = screen.getByRole("button", { name: /Submit debrief/i });
		expect(submitButton).toHaveAttribute("data-loading");
	});

	// --- Submit debrief flow ---

	it("calls submitDebrief.mutateAsync on submit and shows success notification", async () => {
		const mutateAsyncFn = vi.fn().mockResolvedValueOnce(undefined);
		(useSubmitDebrief as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		const onClose = vi.fn();
		renderModal(makeMission(), onClose);

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Beat the Mantis Lords and got the cloak" } });

		const submitButton = screen.getByRole("button", { name: /Submit debrief/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(mutateAsyncFn).toHaveBeenCalledWith({
				publicId: "mis-001",
				debriefText: "Beat the Mantis Lords and got the cloak",
			});
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Mission complete",
					color: "green",
				}),
			);
		});

		await waitFor(() => {
			expect(onClose).toHaveBeenCalled();
		});
	});

	it("shows error notification when submitDebrief fails with Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce(new Error("Server error"));
		(useSubmitDebrief as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makeMission());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Some debrief text" } });

		const submitButton = screen.getByRole("button", { name: /Submit debrief/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Debrief failed",
					message: "Server error",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when submitDebrief fails with non-Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce("something");
		(useSubmitDebrief as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makeMission());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Some debrief text" } });

		const submitButton = screen.getByRole("button", { name: /Submit debrief/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Debrief failed",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});

	// --- Skip debrief flow ---

	it("calls endMission.mutateAsync on skip and shows notification", async () => {
		const mutateAsyncFn = vi.fn().mockResolvedValueOnce(undefined);
		(useEndMission as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		const onClose = vi.fn();
		renderModal(makeMission(), onClose);

		const skipButton = screen.getByRole("button", { name: /Skip debrief/i });
		fireEvent.click(skipButton);

		await waitFor(() => {
			expect(mutateAsyncFn).toHaveBeenCalledWith({ publicId: "mis-001" });
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Mission ended",
					color: "yellow",
				}),
			);
		});

		await waitFor(() => {
			expect(onClose).toHaveBeenCalled();
		});
	});

	it("shows error notification when endMission fails with Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce(new Error("Server error"));
		(useEndMission as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makeMission());

		const skipButton = screen.getByRole("button", { name: /Skip debrief/i });
		fireEvent.click(skipButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "End mission failed",
					message: "Server error",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when endMission fails with non-Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce("something");
		(useEndMission as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makeMission());

		const skipButton = screen.getByRole("button", { name: /Skip debrief/i });
		fireEvent.click(skipButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "End mission failed",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});
});
