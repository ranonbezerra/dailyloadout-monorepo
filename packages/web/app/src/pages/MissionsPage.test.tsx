import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, type Mock, vi } from "vitest";
import { useMissions } from "../hooks/useMission";
import type { MissionListItem } from "../types/mission";
import { MissionsPage } from "./MissionsPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../hooks/useMission", () => ({
	useMissions: vi.fn(),
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

// Mock mantine-datatable so rows render without needing real layout/ResizeObserver
vi.mock("mantine-datatable", () => ({
	DataTable: ({
		records,
		columns,
		noRecordsText,
	}: {
		records: Record<string, unknown>[];
		columns: {
			accessor: string;
			title: string;
			render?: (record: Record<string, unknown>) => React.ReactNode;
		}[];
		noRecordsText?: string;
	}) => {
		if (!records || records.length === 0) {
			return <div data-testid="datatable-empty">{noRecordsText ?? "No records"}</div>;
		}
		return (
			<table data-testid="datatable">
				<thead>
					<tr>
						{columns.map((col) => (
							<th key={col.accessor}>{col.title}</th>
						))}
					</tr>
				</thead>
				<tbody>
					{records.map((record, i) => (
						// biome-ignore lint/suspicious/noArrayIndexKey: test mock
						<tr key={i}>
							{columns.map((col) => (
								<td key={col.accessor}>
									{col.render ? col.render(record) : String(record[col.accessor] ?? "")}
								</td>
							))}
						</tr>
					))}
				</tbody>
			</table>
		);
	},
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<MissionsPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

function makeMissionItem(overrides: Partial<MissionListItem> = {}): MissionListItem {
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
		endedVia: null,
		startedAt: "2024-06-01T10:00:00Z",
		endedAt: null,
		...overrides,
	};
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MissionsPage", () => {
	it("renders the title 'Mission History'", () => {
		(useMissions as Mock).mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Mission History")).toBeInTheDocument();
	});

	it("renders empty state when missions list is empty", () => {
		(useMissions as Mock).mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText(/No missions yet/)).toBeInTheDocument();
		expect(screen.getByText(/Start one from the Play page/)).toBeInTheDocument();
	});

	it("renders mission count text for single mission", () => {
		const items = [makeMissionItem()];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("1 mission total")).toBeInTheDocument();
	});

	it("renders mission count text for multiple missions (plural)", () => {
		const items = [
			makeMissionItem({ publicId: "mis-001" }),
			makeMissionItem({ publicId: "mis-002" }),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 2 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("2 missions total")).toBeInTheDocument();
	});

	it("renders game title in the DataTable", () => {
		const items = [
			makeMissionItem({ publicId: "mis-001" }),
			makeMissionItem({
				publicId: "mis-002",
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
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 2 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getByText("Elden Ring")).toBeInTheDocument();
	});

	it("renders platform labels in the DataTable", () => {
		const items = [
			makeMissionItem({
				publicId: "mis-001",
				libraryEntry: {
					publicId: "le-001",
					game: {
						publicId: "game-001",
						slug: "zelda-totk",
						title: "Zelda TOTK",
						metadataSource: "igdb",
						createdAt: "2024-01-01T00:00:00Z",
					},
					platform: {
						id: 3,
						slug: "switch",
						label: "Nintendo Switch",
						family: "nintendo",
					},
					status: "playing",
					createdAt: "2024-01-01T00:00:00Z",
					updatedAt: "2024-01-01T00:00:00Z",
				},
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Nintendo Switch")).toBeInTheDocument();
	});

	it("shows 'Active' badge for missions with null endedVia", () => {
		const items = [makeMissionItem({ endedVia: null })];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Active")).toBeInTheDocument();
	});

	it("shows 'Debriefed' badge for debrief_completed missions", () => {
		const items = [
			makeMissionItem({
				endedVia: "debrief_completed",
				endedAt: "2024-06-01T12:00:00Z",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Debriefed")).toBeInTheDocument();
	});

	it("shows 'Paused' badge for paused_app missions", () => {
		const items = [
			makeMissionItem({
				endedVia: "paused_app",
				endedAt: "2024-06-01T12:00:00Z",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Paused")).toBeInTheDocument();
	});

	it("shows 'Auto-closed' badge for auto_clamp missions", () => {
		const items = [
			makeMissionItem({
				endedVia: "auto_clamp",
				endedAt: "2024-06-01T12:00:00Z",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Auto-closed")).toBeInTheDocument();
	});

	it("shows 'Retroactive' badge for retroactive missions", () => {
		const items = [
			makeMissionItem({
				endedVia: "retroactive",
				endedAt: "2024-06-01T12:00:00Z",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Retroactive")).toBeInTheDocument();
	});

	it("shows duration in minutes for sessions under 1 hour", () => {
		const items = [
			makeMissionItem({
				startedAt: "2024-06-01T10:00:00Z",
				endedAt: "2024-06-01T10:45:00Z",
				endedVia: "debrief_completed",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("45m")).toBeInTheDocument();
	});

	it("shows duration in hours and minutes for sessions over 1 hour", () => {
		const items = [
			makeMissionItem({
				startedAt: "2024-06-01T10:00:00Z",
				endedAt: "2024-06-01T12:30:00Z",
				endedVia: "debrief_completed",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("2h 30m")).toBeInTheDocument();
	});

	it("shows duration in whole hours when minutes are exactly 0", () => {
		const items = [
			makeMissionItem({
				startedAt: "2024-06-01T10:00:00Z",
				endedAt: "2024-06-01T12:00:00Z",
				endedVia: "debrief_completed",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("2h")).toBeInTheDocument();
	});

	it("does not render any action buttons (history-only page)", () => {
		const items = [
			makeMissionItem({ publicId: "mis-001", endedVia: null }),
			makeMissionItem({
				publicId: "mis-002",
				endedVia: "debrief_completed",
				endedAt: "2024-06-01T12:00:00Z",
			}),
		];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 2 },
			isLoading: false,
		});

		renderPage();

		expect(screen.queryByRole("button", { name: "End mission" })).not.toBeInTheDocument();
		expect(screen.queryByRole("button", { name: "Briefing" })).not.toBeInTheDocument();
	});

	it("renders DataTable column headers", () => {
		const items = [makeMissionItem()];

		(useMissions as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Game")).toBeInTheDocument();
		expect(screen.getByText("Platform")).toBeInTheDocument();
		expect(screen.getByText("Status")).toBeInTheDocument();
		expect(screen.getByText("Duration")).toBeInTheDocument();
		expect(screen.getByText("Started")).toBeInTheDocument();
	});
});
