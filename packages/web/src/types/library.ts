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

export interface LibraryListResponse {
	items: LibraryEntry[];
	total: number;
	limit: number;
	offset: number;
}

// ---------------------------------------------------------------------------
// Request payloads (sent as snake_case to API)
// ---------------------------------------------------------------------------

export interface LibraryEntryCreate {
	gamePublicId: string;
	platformId: number;
	status?: LibraryStatus;
	notes?: string;
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
