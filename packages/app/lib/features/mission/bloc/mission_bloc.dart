import 'package:app/core/mission/mission_models.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'mission_event.dart';
part 'mission_state.dart';

class MissionBloc extends Bloc<MissionEvent, MissionState> {
  MissionBloc({required MissionRepository missionRepository})
    : _missionRepository = missionRepository,
      super(const MissionInitial()) {
    on<LoadMissions>(_onLoadMissions);
    on<LoadActiveMission>(_onLoadActiveMission);
    on<PreviewBriefing>(_onPreviewBriefing);
    on<StartMission>(_onStartMission);
    on<SubmitDebrief>(_onSubmitDebrief);
    on<EndMission>(_onEndMission);
    on<SubmitRetroactiveDebrief>(_onSubmitRetroactiveDebrief);
    on<RegenerateBriefing>(_onRegenerateBriefing);
  }

  final MissionRepository _missionRepository;

  Future<void> _onLoadMissions(
    LoadMissions event,
    Emitter<MissionState> emit,
  ) async {
    emit(const MissionLoading());

    try {
      final response = await _missionRepository.listMissions(
        limit: event.limit ?? 50,
        offset: event.offset ?? 0,
      );

      emit(MissionListLoaded(missions: response.items, total: response.total));
    } on DioException catch (e) {
      emit(MissionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(MissionError(message: e.toString()));
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
    emit(const MissionLoading());

    try {
      final preview = await _missionRepository.previewBriefing(
        event.libraryEntryPublicId,
        positionOverride: event.positionOverride,
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
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }
    return e.message ?? 'An unexpected error occurred.';
  }
}
