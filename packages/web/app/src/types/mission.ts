// ---------------------------------------------------------------------------
// Mission domain types (camelCase for TS, API returns snake_case)
// ---------------------------------------------------------------------------

import type { LibraryEntry } from "./library";

export type EndedVia = "debrief_completed" | "paused_app" | "auto_clamp" | "retroactive";

export type MissionType = "regular" | "retroactive";

export interface SessionContext {
	location?: string | null;
	nextAction?: string | null;
	level?: string | null;
	currentQuest?: string | null;
}

export interface Mission {
	publicId: string;
	libraryEntry: LibraryEntry;
	missionType: MissionType;
	briefingText: string | null;
	debriefText: string | null;
	extractedState: Record<string, unknown> | null;
	endedVia: EndedVia | null;
	startedAt: string;
	endedAt: string | null;
	createdAt: string;
	updatedAt: string;
	lastSessionContext: SessionContext | null;
}

export interface MissionListItem {
	publicId: string;
	libraryEntry: LibraryEntry;
	missionType: MissionType;
	endedVia: EndedVia | null;
	startedAt: string;
	endedAt: string | null;
}

export interface MissionListResponse {
	items: MissionListItem[];
	total: number;
}

export interface BriefingPreview {
	libraryEntry: LibraryEntry;
	briefingText: string | null;
	lastSessionContext: SessionContext | null;
}
