// ---------------------------------------------------------------------------
// Pick domain types (camelCase for TS, API returns snake_case)
// ---------------------------------------------------------------------------

import type { LibraryEntry } from "./library";

export type PickMood = "chill" | "focused" | "energetic" | "adventurous";
export type MentalEnergy = "low" | "medium" | "high";
export type PickAction = "accepted" | "rejected" | "ignored";

export interface Pick {
	publicId: string;
	libraryEntry: LibraryEntry | null;
	mood: PickMood;
	availableMinutes: number;
	mentalEnergy: MentalEnergy;
	context: string | null;
	reasoning: string | null;
	action: PickAction | null;
	createdAt: string;
	updatedAt: string;
}

export interface PickListItem {
	publicId: string;
	libraryEntry: LibraryEntry | null;
	mood: PickMood;
	availableMinutes: number;
	mentalEnergy: MentalEnergy;
	context: string | null;
	reasoning: string | null;
	action: PickAction | null;
	createdAt: string;
}

export interface PickListResponse {
	items: PickListItem[];
	total: number;
}
