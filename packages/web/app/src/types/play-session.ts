// ---------------------------------------------------------------------------
// PlaySession domain types (camelCase for TS, API returns snake_case)
// ---------------------------------------------------------------------------

import type { LibraryEntry } from "./library";

export type EndedVia = "wrap_up_completed" | "paused_app" | "auto_clamp" | "retroactive";

export type PlaySessionType = "regular" | "retroactive";

export interface SessionContext {
	location?: string | null;
	nextAction?: string | null;
	level?: string | null;
	currentQuest?: string | null;
}

export interface PlaySession {
	publicId: string;
	libraryEntry: LibraryEntry;
	playSessionType: PlaySessionType;
	recapText: string | null;
	wrapUpText: string | null;
	extractedState: Record<string, unknown> | null;
	endedVia: EndedVia | null;
	startedAt: string;
	endedAt: string | null;
	createdAt: string;
	updatedAt: string;
	lastSessionContext: SessionContext | null;
}

export interface PlaySessionListItem {
	publicId: string;
	libraryEntry: LibraryEntry;
	playSessionType: PlaySessionType;
	endedVia: EndedVia | null;
	startedAt: string;
	endedAt: string | null;
}

export interface PlaySessionListResponse {
	items: PlaySessionListItem[];
	total: number;
}

export interface RecapPreview {
	libraryEntry: LibraryEntry;
	recapText: string | null;
	lastSessionContext: SessionContext | null;
}
