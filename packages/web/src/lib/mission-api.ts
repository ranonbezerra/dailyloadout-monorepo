import type { BriefingPreview, Mission, MissionListResponse } from "../types/mission";
import { apiFetch } from "./api";

// ---------------------------------------------------------------------------
// snake_case -> camelCase conversion (same pattern as capture-api.ts)
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
// Preview briefing (before starting a mission)
// ---------------------------------------------------------------------------

export async function previewBriefing(
	libraryEntryPublicId: string,
	positionOverride?: string,
): Promise<BriefingPreview> {
	const body: Record<string, string> = { library_entry_public_id: libraryEntryPublicId };
	if (positionOverride) body.position_override = positionOverride;
	const raw = await apiFetch<unknown>("/v1/missions/preview-briefing", {
		method: "POST",
		body: JSON.stringify(body),
	});
	return snakeToCamel<BriefingPreview>(raw);
}

// ---------------------------------------------------------------------------
// Retroactive debrief (unregistered play session)
// ---------------------------------------------------------------------------

export async function submitRetroactiveDebrief(
	libraryEntryPublicId: string,
	debriefText: string,
): Promise<BriefingPreview> {
	const raw = await apiFetch<unknown>("/v1/missions/retroactive-debrief", {
		method: "POST",
		body: JSON.stringify({
			library_entry_public_id: libraryEntryPublicId,
			debrief_text: debriefText,
		}),
	});
	return snakeToCamel<BriefingPreview>(raw);
}

// ---------------------------------------------------------------------------
// Start mission
// ---------------------------------------------------------------------------

export async function startMission(
	libraryEntryPublicId: string,
	briefingText?: string,
): Promise<Mission> {
	const body: Record<string, string> = { library_entry_public_id: libraryEntryPublicId };
	if (briefingText) body.briefing_text = briefingText;
	const raw = await apiFetch<unknown>("/v1/missions", {
		method: "POST",
		body: JSON.stringify(body),
	});
	return snakeToCamel<Mission>(raw);
}

// ---------------------------------------------------------------------------
// Active mission
// ---------------------------------------------------------------------------

export async function getActiveMission(): Promise<Mission | null> {
	const raw = await apiFetch<unknown>("/v1/missions/active");
	if (raw === null) return null;
	return snakeToCamel<Mission>(raw);
}

// ---------------------------------------------------------------------------
// Mission detail
// ---------------------------------------------------------------------------

export async function getMission(publicId: string): Promise<Mission> {
	const raw = await apiFetch<unknown>(`/v1/missions/${publicId}`);
	return snakeToCamel<Mission>(raw);
}

// ---------------------------------------------------------------------------
// List missions
// ---------------------------------------------------------------------------

export async function listMissions(params?: {
	limit?: number;
	offset?: number;
}): Promise<MissionListResponse> {
	const searchParams = new URLSearchParams();
	if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
	if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

	const qs = searchParams.toString();
	const path = qs ? `/v1/missions?${qs}` : "/v1/missions";

	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<MissionListResponse>(raw);
}

// ---------------------------------------------------------------------------
// Submit debrief
// ---------------------------------------------------------------------------

export async function submitDebrief(publicId: string, debriefText: string): Promise<Mission> {
	const raw = await apiFetch<unknown>(`/v1/missions/${publicId}/debrief`, {
		method: "PATCH",
		body: JSON.stringify({ debrief_text: debriefText }),
	});
	return snakeToCamel<Mission>(raw);
}

// ---------------------------------------------------------------------------
// End mission (no debrief)
// ---------------------------------------------------------------------------

export async function endMission(publicId: string, endedVia = "paused_app"): Promise<Mission> {
	const raw = await apiFetch<unknown>(`/v1/missions/${publicId}/end`, {
		method: "POST",
		body: JSON.stringify({ ended_via: endedVia }),
	});
	return snakeToCamel<Mission>(raw);
}

// ---------------------------------------------------------------------------
// Regenerate briefing
// ---------------------------------------------------------------------------

export async function regenerateBriefing(
	publicId: string,
	currentPosition?: string,
): Promise<Mission> {
	const body = currentPosition ? JSON.stringify({ current_position: currentPosition }) : undefined;
	const raw = await apiFetch<unknown>(`/v1/missions/${publicId}/briefing/regenerate`, {
		method: "POST",
		body,
	});
	return snakeToCamel<Mission>(raw);
}
