import 'package:app/core/analytics/analytics_models.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Analytics dashboard showing play stats, heatmap, genre breakdown,
/// platform distribution, and a recent session timeline.
class AnalyticsPage extends StatefulWidget {
  const AnalyticsPage({super.key});

  @override
  State<AnalyticsPage> createState() => _AnalyticsPageState();
}

class _AnalyticsPageState extends State<AnalyticsPage> {
  @override
  void initState() {
    super.initState();
    context.read<AnalyticsBloc>()
      ..add(const LoadAnalytics())
      ..add(const LoadTimeline());
  }

  void _onRetry() {
    context.read<AnalyticsBloc>()
      ..add(const LoadAnalytics())
      ..add(const LoadTimeline());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Analytics')),
      body: BlocConsumer<AnalyticsBloc, AnalyticsState>(
        listenWhen: (previous, current) =>
            current is AnalyticsLoaded && current.loadMoreTimelineError != null,
        listener: (context, state) {
          if (state is! AnalyticsLoaded) return;
          final message = state.loadMoreTimelineError;
          if (message == null) return;
          ScaffoldMessenger.of(context)
            ..hideCurrentSnackBar()
            ..showSnackBar(
              SnackBar(
                content: Text('Could not load more: $message'),
                action: SnackBarAction(
                  label: 'Retry',
                  onPressed: () => context.read<AnalyticsBloc>().add(
                    const LoadMoreTimeline(),
                  ),
                ),
              ),
            );
        },
        builder: (context, state) {
          if (state is AnalyticsLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (state is AnalyticsError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      state.message,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _onRetry,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }

          if (state is AnalyticsLoaded) {
            return _AnalyticsBody(
              state: state,
              onLoadMore: () =>
                  context.read<AnalyticsBloc>().add(const LoadMoreTimeline()),
            );
          }

          return const SizedBox.shrink();
        },
      ),
    );
  }
}

// -- Body -------------------------------------------------------------------

class _AnalyticsBody extends StatelessWidget {
  const _AnalyticsBody({required this.state, required this.onLoadMore});

  final AnalyticsLoaded state;
  final VoidCallback onLoadMore;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _OverviewGrid(overview: state.overview),
          const SizedBox(height: 24),
          _PlayActivitySection(heatmap: state.heatmap),
          const SizedBox(height: 24),
          _GenreSection(genres: state.genreStats.genres),
          const SizedBox(height: 24),
          _PlatformsSection(platforms: state.platformStats.platforms),
          const SizedBox(height: 24),
          _RecentSessionsSection(
            entries: state.timelineItems,
            hasMore: state.hasMoreTimeline,
            isLoadingMore: state.isLoadingMoreTimeline,
            onLoadMore: onLoadMore,
          ),
        ],
      ),
    );
  }
}

// -- Overview KPI Cards -----------------------------------------------------

class _OverviewGrid extends StatelessWidget {
  const _OverviewGrid({required this.overview});

  final StatsOverview overview;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _KpiCard(label: 'Total Games', value: '${overview.totalGames}'),
        _KpiCard(label: 'Sessions (30d)', value: '${overview.missionsLast30d}'),
        _KpiCard(
          label: 'Avg Session',
          value: _formatDuration(overview.avgMissionDurationMinutes?.round()),
        ),
        _LibraryStatusCard(statusCounts: overview.statusCounts),
      ],
    );
  }
}

class _KpiCard extends StatelessWidget {
  const _KpiCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final width = (MediaQuery.sizeOf(context).width - 40) / 2;

    return SizedBox(
      width: width,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: DLColors.textMuted,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                value,
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LibraryStatusCard extends StatelessWidget {
  const _LibraryStatusCard({required this.statusCounts});

  final Map<String, int> statusCounts;

  static const _statusColors = {
    'playing': DLColors.green,
    'backlog': Color(0xFFFBBF24), // amber
    'completed': Color(0xFF60A5FA), // blue
    'dropped': DLColors.red,
    'paused': DLColors.textDim,
  };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final width = (MediaQuery.sizeOf(context).width - 40) / 2;

    return SizedBox(
      width: width,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Library Status',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: DLColors.textMuted,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: statusCounts.entries.map((e) {
                  final color = _statusColors[e.key] ?? DLColors.textDim;
                  return _StatusChip(
                    label: '${e.key} ${e.value}',
                    color: color,
                  );
                }).toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

// -- Play Activity Heatmap --------------------------------------------------

class _PlayActivitySection extends StatelessWidget {
  const _PlayActivitySection({required this.heatmap});

  final PlayHeatmap heatmap;

  static const _cellSize = 12.0;
  static const _cellGap = 2.0;
  static const _dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  static const _monthLabels = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];

  Color _dayColor(int count) {
    if (count == 0) return DLColors.surface2;
    if (count == 1) return const Color(0xFF2D6A4F);
    if (count <= 3) return const Color(0xFF40916C);
    return DLColors.green;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dayMap = {for (final day in heatmap.days) day.date: day};
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = today.subtract(const Duration(days: 89));
    final gridStart = start.subtract(Duration(days: start.weekday % 7));
    final gridEnd = today.add(Duration(days: 6 - (today.weekday % 7)));
    final minDate = _dateKey(start);
    final maxDate = _dateKey(today);

    final weeks = <List<_HeatmapCell>>[];
    var cursor = gridStart;
    while (!cursor.isAfter(gridEnd)) {
      final week = <_HeatmapCell>[];
      for (var day = 0; day < 7; day++) {
        final key = _dateKey(cursor);
        final entry = dayMap[key];
        week.add(
          _HeatmapCell(
            date: key,
            month: cursor.month,
            count: entry?.count ?? 0,
            totalMinutes: entry?.totalMinutes ?? 0,
            isInRange:
                key.compareTo(minDate) >= 0 && key.compareTo(maxDate) <= 0,
          ),
        );
        cursor = cursor.add(const Duration(days: 1));
      }
      weeks.add(week);
    }

    return _SectionCard(
      title: 'Play Activity',
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(width: 26),
                for (var i = 0; i < weeks.length; i++)
                  SizedBox(
                    width: _cellSize + _cellGap,
                    height: 14,
                    child: Text(
                      _monthLabelFor(weeks, i),
                      maxLines: 1,
                      overflow: TextOverflow.visible,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: DLColors.textMuted,
                        fontSize: 10,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: _cellGap),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 26,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (var i = 0; i < _dayLabels.length; i++)
                        SizedBox(
                          height: _cellSize + _cellGap,
                          child: Text(
                            {1, 3, 5}.contains(i) ? _dayLabels[i] : '',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: DLColors.textMuted,
                              fontSize: 10,
                              height: 1,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final week in weeks)
                      Column(
                        children: [
                          for (final cell in week)
                            Padding(
                              padding: const EdgeInsets.only(
                                right: _cellGap,
                                bottom: _cellGap,
                              ),
                              child: Tooltip(
                                message:
                                    '${cell.date}: ${cell.count} '
                                    'session${cell.count == 1 ? '' : 's'}, '
                                    '${_formatDuration(cell.totalMinutes)}',
                                child: SizedBox(
                                  width: _cellSize,
                                  height: _cellSize,
                                  child: cell.isInRange
                                      ? DecoratedBox(
                                          decoration: BoxDecoration(
                                            color: _dayColor(cell.count),
                                            borderRadius: BorderRadius.circular(
                                              2,
                                            ),
                                          ),
                                        )
                                      : const SizedBox.shrink(),
                                ),
                              ),
                            ),
                        ],
                      ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _monthLabelFor(List<List<_HeatmapCell>> weeks, int index) {
    final month = weeks[index].first.month;
    final previousMonth = index > 0 ? weeks[index - 1].first.month : null;
    if (index != 0 && month == previousMonth) return '';
    return _monthLabels[month - 1];
  }
}

class _HeatmapCell {
  const _HeatmapCell({
    required this.date,
    required this.month,
    required this.count,
    required this.totalMinutes,
    required this.isInRange,
  });

  final String date;
  final int month;
  final int count;
  final int totalMinutes;
  final bool isInRange;
}

// -- Time by Genre ----------------------------------------------------------

class _GenreSection extends StatelessWidget {
  const _GenreSection({required this.genres});

  final List<GenreStat> genres;

  static const _palette = [
    DLColors.coral,
    DLColors.violet,
    DLColors.green,
    Color(0xFF60A5FA),
    Color(0xFFFBBF24),
    Color(0xFFF472B6),
    Color(0xFF34D399),
    Color(0xFFA78BFA),
  ];

  @override
  Widget build(BuildContext context) {
    if (genres.isEmpty) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final sorted = List<GenreStat>.of(genres)
      ..sort((a, b) => b.totalMinutes.compareTo(a.totalMinutes));
    final top = sorted.take(8).toList();
    final maxMinutes = top.first.totalMinutes;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Time by genre', style: theme.textTheme.titleMedium),
        const SizedBox(height: 12),
        for (var i = 0; i < top.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _GenreRow(
              genre: top[i],
              maxMinutes: maxMinutes,
              color: _palette[i % _palette.length],
            ),
          ),
      ],
    );
  }
}

class _GenreRow extends StatelessWidget {
  const _GenreRow({
    required this.genre,
    required this.maxMinutes,
    required this.color,
  });

  final GenreStat genre;
  final int maxMinutes;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fraction = maxMinutes > 0 ? genre.totalMinutes / maxMinutes : 0.0;

    return Row(
      children: [
        SizedBox(
          width: 80,
          child: Text(
            genre.genre,
            style: theme.textTheme.bodySmall?.copyWith(color: DLColors.text),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  height: 14,
                  width: constraints.maxWidth * fraction,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(width: 8),
        Text(
          _formatDuration(genre.totalMinutes),
          style: theme.textTheme.labelSmall?.copyWith(
            color: DLColors.textMuted,
          ),
        ),
      ],
    );
  }
}

// -- Platforms ---------------------------------------------------------------

class _PlatformsSection extends StatelessWidget {
  const _PlatformsSection({required this.platforms});

  final List<PlatformStat> platforms;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return _SectionCard(
      title: 'Platforms',
      child: platforms.isEmpty
          ? Text(
              'No platform data yet.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: DLColors.textMuted,
              ),
            )
          : Column(
              children: [
                for (var i = 0; i < platforms.length; i++) ...[
                  _PlatformRow(platform: platforms[i]),
                  if (i != platforms.length - 1)
                    const Divider(height: 16, color: DLColors.lineSoft),
                ],
              ],
            ),
    );
  }
}

class _PlatformRow extends StatelessWidget {
  const _PlatformRow({required this.platform});

  final PlatformStat platform;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      children: [
        Expanded(
          child: Text(
            platform.platformLabel,
            style: theme.textTheme.bodyMedium?.copyWith(color: DLColors.text),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Align(
            alignment: Alignment.centerRight,
            child: Wrap(
              alignment: WrapAlignment.end,
              spacing: 6,
              runSpacing: 6,
              children: [
                _MetricBadge(label: '${platform.gameCount} games'),
                _MetricBadge(
                  label: '${platform.missionCount} sessions',
                  color: DLColors.green,
                ),
                _MetricBadge(label: _formatDuration(platform.totalMinutes)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _MetricBadge extends StatelessWidget {
  const _MetricBadge({required this.label, this.color = DLColors.violet});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.22)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SizedBox(
      width: double.infinity,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              child,
            ],
          ),
        ),
      ),
    );
  }
}

// -- Recent Sessions --------------------------------------------------------

class _RecentSessionsSection extends StatelessWidget {
  const _RecentSessionsSection({
    required this.entries,
    required this.hasMore,
    required this.isLoadingMore,
    required this.onLoadMore,
  });

  final List<TimelineEntry> entries;
  final bool hasMore;
  final bool isLoadingMore;
  final VoidCallback onLoadMore;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) return const SizedBox.shrink();

    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Recent sessions', style: theme.textTheme.titleMedium),
        const SizedBox(height: 12),
        for (final entry in entries)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _TimelineCard(entry: entry),
          ),
        if (isLoadingMore)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          )
        else if (hasMore)
          Center(
            child: TextButton(
              onPressed: onLoadMore,
              child: const Text('Load more'),
            ),
          ),
      ],
    );
  }
}

class _TimelineCard extends StatelessWidget {
  const _TimelineCard({required this.entry});

  final TimelineEntry entry;

  String get _durationLabel => _formatDuration(entry.durationMinutes);

  String get _startedLabel {
    final d = entry.startedAt;
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${months[d.month - 1]} ${d.day}, ${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              entry.gameTitle,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: [
                Chip(label: Text(entry.platformLabel)),
                Chip(label: Text(entry.missionType)),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Icon(
                  Icons.timer_outlined,
                  size: 14,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Text(
                  entry.endedAt == null ? 'Ongoing' : _durationLabel,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(width: 16),
                Icon(
                  Icons.calendar_today_outlined,
                  size: 14,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Text(
                  _startedLabel,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            if (entry.debriefText != null) ...[
              const SizedBox(height: 8),
              Text(
                entry.debriefText!,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: DLColors.textMuted,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// -- Helpers ----------------------------------------------------------------

/// Formats a duration in minutes to a human-readable string.
///
/// Returns:
/// - `null` minutes -> "--"
/// - < 60 minutes   -> "{m}m"
/// - >= 60 minutes  -> "{h}h {m}m" (omits minutes if 0)
String _formatDuration(int? minutes) {
  if (minutes == null) return '\u2014';
  if (minutes < 60) return '${minutes}m';
  final h = minutes ~/ 60;
  final m = minutes % 60;
  if (m == 0) return '${h}h';
  return '${h}h ${m}m';
}

String _dateKey(DateTime date) {
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');
  return '${date.year}-$month-$day';
}
