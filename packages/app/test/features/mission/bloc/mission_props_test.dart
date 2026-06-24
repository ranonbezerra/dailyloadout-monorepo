import 'package:app/core/library/library_models.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

final _now = DateTime.utc(2025, 6);

const _platform = Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'sony');

final _game = Game(
  publicId: 'game-001',
  slug: 'elden-ring',
  title: 'Elden Ring',
  metadataSource: 'igdb',
  createdAt: _now,
);

final _entry = LibraryEntry(
  publicId: 'lib-001',
  game: _game,
  platform: _platform,
  status: 'playing',
  createdAt: _now,
  updatedAt: _now,
);

final _mission = Mission(
  publicId: 'mission-001',
  libraryEntry: _entry,
  missionType: 'new_game',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
  briefingText: 'Welcome back!',
);

final _listItem = MissionListItem(
  publicId: 'mission-001',
  libraryEntry: _entry,
  missionType: 'new_game',
  startedAt: _now,
);

final _preview = BriefingPreview(
  libraryEntry: _entry,
  briefingText: 'Your briefing',
);

void main() {
  group('MissionEvent', () {
    test('LoadMissions supports value equality and props', () {
      const a = LoadMissions(limit: 10, offset: 5);
      const b = LoadMissions(limit: 10, offset: 5);
      expect(a, b);
      expect(a.props, [10, 5]);
      expect(const LoadMissions().props, [null, null]);
    });

    test('LoadMoreMissions supports value equality', () {
      expect(const LoadMoreMissions(), const LoadMoreMissions());
      expect(const LoadMoreMissions().props, isEmpty);
    });

    test('LoadActiveMission supports value equality', () {
      expect(const LoadActiveMission(), const LoadActiveMission());
      expect(const LoadActiveMission().props, isEmpty);
    });

    test('PreviewBriefing supports value equality and props', () {
      const a = PreviewBriefing(
        libraryEntryPublicId: 'lib-1',
        positionOverride: 'chapter 2',
        mode: 'deep',
      );
      const b = PreviewBriefing(
        libraryEntryPublicId: 'lib-1',
        positionOverride: 'chapter 2',
        mode: 'deep',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'chapter 2', 'deep']);
    });

    test('PreviewBriefing uses default mode', () {
      const a = PreviewBriefing(libraryEntryPublicId: 'lib-1');
      expect(a.mode, 'quick');
      expect(a.props, ['lib-1', null, 'quick']);
    });

    test('CancelDeepBriefing supports value equality and props', () {
      const a = CancelDeepBriefing(libraryEntryPublicId: 'lib-1');
      const b = CancelDeepBriefing(libraryEntryPublicId: 'lib-1');
      expect(a, b);
      expect(a.props, ['lib-1']);
    });

    test('StartMission supports value equality and props', () {
      const a = StartMission(libraryEntryPublicId: 'lib-1', briefingText: 'go');
      const b = StartMission(libraryEntryPublicId: 'lib-1', briefingText: 'go');
      expect(a, b);
      expect(a.props, ['lib-1', 'go']);
      expect(const StartMission(libraryEntryPublicId: 'lib-1').props, [
        'lib-1',
        null,
      ]);
    });

    test('SubmitDebrief supports value equality and props', () {
      const a = SubmitDebrief(publicId: 'm-1', debriefText: 'great');
      const b = SubmitDebrief(publicId: 'm-1', debriefText: 'great');
      expect(a, b);
      expect(a.props, ['m-1', 'great']);
    });

    test('EndMission supports value equality and props', () {
      const a = EndMission(publicId: 'm-1', endedVia: 'completed');
      const b = EndMission(publicId: 'm-1', endedVia: 'completed');
      expect(a, b);
      expect(a.props, ['m-1', 'completed']);
      expect(const EndMission(publicId: 'm-1').props, ['m-1', 'paused_app']);
    });

    test('SubmitRetroactiveDebrief supports value equality and props', () {
      const a = SubmitRetroactiveDebrief(
        libraryEntryPublicId: 'lib-1',
        debriefText: 'done',
      );
      const b = SubmitRetroactiveDebrief(
        libraryEntryPublicId: 'lib-1',
        debriefText: 'done',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'done']);
    });

    test('RegenerateBriefing supports value equality and props', () {
      const a = RegenerateBriefing(publicId: 'm-1', currentPosition: 'boss');
      const b = RegenerateBriefing(publicId: 'm-1', currentPosition: 'boss');
      expect(a, b);
      expect(a.props, ['m-1', 'boss']);
      expect(const RegenerateBriefing(publicId: 'm-1').props, ['m-1', null]);
    });
  });

  group('MissionState', () {
    test('MissionInitial supports value equality', () {
      expect(const MissionInitial(), const MissionInitial());
      expect(const MissionInitial().props, isEmpty);
    });

    test('MissionLoading supports value equality', () {
      expect(const MissionLoading(), const MissionLoading());
      expect(const MissionLoading().props, isEmpty);
    });

    test('MissionListLoaded supports value equality, props and copyWith', () {
      final a = MissionListLoaded(missions: [_listItem], total: 2);
      final b = MissionListLoaded(missions: [_listItem], total: 2);
      expect(a, b);
      expect(a.isLoadingMore, false);
      expect(a.hasMore, true);
      expect(a.props, [
        [_listItem],
        2,
        false,
      ]);

      final updated = a.copyWith(isLoadingMore: true);
      expect(updated.isLoadingMore, true);
      expect(updated.missions, [_listItem]);
      expect(updated.total, 2);
    });

    test('ActiveMissionLoaded supports value equality and props', () {
      final a = ActiveMissionLoaded(mission: _mission);
      final b = ActiveMissionLoaded(mission: _mission);
      expect(a, b);
      expect(a.props, [_mission]);
      expect(const ActiveMissionLoaded().props, [null]);
    });

    test('BriefingPreviewLoaded supports value equality and props', () {
      final a = BriefingPreviewLoaded(preview: _preview, isDeep: true);
      final b = BriefingPreviewLoaded(preview: _preview, isDeep: true);
      expect(a, b);
      expect(a.props, [_preview, true]);
      expect(BriefingPreviewLoaded(preview: _preview).props, [_preview, false]);
    });

    test('DeepBriefingLoading supports value equality', () {
      expect(const DeepBriefingLoading(), const DeepBriefingLoading());
      expect(const DeepBriefingLoading().props, isEmpty);
    });

    test('MissionStarted supports value equality and props', () {
      final a = MissionStarted(mission: _mission);
      final b = MissionStarted(mission: _mission);
      expect(a, b);
      expect(a.props, [_mission]);
    });

    test('MissionEnded supports value equality and props', () {
      final a = MissionEnded(mission: _mission);
      final b = MissionEnded(mission: _mission);
      expect(a, b);
      expect(a.props, [_mission]);
    });

    test('MissionError supports value equality and props', () {
      const a = MissionError(message: 'boom');
      const b = MissionError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
    });
  });
}
