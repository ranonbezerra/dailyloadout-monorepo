import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@dl/shared/api", () => ({
	apiFetch: vi.fn(),
	BASE_URL: "http://test",
	getAccessToken: vi.fn(() => "test-token"),
}));

import { apiFetch } from "@dl/shared/api";
import {
	addToLibrary,
	createGame,
	deleteEntry,
	fetchGameGenres,
	fetchLibrary,
	fetchPlatforms,
	searchGames,
	updateEntry,
} from "./library-api";

const mockApiFetch = apiFetch as Mock;

beforeEach(() => {
	mockApiFetch.mockReset();
});

// ---------------------------------------------------------------------------
// Platforms
// ---------------------------------------------------------------------------

describe("fetchPlatforms", () => {
	it("calls GET /v1/platforms and returns camelCased data", async () => {
		const apiResponse = [
			{ id: 1, slug: "pc", label: "PC", family: "computer" },
			{ id: 2, slug: "ps5", label: "PlayStation 5", family: "playstation" },
		];
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchPlatforms();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/platforms");
		expect(result).toEqual(apiResponse);
	});

	it("converts snake_case keys in response to camelCase", async () => {
		const apiResponse = [
			{ id: 1, slug: "switch", label: "Switch", family: "nintendo", created_at: "2024-01-01" },
		];
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchPlatforms();

		expect(result).toEqual([
			{ id: 1, slug: "switch", label: "Switch", family: "nintendo", createdAt: "2024-01-01" },
		]);
	});
});

// ---------------------------------------------------------------------------
// Games
// ---------------------------------------------------------------------------

describe("searchGames", () => {
	it("calls GET /v1/games/search with query and default limit", async () => {
		const apiResponse = [{ public_id: "g1", title: "Hades", slug: "hades" }];
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await searchGames("hades");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/games/search?q=hades&limit=20");
		expect(result).toEqual([{ publicId: "g1", title: "Hades", slug: "hades" }]);
	});

	it("passes a custom limit", async () => {
		mockApiFetch.mockResolvedValueOnce([]);

		await searchGames("zelda", 5);

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/games/search?q=zelda&limit=5");
	});

	it("encodes special characters in query", async () => {
		mockApiFetch.mockResolvedValueOnce([]);

		await searchGames("a&b=c");

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("q=a%26b%3Dc");
	});
});

describe("createGame", () => {
	it("calls POST /v1/games with snake_cased body", async () => {
		const apiResponse = {
			public_id: "g1",
			slug: "celeste",
			title: "Celeste",
			metadata_source: "manual",
			created_at: "2024-01-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await createGame({
			slug: "celeste",
			title: "Celeste",
			coverUrl: "https://img.example.com/celeste.jpg",
			genres: ["platformer"],
		});

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/games", {
			method: "POST",
			body: JSON.stringify({
				slug: "celeste",
				title: "Celeste",
				cover_url: "https://img.example.com/celeste.jpg",
				genres: ["platformer"],
			}),
		});
		expect(result).toEqual({
			publicId: "g1",
			slug: "celeste",
			title: "Celeste",
			metadataSource: "manual",
			createdAt: "2024-01-01",
		});
	});
});

describe("fetchGameGenres", () => {
	it("calls GET /v1/games/genres and returns raw string array", async () => {
		const genres = ["RPG", "Action", "Adventure"];
		mockApiFetch.mockResolvedValueOnce(genres);

		const result = await fetchGameGenres();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/games/genres");
		expect(result).toEqual(genres);
	});
});

// ---------------------------------------------------------------------------
// Library entries
// ---------------------------------------------------------------------------

describe("fetchLibrary", () => {
	it("calls GET /v1/library with no params when none given", async () => {
		const apiResponse = { items: [], total: 0, limit: 20, offset: 0 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchLibrary();

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/library");
		expect(result).toEqual(apiResponse);
	});

	it("appends query params for status, limit, offset", async () => {
		const apiResponse = { items: [], total: 0, limit: 10, offset: 5 };
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		await fetchLibrary({ status: "playing", limit: 10, offset: 5 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("status=playing");
		expect(calledPath).toContain("limit=10");
		expect(calledPath).toContain("offset=5");
	});

	it("converts a grouped snake_case response to camelCase", async () => {
		const apiResponse = {
			items: [
				{
					game: {
						public_id: "g1",
						title: "Hades",
						slug: "hades",
						metadata_source: "igdb",
						created_at: "2024-01-01",
					},
					platforms: [
						{
							public_id: "le1",
							platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
							status: "playing",
							last_played_at: "2024-06-01",
							created_at: "2024-01-01",
							updated_at: "2024-06-01",
						},
						{
							public_id: "le2",
							platform: { id: 2, slug: "switch", label: "Switch", family: "console" },
							status: "backlog",
							last_played_at: null,
							created_at: "2024-01-01",
							updated_at: "2024-06-01",
						},
					],
				},
			],
			total: 1,
			limit: 20,
			offset: 0,
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await fetchLibrary();

		expect(result.items[0].game.publicId).toBe("g1");
		expect(result.items[0].game.metadataSource).toBe("igdb");
		expect(result.items[0].platforms).toHaveLength(2);
		expect(result.items[0].platforms[0].publicId).toBe("le1");
		expect(result.items[0].platforms[0].lastPlayedAt).toBe("2024-06-01");
		expect(result.items[0].platforms[1].publicId).toBe("le2");
		expect(result.items[0].platforms[1].platform.slug).toBe("switch");
	});

	it("handles offset=0 correctly (falsy but valid)", async () => {
		mockApiFetch.mockResolvedValueOnce({ items: [], total: 0, limit: 20, offset: 0 });

		await fetchLibrary({ offset: 0 });

		const calledPath = mockApiFetch.mock.calls[0][0] as string;
		expect(calledPath).toContain("offset=0");
	});
});

describe("addToLibrary", () => {
	it("calls POST /v1/library with snake_cased body and returns a grouped game", async () => {
		const apiResponse = {
			game: {
				public_id: "g1",
				title: "Hades",
				slug: "hades",
				metadata_source: "igdb",
				created_at: "2024-01-01",
			},
			platforms: [
				{
					public_id: "le1",
					platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
					status: "backlog",
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				},
				{
					public_id: "le2",
					platform: { id: 2, slug: "switch", label: "Switch", family: "console" },
					status: "backlog",
					created_at: "2024-01-01",
					updated_at: "2024-01-01",
				},
			],
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await addToLibrary({
			gamePublicId: "g1",
			platformIds: [1, 2],
			status: "backlog",
		});

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/library", {
			method: "POST",
			body: JSON.stringify({
				game_public_id: "g1",
				platform_ids: [1, 2],
				status: "backlog",
			}),
		});
		expect(result.game.publicId).toBe("g1");
		expect(result.platforms).toHaveLength(2);
		expect(result.platforms[0].publicId).toBe("le1");
		expect(result.platforms[1].platform.slug).toBe("switch");
	});
});

describe("updateEntry", () => {
	it("calls PATCH /v1/library/:publicId with snake_cased body", async () => {
		const apiResponse = {
			public_id: "le1",
			game: {
				public_id: "g1",
				title: "Hades",
				slug: "hades",
				metadata_source: "igdb",
				created_at: "2024-01-01",
			},
			platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
			status: "completed",
			created_at: "2024-01-01",
			updated_at: "2024-06-01",
		};
		mockApiFetch.mockResolvedValueOnce(apiResponse);

		const result = await updateEntry("le1", { status: "completed", notes: "Great game" });

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/library/le1", {
			method: "PATCH",
			body: JSON.stringify({ status: "completed", notes: "Great game" }),
		});
		expect(result.status).toBe("completed");
	});
});

describe("deleteEntry", () => {
	it("calls DELETE /v1/library/:publicId", async () => {
		mockApiFetch.mockResolvedValueOnce(undefined);

		await deleteEntry("le1");

		expect(mockApiFetch).toHaveBeenCalledWith("/v1/library/le1", { method: "DELETE" });
	});
});
