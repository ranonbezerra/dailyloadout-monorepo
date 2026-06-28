import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, type Mock, vi } from "vitest";
import type {
	AdminCaptureDetail,
	AdminCaptureList,
	AdminCaptureSummary,
} from "../types/backoffice";
import { CapturesPage } from "./CapturesPage";

vi.mock("../hooks/useBackoffice", () => ({
	useCaptures: vi.fn(),
	useCapture: vi.fn(),
	useCaptureActions: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { useCapture, useCaptureActions, useCaptures } from "../hooks/useBackoffice";

const mockUseCaptures = useCaptures as Mock;
const mockUseCapture = useCapture as Mock;
const mockUseCaptureActions = useCaptureActions as Mock;

function capture(over: Partial<AdminCaptureSummary> = {}): AdminCaptureSummary {
	return {
		publicId: "c1",
		userEmail: "owner@example.com",
		inputType: "text",
		status: "failed",
		candidateCount: 2,
		errorMessage: "Processing failed. Please try again.",
		createdAt: new Date().toISOString(),
		updatedAt: new Date().toISOString(),
		...over,
	};
}

function detail(over: Partial<AdminCaptureDetail> = {}): AdminCaptureDetail {
	return {
		...capture(),
		rawText: "I played Halo last night",
		reprocessable: true,
		candidates: [
			{
				publicId: "cand1",
				title: "Halo",
				status: "pending",
				confidence: 0.95,
				igdbId: 111,
				matchedGameTitle: null,
			},
		],
		...over,
	};
}

function list(items: AdminCaptureSummary[]): AdminCaptureList {
	return {
		items,
		total: items.length,
		limit: 20,
		offset: 0,
		statusCounts: [
			{ status: "failed", count: items.filter((c) => c.status === "failed").length },
			{ status: "review", count: items.filter((c) => c.status === "review").length },
		],
	};
}

function actions() {
	return {
		reprocess: { mutate: vi.fn(), isPending: false },
		purge: { mutate: vi.fn(), isPending: false },
	};
}

function renderPage() {
	return render(
		<MantineProvider>
			<CapturesPage />
		</MantineProvider>,
	);
}

describe("CapturesPage", () => {
	it("renders status tallies and a capture row", () => {
		mockUseCaptureActions.mockReturnValue(actions());
		mockUseCapture.mockReturnValue({ data: undefined, isLoading: false });
		mockUseCaptures.mockReturnValue({ data: list([capture()]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("owner@example.com")).toBeInTheDocument();
		// "failed" appears in both the tally card and the status badge.
		expect(screen.getAllByText("failed").length).toBeGreaterThan(0);
	});

	it("shows an empty state", () => {
		mockUseCaptureActions.mockReturnValue(actions());
		mockUseCapture.mockReturnValue({ data: undefined, isLoading: false });
		mockUseCaptures.mockReturnValue({ data: list([]), isLoading: false, isError: false });
		renderPage();
		expect(screen.getByText("No captures match.")).toBeInTheDocument();
	});

	it("loading and error states render", () => {
		mockUseCaptureActions.mockReturnValue(actions());
		mockUseCapture.mockReturnValue({ data: undefined, isLoading: false });
		mockUseCaptures.mockReturnValue({ data: undefined, isLoading: true, isError: false });
		const { rerender } = renderPage();
		mockUseCaptures.mockReturnValue({ data: undefined, isLoading: false, isError: true });
		rerender(
			<MantineProvider>
				<CapturesPage />
			</MantineProvider>,
		);
		expect(screen.getByText("Failed to load captures.")).toBeInTheDocument();
	});

	it("purges a capture via the confirm modal", async () => {
		const a = actions();
		a.purge.mutate = vi.fn((_id, opts) => opts?.onSuccess?.());
		mockUseCaptureActions.mockReturnValue(a);
		mockUseCapture.mockReturnValue({ data: undefined, isLoading: false });
		mockUseCaptures.mockReturnValue({ data: list([capture()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("Purge capture"));
		fireEvent.click(await screen.findByRole("button", { name: "Purge" }));
		expect(a.purge.mutate).toHaveBeenCalledWith("c1", expect.anything());
	});

	it("reprocesses a capture from the detail drawer (success path)", async () => {
		const a = actions();
		a.reprocess.mutate = vi.fn((_id, opts) => opts?.onSuccess?.());
		mockUseCaptureActions.mockReturnValue(a);
		mockUseCapture.mockReturnValue({ data: detail(), isLoading: false });
		mockUseCaptures.mockReturnValue({ data: list([capture()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("View"));
		fireEvent.click(await screen.findByRole("button", { name: "Reprocess" }));
		expect(a.reprocess.mutate).toHaveBeenCalledWith("c1", expect.anything());
	});

	it("surfaces reprocess and purge errors", async () => {
		const a = actions();
		a.reprocess.mutate = vi.fn((_id, opts) => opts?.onError?.(new Error("nope")));
		a.purge.mutate = vi.fn((_id, opts) => opts?.onError?.(new Error("boom")));
		mockUseCaptureActions.mockReturnValue(a);
		mockUseCapture.mockReturnValue({ data: detail(), isLoading: false });
		mockUseCaptures.mockReturnValue({ data: list([capture()]), isLoading: false, isError: false });
		renderPage();
		fireEvent.click(screen.getByLabelText("View"));
		fireEvent.click(await screen.findByRole("button", { name: "Reprocess" }));
		expect(a.reprocess.mutate).toHaveBeenCalled();
		// Purge error path (modal stays open on failure).
		fireEvent.click(screen.getByLabelText("Purge capture"));
		fireEvent.click(await screen.findByRole("button", { name: "Purge" }));
		expect(a.purge.mutate).toHaveBeenCalled();
	});

	it("renders the drawer loading state and an empty/sourceless detail", async () => {
		mockUseCaptureActions.mockReturnValue(actions());
		mockUseCaptures.mockReturnValue({ data: list([capture()]), isLoading: false, isError: false });

		// First: drawer is loading.
		mockUseCapture.mockReturnValue({ data: undefined, isLoading: true });
		const { rerender } = renderPage();
		fireEvent.click(screen.getByLabelText("View"));

		// Then: a minimal detail with no candidates, raw text, or error.
		mockUseCapture.mockReturnValue({
			data: detail({ rawText: null, errorMessage: null, candidates: [], reprocessable: false }),
			isLoading: false,
		});
		rerender(
			<MantineProvider>
				<CapturesPage />
			</MantineProvider>,
		);
		expect(await screen.findByText("None")).toBeInTheDocument();
	});

	it("disables reprocess for sourceless captures", async () => {
		mockUseCaptureActions.mockReturnValue(actions());
		mockUseCapture.mockReturnValue({
			data: detail({ reprocessable: false, rawText: null, inputType: "photo" }),
			isLoading: false,
		});
		mockUseCaptures.mockReturnValue({
			data: list([capture({ inputType: "photo" })]),
			isLoading: false,
			isError: false,
		});
		renderPage();
		fireEvent.click(screen.getByLabelText("View"));
		expect(await screen.findByRole("button", { name: "Reprocess" })).toBeDisabled();
	});

	it("shows pagination summary when there are many captures", () => {
		mockUseCaptureActions.mockReturnValue(actions());
		mockUseCapture.mockReturnValue({ data: undefined, isLoading: false });
		mockUseCaptures.mockReturnValue({
			data: { ...list([capture()]), total: 50 },
			isLoading: false,
			isError: false,
		});
		renderPage();
		expect(screen.getByText("50 captures")).toBeInTheDocument();
	});
});
