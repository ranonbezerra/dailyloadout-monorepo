import 'package:app/core/auth/email_verification.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/core/loadout/loadout_repository.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'loadout_event.dart';
part 'loadout_state.dart';

class LoadoutBloc extends Bloc<LoadoutEvent, LoadoutState> {
  LoadoutBloc({
    required LoadoutRepository loadoutRepository,
    required MissionRepository missionRepository,
  }) : _loadoutRepository = loadoutRepository,
       _missionRepository = missionRepository,
       super(const LoadoutInitial()) {
    on<CreateLoadout>(_onCreateLoadout);
    on<AcceptLoadout>(_onAcceptLoadout);
    on<RejectLoadout>(_onRejectLoadout);
    on<GenerateLoadoutBriefing>(_onGenerateLoadoutBriefing);
    on<LoadLoadouts>(_onLoadLoadouts);
    on<LoadLatestLoadout>(_onLoadLatestLoadout);
  }

  final LoadoutRepository _loadoutRepository;
  final MissionRepository _missionRepository;

  Future<void> _onCreateLoadout(
    CreateLoadout event,
    Emitter<LoadoutState> emit,
  ) async {
    emit(const LoadoutLoading());

    try {
      final results = await _loadoutRepository.createLoadout(
        mood: event.mood,
        availableMinutes: event.availableMinutes,
        mentalEnergy: event.mentalEnergy,
        count: event.count,
        context: event.context,
      );

      emit(LoadoutResultsLoaded(results: results));
    } on DioException catch (e) {
      emit(LoadoutError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LoadoutError(message: e.toString()));
    }
  }

  Future<void> _onAcceptLoadout(
    AcceptLoadout event,
    Emitter<LoadoutState> emit,
  ) async {
    emit(const LoadoutLoading());

    try {
      final loadout = await _loadoutRepository.acceptLoadout(
        event.publicId,
        briefingText: event.briefingText,
      );
      emit(LoadoutAccepted(loadout: loadout));
    } on DioException catch (e) {
      emit(LoadoutError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LoadoutError(message: e.toString()));
    }
  }

  Future<void> _onGenerateLoadoutBriefing(
    GenerateLoadoutBriefing event,
    Emitter<LoadoutState> emit,
  ) async {
    emit(LoadoutBriefingLoading(publicId: event.publicId));

    try {
      final preview = await _missionRepository.previewBriefing(
        event.libraryEntryPublicId,
        mode: event.mode,
      );
      emit(
        LoadoutBriefingReady(
          publicId: event.publicId,
          briefingText: preview.briefingText ?? '',
        ),
      );
    } on DioException catch (e) {
      emit(LoadoutError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LoadoutError(message: e.toString()));
    }
  }

  Future<void> _onRejectLoadout(
    RejectLoadout event,
    Emitter<LoadoutState> emit,
  ) async {
    emit(const LoadoutLoading());

    try {
      final loadout = await _loadoutRepository.rejectLoadout(event.publicId);
      emit(LoadoutRejected(loadout: loadout));
    } on DioException catch (e) {
      emit(LoadoutError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LoadoutError(message: e.toString()));
    }
  }

  Future<void> _onLoadLoadouts(
    LoadLoadouts event,
    Emitter<LoadoutState> emit,
  ) async {
    emit(const LoadoutLoading());

    try {
      final response = await _loadoutRepository.listLoadouts(
        limit: event.limit ?? 20,
        offset: event.offset ?? 0,
      );

      emit(LoadoutListLoaded(loadouts: response.items, total: response.total));
    } on DioException catch (e) {
      emit(LoadoutError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LoadoutError(message: e.toString()));
    }
  }

  Future<void> _onLoadLatestLoadout(
    LoadLatestLoadout event,
    Emitter<LoadoutState> emit,
  ) async {
    emit(const LoadoutLoading());

    try {
      final loadout = await _loadoutRepository.getLatestLoadout();
      emit(LatestLoadoutLoaded(loadout: loadout));
    } on DioException catch (e) {
      emit(LoadoutError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LoadoutError(message: e.toString()));
    }
  }

  String _extractErrorMessage(DioException e) {
    // Cost-bearing routes 403 until the email is verified; surface the
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
