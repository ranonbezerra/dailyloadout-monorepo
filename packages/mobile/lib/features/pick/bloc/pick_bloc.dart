import 'package:app/core/auth/email_verification.dart';
import 'package:app/core/pick/pick_models.dart';
import 'package:app/core/pick/pick_repository.dart';
import 'package:app/core/play_session/play_session_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'pick_event.dart';
part 'pick_state.dart';

class PickBloc extends Bloc<PickEvent, PickState> {
  PickBloc({
    required PickRepository pickRepository,
    required PlaySessionRepository playSessionRepository,
  }) : _pickRepository = pickRepository,
       _playSessionRepository = playSessionRepository,
       super(const PickInitial()) {
    on<CreatePick>(_onCreatePick);
    on<AcceptPick>(_onAcceptPick);
    on<RejectPick>(_onRejectPick);
    on<GeneratePickRecap>(_onGeneratePickRecap);
    on<LoadPicks>(_onLoadPicks);
    on<LoadLatestPick>(_onLoadLatestPick);
  }

  final PickRepository _pickRepository;
  final PlaySessionRepository _playSessionRepository;

  Future<void> _onCreatePick(CreatePick event, Emitter<PickState> emit) async {
    emit(const PickLoading());

    try {
      final results = await _pickRepository.createPick(
        mood: event.mood,
        availableMinutes: event.availableMinutes,
        mentalEnergy: event.mentalEnergy,
        count: event.count,
        context: event.context,
      );

      emit(PickResultsLoaded(results: results));
    } on DioException catch (e) {
      emit(PickError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PickError(message: e.toString()));
    }
  }

  Future<void> _onAcceptPick(AcceptPick event, Emitter<PickState> emit) async {
    emit(const PickLoading());

    try {
      final pick = await _pickRepository.acceptPick(
        event.publicId,
        recapText: event.recapText,
      );
      emit(PickAccepted(pick: pick));
    } on DioException catch (e) {
      emit(PickError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PickError(message: e.toString()));
    }
  }

  Future<void> _onGeneratePickRecap(
    GeneratePickRecap event,
    Emitter<PickState> emit,
  ) async {
    emit(PickRecapLoading(publicId: event.publicId));

    try {
      final preview = await _playSessionRepository.previewRecap(
        event.libraryEntryPublicId,
        mode: event.mode,
      );
      emit(
        PickRecapReady(
          publicId: event.publicId,
          recapText: preview.recapText ?? '',
        ),
      );
    } on DioException catch (e) {
      emit(PickError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PickError(message: e.toString()));
    }
  }

  Future<void> _onRejectPick(RejectPick event, Emitter<PickState> emit) async {
    emit(const PickLoading());

    try {
      final pick = await _pickRepository.rejectPick(event.publicId);
      emit(PickRejected(pick: pick));
    } on DioException catch (e) {
      emit(PickError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PickError(message: e.toString()));
    }
  }

  Future<void> _onLoadPicks(LoadPicks event, Emitter<PickState> emit) async {
    emit(const PickLoading());

    try {
      final response = await _pickRepository.listPicks(
        limit: event.limit ?? 20,
        offset: event.offset ?? 0,
      );

      emit(PickListLoaded(picks: response.items, total: response.total));
    } on DioException catch (e) {
      emit(PickError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PickError(message: e.toString()));
    }
  }

  Future<void> _onLoadLatestPick(
    LoadLatestPick event,
    Emitter<PickState> emit,
  ) async {
    emit(const PickLoading());

    try {
      final pick = await _pickRepository.getLatestPick();
      emit(LatestPickLoaded(pick: pick));
    } on DioException catch (e) {
      emit(PickError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PickError(message: e.toString()));
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
