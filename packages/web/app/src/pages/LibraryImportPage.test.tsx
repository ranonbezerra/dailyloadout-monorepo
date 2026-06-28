import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
	return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

vi.mock("@tabler/icons-react", () => ({
	IconArrowLeft: () => <span data-testid="icon-back" />,
	IconPhotoUp: () => <span data-testid="icon-photo-up" />,
	IconX: () => <span data-testid="icon-x" />,
	IconAlertTriangle: () => <span data-testid="icon-alert" />,
}));

vi.mock("../hooks/useCapture", () => ({
	useSubmitLibraryImport: vi.fn(),
	useBulkConfirmCandidates: vi.fn(),
	useCandidateDuplicates: vi.fn(),
}));

vi.mock("../hooks/useLibrary", () => ({
	usePlatforms: vi.fn(),
}));

// Mock Mantine Select for jsdom compatibility (native select element).
vi.mock("@mantine/core", async () => {
	const actual = await vi.importActual("@mantine/core");
	return {
		...actual,
		Select: ({
			label,
			placeholder,
			value,
			onChange,
			data,
		}: {
			label?: string;
			placeholder?: string;
			value?: string | null;
			onChange?: (val: string) => void;
			data?: (string | { value: string; label: string })[];
		}) => (
			<select
				aria-label={label || placeholder}
				value={value || ""}
				onChange={(e) => onChange?.(e.target.value)}
			>
				<option value="">Select...</option>
				{data?.map((d) => (
					<option
						key={typeof d === "string" ? d : d.value}
						value={typeof d === "string" ? d : d.value}
					>
						{typeof d === "string" ? d : d.label}
					</option>
				))}
			</select>
		),
	};
});

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import { notifications } from "@mantine/notifications";
import {
	useBulkConfirmCandidates,
	useCandidateDuplicates,
	useSubmitLibraryImport,
} from "../hooks/useCapture";
import { usePlatforms } from "../hooks/useLibrary";
import type { Capture } from "../types/capture";
import type { Platform } from "../types/library";
import { LibraryImportPage, matchDefaultPlatform } from "./LibraryImportPage";

const mockUseSubmitLibraryImport = useSubmitLibraryImport as Mock;
const mockUseBulkConfirmCandidates = useBulkConfirmCandidates as Mock;
const mockUseCandidateDuplicates = useCandidateDuplicates as Mock;
const mockUsePlatforms = usePlatforms as Mock;

const PLATFORMS: Platform[] = [
	{ id: 1, slug: "pc", label: "PC", family: "computer" },
	{ id: 2, slug: "steam", label: "Steam", family: "computer" },
	{ id: 3, slug: "ps5", label: "PlayStation 5", family: "console" },
];

const CAPTURE: Capture = {
	publicId: "cap-1",
	inputType: "library_import",
	rawText: null,
	status: "review",
	errorMessage: null,
	candidates: [
		{
			publicId: "cand-1",
			title: "Hades",
			platformHint: null,
			igdbTitle: "Hades",
			igdbCoverUrl: "https://images.igdb.com/igdb/image/upload/t_cover_big/hades.jpg",
			igdbSummary: null,
			igdbGenres: [],
			confidence: 0.9,
			status: "pending",
			matchedGame: {
				publicId: "g1",
				slug: "hades",
				title: "Hades",
				metadataSource: "igdb",
				createdAt: "2024-01-01",
			},
		},
		{
			publicId: "cand-2",
			title: "Celeste",
			platformHint: null,
			igdbTitle: null,
			igdbCoverUrl: null,
			igdbSummary: null,
			igdbGenres: [],
			confidence: 0.5,
			status: "pending",
			matchedGame: null,
		},
	],
	createdAt: "2024-01-01",
	updatedAt: "2024-01-01",
};

function renderPage() {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={["/library/import"]}>
				<LibraryImportPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

let importMutate: Mock;
let confirmMutate: Mock;

beforeEach(() => {
	vi.clearAllMocks();
	mockUsePlatforms.mockReturnValue({ data: PLATFORMS });
	mockUseCandidateDuplicates.mockReturnValue({ data: [] });

	importMutate = vi.fn(() => Promise.resolve(CAPTURE));
	confirmMutate = vi.fn(() => Promise.resolve({ confirmed: 2, rejected: 0 }));

	mockUseSubmitLibraryImport.mockReturnValue({
		mutateAsync: importMutate,
		isPending: false,
	});
	mockUseBulkConfirmCandidates.mockReturnValue({
		mutateAsync: confirmMutate,
		isPending: false,
	});
});

// ---------------------------------------------------------------------------
// matchDefaultPlatform unit
// ---------------------------------------------------------------------------

describe("matchDefaultPlatform", () => {
	it("matches by slug/label token", () => {
		expect(matchDefaultPlatform(PLATFORMS, "steam")?.id).toBe(2);
		expect(matchDefaultPlatform(PLATFORMS, "ps")?.id).toBe(3);
	});

	it("falls back to the first platform when no match", () => {
		expect(matchDefaultPlatform(PLATFORMS, "xbox")?.id).toBe(1);
	});

	it("returns undefined when there are no platforms", () => {
		expect(matchDefaultPlatform([], "steam")).toBeUndefined();
	});
});

// ---------------------------------------------------------------------------
// Page flow
// ---------------------------------------------------------------------------

describe("LibraryImportPage", () => {
	it("renders the 6 platform picker cards", () => {
		renderPage();
		for (const label of ["Steam", "Xbox", "GOG", "PlayStation", "Epic", "Nintendo Switch"]) {
			expect(screen.getByText(label)).toBeInTheDocument();
		}
	});

	it("shows the per-platform hint copy after picking a platform", () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));
		expect(screen.getByText(/Open your Steam Library and switch to/i)).toBeInTheDocument();
		expect(screen.getByTestId("import-file-input")).toBeInTheDocument();
	});

	it("can navigate back to the platform picker from the hint step", () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-gog"));
		expect(screen.getByText(/In GOG Galaxy/i)).toBeInTheDocument();
		fireEvent.click(screen.getByText("Change platform"));
		expect(screen.getByTestId("platform-card-steam")).toBeInTheDocument();
	});

	it("uploads selected files and renders the confirmation list (all checked)", async () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));

		const input = screen.getByTestId("import-file-input") as HTMLInputElement;
		const files = [
			new File(["a"], "shot1.png", { type: "image/png" }),
			new File(["b"], "shot2.png", { type: "image/png" }),
		];
		fireEvent.change(input, { target: { files } });

		expect(screen.getByText("shot1.png")).toBeInTheDocument();
		expect(screen.getByText("Import 2 screenshots")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Import 2 screenshots"));

		await waitFor(() => expect(importMutate).toHaveBeenCalledWith(files));

		expect(screen.getByDisplayValue("Hades")).toBeInTheDocument();
		expect(screen.getByDisplayValue("Celeste")).toBeInTheDocument();
		// IGDB badge only on the matched candidate
		expect(screen.getByText("IGDB")).toBeInTheDocument();
		expect(screen.getByText("Add 2 games")).toBeInTheDocument();

		const checkboxes = screen.getAllByRole("checkbox");
		expect(checkboxes.every((c) => (c as HTMLInputElement).checked)).toBe(true);
	});

	it("accepts dropped image files (and ignores non-images), de-duped", () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));

		const dropzone = screen.getByTestId("import-dropzone");
		fireEvent.drop(dropzone, {
			dataTransfer: {
				files: [
					new File(["a"], "drop1.png", { type: "image/png" }),
					new File(["x"], "notes.txt", { type: "text/plain" }), // ignored
				],
			},
		});

		expect(screen.getByText("drop1.png")).toBeInTheDocument();
		expect(screen.queryByText("notes.txt")).not.toBeInTheDocument();
		expect(screen.getByText("1 screenshot selected")).toBeInTheDocument();

		// Dropping the same file again does not duplicate it.
		fireEvent.drop(dropzone, {
			dataTransfer: { files: [new File(["a"], "drop1.png", { type: "image/png" })] },
		});
		expect(screen.getByText("1 screenshot selected")).toBeInTheDocument();
	});

	it("removes a single file and clears all", () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));
		fireEvent.change(screen.getByTestId("import-file-input"), {
			target: {
				files: [
					new File(["a"], "a.png", { type: "image/png" }),
					new File(["b"], "b.png", { type: "image/png" }),
				],
			},
		});
		expect(screen.getByText("2 screenshots selected")).toBeInTheDocument();

		fireEvent.click(screen.getByLabelText("Remove a.png"));
		expect(screen.queryByText("a.png")).not.toBeInTheDocument();
		expect(screen.getByText("1 screenshot selected")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Clear all"));
		expect(screen.queryByText("b.png")).not.toBeInTheDocument();
		expect(screen.getByText("Import screenshots")).toBeInTheDocument();
	});

	it("accepts an image pasted from the clipboard", () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));

		fireEvent.paste(document, {
			clipboardData: { files: [new File(["a"], "pasted.png", { type: "image/png" })] },
		});

		expect(screen.getByText("pasted.png")).toBeInTheDocument();
		expect(screen.getByText("1 screenshot selected")).toBeInTheDocument();
	});

	it("bulk-confirms only the checked candidates with the matched platform", async () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));

		const input = screen.getByTestId("import-file-input") as HTMLInputElement;
		const files = [new File(["a"], "shot.png", { type: "image/png" })];
		fireEvent.change(input, { target: { files } });
		fireEvent.click(screen.getByText("Import 1 screenshot"));

		await waitFor(() => expect(screen.getByDisplayValue("Hades")).toBeInTheDocument());

		// Uncheck Celeste
		fireEvent.click(screen.getByLabelText("Select Celeste"));
		expect(screen.getByText("Add 1 games")).toBeInTheDocument();

		fireEvent.click(screen.getByText("Add 1 games"));

		await waitFor(() =>
			expect(confirmMutate).toHaveBeenCalledWith({
				captureId: "cap-1",
				confirmPublicIds: ["cand-1"],
				platformId: 2, // Steam matched default
				status: "backlog",
				titleOverrides: {},
			}),
		);

		expect(notifications.show).toHaveBeenCalledWith(
			expect.objectContaining({ message: "Imported 1 games", color: "green" }),
		);
		expect(mockNavigate).toHaveBeenCalledWith("/library");
	});

	it("uses the chosen status and platform when bulk-confirming", async () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));
		fireEvent.change(screen.getByTestId("import-file-input"), {
			target: { files: [new File(["a"], "shot.png", { type: "image/png" })] },
		});
		fireEvent.click(screen.getByText("Import 1 screenshot"));
		await waitFor(() => expect(screen.getByDisplayValue("Hades")).toBeInTheDocument());

		fireEvent.change(screen.getByLabelText("Status"), { target: { value: "playing" } });
		fireEvent.change(screen.getByLabelText("Platform"), { target: { value: "3" } });

		fireEvent.click(screen.getByText("Add 2 games"));

		await waitFor(() =>
			expect(confirmMutate).toHaveBeenCalledWith({
				captureId: "cap-1",
				confirmPublicIds: ["cand-1", "cand-2"],
				platformId: 3,
				status: "playing",
				titleOverrides: {},
			}),
		);
	});

	it("sends a corrected title as an override on confirm", async () => {
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));
		fireEvent.change(screen.getByTestId("import-file-input"), {
			target: { files: [new File(["a"], "shot.png", { type: "image/png" })] },
		});
		fireEvent.click(screen.getByText("Import 1 screenshot"));
		await waitFor(() => expect(screen.getByDisplayValue("Hades")).toBeInTheDocument());

		// Fix the OCR'd title.
		fireEvent.change(screen.getByDisplayValue("Hades"), {
			target: { value: "Hades II" },
		});
		fireEvent.click(screen.getByText("Add 2 games"));

		await waitFor(() =>
			expect(confirmMutate).toHaveBeenCalledWith(
				expect.objectContaining({ titleOverrides: { "cand-1": "Hades II" } }),
			),
		);
	});

	it("flags duplicates and unchecks them by default", async () => {
		mockUseCandidateDuplicates.mockReturnValue({ data: ["cand-1"] });
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));
		fireEvent.change(screen.getByTestId("import-file-input"), {
			target: { files: [new File(["a"], "shot.png", { type: "image/png" })] },
		});
		fireEvent.click(screen.getByText("Import 1 screenshot"));
		await waitFor(() => expect(screen.getByDisplayValue("Hades")).toBeInTheDocument());

		// The duplicate shows the warning and is unchecked; only the other is added.
		expect(screen.getByText("In library")).toBeInTheDocument();
		const hadesCheckbox = screen.getByLabelText("Select Hades") as HTMLInputElement;
		expect(hadesCheckbox.checked).toBe(false);
		expect(screen.getByText("Add 1 games")).toBeInTheDocument();
	});

	it("surfaces an error notification when upload fails", async () => {
		importMutate.mockRejectedValueOnce(new Error("Daily cap reached"));
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-xbox"));

		const input = screen.getByTestId("import-file-input") as HTMLInputElement;
		fireEvent.change(input, {
			target: { files: [new File(["a"], "shot.png", { type: "image/png" })] },
		});
		fireEvent.click(screen.getByText("Import 1 screenshot"));

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ message: "Daily cap reached", color: "red" }),
			),
		);
	});

	it("surfaces an error notification when bulk confirm fails", async () => {
		confirmMutate.mockRejectedValueOnce(new Error("boom"));
		renderPage();
		fireEvent.click(screen.getByTestId("platform-card-steam"));
		fireEvent.change(screen.getByTestId("import-file-input"), {
			target: { files: [new File(["a"], "shot.png", { type: "image/png" })] },
		});
		fireEvent.click(screen.getByText("Import 1 screenshot"));
		await waitFor(() => expect(screen.getByDisplayValue("Hades")).toBeInTheDocument());

		fireEvent.click(screen.getByText("Add 2 games"));

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ message: "boom", color: "red" }),
			),
		);
		expect(mockNavigate).not.toHaveBeenCalled();
	});

	it("navigates back to library via the header button", () => {
		renderPage();
		fireEvent.click(screen.getByText("Back to Library"));
		expect(mockNavigate).toHaveBeenCalledWith("/library");
	});
});
