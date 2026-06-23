import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/core/loadout/loadout_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'loadout_event.dart';
part 'loadout_state.dart';

class LoadoutBloc
    extends Bloc<LoadoutEvent, LoadoutState> {
  LoadoutBloc({
    required LoadoutRepository loadoutRepository,
  }) : _loadoutRepository = loadoutRepository,
       super(const LoadoutInitial()) {
    on<CreateLoadout>(_onCreateLoadout);
    on<AcceptLoadout>(_onAcceptLoadout);
    on<RejectLoadout>(_onRejectLoadout);
    on<LoadLoadouts>(_onLoadLoadouts);
    on<LoadLatestLoadout>(_onLoadLatestLoadout);
  }

  final LoadoutRepository _loadoutRepository;

  Future<void> _onCreateLoadout(
    CreateLoadout event,
    Emitter<LoadoutState> emit,
  ) async {
    emit(const LoadoutLoading());

    try {
      final results =
          await _loadoutRepository.createLoadout(
        mood: event.mood,
        availableMinutes: event.availableMinutes,
        mentalEnergy: event.mentalEnergy,
        count: event.count,
        context: event.context,
      );

      emit(LoadoutResultsLoaded(results: results));
    } on DioException catch (e) {
      emit(
        LoadoutError(
          message: _extractErrorMessage(e),
        ),
      );
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
      final loadout =
          await _loadoutRepository.acceptLoadout(
        event.publicId,
      );
      emit(LoadoutAccepted(loadout: loadout));
    } on DioException catch (e) {
      emit(
        LoadoutError(
          message: _extractErrorMessage(e),
        ),
      );
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
      final loadout =
          await _loadoutRepository.rejectLoadout(
        event.publicId,
      );
      emit(LoadoutRejected(loadout: loadout));
    } on DioException catch (e) {
      emit(
        LoadoutError(
          message: _extractErrorMessage(e),
        ),
      );
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
      final response =
          await _loadoutRepository.listLoadouts(
        limit: event.limit ?? 20,
        offset: event.offset ?? 0,
      );

      emit(
        LoadoutListLoaded(
          loadouts: response.items,
          total: response.total,
        ),
      );
    } on DioException catch (e) {
      emit(
        LoadoutError(
          message: _extractErrorMessage(e),
        ),
      );
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
      final loadout =
          await _loadoutRepository.getLatestLoadout();
      emit(LatestLoadoutLoaded(loadout: loadout));
    } on DioException catch (e) {
      emit(
        LoadoutError(
          message: _extractErrorMessage(e),
        ),
      );
    } on Exception catch (e) {
      emit(LoadoutError(message: e.toString()));
    }
  }

  String _extractErrorMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }
    return e.message ??
        'An unexpected error occurred.';
  }
}
