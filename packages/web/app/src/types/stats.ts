export interface StatsOverview {
	totalGames: number;
	statusCounts: Record<string, number>;
	playSessionsLast30d: number;
	avgPlaySessionDurationMinutes: number | null;
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
	playSessionCount: number;
}

export interface GenreStats {
	genres: GenreStat[];
}

export interface PlatformStat {
	platformSlug: string;
	platformLabel: string;
	gameCount: number;
	playSessionCount: number;
	totalMinutes: number;
}

export interface PlatformStats {
	platforms: PlatformStat[];
}

export interface TimelineEntry {
	publicId: string;
	gameTitle: string;
	platformLabel: string;
	playSessionType: string;
	recapText: string | null;
	wrapUpText: string | null;
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
