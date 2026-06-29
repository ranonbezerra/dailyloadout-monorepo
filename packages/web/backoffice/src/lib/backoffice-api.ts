/**
 * Backoffice (Epic 21) API client. Every call hits the admin-only `/internal/v1`
 * surface through the shared `apiFetch` (bearer auth + silent refresh). Responses
 * are snake_case → converted to camelCase; the few request bodies are simple
 * enough to send as-is.
 */

import { apiFetch } from "@slate/shared/api";
import { snakeToCamel } from "@slate/shared/case-convert";
import type {
	AdminCaptureDetail,
	AdminCaptureList,
	AdminGameDetail,
	AdminGameList,
	AdminMe,
	AdminPickDetail,
	AdminPickList,
	AdminPlaySessionDetail,
	AdminPlaySessionList,
	AdminUserDetail,
	AdminUserList,
	AuditList,
	CaptureListParams,
	ConfigList,
	ConfigValue,
	DashboardSummary,
	GameEdit,
	GameListParams,
	PickListParams,
	PlaySessionListParams,
	UserListParams,
} from "../types/backoffice";

const BASE = "/internal/v1";

/** Confirm the current session holds admin rights (403 otherwise). */
export async function fetchAdminMe(): Promise<AdminMe> {
	return snakeToCamel<AdminMe>(await apiFetch<unknown>(`${BASE}/me`));
}

export async function fetchDashboard(): Promise<DashboardSummary> {
	return snakeToCamel<DashboardSummary>(await apiFetch<unknown>(`${BASE}/dashboard`));
}

export async function fetchUsers(params: UserListParams = {}): Promise<AdminUserList> {
	const sp = new URLSearchParams();
	if (params.q) sp.set("q", params.q);
	if (params.banned !== undefined) sp.set("banned", String(params.banned));
	if (params.verified !== undefined) sp.set("verified", String(params.verified));
	if (params.limit !== undefined) sp.set("limit", String(params.limit));
	if (params.offset !== undefined) sp.set("offset", String(params.offset));
	const qs = sp.toString();
	return snakeToCamel<AdminUserList>(
		await apiFetch<unknown>(`${BASE}/users${qs ? `?${qs}` : ""}`),
	);
}

export async function fetchUser(publicId: string): Promise<AdminUserDetail> {
	return snakeToCamel<AdminUserDetail>(await apiFetch<unknown>(`${BASE}/users/${publicId}`));
}

export async function banUser(publicId: string, reason?: string): Promise<AdminUserDetail> {
	return snakeToCamel<AdminUserDetail>(
		await apiFetch<unknown>(`${BASE}/users/${publicId}/ban`, {
			method: "POST",
			body: JSON.stringify({ reason: reason ?? null }),
		}),
	);
}

export async function unbanUser(publicId: string): Promise<AdminUserDetail> {
	return snakeToCamel<AdminUserDetail>(
		await apiFetch<unknown>(`${BASE}/users/${publicId}/unban`, { method: "POST" }),
	);
}

export async function verifyUser(publicId: string): Promise<AdminUserDetail> {
	return snakeToCamel<AdminUserDetail>(
		await apiFetch<unknown>(`${BASE}/users/${publicId}/verify`, { method: "POST" }),
	);
}

export async function fetchConfig(): Promise<ConfigList> {
	return snakeToCamel<ConfigList>(await apiFetch<unknown>(`${BASE}/config`));
}

export async function setConfig(key: string, value: ConfigValue): Promise<ConfigList> {
	return snakeToCamel<ConfigList>(
		await apiFetch<unknown>(`${BASE}/config/${key}`, {
			method: "PUT",
			body: JSON.stringify({ value }),
		}),
	);
}

export async function clearConfig(key: string): Promise<ConfigList> {
	return snakeToCamel<ConfigList>(
		await apiFetch<unknown>(`${BASE}/config/${key}`, { method: "DELETE" }),
	);
}

export async function fetchGames(params: GameListParams = {}): Promise<AdminGameList> {
	const sp = new URLSearchParams();
	if (params.q) sp.set("q", params.q);
	if (params.shared !== undefined) sp.set("shared", String(params.shared));
	if (params.source) sp.set("source", params.source);
	if (params.limit !== undefined) sp.set("limit", String(params.limit));
	if (params.offset !== undefined) sp.set("offset", String(params.offset));
	const qs = sp.toString();
	return snakeToCamel<AdminGameList>(
		await apiFetch<unknown>(`${BASE}/games${qs ? `?${qs}` : ""}`),
	);
}

export async function demoteGame(publicId: string): Promise<AdminGameDetail> {
	return snakeToCamel<AdminGameDetail>(
		await apiFetch<unknown>(`${BASE}/games/${publicId}/demote`, { method: "POST" }),
	);
}

export async function promoteGame(publicId: string): Promise<AdminGameDetail> {
	return snakeToCamel<AdminGameDetail>(
		await apiFetch<unknown>(`${BASE}/games/${publicId}/promote`, { method: "POST" }),
	);
}

export async function editGame(publicId: string, edit: GameEdit): Promise<AdminGameDetail> {
	return snakeToCamel<AdminGameDetail>(
		await apiFetch<unknown>(`${BASE}/games/${publicId}`, {
			method: "PATCH",
			body: JSON.stringify(edit),
		}),
	);
}

export async function fetchCaptures(params: CaptureListParams = {}): Promise<AdminCaptureList> {
	const sp = new URLSearchParams();
	if (params.q) sp.set("q", params.q);
	if (params.status) sp.set("status", params.status);
	if (params.limit !== undefined) sp.set("limit", String(params.limit));
	if (params.offset !== undefined) sp.set("offset", String(params.offset));
	const qs = sp.toString();
	return snakeToCamel<AdminCaptureList>(
		await apiFetch<unknown>(`${BASE}/captures${qs ? `?${qs}` : ""}`),
	);
}

export async function fetchCapture(publicId: string): Promise<AdminCaptureDetail> {
	return snakeToCamel<AdminCaptureDetail>(await apiFetch<unknown>(`${BASE}/captures/${publicId}`));
}

export async function reprocessCapture(publicId: string): Promise<AdminCaptureDetail> {
	return snakeToCamel<AdminCaptureDetail>(
		await apiFetch<unknown>(`${BASE}/captures/${publicId}/reprocess`, { method: "POST" }),
	);
}

export async function purgeCapture(publicId: string): Promise<void> {
	await apiFetch<void>(`${BASE}/captures/${publicId}`, { method: "DELETE" });
}

export async function fetchPlaySessions(
	params: PlaySessionListParams = {},
): Promise<AdminPlaySessionList> {
	const sp = new URLSearchParams();
	if (params.q) sp.set("q", params.q);
	if (params.status) sp.set("status", params.status);
	if (params.limit !== undefined) sp.set("limit", String(params.limit));
	if (params.offset !== undefined) sp.set("offset", String(params.offset));
	const qs = sp.toString();
	return snakeToCamel<AdminPlaySessionList>(
		await apiFetch<unknown>(`${BASE}/play-sessions${qs ? `?${qs}` : ""}`),
	);
}

export async function fetchPlaySession(publicId: string): Promise<AdminPlaySessionDetail> {
	return snakeToCamel<AdminPlaySessionDetail>(
		await apiFetch<unknown>(`${BASE}/play-sessions/${publicId}`),
	);
}

export async function clampPlaySession(publicId: string): Promise<AdminPlaySessionDetail> {
	return snakeToCamel<AdminPlaySessionDetail>(
		await apiFetch<unknown>(`${BASE}/play-sessions/${publicId}/clamp`, { method: "POST" }),
	);
}

export async function fetchPicks(params: PickListParams = {}): Promise<AdminPickList> {
	const sp = new URLSearchParams();
	if (params.q) sp.set("q", params.q);
	if (params.action) sp.set("action", params.action);
	if (params.limit !== undefined) sp.set("limit", String(params.limit));
	if (params.offset !== undefined) sp.set("offset", String(params.offset));
	const qs = sp.toString();
	return snakeToCamel<AdminPickList>(
		await apiFetch<unknown>(`${BASE}/picks${qs ? `?${qs}` : ""}`),
	);
}

export async function fetchPick(publicId: string): Promise<AdminPickDetail> {
	return snakeToCamel<AdminPickDetail>(await apiFetch<unknown>(`${BASE}/picks/${publicId}`));
}

export async function fetchAudit(
	params: { limit?: number; offset?: number } = {},
): Promise<AuditList> {
	const sp = new URLSearchParams();
	if (params.limit !== undefined) sp.set("limit", String(params.limit));
	if (params.offset !== undefined) sp.set("offset", String(params.offset));
	const qs = sp.toString();
	return snakeToCamel<AuditList>(await apiFetch<unknown>(`${BASE}/audit${qs ? `?${qs}` : ""}`));
}
