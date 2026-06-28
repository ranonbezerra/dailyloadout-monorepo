export interface StatsOverview {
	totalGames: number;
	statusCounts: Record<string, number>;
	missionsLast30d: number;
	avgMissionDurationMinutes: number | null;
	userCreatedAt: string;
}

export interface HeatmapDay {
	date: string;
	count: number;
	totalMinutes: number;
}

export interface PlayHeatmap {
	days: HeatmapDay[];
}

export interface GenreStat {
	genre: string;
	totalMinutes: number;
	missionCount: number;
}

export interface GenreStats {
	genres: GenreStat[];
}

export interface PlatformStat {
	platformSlug: string;
	platformLabel: string;
	gameCount: number;
	missionCount: number;
	totalMinutes: number;
}

export interface PlatformStats {
	platforms: PlatformStat[];
}

export interface TimelineEntry {
	publicId: string;
	gameTitle: string;
	platformLabel: string;
	missionType: string;
	briefingText: string | null;
	debriefText: string | null;
	endedVia: string | null;
	startedAt: string;
	endedAt: string | null;
	durationMinutes: number | null;
}

export interface TimelineResponse {
	items: TimelineEntry[];
	total: number;
}

export type PeriodFilter = "7d" | "30d" | "90d" | "1y" | "all";
