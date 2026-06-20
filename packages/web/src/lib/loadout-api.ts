import type { Loadout, LoadoutListResponse, LoadoutMood, MentalEnergy } from "../types/loadout";
import { apiFetch } from "./api";

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
// Create loadout
// ---------------------------------------------------------------------------

export async function createLoadout(
	mood: LoadoutMood,
	availableMinutes: number,
	mentalEnergy: MentalEnergy,
	count = 1,
	context?: string,
): Promise<Loadout[]> {
	const raw = await apiFetch<unknown>("/v1/loadouts", {
		method: "POST",
		body: JSON.stringify({
			mood,
			available_minutes: availableMinutes,
			mental_energy: mentalEnergy,
			context: context || null,
			count,
		}),
	});
	return snakeToCamel<Loadout[]>(raw);
}

// ---------------------------------------------------------------------------
// Accept loadout
// ---------------------------------------------------------------------------

export async function acceptLoadout(publicId: string): Promise<Loadout> {
	const raw = await apiFetch<unknown>(`/v1/loadouts/${publicId}/accept`, {
		method: "POST",
	});
	return snakeToCamel<Loadout>(raw);
}

// ---------------------------------------------------------------------------
// Reject loadout
// ---------------------------------------------------------------------------

export async function rejectLoadout(publicId: string): Promise<Loadout> {
	const raw = await apiFetch<unknown>(`/v1/loadouts/${publicId}/reject`, {
		method: "POST",
	});
	return snakeToCamel<Loadout>(raw);
}

// ---------------------------------------------------------------------------
// List loadouts
// ---------------------------------------------------------------------------

export async function listLoadouts(params?: {
	limit?: number;
	offset?: number;
}): Promise<LoadoutListResponse> {
	const searchParams = new URLSearchParams();
	if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
	if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

	const qs = searchParams.toString();
	const path = qs ? `/v1/loadouts?${qs}` : "/v1/loadouts";

	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<LoadoutListResponse>(raw);
}

// ---------------------------------------------------------------------------
// Latest pending loadout
// ---------------------------------------------------------------------------

export async function getLatestLoadout(): Promise<Loadout | null> {
	const raw = await apiFetch<unknown>("/v1/loadouts/latest");
	if (raw === null) return null;
	return snakeToCamel<Loadout>(raw);
}
