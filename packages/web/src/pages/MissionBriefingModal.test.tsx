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

vi.mock("../components/AiBriefingOverlay", () => ({
	AiBriefingOverlay: () => null,
}));

vi.mock("../hooks/useMission", () => ({
	usePreviewBriefing: vi.fn(),
	useRegenerateBriefing: vi.fn(),
	useRetroactiveDebrief: vi.fn(),
	useStartMission: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import { notifications } from "@mantine/notifications";
import {
	usePreviewBriefing,
	useRegenerateBriefing,
	useRetroactiveDebrief,
	useStartMission,
} from "../hooks/useMission";
import type { LibraryEntry } from "../types/library";
import type { BriefingPreview, Mission } from "../types/mission";
import { MissionBriefingModal } from "./MissionBriefingModal";

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
		missionNextAction: null,
		notes: null,
		createdAt: "2024-06-01T00:00:00Z",
		updatedAt: "2024-06-01T00:00:00Z",
		...overrides,
	};
}

function makePreview(overrides: Partial<BriefingPreview> = {}): BriefingPreview {
	return {
		libraryEntry: makeEntry(),
		briefingText: QUICK_TEXT,
		lastSessionContext: null,
		...overrides,
	};
}

function makeMission(overrides: Partial<Mission> = {}): Mission {
	return {
		publicId: "mission-1",
		libraryEntry: makeEntry(),
		missionType: "regular",
		briefingText: "Continue exploring the City of Tears. Look for the Soul Master.",
		debriefText: null,
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
	onConfirm?: (mission: Mission) => void;
	onClose?: () => void;
}

interface ViewOverrides {
	onClose?: () => void;
	onMissionUpdated?: (mission: Mission) => void;
}

function renderPreviewMode(
	libraryEntry: LibraryEntry = makeEntry(),
	overrides: PreviewOverrides = {},
) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<MissionBriefingModal
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

function renderViewMode(mission: Mission = makeMission(), overrides: ViewOverrides = {}) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<MissionBriefingModal
					mode="view"
					mission={mission}
					onClose={overrides.onClose ?? vi.fn()}
					onMissionUpdated={overrides.onMissionUpdated ?? vi.fn()}
				/>
			</MemoryRouter>
		</MantineProvider>,
	);
}

// Render preview mode and choose Quick → lands on the briefing step.
async function renderPreviewBriefing(libraryEntry?: LibraryEntry, overrides?: PreviewOverrides) {
	const result = renderPreviewMode(libraryEntry, overrides);
	fireEvent.click(screen.getByText("⚡ Quick briefing"));
	await screen.findByText(QUICK_TEXT);
	return result;
}

function openUpdate() {
	fireEvent.click(screen.getByRole("button", { name: "Update this briefing" }));
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
	mockStartMutateAsync.mockResolvedValue(makeMission());

	(usePreviewBriefing as Mock).mockReturnValue({
		mutateAsync: mockPreviewMutateAsync,
		isPending: false,
	});
	(useStartMission as Mock).mockReturnValue({
		mutateAsync: mockStartMutateAsync,
		isPending: false,
	});
	(useRegenerateBriefing as Mock).mockReturnValue({
		mutateAsync: mockRegenerateMutateAsync,
		isPending: false,
	});
	(useRetroactiveDebrief as Mock).mockReturnValue({
		mutateAsync: mockRetroactiveMutateAsync,
		isPending: false,
	});
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MissionBriefingModal", () => {
	describe("preview mode — choose briefing", () => {
		it("shows the two briefing-mode buttons and a skip option on open", () => {
			renderPreviewMode();
			expect(screen.getByText("⚡ Quick briefing")).toBeInTheDocument();
			expect(screen.getByText("🔎 Deep briefing (web)")).toBeInTheDocument();
			expect(screen.getByText("▶️ Just play")).toBeInTheDocument();
		});

		it("'Just play' starts the mission with no briefing and confirms", async () => {
			const onConfirm = vi.fn();
			renderPreviewMode(makeEntry(), { onConfirm });

			fireEvent.click(screen.getByText("▶️ Just play"));

			await waitFor(() => {
				expect(mockStartMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({ libraryEntryPublicId: "entry-1", skipBriefing: true }),
				);
			});
			expect(mockPreviewMutateAsync).not.toHaveBeenCalled(); // never generated a briefing
			await waitFor(() => expect(onConfirm).toHaveBeenCalled());
		});

		it("shows the game title and platform", () => {
			renderPreviewMode();
			expect(screen.getByText(/Mission Briefing: Hollow Knight/)).toBeInTheDocument();
			expect(screen.getByText("PC")).toBeInTheDocument();
		});

		it("does NOT fetch a briefing until a mode is chosen", () => {
			renderPreviewMode();
			expect(mockPreviewMutateAsync).not.toHaveBeenCalled();
		});

		it("choosing Quick fetches and shows the quick briefing", async () => {
			renderPreviewMode();
			fireEvent.click(screen.getByText("⚡ Quick briefing"));

			await waitFor(() => {
				expect(mockPreviewMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({ libraryEntryPublicId: "entry-1", mode: "quick" }),
				);
			});
			expect(await screen.findByText(QUICK_TEXT)).toBeInTheDocument();
		});

		it("choosing Deep fetches the deep briefing", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(
				makePreview({ briefingText: "Web-researched: head north to the next area." }),
			);
			renderPreviewMode();
			fireEvent.click(screen.getByText("🔎 Deep briefing (web)"));

			await waitFor(() => {
				expect(mockPreviewMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({ mode: "deep" }),
				);
			});
			expect(
				await screen.findByText("Web-researched: head north to the next area."),
			).toBeInTheDocument();
		});

		it("shows the no-briefing message when the fetched briefing is empty", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(makePreview({ briefingText: null }));
			renderPreviewMode();
			fireEvent.click(screen.getByText("⚡ Quick briefing"));

			expect(await screen.findByText(/No briefing available/)).toBeInTheDocument();
		});
	});

	describe("preview mode — briefing actions", () => {
		it("shows 'Got it' and 'Update this briefing', and no Cancel", async () => {
			await renderPreviewBriefing();
			expect(screen.getByRole("button", { name: "Got it, let's go" })).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Update this briefing" })).toBeInTheDocument();
			expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
		});

		it("'Update this briefing' opens the fix menu with both options", async () => {
			await renderPreviewBriefing();
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
		it("renders the briefing text", () => {
			renderViewMode();
			expect(
				screen.getByText("Continue exploring the City of Tears. Look for the Soul Master."),
			).toBeInTheDocument();
		});

		it("shows the game title", () => {
			renderViewMode();
			expect(screen.getByText(/Mission Briefing: Hollow Knight/)).toBeInTheDocument();
		});

		it("does NOT show the mode-choice buttons", () => {
			renderViewMode();
			expect(screen.queryByText("⚡ Quick briefing")).not.toBeInTheDocument();
			expect(screen.queryByText("🔎 Deep briefing (web)")).not.toBeInTheDocument();
		});

		it("shows 'That's not right' and 'Got it', no Cancel", () => {
			renderViewMode();
			expect(screen.getByRole("button", { name: "That's not right" })).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Got it, let's go" })).toBeInTheDocument();
			expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
		});

		it("shows no briefing message when briefingText is null", () => {
			renderViewMode(makeMission({ briefingText: null }));
			expect(screen.getByText(/No briefing available/)).toBeInTheDocument();
		});

		it("'That's not right' opens the correction form", () => {
			renderViewMode();
			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));
			expect(
				screen.getByText("Tell us where you actually are so we can adjust the briefing:"),
			).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeInTheDocument();
		});
	});

	describe("correction flow", () => {
		it("update button is disabled when correction text is empty", async () => {
			await renderPreviewBriefing();
			openCorrection();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeDisabled();
		});

		it("Back returns through the fix menu to the briefing", async () => {
			await renderPreviewBriefing();
			openCorrection();
			expect(screen.queryByText(QUICK_TEXT)).not.toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "Back" })); // correct → update
			fireEvent.click(screen.getByRole("button", { name: "Back" })); // update → briefing
			expect(screen.getByText(QUICK_TEXT)).toBeInTheDocument();
		});

		it("preview: correction calls previewMutation with positionOverride", async () => {
			await renderPreviewBriefing();
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
			await renderPreviewBriefing();
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
			await renderPreviewBriefing();
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
						message: "Could not regenerate briefing",
						color: "red",
					}),
				);
			});
		});

		it("view: correction calls regenerate with publicId and currentPosition", async () => {
			const updatedMission = makeMission({ briefingText: "Regenerated view briefing." });
			mockRegenerateMutateAsync.mockResolvedValue(updatedMission);
			const onMissionUpdated = vi.fn();

			renderViewMode(makeMission(), { onMissionUpdated });
			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));
			fireEvent.change(screen.getByPlaceholderText(/I'm actually in City of Tears/), {
				target: { value: "I'm at the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Update & regenerate" }));

			await waitFor(() => {
				expect(mockRegenerateMutateAsync).toHaveBeenCalledWith({
					publicId: "mission-1",
					currentPosition: "I'm at the Soul Master",
				});
			});
			await waitFor(() => {
				expect(onMissionUpdated).toHaveBeenCalledWith(updatedMission);
			});
		});
	});

	describe("retroactive flow", () => {
		it("record button is disabled when retroactive text is empty", async () => {
			await renderPreviewBriefing();
			openRetroactive();
			expect(
				screen.getByRole("button", { name: "Record session & update briefing" }),
			).toBeDisabled();
		});

		it("preview: retroactive submit calls retroactiveMutation", async () => {
			mockRetroactiveMutateAsync.mockResolvedValue(
				makePreview({ briefingText: "Updated after retroactive session." }),
			);
			await renderPreviewBriefing();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master and got the Desolate Dive" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update briefing" }));

			await waitFor(() => {
				expect(mockRetroactiveMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					debriefText: "I beat the Soul Master and got the Desolate Dive",
				});
			});
		});

		it("preview: successful retroactive shows success notification", async () => {
			mockRetroactiveMutateAsync.mockResolvedValue(
				makePreview({ briefingText: "Updated after retroactive session." }),
			);
			await renderPreviewBriefing();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update briefing" }));

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
			await renderPreviewBriefing();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update briefing" }));

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
			await renderPreviewBriefing();
			openRetroactive();
			fireEvent.change(screen.getByPlaceholderText(/I played for a couple hours/), {
				target: { value: "I beat the Soul Master" },
			});
			fireEvent.click(screen.getByRole("button", { name: "Record session & update briefing" }));

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
		it("preview: 'Got it, let's go' calls startMission with the briefing", async () => {
			const onConfirm = vi.fn();
			const mission = makeMission();
			mockStartMutateAsync.mockResolvedValue(mission);

			await renderPreviewBriefing(makeEntry(), { onConfirm });
			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));

			await waitFor(() => {
				expect(mockStartMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					briefingText: QUICK_TEXT,
				});
			});
			await waitFor(() => {
				expect(onConfirm).toHaveBeenCalledWith(mission);
			});
		});

		it("preview: startMission error shows notification", async () => {
			await renderPreviewBriefing();
			mockStartMutateAsync.mockRejectedValueOnce(new Error("Server error"));
			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Cannot start mission",
						message: "Server error",
						color: "red",
					}),
				);
			});
		});

		it("preview: startMission with non-Error rejection shows fallback message", async () => {
			await renderPreviewBriefing();
			mockStartMutateAsync.mockRejectedValueOnce(42);
			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Cannot start mission",
						message: "An unexpected error occurred",
						color: "red",
					}),
				);
			});
		});

		it("preview: null briefing passes undefined to startMission", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(makePreview({ briefingText: null }));
			renderPreviewMode();
			fireEvent.click(screen.getByText("⚡ Quick briefing"));
			await screen.findByText(/No briefing available/);

			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));
			await waitFor(() => {
				expect(mockStartMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					briefingText: undefined,
				});
			});
		});
	});

	describe("key change resets state", () => {
		it("resets to the mode-choice step when libraryEntry changes", async () => {
			const { rerender } = render(
				<MantineProvider>
					<MemoryRouter>
						<MissionBriefingModal
							mode="preview"
							libraryEntry={makeEntry()}
							libraryEntryPublicId="entry-1"
							onConfirm={vi.fn()}
							onClose={vi.fn()}
						/>
					</MemoryRouter>
				</MantineProvider>,
			);

			fireEvent.click(screen.getByText("⚡ Quick briefing"));
			await screen.findByText(QUICK_TEXT);
			openCorrection();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeInTheDocument();

			rerender(
				<MantineProvider>
					<MemoryRouter>
						<MissionBriefingModal
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
			expect(screen.getByText("⚡ Quick briefing")).toBeInTheDocument();
			expect(
				screen.queryByRole("button", { name: "Update & regenerate" }),
			).not.toBeInTheDocument();
		});
	});
});
