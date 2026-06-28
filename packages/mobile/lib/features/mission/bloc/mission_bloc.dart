import 'package:app/core/auth/email_verification.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'mission_event.dart';
part 'mission_state.dart';

const _pageSize = 10;

class MissionBloc extends Bloc<MissionEvent, MissionState> {
  MissionBloc({required MissionRepository missionRepository})
    : _missionRepository = missionRepository,
      super(const MissionInitial()) {
    on<LoadMissions>(_onLoadMissions);
    on<LoadMoreMissions>(_onLoadMoreMissions);
    on<LoadActiveMission>(_onLoadActiveMission);
    on<PreviewBriefing>(_onPreviewBriefing);
    on<CancelDeepBriefing>(_onCancelDeepBriefing);
    on<StartMission>(_onStartMission);
    on<SubmitDebrief>(_onSubmitDebrief);
    on<EndMission>(_onEndMission);
    on<SubmitRetroactiveDebrief>(_onSubmitRetroactiveDebrief);
    on<RegenerateBriefing>(_onRegenerateBriefing);
  }

  final MissionRepository _missionRepository;

  /// Active cancel token for an in-flight deep briefing request, if any.
  CancelToken? _deepCancelToken;

  Future<void> _onLoadMissions(
    LoadMissions event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final response = await _missionRepository.listMissions(
        limit: event.limit ?? _pageSize,
        offset: event.offset ?? 0,
      );

      emit(MissionListLoaded(missions: response.items, total: response.total));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  Future<void> _onLoadMoreMissions(
    LoadMoreMissions event,
    Emitter<MissionState> emit,
  ) async {
    final currentState = state;
    if (currentState is! MissionListLoaded || !currentState.hasMore) return;
    if (currentState.isLoadingMore) return;

    emit(currentState.copyWith(isLoadingMore: true));

    try {
      final response = await _missionRepository.listMissions(
        limit: _pageSize,
        offset: currentState.missions.length,
      );

      emit(
        MissionListLoaded(
          missions: [...currentState.missions, ...response.items],
          total: response.total,
        ),
      );
    } on DioException catch (e) {
      // Keep the loaded list visible; surface the error inline.
      emit(
        currentState.copyWith(
          isLoadingMore: false,
          loadMoreError: _extractErrorMessage(e),
        ),
      );
    } on Exception catch (e) {
      emit(
        currentState.copyWith(
          isLoadingMore: false,
          loadMoreError: e.toString(),
        ),
      );
    }
  }

  Future<void> _onLoadActiveMission(
    LoadActiveMission event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final mission = await _missionRepository.getActiveMission();
      emit(ActiveMissionLoaded(mission: mission));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  Future<void> _onPreviewBriefing(
    PreviewBriefing event,
    Emitter<MissionState> emit,
  ) async {
    final isDeep = event.mode == 'deep';
    if (isDeep) {
      _deepCancelToken = CancelToken();
      emit(const DeepBriefingLoading());
    } else {
      emit(const MissionLoading());
    }

    try {
      final preview = await _missionRepository.previewBriefing(
        event.libraryEntryPublicId,
        positionOverride: event.positionOverride,
        mode: event.mode,
        cancelToken: isDeep ? _deepCancelToken : null,
      );
      emit(BriefingPreviewLoaded(preview: preview, isDeep: isDeep));
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) {
        // User cancelled the deep request -- fall back to the quick briefing.
        await _emitQuickPreview(event.libraryEntryPublicId, emit);
        return;
      }
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    } finally {
      if (isDeep) _deepCancelToken = null;
    }
  }

  Future<void> _onCancelDeepBriefing(
    CancelDeepBriefing event,
    Emitter<MissionState> emit,
  ) async {
    _deepCancelToken?.cancel('cancelled_by_user');
  }

  Future<void> _emitQuickPreview(
    String libraryEntryPublicId,
    Emitter<MissionState> emit,
  ) async {
    try {
      final preview = await _missionRepository.previewBriefing(
        libraryEntryPublicId,
      );
      emit(BriefingPreviewLoaded(preview: preview));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  Future<void> _onStartMission(
    StartMission event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final mission = await _missionRepository.startMission(
        event.libraryEntryPublicId,
        briefingText: event.briefingText,
        skipBriefing: event.skipBriefing,
      );
      emit(MissionStarted(mission: mission));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  Future<void> _onSubmitDebrief(
    SubmitDebrief event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final mission = await _missionRepository.submitDebrief(
        event.publicId,
        event.debriefText,
      );
      emit(MissionEnded(mission: mission));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  Future<void> _onEndMission(
    EndMission event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final mission = await _missionRepository.endMission(
        event.publicId,
        endedVia: event.endedVia,
      );
      emit(MissionEnded(mission: mission));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  Future<void> _onSubmitRetroactiveDebrief(
    SubmitRetroactiveDebrief event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final preview = await _missionRepository.submitRetroactiveDebrief(
        event.libraryEntryPublicId,
        event.debriefText,
      );
      emit(BriefingPreviewLoaded(preview: preview));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  Future<void> _onRegenerateBriefing(
    RegenerateBriefing event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final mission = await _missionRepository.regenerateBriefing(
        event.publicId,
        currentPosition: event.currentPosition,
      );
      emit(MissionStarted(mission: mission));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
    }
  }

  String _extractErrorMessage(DioException e) {
    // Briefing generation 403s until the email is verified; surface the
    // actionable verify prompt rather than the bare API detail.
    if (EmailVerification.isUnverifiedError(e)) {
      return EmailVerification.friendlyMessage;
    }
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }
    return e.message ?? 'An unexpected error occurred.';
  }
}
