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

const mockOverview = {
	totalGames: 42,
	statusCounts: { backlog: 20, playing: 5, completed: 15, paused: 2, dropped: 0 },
	missionsLast30d: 12,
	avgMissionDurationMinutes: 95.5,
	userCreatedAt: "2023-01-01T00:00:00Z",
};

const mockHeatmap = {
	days: [
		{ date: "2024-06-01", count: 2, totalMinutes: 180 },
		{ date: "2024-06-02", count: 1, totalMinutes: 60 },
		{ date: "2024-06-03", count: 0, totalMinutes: 0 },
	],
};

const mockGenreStats = {
	genres: [
		{ genre: "Action", totalMinutes: 5400, missionCount: 30 },
		{ genre: "RPG", totalMinutes: 3600, missionCount: 20 },
		{ genre: "Puzzle", totalMinutes: 1200, missionCount: 10 },
	],
};

const mockPlatformStats = {
	platforms: [
		{
			platformSlug: "pc",
			platformLabel: "PC",
			gameCount: 25,
			missionCount: 40,
			totalMinutes: 6000,
		},
		{
			platformSlug: "ps5",
			platformLabel: "PlayStation 5",
			gameCount: 10,
			missionCount: 15,
			totalMinutes: 2400,
		},
	],
};

const mockTimeline = {
	items: [
		{
			publicId: "mission-1",
			gameTitle: "Elden Ring",
			platformLabel: "PC",
			missionType: "regular",
			briefingText: "Continue Stormveil.",
			debriefText: "Defeated Godrick.",
			endedVia: "debrief_completed",
			startedAt: "2024-06-15T18:00:00Z",
			endedAt: "2024-06-15T20:00:00Z",
			durationMinutes: 120,
		},
		{
			publicId: "mission-2",
			gameTitle: "Hades",
			platformLabel: "PC",
			missionType: "regular",
			briefingText: null,
			debriefText: null,
			endedVia: "paused_app",
			startedAt: "2024-06-14T20:00:00Z",
			endedAt: "2024-06-14T21:30:00Z",
			durationMinutes: 90,
		},
	],
	total: 2,
};

vi.mock("../lib/stats-api", () => ({
	fetchOverview: vi.fn(() => Promise.resolve(mockOverview)),
	fetchPlayHeatmap: vi.fn(() => Promise.resolve(mockHeatmap)),
	fetchGenreStats: vi.fn(() => Promise.resolve(mockGenreStats)),
	fetchPlatformStats: vi.fn(() => Promise.resolve(mockPlatformStats)),
	fetchTimeline: vi.fn(() => Promise.resolve(mockTimeline)),
}));

import {
	fetchGenreStats,
	fetchOverview,
	fetchPlatformStats,
	fetchPlayHeatmap,
	fetchTimeline,
} from "../lib/stats-api";
import {
	useGenreStats,
	usePlatformStats,
	usePlayHeatmap,
	useStatsOverview,
	useTimeline,
} from "./useStats";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("useStatsOverview", () => {
	it("returns stats overview data", async () => {
		const { result } = renderHook(() => useStatsOverview(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchOverview).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockOverview);
	});
});

describe("usePlayHeatmap", () => {
	it("returns heatmap data without params", async () => {
		const { result } = renderHook(() => usePlayHeatmap(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchPlayHeatmap).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockHeatmap);
	});

	it("passes date range params to fetchPlayHeatmap", async () => {
		const params = { from: "2024-06-01", to: "2024-06-30" };
		const { result } = renderHook(() => usePlayHeatmap(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchPlayHeatmap).toHaveBeenCalledWith(params);
	});
});

describe("useGenreStats", () => {
	it("returns genre statistics", async () => {
		const { result } = renderHook(() => useGenreStats(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchGenreStats).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockGenreStats);
	});
});

describe("usePlatformStats", () => {
	it("returns platform statistics", async () => {
		const { result } = renderHook(() => usePlatformStats(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchPlatformStats).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockPlatformStats);
	});
});

describe("useTimeline", () => {
	it("returns timeline data without params", async () => {
		const { result } = renderHook(() => useTimeline(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchTimeline).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockTimeline);
	});

	it("passes pagination params to fetchTimeline", async () => {
		const params = { limit: 20, offset: 10 };
		const { result } = renderHook(() => useTimeline(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchTimeline).toHaveBeenCalledWith(params);
	});
});
