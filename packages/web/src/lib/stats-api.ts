import type {
	GenreStats,
	PlatformStats,
	PlayHeatmap,
	StatsOverview,
	TimelineResponse,
} from "../types/stats";
import { apiFetch } from "./api";
import { snakeToCamel } from "./case-convert";

export async function fetchOverview(): Promise<StatsOverview> {
	const raw = await apiFetch<unknown>("/v1/stats/overview");
	return snakeToCamel<StatsOverview>(raw);
}

export async function fetchPlayHeatmap(params?: {
	from?: string;
	to?: string;
}): Promise<PlayHeatmap> {
	const sp = new URLSearchParams();
	if (params?.from) sp.set("from", params.from);
	if (params?.to) sp.set("to", params.to);
	const qs = sp.toString();
	const path = qs ? `/v1/stats/play-heatmap?${qs}` : "/v1/stats/play-heatmap";
	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<PlayHeatmap>(raw);
}

export async function fetchGenreStats(): Promise<GenreStats> {
	const raw = await apiFetch<unknown>("/v1/stats/genres");
	return snakeToCamel<GenreStats>(raw);
}

export async function fetchPlatformStats(): Promise<PlatformStats> {
	const raw = await apiFetch<unknown>("/v1/stats/platforms");
	return snakeToCamel<PlatformStats>(raw);
}

export async function fetchTimeline(params?: {
	limit?: number;
	offset?: number;
}): Promise<TimelineResponse> {
	const sp = new URLSearchParams();
	if (params?.limit !== undefined) sp.set("limit", String(params.limit));
	if (params?.offset !== undefined) sp.set("offset", String(params.offset));
	const qs = sp.toString();
	const path = qs ? `/v1/stats/timeline?${qs}` : "/v1/stats/timeline";
	const raw = await apiFetch<unknown>(path);
	return snakeToCamel<TimelineResponse>(raw);
}
