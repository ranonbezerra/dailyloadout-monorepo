import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@dl/shared/api", () => ({
	apiFetch: vi.fn(),
	BASE_URL: "http://test",
	getAccessToken: vi.fn(() => "test-token"),
}));

import { apiFetch } from "@dl/shared/api";
import {
	fetchGenreStats,
	fetchOverview,
	fetchPlatformStats,
	fetchPlayHeatmap,
	fetchTimeline,
} from "./stats-api";

const mockApiFetch = apiFetch as Mock;

beforeEach(() => {
	mockApiFetch.mockReset();
});

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

describe("fetchOverview", () => {
	it("calls GET /v1/stats/overview and returns camelCased data", async () => {
		const apiResponse = {
			total_games: 42,
			status_counts: { playing: 5, backlog: 30, completed: 7 },
			missions_last_30d: 12,
			avg_mission_duration_minutes: 65.5,
			user_created_at: "2024-01-01T00:00:00Z",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchOverview();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/stats/overview");
		expect(result.totalGames).toBe(42);
		expect(result.statusCounts).toEqual({ playing: 5, backlog: 30, completed: 7 });
		expect(result.missionsLast30d).toBe(12);
		expect(result.avgMissionDurationMinutes).toBe(65.5);
		expect(result.userCreatedAt).toBe("2024-01-01T00:00:00Z");
	});

	it("handles null avg_mission_duration_minutes", async () => {
		const apiResponse = {
			total_games: 0,
			status_counts: {},
			missions_last_30d: 0,
			avg_mission_duration_minutes: null,
			user_created_at: "2024-01-01T00:00:00Z",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchOverview();

		expect(result.avgMissionDurationMinutes).toBeNull();
	});
});

// ---------------------------------------------------------------------------
// Play heatmap
// ---------------------------------------------------------------------------

describe("fetchPlayHeatmap", () => {
	it("calls GET /v1/stats/play-heatmap with no params when none given", async () => {
		const apiResponse = {
			days: [
				{ date: "2024-06-01", count: 2, total_minutes: 120 },
				{ date: "2024-06-02", count: 1, total_minutes: 45 },
			],
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchPlayHeatmap();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/stats/play-heatmap");
		expect(result.days).toHaveLength(2);
		expect(result.days[0].totalMinutes).toBe(120);
		expect(result.days[1].totalMinutes).toBe(45);
	});

	it("appends from and to query params", async () => {
		const apiResponse = { days: [] };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await fetchPlayHeatmap({ from: "2024-01-01", to: "2024-06-30" });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("from=2024-01-01");
		expect(calledPath).toContain("to=2024-06-30");
	});

	it("includes only from when to is omitted", async () => {
		const apiResponse = { days: [] };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await fetchPlayHeatmap({ from: "2024-01-01" });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("from=2024-01-01");
		expect(calledPath).not.toContain("to=");
	});
});

// ---------------------------------------------------------------------------
// Genre stats
// ---------------------------------------------------------------------------

describe("fetchGenreStats", () => {
	it("calls GET /v1/stats/genres and returns camelCased data", async () => {
		const apiResponse = {
			genres: [
				{ genre: "RPG", total_minutes: 500, mission_count: 8 },
				{ genre: "Action", total_minutes: 300, mission_count: 5 },
			],
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchGenreStats();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/stats/genres");
		expect(result.genres).toHaveLength(2);
		expect(result.genres[0].totalMinutes).toBe(500);
		expect(result.genres[0].missionCount).toBe(8);
		expect(result.genres[1].genre).toBe("Action");
	});
});

// ---------------------------------------------------------------------------
// Platform stats
// ---------------------------------------------------------------------------

describe("fetchPlatformStats", () => {
	it("calls GET /v1/stats/platforms and returns camelCased data", async () => {
		const apiResponse = {
			platforms: [
				{
					platform_slug: "pc",
					platform_label: "PC",
					game_count: 20,
					mission_count: 15,
					total_minutes: 900,
				},
				{
					platform_slug: "ps5",
					platform_label: "PlayStation 5",
					game_count: 10,
					mission_count: 8,
					total_minutes: 480,
				},
			],
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchPlatformStats();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/stats/platforms");
		expect(result.platforms).toHaveLength(2);
		expect(result.platforms[0].platformSlug).toBe("pc");
		expect(result.platforms[0].platformLabel).toBe("PC");
		expect(result.platforms[0].gameCount).toBe(20);
		expect(result.platforms[0].missionCount).toBe(15);
		expect(result.platforms[0].totalMinutes).toBe(900);
		expect(result.platforms[1].platformSlug).toBe("ps5");
	});
});

// ---------------------------------------------------------------------------
// Timeline
// ---------------------------------------------------------------------------

describe("fetchTimeline", () => {
	it("calls GET /v1/stats/timeline with no params when none given", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchTimeline();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/stats/timeline");
		expect(result).toEqual(apiResponse);
	});

	it("appends query params for limit and offset", async () => {
		const apiResponse = { items: [], total: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await fetchTimeline({ limit: 10, offset: 20 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("limit=10");
		expect(calledPath).toContain("offset=20");
	});

	it("converts snake_case response items to camelCase", async () => {
		const apiResponse = {
			items: [
				{
					public_id: "m1",
					game_title: "Hades",
					platform_label: "PC",
					mission_type: "regular",
					briefing_text: "Continue from Asphodel",
					debrief_text: "Defeated Theseus",
					ended_via: "debrief_completed",
					started_at: "2024-06-01T10:00:00Z",
					ended_at: "2024-06-01T11:05:00Z",
					duration_minutes: 65,
				},
			],
			total: 1,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchTimeline();

		expect(result.items[0].publicId).toBe("m1");
		expect(result.items[0].gameTitle).toBe("Hades");
		expect(result.items[0].platformLabel).toBe("PC");
		expect(result.items[0].missionType).toBe("regular");
		expect(result.items[0].briefingText).toBe("Continue from Asphodel");
		expect(result.items[0].debriefText).toBe("Defeated Theseus");
		expect(result.items[0].endedVia).toBe("debrief_completed");
		expect(result.items[0].startedAt).toBe("2024-06-01T10:00:00Z");
		expect(result.items[0].endedAt).toBe("2024-06-01T11:05:00Z");
		expect(result.items[0].durationMinutes).toBe(65);
	});

	it("handles null optional fields", async () => {
		const apiResponse = {
			items: [
				{
					public_id: "m2",
					game_title: "Celeste",
					platform_label: "Switch",
					mission_type: "regular",
					briefing_text: null,
					debrief_text: null,
					ended_via: null,
					started_at: "2024-06-01T10:00:00Z",
					ended_at: null,
					duration_minutes: null,
				},
			],
			total: 1,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchTimeline();

		expect(result.items[0].briefingText).toBeNull();
		expect(result.items[0].debriefText).toBeNull();
		expect(result.items[0].endedVia).toBeNull();
		expect(result.items[0].endedAt).toBeNull();
		expect(result.items[0].durationMinutes).toBeNull();
	});

	it("handles offset=0 correctly (falsy but valid)", async () => {
		mockApiFetch.mockResolvedValueOnce({ items: [], total: 0 });

		await fetchTimeline({ offset: 0 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("offset=0");
	});
});
