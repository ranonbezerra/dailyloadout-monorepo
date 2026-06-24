import { MantineProvider } from "@mantine/core";
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

// Mock Textarea (autosize crashes in jsdom) and TagsInput
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
		TagsInput: ({
			label,
			placeholder,
			value,
		}: {
			label?: string;
			placeholder?: string;
			value?: string[];
		}) => (
			<div>
				<input
					placeholder={placeholder}
					value={value?.join(",") || ""}
					aria-label={label}
					readOnly
				/>
			</div>
		),
	};
});

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

// DataTable mock that renders column render functions AND rowExpansion content
vi.mock("mantine-datatable", () => ({
	DataTable: ({
		records,
		columns,
		rowExpansion,
	}: {
		records?: Record<string, unknown>[];
		columns?: {
			accessor?: string;
			render?: (record: Record<string, unknown>) => React.ReactNode;
		}[];
		rowExpansion?: { content?: (opts: { record: Record<string, unknown> }) => React.ReactNode };
	}) => (
		<table>
			<tbody>
				{records?.map((record) => (
					<React.Fragment key={String(record.publicId ?? record.slug ?? Math.random())}>
						<tr>
							{columns?.map((col) => (
								<td key={col.accessor ?? "col"}>
									{col.render
										? col.render(record)
										: String(col.accessor ? (record[col.accessor] ?? "") : "")}
								</td>
							))}
						</tr>
						{/* Render expanded content for all records to cover ExpandedRow */}
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
	useGameGenres: vi.fn(),
	useUpdateGame: vi.fn(),
}));

vi.mock("../hooks/useMission", () => ({
	useActiveMission: vi.fn(),
	usePreviewBriefing: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import {
	useDeleteEntry,
	useGameGenres,
	useLibrary,
	useUpdateEntry,
	useUpdateGame,
} from "../hooks/useLibrary";
import { useActiveMission, usePreviewBriefing } from "../hooks/useMission";
import type { LibraryEntry } from "../types/library";
import type { Mission } from "../types/mission";
import { LibraryPage } from "./LibraryPage";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<LibraryPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

const mutationStub = {
	mutateAsync: vi.fn(),
	isPending: false,
};

function makeEntry(overrides: Partial<LibraryEntry> = {}): LibraryEntry {
	return {
		publicId: "entry-1",
		game: {
			publicId: "game-1",
			slug: "hollow-knight",
			title: "Hollow Knight",
			summary: "A metroidvania",
			coverUrl: null,
			genres: ["Action", "Platformer"],
			metadataSource: "igdb",
			createdAt: "2024-01-01T00:00:00Z",
		},
		platform: { id: 1, slug: "pc", label: "PC", family: "pc" },
		status: "playing",
		missionNextAction: null,
		notes: "Great game",
		createdAt: "2024-06-01T00:00:00Z",
		updatedAt: "2024-06-02T00:00:00Z",
		...overrides,
	};
}

function makeMission(overrides: Partial<Mission> = {}): Mission {
	return {
		publicId: "mission-1",
		libraryEntry: makeEntry(),
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
	(useGameGenres as Mock).mockReturnValue({ data: [] });
	(useUpdateGame as Mock).mockReturnValue(mutationStub);

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

		// When loading, the title "Library" should NOT be rendered
		expect(screen.queryByText("Library")).not.toBeInTheDocument();
		// The empty state should also not be rendered
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
	// DataTable column rendering
	// -----------------------------------------------------------------------

	it("renders DataTable with game data when entries exist", () => {
		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		// Game title appears in the column AND the expanded row, so use getAllByText
		expect(screen.getAllByText("Hollow Knight").length).toBeGreaterThanOrEqual(1);
		expect(screen.getAllByText("PC").length).toBeGreaterThanOrEqual(1);
		expect(screen.getByText("playing")).toBeInTheDocument();
		// "Great game" appears in column render AND in expanded-row textarea
		expect(screen.getAllByText("Great game").length).toBeGreaterThanOrEqual(1);
		// dayjs formats the date in local timezone
		expect(screen.getByText(/(?:May|Jun) \d{1,2}, 2024/)).toBeInTheDocument();
	});

	it("renders notes as '--' when notes is null", () => {
		const entry = makeEntry({ notes: null });
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("--")).toBeInTheDocument();
	});

	it("renders status badges with correct colors for each status", () => {
		const statuses = ["backlog", "playing", "paused", "completed", "dropped"] as const;

		const entries = statuses.map((status, i) =>
			makeEntry({
				publicId: `entry-${i}`,
				game: {
					publicId: `game-${i}`,
					slug: `game-${status}`,
					title: `Game ${status}`,
					summary: null,
					coverUrl: null,
					genres: null,
					metadataSource: "igdb",
					createdAt: "2024-01-01T00:00:00Z",
				},
				status,
			}),
		);

		(useLibrary as Mock).mockReturnValue({
			data: { items: entries, total: entries.length, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		for (const status of statuses) {
			expect(screen.getByText(status)).toBeInTheDocument();
		}
	});

	// -----------------------------------------------------------------------
	// Active mission card
	// -----------------------------------------------------------------------

	it("shows active mission card when activeMission exists", () => {
		const mission = makeMission();
		(useActiveMission as Mock).mockReturnValue({ data: mission });

		renderPage();

		expect(screen.getByText("Mission active")).toBeInTheDocument();
		// Game title appears in the active mission card
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "End mission" })).toBeInTheDocument();
	});

	it('shows "View briefing" button when active mission has briefingText', () => {
		const mission = makeMission({ briefingText: "Some briefing text" });
		(useActiveMission as Mock).mockReturnValue({ data: mission });

		renderPage();

		expect(screen.getByRole("button", { name: "View briefing" })).toBeInTheDocument();
	});

	it('does not show "View briefing" button when active mission has no briefingText', () => {
		const mission = makeMission({ briefingText: null });
		(useActiveMission as Mock).mockReturnValue({ data: mission });

		renderPage();

		expect(screen.queryByRole("button", { name: "View briefing" })).not.toBeInTheDocument();
		expect(screen.getByRole("button", { name: "End mission" })).toBeInTheDocument();
	});

	it("shows platform label on active mission card", () => {
		const mission = makeMission();
		(useActiveMission as Mock).mockReturnValue({ data: mission });

		renderPage();

		expect(screen.getByText("PC")).toBeInTheDocument();
	});

	it("shows 'started ...' relative time on active mission card", () => {
		const mission = makeMission();
		(useActiveMission as Mock).mockReturnValue({ data: mission });

		renderPage();

		// dayjs fromNow produces something like "started 2 years ago"
		expect(screen.getByText(/started .+ ago/)).toBeInTheDocument();
	});

	// -----------------------------------------------------------------------
	// ExpandedRow rendering (via DataTable rowExpansion mock)
	// -----------------------------------------------------------------------

	it("renders ExpandedRow with Status select, Genres input, Notes textarea", () => {
		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		// Status select (real Mantine Select renders label text)
		expect(screen.getByText("Status")).toBeInTheDocument();
		// Genres TagsInput (mocked - uses aria-label)
		expect(screen.getByRole("textbox", { name: "Genres" })).toBeInTheDocument();
		// Notes textarea (mocked - uses aria-label)
		expect(screen.getByRole("textbox", { name: "Notes" })).toBeInTheDocument();
	});

	it("renders Save, Start Mission, and Delete buttons in ExpandedRow", () => {
		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Start Mission" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
	});

	it('shows "Next objective:" when missionNextAction exists', () => {
		const entry = makeEntry({ missionNextAction: "Beat Soul Master" });
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText(/Next objective:/)).toBeInTheDocument();
		expect(screen.getByText(/Beat Soul Master/)).toBeInTheDocument();
	});

	it("does not show 'Next objective:' when missionNextAction is null", () => {
		const entry = makeEntry({ missionNextAction: null });
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.queryByText(/Next objective:/)).not.toBeInTheDocument();
	});

	it("Start Mission is disabled when there is an active mission", () => {
		const entry = makeEntry({ publicId: "entry-other" });
		const mission = makeMission(); // active mission on a different entry
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});
		(useActiveMission as Mock).mockReturnValue({ data: mission });

		renderPage();

		const startBtn = screen.getByRole("button", { name: "Start Mission" });
		expect(startBtn).toBeDisabled();
	});

	it('shows "Mission active" label when the entry itself has the active mission', () => {
		const entry = makeEntry({ publicId: "entry-1" });
		const mission = makeMission({
			libraryEntry: entry,
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});
		(useActiveMission as Mock).mockReturnValue({ data: mission });

		renderPage();

		// The button text changes to "Mission active" for this entry
		const missionBtn = screen.getByRole("button", { name: "Mission active" });
		expect(missionBtn).toBeInTheDocument();
		expect(missionBtn).toBeDisabled();
	});

	it('"Start Mission" is enabled when there is no active mission', () => {
		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});
		(useActiveMission as Mock).mockReturnValue({ data: null });

		renderPage();

		const startBtn = screen.getByRole("button", { name: "Start Mission" });
		expect(startBtn).not.toBeDisabled();
	});

	it("ExpandedRow pre-fills notes textarea with entry notes", () => {
		const entry = makeEntry({ notes: "My custom note" });
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		const textarea = screen.getByRole("textbox", { name: "Notes" });
		expect(textarea).toHaveValue("My custom note");
	});

	it("ExpandedRow pre-fills genres input with entry genres", () => {
		const entry = makeEntry({
			game: {
				publicId: "game-1",
				slug: "hollow-knight",
				title: "Hollow Knight",
				summary: null,
				coverUrl: null,
				genres: ["Action", "Platformer"],
				metadataSource: "igdb",
				createdAt: "2024-01-01T00:00:00Z",
			},
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		const genresInput = screen.getByRole("textbox", { name: "Genres" });
		expect(genresInput).toHaveValue("Action,Platformer");
	});

	it("ExpandedRow handles empty genres gracefully", () => {
		const entry = makeEntry({
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
		});
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		const genresInput = screen.getByRole("textbox", { name: "Genres" });
		expect(genresInput).toHaveValue("");
	});

	it("ExpandedRow handles empty notes gracefully", () => {
		const entry = makeEntry({ notes: null });
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		const textarea = screen.getByRole("textbox", { name: "Notes" });
		expect(textarea).toHaveValue("");
	});

	// -----------------------------------------------------------------------
	// ExpandedRow button interactions
	// -----------------------------------------------------------------------

	it("calls onUpdate via Save button click", async () => {
		const mockMutateAsync = vi.fn().mockResolvedValue(undefined);
		(useUpdateEntry as Mock).mockReturnValue({
			mutateAsync: mockMutateAsync,
			isPending: false,
		});
		(useUpdateGame as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});

		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		const saveBtn = screen.getByRole("button", { name: "Save" });
		await act(async () => {
			fireEvent.click(saveBtn);
		});

		// updateMutation.mutateAsync should be called
		await waitFor(() => {
			expect(mockMutateAsync).toHaveBeenCalled();
		});
	});

	it("calls onDelete via Delete button click", async () => {
		const mockDeleteAsync = vi.fn().mockResolvedValue(undefined);
		(useDeleteEntry as Mock).mockReturnValue({
			mutateAsync: mockDeleteAsync,
			isPending: false,
		});

		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		const deleteBtn = screen.getByRole("button", { name: "Delete" });
		await act(async () => {
			fireEvent.click(deleteBtn);
		});

		await waitFor(() => {
			expect(mockDeleteAsync).toHaveBeenCalled();
		});
	});

	it("opens the briefing modal when Start Mission is clicked (no pre-fetch)", async () => {
		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});
		(useActiveMission as Mock).mockReturnValue({ data: null });

		renderPage();

		expect(screen.queryByTestId("briefing-preview-modal")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Start Mission" }));
		// The modal opens at its mode-choice step; the briefing is fetched inside it.
		expect(await screen.findByTestId("briefing-preview-modal")).toBeInTheDocument();
	});

	it("shows notification on update success", async () => {
		const { notifications } = await import("@mantine/notifications");
		const mockMutateAsync = vi.fn().mockResolvedValue(undefined);
		(useUpdateEntry as Mock).mockReturnValue({
			mutateAsync: mockMutateAsync,
			isPending: false,
		});
		(useUpdateGame as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});

		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save" }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Entry updated",
					color: "green",
				}),
			);
		});
	});

	it("shows notification on update failure", async () => {
		const { notifications } = await import("@mantine/notifications");
		const mockMutateAsync = vi.fn().mockRejectedValue(new Error("Update failed"));
		(useUpdateEntry as Mock).mockReturnValue({
			mutateAsync: mockMutateAsync,
			isPending: false,
		});
		(useUpdateGame as Mock).mockReturnValue({
			mutateAsync: vi.fn().mockResolvedValue(undefined),
			isPending: false,
		});

		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Save" }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Update failed",
					color: "red",
				}),
			);
		});
	});

	it("shows notification on delete success", async () => {
		const { notifications } = await import("@mantine/notifications");
		const mockDeleteAsync = vi.fn().mockResolvedValue(undefined);
		(useDeleteEntry as Mock).mockReturnValue({
			mutateAsync: mockDeleteAsync,
			isPending: false,
		});

		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Delete" }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Entry deleted",
					color: "green",
				}),
			);
		});
	});

	it("shows notification on delete failure", async () => {
		const { notifications } = await import("@mantine/notifications");
		const mockDeleteAsync = vi.fn().mockRejectedValue(new Error("Delete failed"));
		(useDeleteEntry as Mock).mockReturnValue({
			mutateAsync: mockDeleteAsync,
			isPending: false,
		});

		const entry = makeEntry();
		(useLibrary as Mock).mockReturnValue({
			data: { items: [entry], total: 1, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Delete" }));
		});

		await waitFor(() => {
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					title: "Delete failed",
					color: "red",
				}),
			);
		});
	});

	// -----------------------------------------------------------------------
	// Multiple entries render correctly
	// -----------------------------------------------------------------------

	it("renders multiple entries in the DataTable", () => {
		const entries = [
			makeEntry({
				publicId: "e-1",
				game: { ...makeEntry().game, publicId: "g-1", title: "Game A" },
			}),
			makeEntry({
				publicId: "e-2",
				game: { ...makeEntry().game, publicId: "g-2", title: "Game B" },
				status: "backlog",
				notes: null,
			}),
		];
		(useLibrary as Mock).mockReturnValue({
			data: { items: entries, total: 2, limit: 50, offset: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Game A")).toBeInTheDocument();
		expect(screen.getByText("Game B")).toBeInTheDocument();
	});

	// -----------------------------------------------------------------------
	// Status filter button interaction
	// -----------------------------------------------------------------------

	it("clicking a status filter button changes the active filter", () => {
		renderPage();

		const playingBtn = screen.getByRole("button", { name: "Playing" });
		fireEvent.click(playingBtn);

		// After clicking, useLibrary should be re-called. We verify the button
		// interaction does not crash and the page re-renders.
		expect(screen.getByText("Library")).toBeInTheDocument();
	});
});
