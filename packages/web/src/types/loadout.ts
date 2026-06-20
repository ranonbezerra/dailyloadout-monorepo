// ---------------------------------------------------------------------------
// Loadout domain types (camelCase for TS, API returns snake_case)
// ---------------------------------------------------------------------------

import type { LibraryEntry } from "./library";

export type LoadoutMood = "chill" | "focused" | "energetic" | "adventurous";
export type MentalEnergy = "low" | "medium" | "high";
export type LoadoutAction = "accepted" | "rejected" | "ignored";

export interface Loadout {
	publicId: string;
	libraryEntry: LibraryEntry | null;
	mood: LoadoutMood;
	availableMinutes: number;
	mentalEnergy: MentalEnergy;
	context: string | null;
	reasoning: string | null;
	action: LoadoutAction | null;
	createdAt: string;
	updatedAt: string;
}

export interface LoadoutListItem {
	publicId: string;
	libraryEntry: LibraryEntry | null;
	mood: LoadoutMood;
	availableMinutes: number;
	mentalEnergy: MentalEnergy;
	context: string | null;
	reasoning: string | null;
	action: LoadoutAction | null;
	createdAt: string;
}

export interface LoadoutListResponse {
	items: LoadoutListItem[];
	total: number;
}
