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

const mockPlatforms = [
	{ id: 1, slug: "pc", label: "PC", family: "computer" },
	{ id: 2, slug: "ps5", label: "PlayStation 5", family: "playstation" },
];

const mockGames = [
	{
		publicId: "game-1",
		slug: "elden-ring",
		title: "Elden Ring",
		igdbId: 1234,
		summary: "An action RPG",
		coverUrl: "https://example.com/cover.jpg",
		firstReleaseDate: "2022-02-25",
		genres: ["Action", "RPG"],
		metadataSource: "igdb",
		createdAt: "2024-01-01T00:00:00Z",
	},
];

const mockGenres = ["Action", "RPG", "Adventure", "Puzzle"];

const mockPlatformState = {
	publicId: "entry-1",
	platform: mockPlatforms[0],
	status: "playing" as const,
	acquiredAt: null,
	lastPlayedAt: "2024-06-01T00:00:00Z",
	missionNextAction: null,
	notes: null,
	createdAt: "2024-01-01T00:00:00Z",
	updatedAt: "2024-06-01T00:00:00Z",
};

const mockLibraryEntry = {
	...mockPlatformState,
	game: mockGames[0],
};

const mockGameGroup = {
	game: mockGames[0],
	platforms: [mockPlatformState],
};

const mockLibraryResponse = {
	items: [mockGameGroup],
	total: 1,
	limit: 50,
	offset: 0,
};

vi.mock("../lib/library-api", () => ({
	fetchPlatforms: vi.fn(() => Promise.resolve(mockPlatforms)),
	searchGames: vi.fn(() => Promise.resolve(mockGames)),
	fetchGameGenres: vi.fn(() => Promise.resolve(mockGenres)),
	fetchLibrary: vi.fn(() => Promise.resolve(mockLibraryResponse)),
	addToLibrary: vi.fn(() => Promise.resolve(mockGameGroup)),
	updateEntry: vi.fn(() => Promise.resolve(mockLibraryEntry)),
	deleteEntry: vi.fn(() => Promise.resolve(undefined)),
	createGame: vi.fn(() => Promise.resolve(mockGames[0])),
}));

import {
	addToLibrary,
	createGame,
	deleteEntry,
	fetchGameGenres,
	fetchLibrary,
	fetchPlatforms,
	searchGames,
	updateEntry,
} from "../lib/library-api";
import {
	useAddToLibrary,
	useCreateGame,
	useDeleteEntry,
	useGameGenres,
	useLibrary,
	usePlatforms,
	useSearchGames,
	useUpdateEntry,
} from "./useLibrary";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("usePlatforms", () => {
	it("returns platform data after the query resolves", async () => {
		const { result } = renderHook(() => usePlatforms(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchPlatforms).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockPlatforms);
	});
});

describe("useSearchGames", () => {
	it("is disabled when query is shorter than 2 characters", () => {
		const { result } = renderHook(() => useSearchGames("a"), {
			wrapper: createWrapper(),
		});

		expect(result.current.fetchStatus).toBe("idle");
		expect(searchGames).not.toHaveBeenCalled();
	});

	it("fetches games when query is at least 2 characters", async () => {
		const { result } = renderHook(() => useSearchGames("el"), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(searchGames).toHaveBeenCalledWith("el");
		expect(result.current.data).toEqual(mockGames);
	});
});

describe("useGameGenres", () => {
	it("returns genre list after the query resolves", async () => {
		const { result } = renderHook(() => useGameGenres(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchGameGenres).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockGenres);
	});
});

describe("useLibrary", () => {
	it("returns library entries without params", async () => {
		const { result } = renderHook(() => useLibrary(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchLibrary).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockLibraryResponse);
	});

	it("passes params to fetchLibrary", async () => {
		const params = { status: "playing", limit: 10, offset: 0 };
		const { result } = renderHook(() => useLibrary(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(fetchLibrary).toHaveBeenCalledWith(params);
	});
});

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

describe("useAddToLibrary", () => {
	it("calls addToLibrary with the correct payload", async () => {
		const { result } = renderHook(() => useAddToLibrary(), {
			wrapper: createWrapper(),
		});

		const payload = { gamePublicId: "game-1", platformIds: [1, 2], status: "backlog" as const };
		await result.current.mutateAsync(payload);

		expect(addToLibrary).toHaveBeenCalledWith(payload);
	});
});

describe("useUpdateEntry", () => {
	it("calls updateEntry with publicId and data", async () => {
		const { result } = renderHook(() => useUpdateEntry(), {
			wrapper: createWrapper(),
		});

		const vars = { publicId: "entry-1", data: { status: "completed" as const } };
		await result.current.mutateAsync(vars);

		expect(updateEntry).toHaveBeenCalledWith("entry-1", { status: "completed" });
	});
});

describe("useDeleteEntry", () => {
	it("calls deleteEntry with the publicId", async () => {
		const { result } = renderHook(() => useDeleteEntry(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync("entry-1");

		expect(deleteEntry).toHaveBeenCalledWith("entry-1");
	});
});

describe("useCreateGame", () => {
	it("calls createGame with the game payload", async () => {
		const { result } = renderHook(() => useCreateGame(), {
			wrapper: createWrapper(),
		});

		const payload = { slug: "new-game", title: "New Game", genres: ["Action"] };
		await result.current.mutateAsync(payload);

		expect(createGame).toHaveBeenCalledWith(payload);
	});
});
