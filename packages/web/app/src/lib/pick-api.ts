import { apiFetch } from "@slate/shared/api";
import { snakeToCamel } from "@slate/shared/case-convert";
import type { MentalEnergy, Pick, PickListResponse, PickMood } from "../types/pick";

// ---------------------------------------------------------------------------
// Create pick
// ---------------------------------------------------------------------------

export async function createPick(
	mood: PickMood,
	availableMinutes: number,
	mentalEnergy: MentalEnergy,
	count = 1,
	context?: string,
): Promise<Pick[]> {
	const raw = await apiFetch<unknown>("/v1/picks", {
		method: "POST",
		body: JSON.stringify({
			mood,
			available_minutes: availableMinutes,
			mental_energy: mentalEnergy,
			context: context || null,
			count,
		}),
	});
	return snakeToCamel<Pick[]>(raw);
}

// ---------------------------------------------------------------------------
// Accept pick
// ---------------------------------------------------------------------------

export async function acceptPick(publicId: string, recapText?: string): Promise<Pick> {
	const raw = await apiFetch<unknown>(`/v1/picks/${publicId}/accept`, {
		method: "POST",
		body: recapText ? JSON.stringify({ recap_text: recapText }) : undefined,
	});
	return snakeToCamel<Pick>(raw);
}

// ---------------------------------------------------------------------------
// Reject pick
// ---------------------------------------------------------------------------

export async function rejectPick(publicId: string): Promise<Pick> {
	const raw = await apiFetch<unknown>(`/v1/picks/${publicId}/reject`, {
		method: "POST",
	});
	return snakeToCamel<Pick>(raw);
}

// ---------------------------------------------------------------------------
// List picks
// ---------------------------------------------------------------------------

export async function listPicks(params?: {
	limit?: number;
	offset?: number;
}): Promise<PickListResponse> {
	const searchParams = new URLSearchParams();
	if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
	if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

	const qs = searchParams.toString();
	const path = qs ? `/v1/picks?${qs}` : "/v1/picks";

	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<PickListResponse>(raw);
}

// ---------------------------------------------------------------------------
// Latest pending pick
// ---------------------------------------------------------------------------

export async function getLatestPick(): Promise<Pick | null> {
	const raw = await apiFetch<unknown>("/v1/picks/latest");
	if (raw === null) return null;
	return snakeToCamel<Pick>(raw);
}
