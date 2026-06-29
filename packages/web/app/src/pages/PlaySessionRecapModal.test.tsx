import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// jsdom polyfills for Mantine Textarea autosize
// ---------------------------------------------------------------------------

if (!document.fonts) {
	Object.defineProperty(document, "fonts", {
		value: {
			addEventListener: vi.fn(),
			removeEventListener: vi.fn(),
		},
	});
}

if (typeof ResizeObserver === "undefined") {
	(globalThis as unknown as Record<string, unknown>).ResizeObserver = class {
		observe() {}
		unobserve() {}
		disconnect() {}
	};
}

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock Modal to render title in a <div> instead of <header>/<h2>,
// avoiding the "In HTML, <h4> cannot be a child of <h2>" warning.
vi.mock("@mantine/core", async () => {
	const actual = await vi.importActual("@mantine/core");
	return {
		...actual,
		Modal: ({
			opened,
			children,
			title,
		}: {
			opened: boolean;
			children?: React.ReactNode;
			title?: React.ReactNode;
		}) => {
			if (!opened) return null;
			return (
				<div data-testid="mock-modal" role="dialog">
					{title && <div data-testid="mock-modal-title">{title}</div>}
					{children}
				</div>
			);
		},
	};
});

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

vi.mock("../components/AiRecapOverlay", () => ({
	AiRecapOverlay: () => null,
}));

vi.mock("../hooks/usePlaySession", () => ({
	usePreviewRecap: vi.fn(),
	useRegenerateRecap: vi.fn(),
	useRetroactiveWrapUp: vi.fn(),
	useStartPlaySession: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import { notifications } from "@mantine/notifications";
import {
	usePreviewRecap,
	useRegenerateRecap,
	useRetroactiveWrapUp,
	useStartPlaySession,
} from "../hooks/usePlaySession";
import type { LibraryEntry } from "../types/library";
import type { PlaySession, RecapPreview } from "../types/play-session";
import { PlaySessionRecapModal } from "./PlaySessionRecapModal";

// ---------------------------------------------------------------------------
// Factories
// ---------------------------------------------------------------------------

const QUICK_TEXT =
	"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.";

function makeEntry(overrides: Partial<LibraryEntry> = {}): LibraryEntry {
	return {
		publicId: "entry-1",
		game: {
			publicId: "game-1",
			slug: "hollow-knight",
			title: "Hollow Knight",
			summary: "A metroidvania",
			coverUrl: null,
			genres: ["Action"],
			metadataSource: "igdb",
			createdAt: "2024-01-01T00:00:00Z",
		},
		platform: { id: 1, slug: "pc", label: "PC", family: "pc" },
		status: "playing",
		playSessionNextAction: null,
		notes: null,
		createdAt: "2024-06-01T00:00:00Z",
		updatedAt: "2024-06-01T00:00:00Z",
		...overrides,
	};
}

function makePreview(overrides: Partial<RecapPreview> = {}): RecapPreview {
	return {
		libraryEntry: makeEntry(),
		recapText: QUICK_TEXT,
		lastSessionContext: null,
		...overrides,
	};
}

function makePlaySession(overrides: Partial<PlaySession> = {}): PlaySession {
	return {
		publicId: "playSession-1",
		libraryEntry: makeEntry(),
		playSessionType: "regular",
		recapText: "Continue exploring the City of Tears. Look for the Soul Master.",
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

// ---------------------------------------------------------------------------
// Mutable mock return values
// ---------------------------------------------------------------------------

const mockPreviewMutateAsync = vi.fn();
const mockStartMutateAsync = vi.fn();
const mockRegenerateMutateAsync = vi.fn();
const mockRetroactiveMutateAsync = vi.fn();

// ---------------------------------------------------------------------------
// Render + navigation helpers
// ---------------------------------------------------------------------------

interface PreviewOverrides {
	libraryEntryPublicId?: string;
	onConfirm?: (playSession: PlaySession) => void;
	onClose?: () => void;
}

interface ViewOverrides {
	onClose?: () => void;
	onPlaySessionUpdated?: (playSession: PlaySession) => void;
}

function renderPreviewMode(
	libraryEntry: LibraryEntry = makeEntry(),
	overrides: PreviewOverrides = {},
) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<PlaySessionRecapModal
					mode="preview"
					libraryEntry={libraryEntry}
					libraryEntryPublicId={overrides.libraryEntryPublicId ?? libraryEntry.publicId}
					onConfirm={overrides.onConfirm ?? vi.fn()}
					onClose={overrides.onClose ?? vi.fn()}
				/>
			</MemoryRouter>
		</MantineProvider>,
	);
}

function renderViewMode(
	playSession: PlaySession = makePlaySession(),
	overrides: ViewOverrides = {},
) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<PlaySessionRecapModal
					mode="view"
					playSession={playSession}
					onClose={overrides.onClose ?? vi.fn()}
					onPlaySessionUpdated={overrides.onPlaySessionUpdated ?? vi.fn()}
				/>
			</MemoryRouter>
		</MantineProvider>,
	);
}

// Render preview mode and choose Quick → lands on the recap step.
async function renderPreviewRecap(libraryEntry?: LibraryEntry, overrides?: PreviewOverrides) {
	const result = renderPreviewMode(libraryEntry, overrides);
	fireEvent.click(screen.getByText("⚡ Quick recap"));
	await screen.findByText(QUICK_TEXT);
	return result;
}

function openUpdate() {
	fireEvent.click(screen.getByRole("button", { name: "Update this recap" }));
}
function openCorrection() {
	openUpdate();
	fireEvent.click(screen.getByRole("button", { name: "Correct my current position" }));
}
function openRetroactive() {
	openUpdate();
	fireEvent.click(screen.getByRole("button", { name: "Log a session I didn't register" }));
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
	mockPreviewMutateAsync.mockReset();
	mockStartMutateAsync.mockReset();
	mockRegenerateMutateAsync.mockReset();
	mockRetroactiveMutateAsync.mockReset();
	vi.clearAllMocks();

	mockPreviewMutateAsync.mockResolvedValue(makePreview());
	mockStartMutateAsync.mockResolvedValue(makePlaySession());

	(usePreviewRecap as Mock).mockReturnValue({
		mutateAsync: mockPreviewMutateAsync,
		isPending: false,
	});
	(useStartPlaySession as Mock).mockReturnValue({
		mutateAsync: mockStartMutateAsync,
		isPending: false,
	});
	(useRegenerateRecap as Mock).mockReturnValue({
		mutateAsync: mockRegenerateMutateAsync,
		isPending: false,
	});
	(useRetroactiveWrapUp as Mock).mockReturnValue({
		mutateAsync: mockRetroactiveMutateAsync,
		isPending: false,
	});
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PlaySessionRecapModal", () => {
	describe("preview mode — choose recap", () => {
		it("shows the two recap-mode buttons and a skip option on open", () => {
			renderPreviewMode();
			expect(screen.getByText("⚡ Quick recap")).toBeInTheDocument();
			expect(screen.getByText("🔎 Deep recap (web)")).toBeInTheDocument();
			expect(screen.getByText("▶️ Just play")).toBeInTheDocument();
		});

		it("'Just play' starts the playSession with no recap and confirms", async () => {
			const onConfirm = vi.fn();
			renderPreviewMode(makeEntry(), { onConfirm });

			fireEvent.click(screen.getByText("▶️ Just play"));

			await waitFor(() => {
				expect(mockStartMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({ libraryEntryPublicId: "entry-1", skipRecap: true }),
				);
			});
			expect(mockPreviewMutateAsync).not.toHaveBeenCalled(); // never generated a recap
			await waitFor(() => expect(onConfirm).toHaveBeenCalled());
		});

		it("shows the game title and platform", () => {
			renderPreviewMode();
			expect(screen.getByText(/Recap: Hollow Knight/)).toBeInTheDocument();
			expect(screen.getByText("PC")).toBeInTheDocument();
		});

		it("does NOT fetch a recap until a mode is chosen", () => {
			renderPreviewMode();
			expect(mockPreviewMutateAsync).not.toHaveBeenCalled();
		});

		it("choosing Quick fetches and shows the quick recap", async () => {
			renderPreviewMode();
			fireEvent.click(screen.getByText("⚡ Quick recap"));

			await waitFor(() => {
				expect(mockPreviewMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({ libraryEntryPublicId: "entry-1", mode: "quick" }),
				);
			});
			expect(await screen.findByText(QUICK_TEXT)).toBeInTheDocument();
		});

		it("choosing Deep fetches the deep recap", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(
				makePreview({ recapText: "Web-researched: head north to the next area." }),
			);
			renderPreviewMode();
			fireEvent.click(screen.getByText("🔎 Deep recap (web)"));

			await waitFor(() => {
				expect(mockPreviewMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({ mode: "deep" }),
				);
			});
			expect(
				await screen.findByText("Web-researched: head north to the next area."),
			).toBeInTheDocument();
		});

		it("shows the no-recap message when the fetched recap is empty", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(makePreview({ recapText: null }));
			renderPreviewMode();
			fireEvent.click(screen.getByText("⚡ Quick recap"));

			expect(await screen.findByText(/No recap available/)).toBeInTheDocument();
		});
	});

	describe("preview mode — recap actions", () => {
		it("shows 'Got it' and 'Update this recap', and no Cancel", async () => {
			await renderPreviewRecap();
			expect(screen.getByRole("button", { name: "Got it, let's go" })).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Update this recap" })).toBeInTheDocument();
			expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
		});

		it("'Update this recap' opens the fix menu with both options", async () => {
			await renderPreviewRecap();
			openUpdate();
			expect(
				screen.getByRole("button", { name: "Correct my current position" }),
			).toBeInTheDocument();
			expect(
				screen.getByRole("button", { name: "Log a session I didn't register" }),
			).toBeInTheDocument();
		});
	});

	describe("view mode", () => {
		it("renders the recap text", () => {
			renderViewMode();
			expect(
				screen.getByText("Continue exploring the City of Tears. Look for the Soul Master."),
			).toBeInTheDocument();
		});

		it("shows the game title", () => {
			renderViewMode();
			expect(screen.getByText(/Recap: Hollow Knight/)).toBeInTheDocument();
		});

		it("does NOT show the mode-choice buttons", () => {
			renderViewMode();
			expect(screen.queryByText("⚡ Quick recap")).not.toBeInTheDocument();
			expect(screen.queryByText("🔎 Deep recap (web)")).not.toBeInTheDocument();
		});

		it("shows 'That's not right' and 'Got it', no Cancel", () => {
			renderViewMode();
			expect(screen.getByRole("button", { name: "That's not right" })).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Got it, let's go" })).toBeInTheDocument();
			expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
		});

		it("shows no recap message when recapText is null", () => {
			renderViewMode(makePlaySession({ recapText: null }));
			expect(screen.getByText(/No recap available/)).toBeInTheDocument();
		});

		it("'That's not right' opens the correction form", () => {
			renderViewMode();
			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));
			expect(
				screen.getByText("Tell us where you actually are so we can adjust the recap:"),
			).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeInTheDocument();
		});
	});

	describe("correction flow", () => {
		it("update button is disabled when correction text is empty", async () => {
			await renderPreviewRecap();
			openCorrection();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeDisabled();
		});

		it("Back returns through the fix menu to the recap", async () => {
			await renderPreviewRecap();
			openCorrection();
			expect(screen.queryByText(QUICK_TEXT)).not.toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "Back" })); // correct → update
			fireEvent.click(screen.getByRole("button", { name: "Back" })); // update → recap
			expect(screen.getByText(QUICK_TEXT)).toBeInTheDocument();
		});

		it("preview: correction calls previewMutation with positionOverride", async () => {
			await renderPreviewRecap();
			openCorrection();
			fireEvent.change(screen.getByPlaceholderText(/I'm actually in City of Tears/), {
				target: { value: "I'm in City of Tears" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Update & regenerate" }));

			await waitFor(() => {
				expect(mockPreviewMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					positionOverride: "I'm in City of Tears",
				});
			});
		});

		it("preview: correction error shows notification", async () => {
			await renderPreviewRecap();
			mockPreviewMutateAsync.mockRejectedValueOnce(new Error("Network failure"));
			openCorrection();
			fireEvent.change(screen.getByPlaceholderText(/I'm actually in City of Tears/), {
				target: { value: "I'm in City of Tears" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Update & regenerate" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Regeneration failed",
						message: "Network failure",
						color: "red",
					}),
				);
			});
		});

		it("preview: correction with non-Error rejection shows fallback message", async () => {
			await renderPreviewRecap();
			mockPreviewMutateAsync.mockRejectedValueOnce("string error");
			openCorrection();
			fireEvent.change(screen.getByPlaceholderText(/I'm actually in City of Tears/), {
				target: { value: "I'm in City of Tears" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Update & regenerate" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Regeneration failed",
						message: "Couldn't regenerate recap",
						color: "red",
					}),
				);
			});
		});

		it("view: correction calls regenerate with publicId and currentPosition", async () => {
			const updatedPlaySession = makePlaySession({ recapText: "Regenerated view recap." });
			mockRegenerateMutateAsync.mockResolvedValue(updatedPlaySession);
			const onPlaySessionUpdated = vi.fn();

			renderViewMode(makePlaySession(), { onPlaySessionUpdated });
			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));
			fireEvent.change(screen.getByPlaceholderText(/I'm actually in City of Tears/), {
				target: { value: "I'm at the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Update & regenerate" }));

			await waitFor(() => {
				expect(mockRegenerateMutateAsync).toHaveBeenCalledWith({
					publicId: "playSession-1",
					currentPosition: "I'm at the Soul Master",
				});
			});
			await waitFor(() => {
				expect(onPlaySessionUpdated).toHaveBeenCalledWith(updatedPlaySession);
			});
		});
	});

	describe("retroactive flow", () => {
		it("record button is disabled when retroactive text is empty", async () => {
			await renderPreviewRecap();
			openRetroactive();
			expect(screen.getByRole("button", { name: "Record session & update recap" })).toBeDisabled();
		});

		it("preview: retroactive submit calls retroactiveMutation", async () => {
			mockRetroactiveMutateAsync.mockResolvedValue(
				makePreview({ recapText: "Updated after retroactive session." }),
			);
			await renderPreviewRecap();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master and got the Desolate Dive" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update recap" }));

			await waitFor(() => {
				expect(mockRetroactiveMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					wrapUpText: "I beat the Soul Master and got the Desolate Dive",
				});
			});
		});

		it("preview: successful retroactive shows success notification", async () => {
			mockRetroactiveMutateAsync.mockResolvedValue(
				makePreview({ recapText: "Updated after retroactive session." }),
			);
			await renderPreviewRecap();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update recap" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Session recorded",
						color: "teal",
					}),
				);
			});
		});

		it("preview: retroactive error shows error notification", async () => {
			mockRetroactiveMutateAsync.mockRejectedValue(new Error("Session recording failed"));
			await renderPreviewRecap();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update recap" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Failed to record session",
						message: "Session recording failed",
						color: "red",
					}),
				);
			});
		});

		it("preview: retroactive with non-Error rejection shows fallback message", async () => {
			mockRetroactiveMutateAsync.mockRejectedValue({ code: 500 });
			await renderPreviewRecap();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update recap" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Failed to record session",
						message: "An unexpected error occurred",
						color: "red",
					}),
				);
			});
		});
	});

	describe("confirm start", () => {
		it("preview: 'Got it, let's go' calls startPlaySession with the recap", async () => {
			const onConfirm = vi.fn();
			const playSession = makePlaySession();
			mockStartMutateAsync.mockResolvedValue(playSession);

			await renderPreviewRecap(makeEntry(), { onConfirm });
			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));

			await waitFor(() => {
				expect(mockStartMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					recapText: QUICK_TEXT,
				});
			});
			await waitFor(() => {
				expect(onConfirm).toHaveBeenCalledWith(playSession);
			});
		});

		it("preview: startPlaySession error shows notification", async () => {
			await renderPreviewRecap();
			mockStartMutateAsync.mockRejectedValueOnce(new Error("Server error"));
			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Couldn't start session",
						message: "Server error",
						color: "red",
					}),
				);
			});
		});

		it("preview: startPlaySession with non-Error rejection shows fallback message", async () => {
			await renderPreviewRecap();
			mockStartMutateAsync.mockRejectedValueOnce(42);
			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Couldn't start session",
						message: "An unexpected error occurred",
						color: "red",
					}),
				);
			});
		});

		it("preview: null recap passes undefined to startPlaySession", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(makePreview({ recapText: null }));
			renderPreviewMode();
			fireEvent.click(screen.getByText("⚡ Quick recap"));
			await screen.findByText(/No recap available/);

			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));
			await waitFor(() => {
				expect(mockStartMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					recapText: undefined,
				});
			});
		});
	});

	describe("key change resets state", () => {
		it("resets to the mode-choice step when libraryEntry changes", async () => {
			const { rerender } = render(
				<MantineProvider>
					<MemoryRouter>
						<PlaySessionRecapModal
							mode="preview"
							libraryEntry={makeEntry()}
							libraryEntryPublicId="entry-1"
							onConfirm={vi.fn()}
							onClose={vi.fn()}
						/>
					</MemoryRouter>
				</MantineProvider>,
			);

			fireEvent.click(screen.getByText("⚡ Quick recap"));
			await screen.findByText(QUICK_TEXT);
			openCorrection();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeInTheDocument();

			rerender(
				<MantineProvider>
					<MemoryRouter>
						<PlaySessionRecapModal
							mode="preview"
							libraryEntry={makeEntry({ publicId: "entry-2" })}
							libraryEntryPublicId="entry-2"
							onConfirm={vi.fn()}
							onClose={vi.fn()}
						/>
					</MemoryRouter>
				</MantineProvider>,
			);

			// Back at the mode-choice step; the correction form is gone.
			expect(screen.getByText("⚡ Quick recap")).toBeInTheDocument();
			expect(
				screen.queryByRole("button", { name: "Update & regenerate" }),
			).not.toBeInTheDocument();
		});
	});
});
