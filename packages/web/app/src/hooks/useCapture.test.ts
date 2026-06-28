import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWrapper } from "../test/wrapper";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@dl/shared/api", () => ({
	BASE_URL: "http://localhost:8100",
	apiFetch: vi.fn(() => Promise.resolve(null)),
	getAccessToken: vi.fn(() => null),
	getRefreshToken: vi.fn(() => null),
	saveTokens: vi.fn(),
	clearTokens: vi.fn(),
}));

const mockCapture = {
	publicId: "cap-1",
	inputType: "text",
	rawText: "Elden Ring on PC",
	status: "review" as const,
	errorMessage: null,
	candidates: [
		{
			publicId: "cand-1",
			title: "Elden Ring",
			platformHint: "PC",
			igdbTitle: "Elden Ring",
			igdbCoverUrl: "https://example.com/cover.jpg",
			igdbSummary: "An action RPG",
			igdbGenres: ["Action", "RPG"],
			confidence: 0.95,
			status: "pending" as const,
			matchedGame: null,
		},
	],
	createdAt: "2024-06-01T00:00:00Z",
	updatedAt: "2024-06-01T00:00:00Z",
};

const mockCaptureListResponse = {
	items: [
		{
			publicId: "cap-1",
			inputType: "text",
			rawText: "Elden Ring on PC",
			status: "review" as const,
			errorMessage: null,
			candidateTitles: ["Elden Ring"],
			createdAt: "2024-06-01T00:00:00Z",
			updatedAt: "2024-06-01T00:00:00Z",
		},
	],
	total: 1,
};

const mockLibraryEntry = {
	publicId: "entry-1",
	game: {
		publicId: "game-1",
		slug: "elden-ring",
		title: "Elden Ring",
		metadataSource: "igdb",
		createdAt: "2024-01-01T00:00:00Z",
	},
	platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
	status: "backlog" as const,
	createdAt: "2024-06-01T00:00:00Z",
	updatedAt: "2024-06-01T00:00:00Z",
};

vi.mock("../lib/capture-api", () => ({
	listCaptures: vi.fn(() => Promise.resolve(mockCaptureListResponse)),
	getCapture: vi.fn(() => Promise.resolve(mockCapture)),
	submitTextCapture: vi.fn(() => Promise.resolve(mockCapture)),
	submitPhotoCapture: vi.fn(() => Promise.resolve(mockCapture)),
	submitLibraryImport: vi.fn(() => Promise.resolve(mockCapture)),
	bulkConfirmCandidates: vi.fn(() => Promise.resolve({ confirmed: 1, rejected: 0 })),
	transcribeAudio: vi.fn(() =>
		Promise.resolve({ text: "Elden Ring", language: "en", durationSeconds: 2.5 }),
	),
	confirmCandidate: vi.fn(() => Promise.resolve(mockLibraryEntry)),
	rejectCandidate: vi.fn(() => Promise.resolve(undefined)),
}));

import {
	bulkConfirmCandidates,
	confirmCandidate,
	getCapture,
	listCaptures,
	rejectCandidate,
	submitLibraryImport,
	submitPhotoCapture,
	submitTextCapture,
} from "../lib/capture-api";
import {
	useBulkConfirmCandidates,
	useCapture,
	useCaptures,
	useConfirmCandidate,
	useRejectCandidate,
	useSubmitLibraryImport,
	useSubmitPhotoCapture,
	useSubmitTextCapture,
} from "./useCapture";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("useCaptures", () => {
	it("returns capture list without status filter", async () => {
		const { result } = renderHook(() => useCaptures(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listCaptures).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockCaptureListResponse);
	});

	it("passes status filter to listCaptures", async () => {
		const { result } = renderHook(() => useCaptures("review"), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listCaptures).toHaveBeenCalledWith({ status: "review" });
	});
});

describe("useCapture", () => {
	it("is disabled when publicId is empty", () => {
		const { result } = renderHook(() => useCapture(""), {
			wrapper: createWrapper(),
		});

		expect(result.current.fetchStatus).toBe("idle");
		expect(getCapture).not.toHaveBeenCalled();
	});

	it("fetches a single capture when publicId is truthy", async () => {
		const { result } = renderHook(() => useCapture("cap-1"), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getCapture).toHaveBeenCalledWith("cap-1");
		expect(result.current.data).toEqual(mockCapture);
	});
});

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

describe("useSubmitTextCapture", () => {
	it("calls submitTextCapture with rawText and inputType", async () => {
		const { result } = renderHook(() => useSubmitTextCapture(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ rawText: "Elden Ring on PC", inputType: "voice" });

		expect(submitTextCapture).toHaveBeenCalledWith("Elden Ring on PC", "voice");
	});

	it("calls submitTextCapture with rawText only (default inputType)", async () => {
		const { result } = renderHook(() => useSubmitTextCapture(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ rawText: "Zelda on Switch" });

		expect(submitTextCapture).toHaveBeenCalledWith("Zelda on Switch", undefined);
	});
});

describe("useSubmitPhotoCapture", () => {
	it("calls submitPhotoCapture with the image file", async () => {
		const { result } = renderHook(() => useSubmitPhotoCapture(), {
			wrapper: createWrapper(),
		});

		const file = new File(["dummy"], "photo.jpg", { type: "image/jpeg" });
		await result.current.mutateAsync(file);

		expect(submitPhotoCapture).toHaveBeenCalledWith(file);
	});
});

describe("useSubmitLibraryImport", () => {
	it("calls submitLibraryImport with the files array", async () => {
		const { result } = renderHook(() => useSubmitLibraryImport(), {
			wrapper: createWrapper(),
		});

		const files = [new File(["a"], "a.png", { type: "image/png" })];
		await result.current.mutateAsync(files);

		expect(submitLibraryImport).toHaveBeenCalledWith(files);
	});
});

describe("useBulkConfirmCandidates", () => {
	it("calls bulkConfirmCandidates with all args", async () => {
		const { result } = renderHook(() => useBulkConfirmCandidates(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			captureId: "cap-1",
			confirmPublicIds: ["c1", "c2"],
			platformId: 3,
			status: "backlog",
		});

		expect(bulkConfirmCandidates).toHaveBeenCalledWith(
			"cap-1",
			["c1", "c2"],
			3,
			"backlog",
			undefined,
		);
	});

	it("calls bulkConfirmCandidates without optional status", async () => {
		const { result } = renderHook(() => useBulkConfirmCandidates(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			captureId: "cap-1",
			confirmPublicIds: ["c1"],
			platformId: 4,
		});

		expect(bulkConfirmCandidates).toHaveBeenCalledWith("cap-1", ["c1"], 4, undefined, undefined);
	});
});

describe("useConfirmCandidate", () => {
	it("calls confirmCandidate with all required args", async () => {
		const { result } = renderHook(() => useConfirmCandidate(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			captureId: "cap-1",
			candidateId: "cand-1",
			platformId: 1,
			status: "playing",
		});

		expect(confirmCandidate).toHaveBeenCalledWith("cap-1", "cand-1", 1, "playing");
	});

	it("calls confirmCandidate without optional status", async () => {
		const { result } = renderHook(() => useConfirmCandidate(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			captureId: "cap-1",
			candidateId: "cand-1",
			platformId: 2,
		});

		expect(confirmCandidate).toHaveBeenCalledWith("cap-1", "cand-1", 2, undefined);
	});
});

describe("useRejectCandidate", () => {
	it("calls rejectCandidate with captureId and candidateId", async () => {
		const { result } = renderHook(() => useRejectCandidate(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ captureId: "cap-1", candidateId: "cand-1" });

		expect(rejectCandidate).toHaveBeenCalledWith("cap-1", "cand-1");
	});
});
