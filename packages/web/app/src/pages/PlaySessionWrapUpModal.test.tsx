import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useEndPlaySession, useSubmitWrapUp } from "../hooks/usePlaySession";
import type { PlaySession } from "../types/play-session";
import { PlaySessionWrapUpModal } from "./PlaySessionWrapUpModal";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../hooks/usePlaySession", () => ({
	useEndPlaySession: vi.fn(),
	useSubmitWrapUp: vi.fn(),
	usePlaySessions: vi.fn(() => ({ data: null, isLoading: false })),
	useActivePlaySession: vi.fn(() => ({ data: null })),
	usePlaySession: vi.fn(() => ({ data: null, isLoading: false })),
	useStartPlaySession: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	usePreviewRecap: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useRegenerateRecap: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useRetroactiveWrapUp: vi.fn(() => ({
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

function makePlaySession(overrides: Partial<PlaySession> = {}): PlaySession {
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
		playSessionType: "regular",
		recapText: "Welcome back to Hollow Knight...",
		wrapUpText: null,
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

function renderModal(playSession: PlaySession | null, onClose = defaultOnClose) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<PlaySessionWrapUpModal playSession={playSession} onClose={onClose} />
			</MemoryRouter>
		</MantineProvider>,
	);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PlaySessionWrapUpModal", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		(useEndPlaySession as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: false,
		});
		(useSubmitWrapUp as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: false,
		});
	});

	it("returns null and renders nothing when playSession is null", () => {
		renderModal(null);

		expect(screen.queryByText(/End PlaySession/)).not.toBeInTheDocument();
		expect(screen.queryByTestId("mock-modal")).not.toBeInTheDocument();
	});

	it("renders modal title with the game name", () => {
		renderModal(makePlaySession());

		expect(screen.getByText(/End session: Hollow Knight/)).toBeInTheDocument();
	});

	it("renders title with different game name", () => {
		const playSession = makePlaySession({
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

		renderModal(playSession);

		expect(screen.getByText(/End session: Elden Ring/)).toBeInTheDocument();
	});

	it("renders the wrapUp description text", () => {
		renderModal(makePlaySession());

		expect(screen.getByText(/What happened this session/)).toBeInTheDocument();
	});

	it("renders the textarea with correct placeholder", () => {
		renderModal(makePlaySession());

		expect(screen.getByPlaceholderText(/Beat the Mantis Lords/)).toBeInTheDocument();
	});

	it("renders 'Skip wrap-up' and 'Save wrap-up' buttons", () => {
		renderModal(makePlaySession());

		expect(screen.getByRole("button", { name: /Skip wrap-up/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /Save wrap-up/i })).toBeInTheDocument();
	});

	it("submit wrapUp button is disabled when text is shorter than 3 characters", () => {
		renderModal(makePlaySession());

		const submitButton = screen.getByRole("button", { name: /Save wrap-up/i });
		expect(submitButton).toBeDisabled();
	});

	it("submit wrapUp button becomes enabled when text is 3+ characters", () => {
		renderModal(makePlaySession());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Got the cloak" } });

		const submitButton = screen.getByRole("button", { name: /Save wrap-up/i });
		expect(submitButton).not.toBeDisabled();
	});

	it("submit wrapUp stays disabled with only whitespace", () => {
		renderModal(makePlaySession());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "   " } });

		const submitButton = screen.getByRole("button", { name: /Save wrap-up/i });
		expect(submitButton).toBeDisabled();
	});

	it("skip wrapUp button is not disabled even without text", () => {
		renderModal(makePlaySession());

		const skipButton = screen.getByRole("button", { name: /Skip wrap-up/i });
		expect(skipButton).not.toBeDisabled();
	});

	it("shows loading state on skip button when endPlaySession is pending", () => {
		(useEndPlaySession as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: true,
		});

		renderModal(makePlaySession());

		const skipButton = screen.getByRole("button", { name: /Skip wrap-up/i });
		expect(skipButton).toHaveAttribute("data-loading");
	});

	it("shows loading state on submit button when submitWrapUp is pending", () => {
		(useSubmitWrapUp as Mock).mockReturnValue({
			mutateAsync: vi.fn(),
			isPending: true,
		});

		renderModal(makePlaySession());

		const submitButton = screen.getByRole("button", { name: /Save wrap-up/i });
		expect(submitButton).toHaveAttribute("data-loading");
	});

	// --- Save wrap-up flow ---

	it("calls submitWrapUp.mutateAsync on submit and shows success notification", async () => {
		const mutateAsyncFn = vi.fn().mockResolvedValueOnce(undefined);
		(useSubmitWrapUp as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		const onClose = vi.fn();
		renderModal(makePlaySession(), onClose);

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Beat the Mantis Lords and got the cloak" } });

		const submitButton = screen.getByRole("button", { name: /Save wrap-up/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(mutateAsyncFn).toHaveBeenCalledWith({
				publicId: "mis-001",
				wrapUpText: "Beat the Mantis Lords and got the cloak",
			});
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Session complete",
					color: "green",
				}),
			);
		});

		await waitFor(() => {
			expect(onClose).toHaveBeenCalled();
		});
	});

	it("shows error notification when submitWrapUp fails with Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce(new Error("Server error"));
		(useSubmitWrapUp as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makePlaySession());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Some wrapUp text" } });

		const submitButton = screen.getByRole("button", { name: /Save wrap-up/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Couldn't save your wrap-up",
					message: "Server error",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when submitWrapUp fails with non-Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce("something");
		(useSubmitWrapUp as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makePlaySession());

		const textarea = screen.getByPlaceholderText(/Beat the Mantis Lords/);
		fireEvent.change(textarea, { target: { value: "Some wrapUp text" } });

		const submitButton = screen.getByRole("button", { name: /Save wrap-up/i });
		fireEvent.click(submitButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Couldn't save your wrap-up",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});

	// --- Skip wrap-up flow ---

	it("calls endPlaySession.mutateAsync on skip and shows notification", async () => {
		const mutateAsyncFn = vi.fn().mockResolvedValueOnce(undefined);
		(useEndPlaySession as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		const onClose = vi.fn();
		renderModal(makePlaySession(), onClose);

		const skipButton = screen.getByRole("button", { name: /Skip wrap-up/i });
		fireEvent.click(skipButton);

		await waitFor(() => {
			expect(mutateAsyncFn).toHaveBeenCalledWith({ publicId: "mis-001" });
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Session ended",
					color: "yellow",
				}),
			);
		});

		await waitFor(() => {
			expect(onClose).toHaveBeenCalled();
		});
	});

	it("shows error notification when endPlaySession fails with Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce(new Error("Server error"));
		(useEndPlaySession as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makePlaySession());

		const skipButton = screen.getByRole("button", { name: /Skip wrap-up/i });
		fireEvent.click(skipButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Couldn't end session",
					message: "Server error",
					color: "red",
				}),
			);
		});
	});

	it("shows generic error notification when endPlaySession fails with non-Error", async () => {
		const mutateAsyncFn = vi.fn().mockRejectedValueOnce("something");
		(useEndPlaySession as Mock).mockReturnValue({
			mutateAsync: mutateAsyncFn,
			isPending: false,
		});

		renderModal(makePlaySession());

		const skipButton = screen.getByRole("button", { name: /Skip wrap-up/i });
		fireEvent.click(skipButton);

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Couldn't end session",
					message: "An unexpected error occurred",
					color: "red",
				}),
			);
		});
	});
});
