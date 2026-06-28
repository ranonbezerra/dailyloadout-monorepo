import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

// Mock Textarea (autosize crashes in jsdom)
vi.mock("@mantine/core", async () => {
	const actual = await vi.importActual("@mantine/core");
	return {
		...actual,
		Textarea: ({
			label,
			placeholder,
			value,
			onChange,
		}: {
			label?: string;
			placeholder?: string;
			value?: string;
			onChange?: React.ChangeEventHandler<HTMLTextAreaElement>;
		}) => (
			<div>
				<textarea placeholder={placeholder} value={value} onChange={onChange} aria-label={label} />
			</div>
		),
	};
});

vi.mock("./AddGameModal", () => ({ AddGameModal: () => null }));
vi.mock("./CaptureTextModal", () => ({ CaptureTextModal: () => null }));
vi.mock("./CaptureVoiceModal", () => ({ CaptureVoiceModal: () => null }));
vi.mock("./CapturePhotoModal", () => ({ CapturePhotoModal: () => null }));
vi.mock("./CaptureReviewModal", () => ({ CaptureReviewModal: () => null }));
vi.mock("./MissionBriefingModal", () => ({
	MissionBriefingModal: ({ mode }: { mode: string }) =>
		mode === "preview" ? <div data-testid="briefing-preview-modal" /> : null,
}));
vi.mock("./MissionDebriefModal", () => ({ MissionDebriefModal: () => null }));
vi.mock("../components/QuickAddMenu", () => ({
	QuickAddMenu: () => <button type="button">Quick Add</button>,
}));
vi.mock("../components/AiBriefingOverlay", () => ({
	AiBriefingOverlay: () => null,
}));

// DataTable mock that renders column render functions AND rowExpansion content.
// Records are now grouped games keyed by game.publicId.
vi.mock("mantine-datatable", () => ({
	DataTable: ({
		records,
		columns,
		rowExpansion,
	}: {
		records?: { game?: { publicId?: string } }[];
		columns?: {
			accessor?: string;
			render?: (record: unknown) => React.ReactNode;
		}[];
		rowExpansion?: { content?: (opts: { record: unknown }) => React.ReactNode };
	}) => (
		<table>
			<tbody>
				{records?.map((record) => (
					<React.Fragment key={String(record.game?.publicId ?? Math.random())}>
						<tr>
							{columns?.map((col) => (
								<td key={col.accessor ?? "col"}>{col.render ? col.render(record) : null}</td>
							))}
						</tr>
						{/* Render expanded content for all records to cover ExpandedGameRow */}
						{rowExpansion?.content && (
							<tr>
								<td colSpan={columns?.length || 1}>{rowExpansion.content({ record })}</td>
							</tr>
						)}
					</React.Fragment>
				))}
			</tbody>
		</table>
	),
}));

vi.mock("../hooks/useLibrary", () => ({
	useLibrary: vi.fn(),
	useUpdateEntry: vi.fn(),
	useDeleteEntry: vi.fn(),
	useAddToLibrary: vi.fn(),
	usePlatforms: vi.fn(),
}));

vi.mock("../hooks/useMission", () => ({
	useActiveMission: vi.fn(),
	usePreviewBriefing: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import {
	useAddToLibrary,
	useDeleteEntry,
	useLibrary,
	usePlatforms,
	useUpdateEntry,
} from "../hooks/useLibrary";
import { useActiveMission, usePreviewBriefing } from "../hooks/useMission";
import type { Game, LibraryGameGroup, LibraryPlatformState } from "../types/library";
import type { Mission } from "../types/mission";
import { LibraryPage } from "./LibraryPage";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
	return render(
		<MantineProvider>
			<ModalsProvider>
				<MemoryRouter>
					<LibraryPage />
				</MemoryRouter>
			</ModalsProvider>
		</MantineProvider>,
	);
}

const PC = { id: 1, slug: "pc", label: "PC", family: "pc" };
const SWITCH = { id: 2, slug: "switch", label: "Nintendo Switch", family: "console" };

function makeGame(overrides: Partial<Game> = {}): Game {
	return {
		publicId: "game-1",
		slug: "hollow-knight",
		title: "Hollow Knight",
		summary: "A metroidvania",
		coverUrl: null,
		genres: ["Action", "Platformer"],
		metadataSource: "igdb",
		createdAt: "2024-06-01T00:00:00Z",
		...overrides,
	};
}

function makeState(overrides: Partial<LibraryPlatformState> = {}): LibraryPlatformState {
	return {
		publicId: "entry-1",
		platform: PC,
		status: "playing",
		missionNextAction: null,
		notes: "Great game",
		createdAt: "2024-06-01T00:00:00Z",
		updatedAt: "2024-06-02T00:00:00Z",
		...overrides,
	};
}

function makeGroup(overrides: Partial<LibraryGameGroup> = {}): LibraryGameGroup {
	return {
		game: makeGame(),
		platforms: [makeState()],
		...overrides,
	};
}

function makeMission(overrides: Partial<Mission> = {}): Mission {
	return {
		publicId: "mission-1",
		libraryEntry: {
			publicId: "entry-1",
			game: makeGame(),
			platform: PC,
			status: "playing",
			missionNextAction: null,
			notes: null,
			createdAt: "2024-06-01T00:00:00Z",
			updatedAt: "2024-06-02T00:00:00Z",
		},
		missionType: "regular",
		briefingText: "Your next adventure awaits",
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

/**
 * Clicks an entry "Remove" button, then confirms in the resulting modal.
 * Removal is guarded by a confirmation dialog, so tests must confirm.
 */
async function clickRemoveAndConfirm() {
	await act(async () => {
		fireEvent.click(screen.getByRole("button", { name: "Remove" }));
	});
	const confirmBtn = await screen.findByRole("button", { name: "Delete entry" });
	await act(async () => {
		fireEvent.click(confirmBtn);
	});
}

const mutationStub = {
	mutateAsync: vi.fn(),
	isPending: false,
};

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
	vi.clearAllMocks();

	(useLibrary as Mock).mockReturnValue({
		data: { items: [], total: 0, limit: 50, offset: 0 },
		isLoading: false,
	});

	(useUpdateEntry as Mock).mockReturnValue(mutationStub);
	(useDeleteEntry as Mock).mockReturnValue(mutationStub);
	(useAddToLibrary as Mock).mockReturnValue(mutationStub);
	(usePlatforms as Mock).mockReturnValue({ data: [PC, SWITCH] });

	(useActiveMission as Mock).mockReturnValue({ data: null });
	(usePreviewBriefing as Mock).mockReturnValue(mutationStub);
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LibraryPage", () => {
	it("shows skeletons when loading", () => {
		(useLibrary as Mock).mockReturnValue({ data: undefined, isLoading: true });

		renderPage();

		expect(screen.queryByText("Library")).not.toBeInTheDocument();
		expect(screen.queryByText("Your library is empty")).not.toBeInTheDocument();
	});

	it("shows empty state message when library has no entries", () => {
		renderPage();

		expect(
			screen.getByText("Your library is empty. Use Quick Add to add your first game!"),
		).toBeInTheDocument();
	});

	it('renders title "Library"', () => {
		renderPage();

		expect(screen.getByText("Library")).toBeInTheDocument();
	});

	it("renders all status filter buttons", () => {
		renderPage();

		const labels = ["All", "Backlog", "Playing", "Paused", "Completed", "Dropped"];
		for (const label of labels) {
			expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
		}
	});

	it("renders the QuickAddMenu", () => {
		renderPage();

		expect(screen.getByRole("button", { name: "Quick Add" })).toBeInTheDocument();
	});

	it("renders a Capture History link in the header", () => {
		renderPage();

		expect(screen.getByText("Capture History")).toBeInTheDocument();
	});

	// -----------------------------------------------------------------------
	// Grouped-game row rendering
	// -----------------------------------------------------------------------

	it("renders one row per game with its title and added date", () => {
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		// Title appears in the column AND the expanded per-platform card.
		expect(screen.getAllByText("Hollow Knight").length).toBeGreaterThanOrEqual(1);
		// dayjs formats the game's createdAt
		expect(screen.getByText(/(?:May|Jun) \d{1,2}, 2024/)).toBeInTheDocument();
	});

	it("renders a status badge per platform in the Platforms column", () => {
		const group = makeGroup({
			platforms: [
				makeState({ publicId: "e-pc", platform: PC, status: "playing" }),
				makeState({ publicId: "e-sw", platform: SWITCH, status: "backlog" }),
			],
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [group], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		// Per-platform badges show "<platform>: <status>"
		expect(screen.getAllByText("PC: playing").length).toBeGreaterThanOrEqual(1);
		expect(screen.getAllByText("Nintendo Switch: backlog").length).toBeGreaterThanOrEqual(1);
	});

	// -----------------------------------------------------------------------
	// Expanded per-platform controls
	// -----------------------------------------------------------------------

	it("renders a Status select, Notes textarea, and per-platform buttons", () => {
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Status")).toBeInTheDocument();
		expect(screen.getByRole("textbox", { name: "Notes" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Start Mission" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Remove" })).toBeInTheDocument();
	});

	it("renders read-only genre badges and no genre input", () => {
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.queryByRole("textbox", { name: "Genres" })).not.toBeInTheDocument();
		expect(screen.getByText("Genres")).toBeInTheDocument();
		expect(screen.getByText("Action")).toBeInTheDocument();
		expect(screen.getByText("Platformer")).toBeInTheDocument();
	});

	it("hides the Genres section when the game has no genres", () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ game: makeGame({ genres: null }) })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		expect(screen.queryByText("Genres")).not.toBeInTheDocument();
	});

	it("pre-fills the notes textarea with the entry's notes", () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ notes: "My custom note" })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		expect(screen.getByRole("textbox", { name: "Notes" })).toHaveValue("My custom note");
	});

	it("handles empty notes gracefully", () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ notes: null })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		expect(screen.getByRole("textbox", { name: "Notes" })).toHaveValue("");
	});

	it('shows "Next objective:" when a platform has a missionNextAction', () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ missionNextAction: "Beat Soul Master" })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText(/Next objective:/)).toBeInTheDocument();
		expect(screen.getByText(/Beat Soul Master/)).toBeInTheDocument();
	});

	it("renders a per-platform card for each owned platform", () => {
		const group = makeGroup({
			platforms: [
				makeState({ publicId: "e-pc", platform: PC, notes: "pc note" }),
				makeState({ publicId: "e-sw", platform: SWITCH, notes: "switch note" }),
			],
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [group], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		// Two Save buttons → two platform editors
		expect(screen.getAllByRole("button", { name: "Save" })).toHaveLength(2);
		const notes = screen.getAllByRole("textbox", { name: "Notes" });
		expect(notes).toHaveLength(2);
		expect(notes[0]).toHaveValue("pc note");
		expect(notes[1]).toHaveValue("switch note");
	});

	// -----------------------------------------------------------------------
	// Start Mission per platform (one-active-mission rule)
	// -----------------------------------------------------------------------

	it("disables Start Mission for every platform when a mission is active", () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ publicId: "entry-1" })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});
		// Active mission is on a DIFFERENT entry, so this platform shows the
		// disabled "Start Mission" label rather than "Mission active".
		(useActiveMission as Mock).mockReturnValue({
			data: makeMission({
				libraryEntry: {
					publicId: "entry-other",
					game: makeGame(),
					platform: PC,
					status: "playing",
					missionNextAction: null,
					notes: null,
					createdAt: "2024-06-01T00:00:00Z",
					updatedAt: "2024-06-02T00:00:00Z",
				},
			}),
		});

		renderPage();

		expect(screen.getByRole("button", { name: "Start Mission" })).toBeDisabled();
	});

	it('labels the active platform "Mission active" and disables it', () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ publicId: "entry-1" })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});
		(useActiveMission as Mock).mockReturnValue({
			data: makeMission(), // libraryEntry.publicId === "entry-1"
		});

		renderPage();

		const btn = screen.getByRole("button", { name: "Mission active" });
		expect(btn).toBeDisabled();
	});

	it("enables Start Mission when no mission is active", () => {
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});
		(useActiveMission as Mock).mockReturnValue({ data: null });

		renderPage();

		expect(screen.getByRole("button", { name: "Start Mission" })).not.toBeDisabled();
	});

	it("opens the briefing preview modal when Start Mission is clicked", async () => {
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});
		(useActiveMission as Mock).mockReturnValue({ data: null });

		renderPage();

		expect(screen.queryByTestId("briefing-preview-modal")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Start Mission" }));
		expect(await screen.findByTestId("briefing-preview-modal")).toBeInTheDocument();
	});

	// -----------------------------------------------------------------------
	// Update / delete a specific platform entry
	// -----------------------------------------------------------------------

	it("updates a platform entry by its public_id via Save", async () => {
		const mockMutateAsync = vi.fn().mockResolvedValue(undefined);
		(useUpdateEntry as Mock).mockReturnValue({ mutateAsync: mockMutateAsync, isPending: false });
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ publicId: "entry-pc" })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save" }));
		});

		await waitFor(() => {
			expect(mockMutateAsync).toHaveBeenCalledWith(
				expect.objectContaining({ publicId: "entry-pc" }),
			);
		});
	});

	it("deletes a platform entry by its public_id via Remove + confirm", async () => {
		const mockDeleteAsync = vi.fn().mockResolvedValue(undefined);
		(useDeleteEntry as Mock).mockReturnValue({ mutateAsync: mockDeleteAsync, isPending: false });
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ publicId: "entry-pc" })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		await clickRemoveAndConfirm();

		await waitFor(() => {
			expect(mockDeleteAsync).toHaveBeenCalledWith("entry-pc");
		});
	});

	it("shows a success notification on update", async () => {
		const { notifications } = await import("@mantine/notifications");
		(useUpdateEntry as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save" }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Entry updated", color: "green" }),
			);
		});
	});

	it("shows an error notification on update failure", async () => {
		const { notifications } = await import("@mantine/notifications");
		(useUpdateEntry as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockRejectedValue(new Error("Update failed")),
			isPending: false,
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save" }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Update failed", color: "red" }),
			);
		});
	});

	it("shows a success notification on delete", async () => {
		const { notifications } = await import("@mantine/notifications");
		(useDeleteEntry as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await clickRemoveAndConfirm();

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Entry deleted", color: "green" }),
			);
		});
	});

	it("shows an error notification on delete failure", async () => {
		const { notifications } = await import("@mantine/notifications");
		(useDeleteEntry as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockRejectedValue(new Error("Delete failed")),
			isPending: false,
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [makeGroup()], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await clickRemoveAndConfirm();

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Delete failed", color: "red" }),
			);
		});
	});

	// -----------------------------------------------------------------------
	// Add-platform affordance
	// -----------------------------------------------------------------------

	it("offers an Add platform control for platforms the user doesn't own yet", () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ platform: PC })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		// The "Add platform" MultiSelect label and the Add button are present.
		expect(screen.getByText("Add platform")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
	});

	it("hides the Add control when every platform is already owned", () => {
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [
					makeGroup({
						platforms: [
							makeState({ publicId: "e-pc", platform: PC }),
							makeState({ publicId: "e-sw", platform: SWITCH }),
						],
					}),
				],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		expect(screen.queryByRole("button", { name: "Add" })).not.toBeInTheDocument();
		expect(screen.getByText("Owned on every available platform.")).toBeInTheDocument();
	});

	it("warns when Add is clicked with no platform selected", async () => {
		const { notifications } = await import("@mantine/notifications");
		(useLibrary as Mock).mockReturnValue({
			data: {
				items: [makeGroup({ platforms: [makeState({ platform: PC })] })],
				total: 1,
				limit: 50,
				offset: 0,
			},
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Add" }));
		});

		expect(notifications.show).toHaveBeenCalledWith(
			expect.objectContaining({ title: "No platform selected", color: "red" }),
		);
	});

	// -----------------------------------------------------------------------
	// Active mission card
	// -----------------------------------------------------------------------

	it("shows the active mission card when a mission is active", () => {
		(useActiveMission as Mock).mockReturnValue({ data: makeMission() });

		renderPage();

		expect(screen.getByText("Mission active")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "End mission" })).toBeInTheDocument();
	});

	it('shows "View briefing" only when the active mission has briefing text', () => {
		(useActiveMission as Mock).mockReturnValue({ data: makeMission({ briefingText: null }) });

		const { unmount } = renderPage();
		expect(screen.queryByRole("button", { name: "View briefing" })).not.toBeInTheDocument();
		unmount();

		(useActiveMission as Mock).mockReturnValue({ data: makeMission({ briefingText: "go" }) });
		renderPage();
		expect(screen.getByRole("button", { name: "View briefing" })).toBeInTheDocument();
	});

	// -----------------------------------------------------------------------
	// Multiple games render correctly
	// -----------------------------------------------------------------------

	it("renders multiple game rows", () => {
		const groups = [
			makeGroup({ game: makeGame({ publicId: "g-1", title: "Game A" }) }),
			makeGroup({
				game: makeGame({ publicId: "g-2", title: "Game B" }),
				platforms: [makeState({ publicId: "e-2", status: "backlog", notes: null })],
			}),
		];
		(useLibrary as Mock).mockReturnValue({
			data: { items: groups, total: 2, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Game A")).toBeInTheDocument();
		expect(screen.getByText("Game B")).toBeInTheDocument();
	});

	// -----------------------------------------------------------------------
	// Status filter button interaction
	// -----------------------------------------------------------------------

	it("clicking a status filter button does not crash and keeps the page mounted", () => {
		renderPage();

		fireEvent.click(screen.getByRole("button", { name: "Playing" }));

		expect(screen.getByText("Library")).toBeInTheDocument();
	});
});
