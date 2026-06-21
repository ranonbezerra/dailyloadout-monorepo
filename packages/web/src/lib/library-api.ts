import type {
	Game,
	GameCreate,
	LibraryEntry,
	LibraryEntryCreate,
	LibraryEntryUpdate,
	LibraryListResponse,
	Platform,
} from "../types/library";
import { apiFetch, BASE_URL, getAccessToken } from "./api";
import { camelToSnake, snakeToCamel } from "./case-convert";

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

export async function addToLibrary(data: LibraryEntryCreate): Promise<LibraryEntry> {
	const raw = await apiFetch<unknown>("/v1/library", {
		method: "POST",
		body: JSON.stringify(camelToSnake(data as unknown as Record<string, unknown>)),
	});
	return snakeToCamel<LibraryEntry>(raw);
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
	// The API returns 204 No Content. apiFetch always calls res.json() which
	// would fail on an empty body, so we use fetch directly for this endpoint.
	const headers: Record<string, string> = {};
	const accessToken = getAccessToken();
	if (accessToken) {
		headers.Authorization = `Bearer ${accessToken}`;
	}

	const res = await fetch(`${BASE_URL}/v1/library/${publicId}`, {
		method: "DELETE",
		headers,
	});

	if (!res.ok) {
		const errBody = await res.text();
		throw new Error(errBody || `Request failed: ${res.status}`);
	}
}
