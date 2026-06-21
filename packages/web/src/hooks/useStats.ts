import { useQuery } from "@tanstack/react-query";
import {
	fetchGenreStats,
	fetchOverview,
	fetchPlatformStats,
	fetchPlayHeatmap,
	fetchTimeline,
} from "../lib/stats-api";

const STATS_KEY = ["stats"] as const;

export function useStatsOverview() {
	return useQuery({
		queryKey: [...STATS_KEY, "overview"],
		queryFn: fetchOverview,
	});
}

export function usePlayHeatmap(params?: { from?: string; to?: string }) {
	return useQuery({
		queryKey: [...STATS_KEY, "heatmap", params],
		queryFn: () => fetchPlayHeatmap(params),
	});
}

export function useGenreStats() {
	return useQuery({
		queryKey: [...STATS_KEY, "genres"],
		queryFn: fetchGenreStats,
	});
}

export function usePlatformStats() {
	return useQuery({
		queryKey: [...STATS_KEY, "platforms"],
		queryFn: fetchPlatformStats,
	});
}

export function useTimeline(params?: { limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...STATS_KEY, "timeline", params],
		queryFn: () => fetchTimeline(params),
	});
}
