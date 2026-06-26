// ---------------------------------------------------------------------------
// Library domain types (camelCase for TS, API returns snake_case)
// ---------------------------------------------------------------------------

export type LibraryStatus = "backlog" | "playing" | "paused" | "completed" | "dropped";

export interface Platform {
	id: number;
	slug: string;
	label: string;
	family: string;
}

export interface Game {
	publicId: string;
	slug: string;
	title: string;
	igdbId?: number | null;
	summary?: string | null;
	coverUrl?: string | null;
	firstReleaseDate?: string | null;
	genres?: string[] | null;
	metadataSource: string;
	createdAt: string;
}

/**
 * A single platform's library entry for a game. This is the unit that the API
 * lets you update/delete/start-a-mission for — its `publicId` is the library
 * ENTRY id, used to target this specific platform.
 */
export interface LibraryEntry {
	publicId: string;
	game: Game;
	platform: Platform;
	status: LibraryStatus;
	acquiredAt?: string | null;
	lastPlayedAt?: string | null;
	missionNextAction?: string | null;
	notes?: string | null;
	createdAt: string;
	updatedAt: string;
}

/**
 * Per-platform state inside a grouped library game. Mirrors a single library
 * entry minus the game (which lives on the parent group). `publicId` is the
 * library ENTRY id — use it to target this platform for update/delete/mission.
 */
export interface LibraryPlatformState {
	publicId: string;
	platform: Platform;
	status: LibraryStatus;
	acquiredAt?: string | null;
	lastPlayedAt?: string | null;
	missionNextAction?: string | null;
	notes?: string | null;
	createdAt: string;
	updatedAt: string;
}

/**
 * A game owned on one or more platforms, grouped into a single row by the API.
 * The frontend renders this as-is — it must NOT group or aggregate anything.
 */
export interface LibraryGameGroup {
	game: Game;
	platforms: LibraryPlatformState[];
}

export interface LibraryListResponse {
	/** Distinct games (pagination is by game). */
	items: LibraryGameGroup[];
	total: number;
	limit: number;
	offset: number;
}

// ---------------------------------------------------------------------------
// Request payloads (sent as snake_case to API)
// ---------------------------------------------------------------------------

export interface LibraryEntryCreate {
	gamePublicId: string;
	platformIds: number[];
	status?: LibraryStatus;
	notes?: string;
	acquiredAt?: string;
}

export interface LibraryEntryUpdate {
	status?: LibraryStatus;
	notes?: string;
}

export interface GameCreate {
	slug: string;
	title: string;
	summary?: string;
	coverUrl?: string;
	genres?: string[];
}
