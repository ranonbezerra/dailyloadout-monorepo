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

const mockLoadout = {
	publicId: "loadout-1",
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

const mockLoadoutListResponse = {
	items: [
		{
			publicId: "loadout-1",
			libraryEntry: mockLoadout.libraryEntry,
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

vi.mock("../lib/loadout-api", () => ({
	listLoadouts: vi.fn(() => Promise.resolve(mockLoadoutListResponse)),
	getLatestLoadout: vi.fn(() => Promise.resolve(mockLoadout)),
	createLoadout: vi.fn(() => Promise.resolve([mockLoadout])),
	acceptLoadout: vi.fn(() => Promise.resolve({ ...mockLoadout, action: "accepted" })),
	rejectLoadout: vi.fn(() => Promise.resolve({ ...mockLoadout, action: "rejected" })),
}));

import {
	acceptLoadout,
	createLoadout,
	getLatestLoadout,
	listLoadouts,
	rejectLoadout,
} from "../lib/loadout-api";
import {
	useAcceptLoadout,
	useCreateLoadout,
	useLatestLoadout,
	useLoadouts,
	useRejectLoadout,
} from "./useLoadout";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("useLoadouts", () => {
	it("returns loadout list without params", async () => {
		const { result } = renderHook(() => useLoadouts(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listLoadouts).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockLoadoutListResponse);
	});

	it("passes pagination params to listLoadouts", async () => {
		const params = { limit: 5, offset: 10 };
		const { result } = renderHook(() => useLoadouts(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listLoadouts).toHaveBeenCalledWith(params);
	});
});

describe("useLatestLoadout", () => {
	it("returns the latest pending loadout", async () => {
		const { result } = renderHook(() => useLatestLoadout(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getLatestLoadout).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockLoadout);
	});
});

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

describe("useCreateLoadout", () => {
	it("calls createLoadout with all required args", async () => {
		const { result } = renderHook(() => useCreateLoadout(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			mood: "focused",
			availableMinutes: 120,
			mentalEnergy: "high",
		});

		expect(createLoadout).toHaveBeenCalledWith("focused", 120, "high", undefined, undefined);
	});

	it("calls createLoadout with optional count and context", async () => {
		const { result } = renderHook(() => useCreateLoadout(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			mood: "chill",
			availableMinutes: 60,
			mentalEnergy: "low",
			count: 3,
			context: "Evening wind-down",
		});

		expect(createLoadout).toHaveBeenCalledWith("chill", 60, "low", 3, "Evening wind-down");
	});
});

describe("useAcceptLoadout", () => {
	it("calls acceptLoadout with the publicId", async () => {
		const { result } = renderHook(() => useAcceptLoadout(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "loadout-1" });

		expect(acceptLoadout).toHaveBeenCalledWith("loadout-1", undefined);
	});

	it("forwards an optional briefingText", async () => {
		const { result } = renderHook(() => useAcceptLoadout(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "loadout-1",
			briefingText: "Resume at the gate.",
		});

		expect(acceptLoadout).toHaveBeenCalledWith("loadout-1", "Resume at the gate.");
	});
});

describe("useRejectLoadout", () => {
	it("calls rejectLoadout with the publicId", async () => {
		const { result } = renderHook(() => useRejectLoadout(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync("loadout-1");

		expect(rejectLoadout).toHaveBeenCalledWith("loadout-1");
	});
});
