import { apiFetch } from "@dl/shared/api";
import { camelToSnake, snakeToCamel } from "@dl/shared/case-convert";
import type {
	Game,
	GameCreate,
	LibraryEntry,
	LibraryEntryCreate,
	LibraryEntryUpdate,
	LibraryGameGroup,
	LibraryListResponse,
	Platform,
} from "../types/library";

// ---------------------------------------------------------------------------
// Platforms
// ---------------------------------------------------------------------------

export async function fetchPlatforms(): Promise<Platform[]> {
	const raw = await apiFetch<unknown>("/v1/platforms");
	return snakeToCamel<Platform[]>(raw);
}

// ---------------------------------------------------------------------------
// Games
// ---------------------------------------------------------------------------

export async function searchGames(query: string, limit = 20): Promise<Game[]> {
	const params = new URLSearchParams({ q: query, limit: String(limit) });
	const raw = await apiFetch<unknown>(`/v1/games/search?${params}`);
	return snakeToCamel<Game[]>(raw);
}

export async function createGame(data: GameCreate): Promise<Game> {
	const raw = await apiFetch<unknown>("/v1/games", {
		method: "POST",
		body: JSON.stringify(camelToSnake(data as unknown as Record<string, unknown>)),
	});
	return snakeToCamel<Game>(raw);
}

export async function fetchGameGenres(): Promise<string[]> {
	return apiFetch<string[]>("/v1/games/genres");
}

// ---------------------------------------------------------------------------
// Library entries
// ---------------------------------------------------------------------------

export async function fetchLibrary(params?: {
	status?: string;
	limit?: number;
	offset?: number;
}): Promise<LibraryListResponse> {
	const searchParams = new URLSearchParams();
	if (params?.status) searchParams.set("status", params.status);
	if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
	if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

	const qs = searchParams.toString();
	const path = qs ? `/v1/library?${qs}` : "/v1/library";

	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<LibraryListResponse>(raw);
}

export async function fetchLibraryEntry(publicId: string): Promise<LibraryEntry> {
	const raw = await apiFetch<unknown>(`/v1/library/${publicId}`);
	return snakeToCamel<LibraryEntry>(raw);
}

export async function addToLibrary(data: LibraryEntryCreate): Promise<LibraryGameGroup> {
	const raw = await apiFetch<unknown>("/v1/library", {
		method: "POST",
		body: JSON.stringify(camelToSnake(data as unknown as Record<string, unknown>)),
	});
	return snakeToCamel<LibraryGameGroup>(raw);
}

export async function updateEntry(
	publicId: string,
	data: LibraryEntryUpdate,
): Promise<LibraryEntry> {
	const raw = await apiFetch<unknown>(`/v1/library/${publicId}`, {
		method: "PATCH",
		body: JSON.stringify(camelToSnake(data as unknown as Record<string, unknown>)),
	});
	return snakeToCamel<LibraryEntry>(raw);
}

export async function deleteEntry(publicId: string): Promise<void> {
	await apiFetch<void>(`/v1/library/${publicId}`, { method: "DELETE" });
}
