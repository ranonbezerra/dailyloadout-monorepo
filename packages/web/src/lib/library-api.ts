import type {
	Game,
	GameCreate,
	LibraryEntry,
	LibraryEntryCreate,
	LibraryEntryUpdate,
	LibraryListResponse,
	Platform,
} from "../types/library";
import { apiFetch, getAccessToken } from "./api";

// ---------------------------------------------------------------------------
// snake_case -> camelCase conversion
// ---------------------------------------------------------------------------

function snakeToCamelKey(key: string): string {
	return key.replace(/_([a-z])/g, (_, char: string) => char.toUpperCase());
}

function snakeToCamel<T>(data: unknown): T {
	if (Array.isArray(data)) {
		return data.map((item) => snakeToCamel(item)) as T;
	}
	if (data !== null && typeof data === "object") {
		const converted: Record<string, unknown> = {};
		for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
			converted[snakeToCamelKey(key)] = snakeToCamel(value);
		}
		return converted as T;
	}
	return data as T;
}

// ---------------------------------------------------------------------------
// camelCase -> snake_case conversion (for request payloads)
// ---------------------------------------------------------------------------

function camelToSnakeKey(key: string): string {
	return key.replace(/[A-Z]/g, (char) => `_${char.toLowerCase()}`);
}

function camelToSnake(data: Record<string, unknown>): Record<string, unknown> {
	const converted: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(data)) {
		if (value !== undefined) {
			converted[camelToSnakeKey(key)] = value;
		}
	}
	return converted;
}

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

const BASE_URL =
	(typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) || "http://localhost:8100";

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
