import { apiFetch } from "@slate/shared/api";
import { snakeToCamel } from "@slate/shared/case-convert";
import type { PlaySession, PlaySessionListResponse, RecapPreview } from "../types/play-session";

// ---------------------------------------------------------------------------
// Preview recap (before starting a playSession)
// ---------------------------------------------------------------------------

export type RecapMode = "quick" | "deep" | "auto";

export async function previewRecap(
	libraryEntryPublicId: string,
	positionOverride?: string,
	mode: RecapMode = "quick",
	signal?: AbortSignal,
): Promise<RecapPreview> {
	const body: Record<string, string> = {
		library_entry_public_id: libraryEntryPublicId,
		mode,
	};
	if (positionOverride) body.position_override = positionOverride;
	const raw = await apiFetch<unknown>("/v1/play-sessions/preview-recap", {
		method: "POST",
		body: JSON.stringify(body),
		signal,
	});
	return snakeToCamel<RecapPreview>(raw);
}

// ---------------------------------------------------------------------------
// Retroactive wrapUp (unregistered play session)
// ---------------------------------------------------------------------------

export async function submitRetroactiveWrapUp(
	libraryEntryPublicId: string,
	wrapUpText: string,
): Promise<RecapPreview> {
	const raw = await apiFetch<unknown>("/v1/play-sessions/retroactive-wrap-up", {
		method: "POST",
		body: JSON.stringify({
			library_entry_public_id: libraryEntryPublicId,
			wrap_up_text: wrapUpText,
		}),
	});
	return snakeToCamel<RecapPreview>(raw);
}

// ---------------------------------------------------------------------------
// Start playSession
// ---------------------------------------------------------------------------

export async function startPlaySession(
	libraryEntryPublicId: string,
	recapText?: string,
	skipRecap?: boolean,
): Promise<PlaySession> {
	const body: Record<string, unknown> = { library_entry_public_id: libraryEntryPublicId };
	if (recapText) body.recap_text = recapText;
	if (skipRecap) body.skip_recap = true;
	const raw = await apiFetch<unknown>("/v1/play-sessions", {
		method: "POST",
		body: JSON.stringify(body),
	});
	return snakeToCamel<PlaySession>(raw);
}

// ---------------------------------------------------------------------------
// Active playSession
// ---------------------------------------------------------------------------

export async function getActivePlaySession(): Promise<PlaySession | null> {
	const raw = await apiFetch<unknown>("/v1/play-sessions/active");
	if (raw === null) return null;
	return snakeToCamel<PlaySession>(raw);
}

// ---------------------------------------------------------------------------
// PlaySession detail
// ---------------------------------------------------------------------------

export async function getPlaySession(publicId: string): Promise<PlaySession> {
	const raw = await apiFetch<unknown>(`/v1/play-sessions/${publicId}`);
	return snakeToCamel<PlaySession>(raw);
}

// ---------------------------------------------------------------------------
// List playSessions
// ---------------------------------------------------------------------------

export async function listPlaySessions(params?: {
	limit?: number;
	offset?: number;
}): Promise<PlaySessionListResponse> {
	const searchParams = new URLSearchParams();
	if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
	if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

	const qs = searchParams.toString();
	const path = qs ? `/v1/play-sessions?${qs}` : "/v1/play-sessions";

	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<PlaySessionListResponse>(raw);
}

// ---------------------------------------------------------------------------
// Submit wrapUp
// ---------------------------------------------------------------------------

export async function submitWrapUp(publicId: string, wrapUpText: string): Promise<PlaySession> {
	const raw = await apiFetch<unknown>(`/v1/play-sessions/${publicId}/wrap-up`, {
		method: "PATCH",
		body: JSON.stringify({ wrap_up_text: wrapUpText }),
	});
	return snakeToCamel<PlaySession>(raw);
}

// ---------------------------------------------------------------------------
// End session (no wrapUp)
// ---------------------------------------------------------------------------

export async function endPlaySession(
	publicId: string,
	endedVia = "paused_app",
): Promise<PlaySession> {
	const raw = await apiFetch<unknown>(`/v1/play-sessions/${publicId}/end`, {
		method: "POST",
		body: JSON.stringify({ ended_via: endedVia }),
	});
	return snakeToCamel<PlaySession>(raw);
}

// ---------------------------------------------------------------------------
// Regenerate recap
// ---------------------------------------------------------------------------

export async function regenerateRecap(
	publicId: string,
	currentPosition?: string,
): Promise<PlaySession> {
	const body = currentPosition ? JSON.stringify({ current_position: currentPosition }) : undefined;
	const raw = await apiFetch<unknown>(`/v1/play-sessions/${publicId}/recap/regenerate`, {
		method: "POST",
		body,
	});
	return snakeToCamel<PlaySession>(raw);
}
