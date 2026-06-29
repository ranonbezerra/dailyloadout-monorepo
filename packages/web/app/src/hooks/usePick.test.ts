import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWrapper } from "../test/wrapper";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@slate/shared/api", () => ({
	BASE_URL: "http://localhost:8100",
	apiFetch: vi.fn(() => Promise.resolve(null)),
	getAccessToken: vi.fn(() => null),
	getRefreshToken: vi.fn(() => null),
	saveTokens: vi.fn(),
	clearTokens: vi.fn(),
}));

const mockPick = {
	publicId: "pick-1",
	libraryEntry: {
		publicId: "entry-1",
		game: {
			publicId: "game-1",
			slug: "elden-ring",
			title: "Elden Ring",
			metadataSource: "igdb",
			createdAt: "2024-01-01T00:00:00Z",
		},
		platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
		status: "playing" as const,
		createdAt: "2024-01-01T00:00:00Z",
		updatedAt: "2024-06-01T00:00:00Z",
	},
	mood: "focused" as const,
	availableMinutes: 120,
	mentalEnergy: "high" as const,
	context: null,
	reasoning: "Great time for a deep RPG session.",
	action: null,
	createdAt: "2024-06-15T00:00:00Z",
	updatedAt: "2024-06-15T00:00:00Z",
};

const mockPickListResponse = {
	items: [
		{
			publicId: "pick-1",
			libraryEntry: mockPick.libraryEntry,
			mood: "focused" as const,
			availableMinutes: 120,
			mentalEnergy: "high" as const,
			context: null,
			reasoning: "Great time for a deep RPG session.",
			action: null,
			createdAt: "2024-06-15T00:00:00Z",
		},
	],
	total: 1,
};

vi.mock("../lib/pick-api", () => ({
	listPicks: vi.fn(() => Promise.resolve(mockPickListResponse)),
	getLatestPick: vi.fn(() => Promise.resolve(mockPick)),
	createPick: vi.fn(() => Promise.resolve([mockPick])),
	acceptPick: vi.fn(() => Promise.resolve({ ...mockPick, action: "accepted" })),
	rejectPick: vi.fn(() => Promise.resolve({ ...mockPick, action: "rejected" })),
}));

import { acceptPick, createPick, getLatestPick, listPicks, rejectPick } from "../lib/pick-api";
import { useAcceptPick, useCreatePick, useLatestPick, usePicks, useRejectPick } from "./usePick";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("usePicks", () => {
	it("returns pick list without params", async () => {
		const { result } = renderHook(() => usePicks(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listPicks).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockPickListResponse);
	});

	it("passes pagination params to listPicks", async () => {
		const params = { limit: 5, offset: 10 };
		const { result } = renderHook(() => usePicks(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listPicks).toHaveBeenCalledWith(params);
	});
});

describe("useLatestPick", () => {
	it("returns the latest pending pick", async () => {
		const { result } = renderHook(() => useLatestPick(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getLatestPick).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockPick);
	});
});

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

describe("useCreatePick", () => {
	it("calls createPick with all required args", async () => {
		const { result } = renderHook(() => useCreatePick(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			mood: "focused",
			availableMinutes: 120,
			mentalEnergy: "high",
		});

		expect(createPick).toHaveBeenCalledWith("focused", 120, "high", undefined, undefined);
	});

	it("calls createPick with optional count and context", async () => {
		const { result } = renderHook(() => useCreatePick(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			mood: "chill",
			availableMinutes: 60,
			mentalEnergy: "low",
			count: 3,
			context: "Evening wind-down",
		});

		expect(createPick).toHaveBeenCalledWith("chill", 60, "low", 3, "Evening wind-down");
	});
});

describe("useAcceptPick", () => {
	it("calls acceptPick with the publicId", async () => {
		const { result } = renderHook(() => useAcceptPick(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "pick-1" });

		expect(acceptPick).toHaveBeenCalledWith("pick-1", undefined);
	});

	it("forwards an optional recapText", async () => {
		const { result } = renderHook(() => useAcceptPick(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "pick-1",
			recapText: "Resume at the gate.",
		});

		expect(acceptPick).toHaveBeenCalledWith("pick-1", "Resume at the gate.");
	});
});

describe("useRejectPick", () => {
	it("calls rejectPick with the publicId", async () => {
		const { result } = renderHook(() => useRejectPick(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync("pick-1");

		expect(rejectPick).toHaveBeenCalledWith("pick-1");
	});
});
