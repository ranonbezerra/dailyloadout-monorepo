import { PieChart } from "@mantine/charts";
import {
	Badge,
	Box,
	Card,
	Group,
	Loader,
	Pagination,
	ScrollArea,
	SegmentedControl,
	Select,
	SimpleGrid,
	Skeleton,
	Stack,
	Table,
	Text,
	Title,
	Tooltip,
} from "@mantine/core";
import { Fragment, useState } from "react";
import {
	useGenreStats,
	usePlatformStats,
	usePlayHeatmap,
	useStatsOverview,
	useTimeline,
} from "../hooks/useStats";
import type { HeatmapDay, PeriodFilter } from "../types/stats";

function getDateRange(period: PeriodFilter): { from?: string; to?: string } {
	if (period === "all") return {};
	const now = new Date();
	const days = period === "7d" ? 7 : period === "30d" ? 30 : period === "90d" ? 90 : 365;
	const from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
	return { from: from.toISOString().split("T")[0] };
}

function formatMinutes(minutes: number): string {
	if (minutes < 60) return `${minutes}m`;
	const h = Math.floor(minutes / 60);
	const m = minutes % 60;
	return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function toDateStr(d: Date): string {
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const STATUS_COLORS: Record<string, string> = {
	playing: "green",
	backlog: "blue",
	completed: "violet",
	dropped: "red",
	paused: "yellow",
};

// ---------------------------------------------------------------------------
// GitHub-style contribution heatmap
// ---------------------------------------------------------------------------

const CELL_SIZE = 12;
const CELL_GAP = 2;
const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec",
];

function getHeatColor(count: number): string {
	if (count === 0) return "var(--mantine-color-dark-4)";
	if (count === 1) return "var(--mantine-color-green-3)";
	if (count <= 3) return "var(--mantine-color-green-5)";
	return "var(--mantine-color-green-7)";
}

function ContributionHeatmap({
	days,
	from,
	registeredAt,
}: {
	days: HeatmapDay[];
	from?: string;
	registeredAt?: string;
}) {
	const dayMap = new Map<string, HeatmapDay>();
	for (const day of days) {
		dayMap.set(day.date, day);
	}

	// Effective date bounds (no cells before registration or after today)
	const today = new Date();
	const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	let effectiveStart = from ? new Date(`${from}T00:00:00`) : new Date(todayDate);
	if (!from) effectiveStart.setDate(effectiveStart.getDate() - 30);
	if (registeredAt) {
		const regDate = new Date(`${registeredAt.split("T")[0]}T00:00:00`);
		if (regDate > effectiveStart) effectiveStart = regDate;
	}
	const minDate = toDateStr(effectiveStart);
	const maxDate = toDateStr(todayDate);

	// Align to week boundaries for grid layout
	const gridStart = new Date(effectiveStart);
	gridStart.setDate(gridStart.getDate() - gridStart.getDay());
	const gridEnd = new Date(todayDate);
	const endDow = gridEnd.getDay();
	if (endDow < 6) gridEnd.setDate(gridEnd.getDate() + (6 - endDow));

	// Build week columns (each column = 7 vertical cells)
	const weeks: { date: string; count: number; totalMinutes: number }[][] = [];
	const cursor = new Date(gridStart);
	while (cursor <= gridEnd) {
		const week: { date: string; count: number; totalMinutes: number }[] = [];
		for (let d = 0; d < 7; d++) {
			const dateStr = toDateStr(cursor);
			const entry = dayMap.get(dateStr);
			week.push({
				date: dateStr,
				count: entry?.count ?? 0,
				totalMinutes: entry?.totalMinutes ?? 0,
			});
			cursor.setDate(cursor.getDate() + 1);
		}
		weeks.push(week);
	}

	const weekCount = weeks.length;

	// Build month labels: one per week column, shown when month changes
	const monthLabels = weeks.map((week, wi) => {
		const weekDate = new Date(`${week[0].date}T00:00:00`);
		const prevMonth = wi > 0 ? new Date(`${weeks[wi - 1][0].date}T00:00:00`).getMonth() : -1;
		return wi === 0 || weekDate.getMonth() !== prevMonth ? MONTH_NAMES[weekDate.getMonth()] : "";
	});

	return (
		<ScrollArea>
			<div
				style={{
					display: "inline-grid",
					gridTemplateColumns: `24px repeat(${weekCount}, ${CELL_SIZE}px)`,
					gridTemplateRows: `14px repeat(7, ${CELL_SIZE}px)`,
					gap: CELL_GAP,
				}}
			>
				{/* Row 0: empty corner + month labels */}
				<div />
				{weeks.map((week, wi) => (
					<span
						key={`m-${week[0].date}`}
						style={{ fontSize: 10, color: "var(--mantine-color-dimmed)", lineHeight: "14px" }}
					>
						{monthLabels[wi]}
					</span>
				))}

				{/* Rows 1-7: day label + cells for each day of week */}
				{DAY_LABELS.map((label, dow) => (
					<Fragment key={label}>
						<span
							style={{
								fontSize: 10,
								color: "var(--mantine-color-dimmed)",
								lineHeight: `${CELL_SIZE}px`,
							}}
						>
							{[1, 3, 5].includes(dow) ? label : ""}
						</span>
						{weeks.map((week) => {
							const cell = week[dow];
							const outOfBounds = cell.date < minDate || cell.date > maxDate;
							if (outOfBounds) {
								return <div key={cell.date} />;
							}
							return (
								<Tooltip
									key={cell.date}
									label={`${cell.date}: ${cell.count} session${cell.count !== 1 ? "s" : ""}, ${formatMinutes(cell.totalMinutes)}`}
								>
									<Box
										w={CELL_SIZE}
										h={CELL_SIZE}
										style={{
											borderRadius: 2,
											backgroundColor: getHeatColor(cell.count),
										}}
									/>
								</Tooltip>
							);
						})}
					</Fragment>
				))}
			</div>
		</ScrollArea>
	);
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function AnalyticsPage() {
	const [period, setPeriod] = useState<PeriodFilter>("30d");
	const [timelinePage, setTimelinePage] = useState(1);
	const [timelinePageSize, setTimelinePageSize] = useState("10");
	const dateRange = getDateRange(period);

	const { data: overview, isLoading: loadingOverview } = useStatsOverview();
	const { data: heatmap, isLoading: loadingHeatmap } = usePlayHeatmap(dateRange);
	const { data: genres } = useGenreStats();
	const { data: platforms } = usePlatformStats();

	const pageSize = Number(timelinePageSize);
	const { data: timeline, isLoading: loadingTimeline } = useTimeline({
		limit: pageSize,
		offset: (timelinePage - 1) * pageSize,
	});

	if (loadingOverview) {
		return (
			<Stack p="md">
				<Skeleton height={36} width={200} />
				<SimpleGrid cols={4}>
					<Skeleton height={100} />
					<Skeleton height={100} />
					<Skeleton height={100} />
					<Skeleton height={100} />
				</SimpleGrid>
			</Stack>
		);
	}

	const genreChartData = (genres?.genres ?? []).slice(0, 8).map((g, i) => ({
		name: g.genre,
		value: g.totalMinutes,
		color: ["blue", "cyan", "teal", "green", "yellow", "orange", "red", "violet"][i % 8],
	}));

	const totalPages = Math.ceil((timeline?.total ?? 0) / pageSize);
	const rangeFrom = (timelinePage - 1) * pageSize + 1;
	const rangeTo = Math.min(timelinePage * pageSize, timeline?.total ?? 0);

	return (
		<Stack p="md" gap="lg">
			<Group justify="space-between">
				<Title order={2}>Analytics</Title>
				<SegmentedControl
					value={period}
					onChange={(v) => setPeriod(v as PeriodFilter)}
					data={[
						{ label: "7d", value: "7d" },
						{ label: "30d", value: "30d" },
						{ label: "90d", value: "90d" },
						{ label: "1y", value: "1y" },
						{ label: "All", value: "all" },
					]}
				/>
			</Group>

			{/* KPI Cards */}
			<SimpleGrid cols={{ base: 2, md: 4 }}>
				<Card shadow="sm" padding="lg" radius="md" withBorder>
					<Text size="sm" c="dimmed">
						Total Games
					</Text>
					<Text size="xl" fw={700}>
						{overview?.totalGames ?? 0}
					</Text>
				</Card>
				<Card shadow="sm" padding="lg" radius="md" withBorder>
					<Text size="sm" c="dimmed">
						Sessions (30d)
					</Text>
					<Text size="xl" fw={700}>
						{overview?.playSessionsLast30d ?? 0}
					</Text>
				</Card>
				<Card shadow="sm" padding="lg" radius="md" withBorder>
					<Text size="sm" c="dimmed">
						Avg Session
					</Text>
					<Text size="xl" fw={700}>
						{overview?.avgPlaySessionDurationMinutes
							? formatMinutes(Math.round(overview.avgPlaySessionDurationMinutes))
							: "\u2014"}
					</Text>
				</Card>
				<Card shadow="sm" padding="lg" radius="md" withBorder>
					<Text size="sm" c="dimmed">
						Status
					</Text>
					<Group gap={4} mt={4}>
						{Object.entries(overview?.statusCounts ?? {}).map(([status, count]) => (
							<Badge key={status} color={STATUS_COLORS[status] ?? "gray"} size="sm">
								{status}: {count}
							</Badge>
						))}
					</Group>
				</Card>
			</SimpleGrid>

			{/* Heatmap */}
			<Card shadow="sm" padding="lg" radius="md" withBorder>
				<Text fw={600} mb="sm">
					Play Activity
				</Text>
				{loadingHeatmap ? (
					<Loader size="sm" />
				) : (
					<ContributionHeatmap
						days={heatmap?.days ?? []}
						from={dateRange.from}
						registeredAt={overview?.userCreatedAt}
					/>
				)}
			</Card>

			{/* Charts Row */}
			<SimpleGrid cols={{ base: 1, md: 2 }}>
				{/* Genres */}
				<Card shadow="sm" padding="lg" radius="md" withBorder>
					<Text fw={600} mb="sm">
						Time by Genre
					</Text>
					{genreChartData.length > 0 ? (
						<PieChart
							data={genreChartData}
							withTooltip
							tooltipDataSource="segment"
							size={200}
							mx="auto"
						/>
					) : (
						<Text c="dimmed" size="sm">
							No genre data yet.
						</Text>
					)}
				</Card>

				{/* Platforms */}
				<Card shadow="sm" padding="lg" radius="md" withBorder>
					<Text fw={600} mb="sm">
						Platforms
					</Text>
					<Stack gap="xs">
						{(platforms?.platforms ?? []).map((p) => (
							<Group key={p.platformSlug} justify="space-between">
								<Text size="sm">{p.platformLabel}</Text>
								<Group gap="xs">
									<Badge size="xs" variant="light">
										{p.gameCount} games
									</Badge>
									<Badge size="xs" variant="light" color="green">
										{p.playSessionCount} sessions
									</Badge>
								</Group>
							</Group>
						))}
						{(platforms?.platforms ?? []).length === 0 && (
							<Text c="dimmed" size="sm">
								No platform data yet.
							</Text>
						)}
					</Stack>
				</Card>
			</SimpleGrid>

			{/* Recent Sessions with pagination */}
			<Card shadow="sm" padding="lg" radius="md" withBorder>
				<Text fw={600} mb="sm">
					Recent Sessions
				</Text>
				{loadingTimeline ? (
					<Loader size="sm" />
				) : (timeline?.items ?? []).length === 0 ? (
					<Text c="dimmed" size="sm" ta="center" py="xl">
						No completed sessions yet.
					</Text>
				) : (
					<>
						<Table highlightOnHover verticalSpacing="sm" horizontalSpacing="lg">
							<Table.Thead>
								<Table.Tr>
									<Table.Th>
										<Text size="xs" c="dimmed" tt="uppercase">
											Game
										</Text>
									</Table.Th>
									<Table.Th>
										<Text size="xs" c="dimmed" tt="uppercase">
											Platform
										</Text>
									</Table.Th>
									<Table.Th>
										<Text size="xs" c="dimmed" tt="uppercase">
											Type
										</Text>
									</Table.Th>
									<Table.Th>
										<Text size="xs" c="dimmed" tt="uppercase">
											Duration
										</Text>
									</Table.Th>
									<Table.Th>
										<Text size="xs" c="dimmed" tt="uppercase">
											Date
										</Text>
									</Table.Th>
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{timeline?.items.map((item) => (
									<Table.Tr key={item.publicId}>
										<Table.Td>
											<Text size="sm" fw={500}>
												{item.gameTitle}
											</Text>
											{item.wrapUpText && (
												<Text size="xs" c="dimmed" lineClamp={1}>
													{item.wrapUpText}
												</Text>
											)}
										</Table.Td>
										<Table.Td>
											<Text size="sm">{item.platformLabel}</Text>
										</Table.Td>
										<Table.Td>
											<Badge size="sm" variant="light">
												{item.playSessionType}
											</Badge>
										</Table.Td>
										<Table.Td>
											<Text size="sm">
												{item.durationMinutes != null
													? formatMinutes(item.durationMinutes)
													: "\u2014"}
											</Text>
										</Table.Td>
										<Table.Td>
											<Text size="sm">{new Date(item.startedAt).toLocaleDateString()}</Text>
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>

						<Group justify="space-between" mt="md">
							<Group gap="sm">
								<Select
									size="xs"
									w={80}
									data={["10", "20", "50"]}
									value={timelinePageSize}
									onChange={(v) => {
										if (v) {
											setTimelinePageSize(v);
											setTimelinePage(1);
										}
									}}
								/>
								<Text size="sm" c="dimmed">
									{timeline?.total
										? `${rangeFrom}\u2013${rangeTo} of ${timeline.total}`
										: "0 results"}
								</Text>
							</Group>
							{totalPages > 1 && (
								<Pagination
									size="sm"
									total={totalPages}
									value={timelinePage}
									onChange={setTimelinePage}
								/>
							)}
						</Group>
					</>
				)}
			</Card>
		</Stack>
	);
}
