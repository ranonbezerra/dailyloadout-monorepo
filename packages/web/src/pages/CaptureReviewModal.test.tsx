import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

vi.mock("@tabler/icons-react", () => ({
	IconCheck: () => <span data-testid="icon-check" />,
	IconX: () => <span data-testid="icon-x" />,
}));

vi.mock("../hooks/useCapture", () => ({
	useCapture: vi.fn(),
	useConfirmCandidate: vi.fn(),
	useRejectCandidate: vi.fn(),
}));

vi.mock("../hooks/useLibrary", () => ({
	usePlatforms: vi.fn(),
}));

// Mock Mantine Modal and Select for jsdom compatibility
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
		}) =>
			opened ? (
				<div data-testid="modal">
					{title && <div>{title}</div>}
					{children}
				</div>
			) : null,
		Select: ({
			label,
			placeholder,
			value,
			onChange,
			data,
		}: {
			label?: string;
			placeholder?: string;
			value?: string;
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
import { useCapture, useConfirmCandidate, useRejectCandidate } from "../hooks/useCapture";
import { usePlatforms } from "../hooks/useLibrary";
import type { Capture, CaptureCandidate } from "../types/capture";
import { CaptureReviewModal } from "./CaptureReviewModal";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockConfirmMutateAsync = vi.fn();
const mockRejectMutateAsync = vi.fn();

function renderModal(captureId: string | null = "cap-1", onClose = vi.fn()) {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<CaptureReviewModal captureId={captureId} onClose={onClose} />
			</MemoryRouter>
		</MantineProvider>,
	);
}

function makeCandidate(overrides: Partial<CaptureCandidate> = {}): CaptureCandidate {
	return {
		publicId: "cand-1",
		title: "Hollow Knight",
		platformHint: "PC",
		igdbTitle: "Hollow Knight",
		igdbCoverUrl: "https://images.igdb.com/igdb/image/upload/t_cover_big/cover.jpg",
		igdbSummary: "A metroidvania game",
		igdbGenres: ["Action", "Platformer"],
		confidence: 0.9,
		status: "pending",
		matchedGame: null,
		...overrides,
	};
}

function makeCapture(overrides: Partial<Capture> = {}): Capture {
	return {
		publicId: "cap-1",
		inputType: "text",
		rawText: "I played Hollow Knight on PC",
		status: "review",
		errorMessage: null,
		candidates: [makeCandidate()],
		createdAt: "2024-06-01T00:00:00Z",
		updatedAt: "2024-06-01T00:00:00Z",
		...overrides,
	};
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
	mockConfirmMutateAsync.mockReset();
	mockRejectMutateAsync.mockReset();
	vi.clearAllMocks();

	(useCapture as Mock).mockReturnValue({
		data: makeCapture(),
		isLoading: false,
	});

	(usePlatforms as Mock).mockReturnValue({
		data: [
			{ id: 1, slug: "pc", label: "PC", family: "pc" },
			{ id: 2, slug: "ps5", label: "PlayStation 5", family: "playstation" },
		],
	});

	(useConfirmCandidate as Mock).mockReturnValue({
		mutateAsync: mockConfirmMutateAsync,
		isPending: false,
	});
	(useRejectCandidate as Mock).mockReturnValue({
		mutateAsync: mockRejectMutateAsync,
		isPending: false,
	});
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CaptureReviewModal", () => {
	it("returns null when captureId is null", () => {
		renderModal(null);

		// When captureId is null the component returns null -- no modal content renders
		expect(screen.queryByText("Review Candidates")).not.toBeInTheDocument();
		expect(screen.queryByText("Loading capture...")).not.toBeInTheDocument();
	});

	it("shows loading state", () => {
		(useCapture as Mock).mockReturnValue({
			data: undefined,
			isLoading: true,
		});

		renderModal();

		expect(screen.getByText("Loading capture...")).toBeInTheDocument();
	});

	it('shows "Capture not found" when capture is null after loading', () => {
		(useCapture as Mock).mockReturnValue({
			data: null,
			isLoading: false,
		});

		renderModal();

		expect(screen.getByText("Capture not found.")).toBeInTheDocument();
	});

	it('shows "No candidates were extracted" when capture has empty candidates', () => {
		(useCapture as Mock).mockReturnValue({
			data: makeCapture({ candidates: [] }),
			isLoading: false,
		});

		renderModal();

		expect(
			screen.getByText("No candidates were extracted from this capture."),
		).toBeInTheDocument();
	});

	it("shows candidate card with title, confidence badge, and status badge", () => {
		renderModal();

		// Title
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		// Confidence badge (0.9 = "High")
		expect(screen.getByText("High")).toBeInTheDocument();
		// Status badge
		expect(screen.getByText("pending")).toBeInTheDocument();
	});

	it("shows platform hint on candidate card", () => {
		renderModal();

		expect(screen.getByText("Platform hint: PC")).toBeInTheDocument();
	});

	it("shows summary on candidate card", () => {
		renderModal();

		expect(screen.getByText("A metroidvania game")).toBeInTheDocument();
	});

	it("shows genre badges on candidate card", () => {
		renderModal();

		expect(screen.getByText("Action")).toBeInTheDocument();
		expect(screen.getByText("Platformer")).toBeInTheDocument();
	});

	it("shows platform and status selects for pending candidates", () => {
		renderModal();

		// Platform and Status selects rendered with aria-labels
		expect(screen.getByLabelText("Platform")).toBeInTheDocument();
		expect(screen.getByLabelText("Status")).toBeInTheDocument();
	});

	it("shows confirm and reject buttons for pending candidates", () => {
		renderModal();

		expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
	});

	it("confirm button is disabled without platform selected", () => {
		renderModal();

		const confirmButton = screen.getByRole("button", { name: /confirm/i });
		expect(confirmButton).toBeDisabled();
	});

	it("resolved candidates are dimmed (opacity)", () => {
		(useCapture as Mock).mockReturnValue({
			data: makeCapture({
				candidates: [makeCandidate({ status: "confirmed", publicId: "cand-confirmed" })],
			}),
			isLoading: false,
		});

		renderModal();

		// The Card has opacity={isResolved ? 0.6 : 1}. Mantine renders style on the element.
		// Look for the card element that contains the candidate text.
		const title = screen.getByText("Hollow Knight");
		// Walk up to find the card with opacity
		const card =
			title.closest('[class*="card"], [class*="Card"]') ||
			title.parentElement?.parentElement?.parentElement?.parentElement;
		if (card instanceof HTMLElement) {
			expect(card.style.opacity).toBe("0.6");
		}
	});

	it("does not show selects or action buttons for resolved candidates", () => {
		(useCapture as Mock).mockReturnValue({
			data: makeCapture({
				candidates: [makeCandidate({ status: "confirmed", publicId: "cand-confirmed" })],
			}),
			isLoading: false,
		});

		renderModal();

		expect(screen.queryByLabelText("Platform")).not.toBeInTheDocument();
		expect(screen.queryByLabelText("Status")).not.toBeInTheDocument();
		expect(screen.queryByRole("button", { name: /confirm/i })).not.toBeInTheDocument();
		expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
	});

	it("shows medium confidence for score between 0.5 and 0.8", () => {
		(useCapture as Mock).mockReturnValue({
			data: makeCapture({
				candidates: [makeCandidate({ confidence: 0.6 })],
			}),
			isLoading: false,
		});

		renderModal();

		expect(screen.getByText("Medium")).toBeInTheDocument();
	});

	it("shows low confidence for score below 0.5", () => {
		(useCapture as Mock).mockReturnValue({
			data: makeCapture({
				candidates: [makeCandidate({ confidence: 0.3 })],
			}),
			isLoading: false,
		});

		renderModal();

		expect(screen.getByText("Low")).toBeInTheDocument();
	});

	it("shows unknown confidence when confidence is null", () => {
		(useCapture as Mock).mockReturnValue({
			data: makeCapture({
				candidates: [makeCandidate({ confidence: null })],
			}),
			isLoading: false,
		});

		renderModal();

		expect(screen.getByText("Unknown")).toBeInTheDocument();
	});

	it('shows "Extracted as" text when igdbTitle differs from title', () => {
		(useCapture as Mock).mockReturnValue({
			data: makeCapture({
				candidates: [
					makeCandidate({
						title: "hollow night",
						igdbTitle: "Hollow Knight",
					}),
				],
			}),
			isLoading: false,
		});

		renderModal();

		expect(screen.getByText("Extracted as: hollow night")).toBeInTheDocument();
	});

	it("shows raw text from capture", () => {
		renderModal();

		expect(screen.getByText("Original text: I played Hollow Knight on PC")).toBeInTheDocument();
	});

	// ---------------------------------------------------------------------------
	// Confirm / Reject handler tests (lines 103-137, 270)
	// ---------------------------------------------------------------------------

	describe("confirm handler", () => {
		it("clicking Confirm with platform selected calls confirmMutation.mutateAsync", async () => {
			mockConfirmMutateAsync.mockResolvedValue({});

			renderModal();

			// Select a platform
			const platformSelect = screen.getByLabelText("Platform");
			fireEvent.change(platformSelect, { target: { value: "1" } });

			// Click confirm
			fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

			await waitFor(() => {
				expect(mockConfirmMutateAsync).toHaveBeenCalledWith({
					captureId: "cap-1",
					candidateId: "cand-1",
					platformId: 1,
					status: "backlog",
				});
			});
		});

		it("successful confirm shows success notification", async () => {
			mockConfirmMutateAsync.mockResolvedValue({});

			renderModal();

			const platformSelect = screen.getByLabelText("Platform");
			fireEvent.change(platformSelect, { target: { value: "1" } });

			fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Candidate confirmed",
						message: '"Hollow Knight" added to library.',
						color: "green",
					}),
				);
			});
		});

		it("failed confirm shows error notification", async () => {
			mockConfirmMutateAsync.mockRejectedValue(new Error("Duplicate entry"));

			renderModal();

			const platformSelect = screen.getByLabelText("Platform");
			fireEvent.change(platformSelect, { target: { value: "1" } });

			fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Confirm failed",
						message: "Duplicate entry",
						color: "red",
					}),
				);
			});
		});

		it("failed confirm with non-Error rejection shows fallback message", async () => {
			mockConfirmMutateAsync.mockRejectedValue("unexpected");

			renderModal();

			const platformSelect = screen.getByLabelText("Platform");
			fireEvent.change(platformSelect, { target: { value: "1" } });

			fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Confirm failed",
						message: "An unexpected error occurred",
						color: "red",
					}),
				);
			});
		});

		it("when pendingCount <= 1 after confirm, onClose is called", async () => {
			mockConfirmMutateAsync.mockResolvedValue({});
			const onClose = vi.fn();

			// Only 1 pending candidate (the default)
			renderModal("cap-1", onClose);

			const platformSelect = screen.getByLabelText("Platform");
			fireEvent.change(platformSelect, { target: { value: "1" } });

			fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

			await waitFor(() => {
				expect(onClose).toHaveBeenCalled();
			});
		});

		it("when pendingCount > 1 after confirm, onClose is NOT called", async () => {
			mockConfirmMutateAsync.mockResolvedValue({});
			const onClose = vi.fn();

			// Two pending candidates
			(useCapture as Mock).mockReturnValue({
				data: makeCapture({
					candidates: [
						makeCandidate({ publicId: "cand-1" }),
						makeCandidate({ publicId: "cand-2", title: "Celeste", igdbTitle: "Celeste" }),
					],
				}),
				isLoading: false,
			});

			renderModal("cap-1", onClose);

			// Select platform on the first candidate
			const platformSelects = screen.getAllByLabelText("Platform");
			fireEvent.change(platformSelects[0], { target: { value: "1" } });

			const confirmButtons = screen.getAllByRole("button", { name: /confirm/i });
			fireEvent.click(confirmButtons[0]);

			await waitFor(() => {
				expect(mockConfirmMutateAsync).toHaveBeenCalled();
			});

			// onClose should NOT be called since pendingCount is 2
			expect(onClose).not.toHaveBeenCalled();
		});
	});

	describe("reject handler", () => {
		it("clicking Reject calls rejectMutation.mutateAsync", async () => {
			mockRejectMutateAsync.mockResolvedValue({});

			renderModal();

			fireEvent.click(screen.getByRole("button", { name: /reject/i }));

			await waitFor(() => {
				expect(mockRejectMutateAsync).toHaveBeenCalledWith({
					captureId: "cap-1",
					candidateId: "cand-1",
				});
			});
		});

		it("successful reject shows notification with candidate title", async () => {
			mockRejectMutateAsync.mockResolvedValue({});

			renderModal();

			fireEvent.click(screen.getByRole("button", { name: /reject/i }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Candidate rejected",
						message: '"Hollow Knight" has been rejected.',
						color: "gray",
					}),
				);
			});
		});

		it("failed reject shows error notification", async () => {
			mockRejectMutateAsync.mockRejectedValue(new Error("Server unavailable"));

			renderModal();

			fireEvent.click(screen.getByRole("button", { name: /reject/i }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Reject failed",
						message: "Server unavailable",
						color: "red",
					}),
				);
			});
		});

		it("failed reject with non-Error rejection shows fallback message", async () => {
			mockRejectMutateAsync.mockRejectedValue(null);

			renderModal();

			fireEvent.click(screen.getByRole("button", { name: /reject/i }));

			await waitFor(() => {
				expect(notifications.show).toHaveBeenCalledWith(
					expect.objectContaining({
						title: "Reject failed",
						message: "An unexpected error occurred",
						color: "red",
					}),
				);
			});
		});

		it("when pendingCount <= 1 after reject, onClose is called", async () => {
			mockRejectMutateAsync.mockResolvedValue({});
			const onClose = vi.fn();

			renderModal("cap-1", onClose);

			fireEvent.click(screen.getByRole("button", { name: /reject/i }));

			await waitFor(() => {
				expect(onClose).toHaveBeenCalled();
			});
		});
	});

	describe("CandidateCard platformId state", () => {
		it("changing platform select updates the value used in confirm", async () => {
			mockConfirmMutateAsync.mockResolvedValue({});

			renderModal();

			// Select PS5 (id=2) instead of default
			const platformSelect = screen.getByLabelText("Platform");
			fireEvent.change(platformSelect, { target: { value: "2" } });

			fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

			await waitFor(() => {
				expect(mockConfirmMutateAsync).toHaveBeenCalledWith(
					expect.objectContaining({
						platformId: 2,
					}),
				);
			});
		});
	});
});
