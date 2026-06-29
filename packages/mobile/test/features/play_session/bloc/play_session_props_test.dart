import 'package:app/core/library/library_models.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
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

final _playSession = PlaySession(
  publicId: 'playSession-001',
  libraryEntry: _entry,
  playSessionType: 'new_game',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
  recapText: 'Welcome back!',
);

final _listItem = PlaySessionListItem(
  publicId: 'playSession-001',
  libraryEntry: _entry,
  playSessionType: 'new_game',
  startedAt: _now,
);

final _preview = RecapPreview(libraryEntry: _entry, recapText: 'Your recap');

void main() {
  group('PlaySessionEvent', () {
    test('LoadPlaySessions supports value equality and props', () {
      const a = LoadPlaySessions(limit: 10, offset: 5);
      const b = LoadPlaySessions(limit: 10, offset: 5);
      expect(a, b);
      expect(a.props, [10, 5]);
      expect(const LoadPlaySessions().props, [null, null]);
    });

    test('LoadMorePlaySessions supports value equality', () {
      expect(const LoadMorePlaySessions(), const LoadMorePlaySessions());
      expect(const LoadMorePlaySessions().props, isEmpty);
    });

    test('LoadActivePlaySession supports value equality', () {
      expect(const LoadActivePlaySession(), const LoadActivePlaySession());
      expect(const LoadActivePlaySession().props, isEmpty);
    });

    test('PreviewRecap supports value equality and props', () {
      const a = PreviewRecap(
        libraryEntryPublicId: 'lib-1',
        positionOverride: 'chapter 2',
        mode: 'deep',
      );
      const b = PreviewRecap(
        libraryEntryPublicId: 'lib-1',
        positionOverride: 'chapter 2',
        mode: 'deep',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'chapter 2', 'deep']);
    });

    test('PreviewRecap uses default mode', () {
      const a = PreviewRecap(libraryEntryPublicId: 'lib-1');
      expect(a.mode, 'quick');
      expect(a.props, ['lib-1', null, 'quick']);
    });

    test('CancelDeepRecap supports value equality and props', () {
      const a = CancelDeepRecap(libraryEntryPublicId: 'lib-1');
      const b = CancelDeepRecap(libraryEntryPublicId: 'lib-1');
      expect(a, b);
      expect(a.props, ['lib-1']);
    });

    test('StartPlaySession supports value equality and props', () {
      const a = StartPlaySession(
        libraryEntryPublicId: 'lib-1',
        recapText: 'go',
      );
      const b = StartPlaySession(
        libraryEntryPublicId: 'lib-1',
        recapText: 'go',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'go', false]);
      expect(const StartPlaySession(libraryEntryPublicId: 'lib-1').props, [
        'lib-1',
        null,
        false,
      ]);
      expect(
        const StartPlaySession(
          libraryEntryPublicId: 'lib-1',
          skipRecap: true,
        ).props,
        ['lib-1', null, true],
      );
    });

    test('SubmitWrapUp supports value equality and props', () {
      const a = SubmitWrapUp(publicId: 'm-1', wrapUpText: 'great');
      const b = SubmitWrapUp(publicId: 'm-1', wrapUpText: 'great');
      expect(a, b);
      expect(a.props, ['m-1', 'great']);
    });

    test('EndPlaySession supports value equality and props', () {
      const a = EndPlaySession(publicId: 'm-1', endedVia: 'completed');
      const b = EndPlaySession(publicId: 'm-1', endedVia: 'completed');
      expect(a, b);
      expect(a.props, ['m-1', 'completed']);
      expect(const EndPlaySession(publicId: 'm-1').props, [
        'm-1',
        'paused_app',
      ]);
    });

    test('SubmitRetroactiveWrapUp supports value equality and props', () {
      const a = SubmitRetroactiveWrapUp(
        libraryEntryPublicId: 'lib-1',
        wrapUpText: 'done',
      );
      const b = SubmitRetroactiveWrapUp(
        libraryEntryPublicId: 'lib-1',
        wrapUpText: 'done',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'done']);
    });

    test('RegenerateRecap supports value equality and props', () {
      const a = RegenerateRecap(publicId: 'm-1', currentPosition: 'boss');
      const b = RegenerateRecap(publicId: 'm-1', currentPosition: 'boss');
      expect(a, b);
      expect(a.props, ['m-1', 'boss']);
      expect(const RegenerateRecap(publicId: 'm-1').props, ['m-1', null]);
    });
  });

  group('PlaySessionState', () {
    test('PlaySessionInitial supports value equality', () {
      expect(const PlaySessionInitial(), const PlaySessionInitial());
      expect(const PlaySessionInitial().props, isEmpty);
    });

    test('PlaySessionLoading supports value equality', () {
      expect(const PlaySessionLoading(), const PlaySessionLoading());
      expect(const PlaySessionLoading().props, isEmpty);
    });

    test(
      'PlaySessionListLoaded supports value equality, props and copyWith',
      () {
        final a = PlaySessionListLoaded(playSessions: [_listItem], total: 2);
        final b = PlaySessionListLoaded(playSessions: [_listItem], total: 2);
        expect(a, b);
        expect(a.isLoadingMore, false);
        expect(a.hasMore, true);
        expect(a.props, [
          [_listItem],
          2,
          false,
          null,
        ]);

        final updated = a.copyWith(isLoadingMore: true);
        expect(updated.isLoadingMore, true);
        expect(updated.playSessions, [_listItem]);
        expect(updated.total, 2);

        final errored = a.copyWith(loadMoreError: 'oops');
        expect(errored.loadMoreError, 'oops');
        expect(errored.props.last, 'oops');
      },
    );

    test('ActivePlaySessionLoaded supports value equality and props', () {
      final a = ActivePlaySessionLoaded(playSession: _playSession);
      final b = ActivePlaySessionLoaded(playSession: _playSession);
      expect(a, b);
      expect(a.props, [_playSession]);
      expect(const ActivePlaySessionLoaded().props, [null]);
    });

    test('RecapPreviewLoaded supports value equality and props', () {
      final a = RecapPreviewLoaded(preview: _preview, isDeep: true);
      final b = RecapPreviewLoaded(preview: _preview, isDeep: true);
      expect(a, b);
      expect(a.props, [_preview, true]);
      expect(RecapPreviewLoaded(preview: _preview).props, [_preview, false]);
    });

    test('DeepRecapLoading supports value equality', () {
      expect(const DeepRecapLoading(), const DeepRecapLoading());
      expect(const DeepRecapLoading().props, isEmpty);
    });

    test('PlaySessionStarted supports value equality and props', () {
      final a = PlaySessionStarted(playSession: _playSession);
      final b = PlaySessionStarted(playSession: _playSession);
      expect(a, b);
      expect(a.props, [_playSession]);
    });

    test('PlaySessionEnded supports value equality and props', () {
      final a = PlaySessionEnded(playSession: _playSession);
      final b = PlaySessionEnded(playSession: _playSession);
      expect(a, b);
      expect(a.props, [_playSession]);
    });

    test('PlaySessionError supports value equality and props', () {
      const a = PlaySessionError(message: 'boom');
      const b = PlaySessionError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
    });
  });
}
