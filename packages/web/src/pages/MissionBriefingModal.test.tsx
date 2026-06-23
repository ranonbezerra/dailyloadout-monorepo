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
// Helpers
// ---------------------------------------------------------------------------

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
		briefingText:
			"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.",
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
// Render helpers
// ---------------------------------------------------------------------------

interface PreviewOverrides {
	libraryEntryPublicId?: string;
	onConfirm?: (mission: Mission) => void;
	onPreviewUpdated?: (preview: BriefingPreview) => void;
	onClose?: () => void;
}

interface ViewOverrides {
	onClose?: () => void;
	onMissionUpdated?: (mission: Mission) => void;
}

function renderPreviewMode(
	preview: BriefingPreview = makePreview(),
	overrides: PreviewOverrides = {},
) {
	const onConfirm = overrides.onConfirm ?? vi.fn();
	const onPreviewUpdated = overrides.onPreviewUpdated ?? vi.fn();
	const onClose = overrides.onClose ?? vi.fn();

	return render(
		<MantineProvider>
			<MemoryRouter>
				<MissionBriefingModal
					mode="preview"
					preview={preview}
					libraryEntryPublicId={overrides.libraryEntryPublicId ?? preview.libraryEntry.publicId}
					onConfirm={onConfirm}
					onPreviewUpdated={onPreviewUpdated}
					onClose={onClose}
				/>
			</MemoryRouter>
		</MantineProvider>,
	);
}

function renderViewMode(mission: Mission = makeMission(), overrides: ViewOverrides = {}) {
	const onClose = overrides.onClose ?? vi.fn();
	const onMissionUpdated = overrides.onMissionUpdated ?? vi.fn();

	return render(
		<MantineProvider>
			<MemoryRouter>
				<MissionBriefingModal
					mode="view"
					mission={mission}
					onClose={onClose}
					onMissionUpdated={onMissionUpdated}
				/>
			</MemoryRouter>
		</MantineProvider>,
	);
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
	describe("preview mode", () => {
		it("renders the briefing text", () => {
			renderPreviewMode();

			expect(
				screen.getByText(
					"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.",
				),
			).toBeInTheDocument();
		});

		it("shows the game title in the modal title", () => {
			renderPreviewMode();

			expect(screen.getByText(/Mission Briefing: Hollow Knight/)).toBeInTheDocument();
		});

		it("shows the platform label", () => {
			renderPreviewMode();

			expect(screen.getByText("PC")).toBeInTheDocument();
		});

		it('shows "I played without registering" button', () => {
			renderPreviewMode();

			expect(
				screen.getByRole("button", { name: "I played without registering" }),
			).toBeInTheDocument();
		});

		it('shows "That\'s not right" button', () => {
			renderPreviewMode();

			expect(screen.getByRole("button", { name: "That's not right" })).toBeInTheDocument();
		});

		it('shows "Got it, let\'s go" button', () => {
			renderPreviewMode();

			expect(screen.getByRole("button", { name: "Got it, let's go" })).toBeInTheDocument();
		});

		it('shows "Cancel" button', () => {
			renderPreviewMode();

			expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
		});

		it("shows no briefing message when briefingText is null", () => {
			const preview = makePreview({ briefingText: null });

			renderPreviewMode(preview);

			expect(screen.getByText(/No briefing available/)).toBeInTheDocument();
		});

		it('"That\'s not right" opens correction form', () => {
			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			// Correction form should appear with textarea and Update button
			expect(
				screen.getByText("Tell us where you actually are so we can adjust the briefing:"),
			).toBeInTheDocument();
			expect(screen.getByPlaceholderText(/I'm actually in City of Tears/)).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
		});

		it('"I played without registering" opens retroactive form', () => {
			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "I played without registering" }));

			expect(
				screen.getByText(
					"Tell us what happened in that unregistered session so we can update your briefing:",
				),
			).toBeInTheDocument();
			expect(screen.getByPlaceholderText(/I played for a couple hours/)).toBeInTheDocument();
			expect(
				screen.getByRole("button", { name: "Record session & update briefing" }),
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

		it("shows the game title in the modal title", () => {
			renderViewMode();

			expect(screen.getByText(/Mission Briefing: Hollow Knight/)).toBeInTheDocument();
		});

		it('does NOT show "I played without registering" button', () => {
			renderViewMode();

			expect(
				screen.queryByRole("button", { name: "I played without registering" }),
			).not.toBeInTheDocument();
		});

		it('shows "That\'s not right" button', () => {
			renderViewMode();

			expect(screen.getByRole("button", { name: "That's not right" })).toBeInTheDocument();
		});

		it('shows "Got it, let\'s go" button', () => {
			renderViewMode();

			expect(screen.getByRole("button", { name: "Got it, let's go" })).toBeInTheDocument();
		});

		it('does NOT show "Cancel" button (view mode just has single close button)', () => {
			renderViewMode();

			expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
		});

		it("shows no briefing message when briefingText is null", () => {
			const mission = makeMission({ briefingText: null });

			renderViewMode(mission);

			expect(screen.getByText(/No briefing available/)).toBeInTheDocument();
		});

		it('"That\'s not right" opens correction form in view mode', () => {
			renderViewMode();

			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			expect(
				screen.getByText("Tell us where you actually are so we can adjust the briefing:"),
			).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeInTheDocument();
		});
	});

	describe("correction flow", () => {
		it("update button is disabled when correction text is empty", () => {
			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			const updateBtn = screen.getByRole("button", { name: "Update & regenerate" });
			expect(updateBtn).toBeDisabled();
		});

		it("back button returns to briefing step", () => {
			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			// Briefing text should not be visible in correction step
			expect(
				screen.queryByText(
					"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.",
				),
			).not.toBeInTheDocument();

			fireEvent.click(screen.getByRole("button", { name: "Back" }));

			// Briefing text should be visible again
			expect(
				screen.getByText(
					"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.",
				),
			).toBeInTheDocument();
		});

		it("preview: correction calls previewMutation with positionOverride", async () => {
			const updatedPreview = makePreview({
				briefingText: "Updated briefing after correction.",
			});
			mockPreviewMutateAsync.mockResolvedValue(updatedPreview);

			renderPreviewMode();

			// Open correction form
			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			// Type correction
			const textarea = screen.getByPlaceholderText(/I'm actually in City of Tears/);
			fireEvent.change(textarea, { target: { value: "I'm in City of Tears" } });

			// Click update
			fireEvent.click(screen.getByRole("button", { name: "Update & regenerate" }));

			await waitFor(() => {
				expect(mockPreviewMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					positionOverride: "I'm in City of Tears",
				});
			});
		});

		it("preview: correction error shows notification", async () => {
			mockPreviewMutateAsync.mockRejectedValue(new Error("Network failure"));

			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			const textarea = screen.getByPlaceholderText(/I'm actually in City of Tears/);
			fireEvent.change(textarea, { target: { value: "I'm in City of Tears" } });

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
			mockPreviewMutateAsync.mockRejectedValue("string error");

			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			const textarea = screen.getByPlaceholderText(/I'm actually in City of Tears/);
			fireEvent.change(textarea, { target: { value: "I'm in City of Tears" } });

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
			const updatedMission = makeMission({
				briefingText: "Regenerated view briefing.",
			});
			mockRegenerateMutateAsync.mockResolvedValue(updatedMission);
			const onMissionUpdated = vi.fn();

			renderViewMode(makeMission(), { onMissionUpdated });

			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));

			const textarea = screen.getByPlaceholderText(/I'm actually in City of Tears/);
			fireEvent.change(textarea, { target: { value: "I'm at the Soul Master" } });

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
		it("record button is disabled when retroactive text is empty", () => {
			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "I played without registering" }));

			const recordBtn = screen.getByRole("button", {
				name: "Record session & update briefing",
			});
			expect(recordBtn).toBeDisabled();
		});

		it("back button returns to briefing step from retroactive", () => {
			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "I played without registering" }));

			fireEvent.click(screen.getByRole("button", { name: "Back" }));

			// Briefing text should be visible again
			expect(
				screen.getByText(
					"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.",
				),
			).toBeInTheDocument();
		});

		it("preview: retroactive submit calls retroactiveMutation", async () => {
			const updatedPreview = makePreview({
				briefingText: "Updated after retroactive session.",
			});
			mockRetroactiveMutateAsync.mockResolvedValue(updatedPreview);

			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "I played without registering" }));

			const textarea = screen.getByPlaceholderText(/I played for a couple hours/);
			fireEvent.change(textarea, {
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
			const updatedPreview = makePreview({
				briefingText: "Updated after retroactive session.",
			});
			mockRetroactiveMutateAsync.mockResolvedValue(updatedPreview);

			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "I played without registering" }));

			const textarea = screen.getByPlaceholderText(/I played for a couple hours/);
			fireEvent.change(textarea, {
				target: { value: "I beat the Soul Master" },
			});

			fireEvent.click(screen.getByRole("button", { name: "Record session & update briefing" }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Session recorded",
						message: "Your unregistered session has been saved. The briefing has been updated.",
						color: "teal",
					}),
				);
			});
		});

		it("preview: retroactive error shows error notification", async () => {
			mockRetroactiveMutateAsync.mockRejectedValue(new Error("Session recording failed"));

			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "I played without registering" }));

			const textarea = screen.getByPlaceholderText(/I played for a couple hours/);
			fireEvent.change(textarea, {
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

			renderPreviewMode();

			fireEvent.click(screen.getByRole("button", { name: "I played without registering" }));

			const textarea = screen.getByPlaceholderText(/I played for a couple hours/);
			fireEvent.change(textarea, {
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
		it("preview: 'Got it, let's go' calls startMission.mutateAsync", async () => {
			const mission = makeMission();
			mockStartMutateAsync.mockResolvedValue(mission);
			const onConfirm = vi.fn();

			renderPreviewMode(makePreview(), { onConfirm });

			fireEvent.click(screen.getByRole("button", { name: "Got it, let's go" }));

			await waitFor(() => {
				expect(mockStartMutateAsync).toHaveBeenCalledWith({
					libraryEntryPublicId: "entry-1",
					briefingText:
						"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.",
				});
			});

			await waitFor(() => {
				expect(onConfirm).toHaveBeenCalledWith(mission);
			});
		});

		it("preview: startMission error shows notification", async () => {
			mockStartMutateAsync.mockRejectedValue(new Error("Server error"));

			renderPreviewMode();

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
			mockStartMutateAsync.mockRejectedValue(42);

			renderPreviewMode();

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

		it("preview: startMission with null briefingText passes undefined", async () => {
			const mission = makeMission();
			mockStartMutateAsync.mockResolvedValue(mission);
			const onConfirm = vi.fn();
			const preview = makePreview({ briefingText: null });

			renderPreviewMode(preview, { onConfirm });

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
		it("resets correction state when libraryEntryPublicId changes", () => {
			const preview1 = makePreview();
			const { rerender } = render(
				<MantineProvider>
					<MemoryRouter>
						<MissionBriefingModal
							mode="preview"
							preview={preview1}
							libraryEntryPublicId="entry-1"
							onConfirm={vi.fn()}
							onPreviewUpdated={vi.fn()}
							onClose={vi.fn()}
						/>
					</MemoryRouter>
				</MantineProvider>,
			);

			// Navigate to correction step and type something
			fireEvent.click(screen.getByRole("button", { name: "That's not right" }));
			const textarea = screen.getByPlaceholderText(/I'm actually in City of Tears/);
			fireEvent.change(textarea, { target: { value: "Some correction" } });

			// Verify we are on the correction step
			expect(screen.getByRole("button", { name: "Update & regenerate" })).toBeInTheDocument();

			// Re-render with a different libraryEntryPublicId
			const preview2 = makePreview({
				libraryEntry: makeEntry({ publicId: "entry-2" }),
				briefingText: "A different briefing for entry 2.",
			});

			rerender(
				<MantineProvider>
					<MemoryRouter>
						<MissionBriefingModal
							mode="preview"
							preview={preview2}
							libraryEntryPublicId="entry-2"
							onConfirm={vi.fn()}
							onPreviewUpdated={vi.fn()}
							onClose={vi.fn()}
						/>
					</MemoryRouter>
				</MantineProvider>,
			);

			// Should be back on briefing step showing the new briefing text
			expect(screen.getByText("A different briefing for entry 2.")).toBeInTheDocument();

			// Correction form should not be visible
			expect(
				screen.queryByRole("button", { name: "Update & regenerate" }),
			).not.toBeInTheDocument();
		});
	});

	describe("deep briefing toggle", () => {
		it("requests a deep briefing when switching to Deep", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(
				makePreview({ briefingText: "Web-researched: head north to the next area." }),
			);
			renderPreviewMode();

			fireEvent.click(screen.getByText("Deep (web)"));

			await waitFor(() => {
				expect(mockPreviewMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({ mode: "deep" }),
				);
			});
			expect(
				await screen.findByText("Web-researched: head north to the next area."),
			).toBeInTheDocument();
		});

		it("shows the toggle only in preview mode, not view mode", () => {
			const { unmount } = renderPreviewMode();
			expect(screen.getByText("Deep (web)")).toBeInTheDocument();
			unmount();

			renderViewMode();
			expect(screen.queryByText("Deep (web)")).not.toBeInTheDocument();
		});

		it("reverts to the quick briefing when switching back to Quick", async () => {
			mockPreviewMutateAsync.mockResolvedValueOnce(
				makePreview({ briefingText: "Deep briefing content." }),
			);
			renderPreviewMode();

			fireEvent.click(screen.getByText("Deep (web)"));
			expect(await screen.findByText("Deep briefing content.")).toBeInTheDocument();

			fireEvent.click(screen.getByText("Quick"));
			// Original quick briefing is shown again.
			expect(
				screen.getByText(
					"You are deep within the Forgotten Crossroads. Your next goal is to find the City of Tears.",
				),
			).toBeInTheDocument();
		});
	});
});
