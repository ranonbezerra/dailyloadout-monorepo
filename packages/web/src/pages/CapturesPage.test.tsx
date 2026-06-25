import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, type Mock, vi } from "vitest";
import { useCaptures } from "../hooks/useCapture";
import type { CaptureListItem } from "../types/capture";
import { CapturesPage } from "./CapturesPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../hooks/useCapture", () => ({
	useCaptures: vi.fn(),
	useCapture: vi.fn(() => ({ data: null, isLoading: false })),
	useSubmitTextCapture: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useSubmitPhotoCapture: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useConfirmCandidate: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useRejectCandidate: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
	useTranscribeAudio: vi.fn(() => ({
		mutateAsync: vi.fn(),
		isPending: false,
	})),
}));

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

// Mock child modals to avoid rendering them and pulling in extra dependencies
vi.mock("./AddGameModal", () => ({
	AddGameModal: () => null,
}));
vi.mock("./CaptureTextModal", () => ({
	CaptureTextModal: () => null,
}));
vi.mock("./CaptureVoiceModal", () => ({
	CaptureVoiceModal: () => null,
}));
vi.mock("./CapturePhotoModal", () => ({
	CapturePhotoModal: () => null,
}));
vi.mock("./CaptureReviewModal", () => ({
	CaptureReviewModal: () => null,
}));
vi.mock("../components/QuickAddMenu", () => ({
	QuickAddMenu: () => <button type="button">Quick Add</button>,
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
				<CapturesPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

function makeCaptureItem(overrides: Partial<CaptureListItem> = {}): CaptureListItem {
	return {
		publicId: "cap-001",
		inputType: "text",
		rawText: "Elden Ring, Hollow Knight",
		status: "review",
		errorMessage: null,
		candidateTitles: ["Elden Ring", "Hollow Knight"],
		createdAt: "2024-06-01T12:00:00Z",
		updatedAt: "2024-06-01T12:01:00Z",
		...overrides,
	};
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CapturesPage", () => {
	it("renders skeleton loading state when isLoading is true", () => {
		(useCaptures as Mock).mockReturnValue({
			data: undefined,
			isLoading: true,
		});

		const { container } = renderPage();

		// The title "Capture History" should NOT be present while loading
		expect(screen.queryByText("Capture History")).not.toBeInTheDocument();

		// The loading branch renders content (skeletons)
		expect(container.innerHTML.length).toBeGreaterThan(0);
	});

	it("renders empty state when captures list is empty", () => {
		(useCaptures as Mock).mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText(/No captures yet/)).toBeInTheDocument();
		expect(screen.getByText("Capture History")).toBeInTheDocument();
	});

	it("renders capture data in the table when items exist", () => {
		const items = [
			makeCaptureItem({ publicId: "cap-001", rawText: "Elden Ring, Hollow Knight" }),
			makeCaptureItem({
				publicId: "cap-002",
				rawText: null,
				candidateTitles: ["Zelda TOTK"],
				inputType: "voice",
				status: "committed",
			}),
		];

		(useCaptures as Mock).mockReturnValue({
			data: { items, total: 2 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Elden Ring, Hollow Knight")).toBeInTheDocument();
		expect(screen.getByText("Zelda TOTK")).toBeInTheDocument();
	});

	it("renders fallback description for captures with no rawText and no candidateTitles", () => {
		const items = [
			makeCaptureItem({
				publicId: "cap-003",
				rawText: null,
				candidateTitles: [],
				inputType: "photo",
			}),
		];

		(useCaptures as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("photo capture")).toBeInTheDocument();
	});

	it("renders status filter buttons", () => {
		(useCaptures as Mock).mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Review" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Committed" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Failed" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Cancelled" })).toBeInTheDocument();
	});

	it("renders the Quick Add button", () => {
		(useCaptures as Mock).mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByRole("button", { name: "Quick Add" })).toBeInTheDocument();
	});

	it("renders status badges with correct text", () => {
		const items = [
			makeCaptureItem({ publicId: "cap-r", status: "review" }),
			makeCaptureItem({ publicId: "cap-c", status: "committed" }),
			makeCaptureItem({ publicId: "cap-f", status: "failed" }),
			makeCaptureItem({ publicId: "cap-pc", status: "partially_committed" }),
		];

		(useCaptures as Mock).mockReturnValue({
			data: { items, total: items.length },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("review")).toBeInTheDocument();
		expect(screen.getByText("committed")).toBeInTheDocument();
		expect(screen.getByText("failed")).toBeInTheDocument();
		expect(screen.getByText("partially committed")).toBeInTheDocument();
	});

	it("renders inputType column for each capture", () => {
		const items = [
			makeCaptureItem({ publicId: "cap-t", inputType: "text" }),
			makeCaptureItem({ publicId: "cap-v", inputType: "voice" }),
		];

		(useCaptures as Mock).mockReturnValue({
			data: { items, total: 2 },
			isLoading: false,
		});

		renderPage();

		const textCells = screen.getAllByText("text");
		expect(textCells.length).toBeGreaterThanOrEqual(1);
		expect(screen.getByText("voice")).toBeInTheDocument();
	});

	it("renders the title 'Capture History' in non-loading state", () => {
		(useCaptures as Mock).mockReturnValue({
			data: { items: [], total: 0 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Capture History")).toBeInTheDocument();
	});

	it("renders created date formatted", () => {
		const items = [makeCaptureItem({ publicId: "cap-d", createdAt: "2024-06-15T12:00:00Z" })];

		(useCaptures as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Jun 15, 2024")).toBeInTheDocument();
	});

	it("renders the DataTable with column headers", () => {
		const items = [makeCaptureItem()];

		(useCaptures as Mock).mockReturnValue({
			data: { items, total: 1 },
			isLoading: false,
		});

		renderPage();

		expect(screen.getByText("Description")).toBeInTheDocument();
		expect(screen.getByText("Type")).toBeInTheDocument();
		expect(screen.getByText("Status")).toBeInTheDocument();
		expect(screen.getByText("Created")).toBeInTheDocument();
	});
});
