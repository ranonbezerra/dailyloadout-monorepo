import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:logger/logger.dart';

part 'library_event.dart';
part 'library_state.dart';

class LibraryBloc extends Bloc<LibraryEvent, LibraryState> {
  LibraryBloc({required LibraryRepository libraryRepository})
    : _libraryRepository = libraryRepository,
      super(const LibraryInitial()) {
    on<LoadLibrary>(_onLoadLibrary);
    on<AddEntry>(_onAddEntry);
    on<UpdateEntry>(_onUpdateEntry);
    on<DeleteEntry>(_onDeleteEntry);
    on<SearchGames>(_onSearchGames);
    on<CreateGame>(_onCreateGame);
  }

  final LibraryRepository _libraryRepository;
  final Logger _logger = Logger(printer: PrettyPrinter(methodCount: 0));

  /// Tracks the current status filter so mutations can reload with it.
  String? _currentStatusFilter;

  Future<void> _onLoadLibrary(
    LoadLibrary event,
    Emitter<LibraryState> emit,
  ) async {
    emit(const LibraryLoading());

    try {
      _currentStatusFilter = event.status;

      final response = await _libraryRepository.listLibrary(
        status: event.status,
        limit: event.limit ?? 50,
        offset: event.offset ?? 0,
      );

      final hasMore = response.offset + response.items.length < response.total;

      emit(
        LibraryLoaded(
          groups: response.items,
          total: response.total,
          hasMore: hasMore,
        ),
      );
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(LibraryError(message: message));
    } on Exception catch (e) {
      emit(LibraryError(message: e.toString()));
    }
  }

  Future<void> _onAddEntry(AddEntry event, Emitter<LibraryState> emit) async {
    emit(const LibraryLoading());

    try {
      await _libraryRepository.addToLibrary(
        gamePublicId: event.gamePublicId,
        platformIds: event.platformIds,
        status: event.status,
        notes: event.notes,
      );

      // Reload library with the current filter.
      await _reload(emit);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(LibraryError(message: message));
    } on Exception catch (e) {
      emit(LibraryError(message: e.toString()));
    }
  }

  Future<void> _onUpdateEntry(
    UpdateEntry event,
    Emitter<LibraryState> emit,
  ) async {
    emit(const LibraryLoading());

    try {
      await _libraryRepository.updateEntry(
        event.publicId,
        status: event.status,
        notes: event.notes,
      );

      // Reload library with the current filter.
      await _reload(emit);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(LibraryError(message: message));
    } on Exception catch (e) {
      emit(LibraryError(message: e.toString()));
    }
  }

  Future<void> _onDeleteEntry(
    DeleteEntry event,
    Emitter<LibraryState> emit,
  ) async {
    emit(const LibraryLoading());

    try {
      await _libraryRepository.deleteEntry(event.publicId);

      // Reload library with the current filter.
      await _reload(emit);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(LibraryError(message: message));
    } on Exception catch (e) {
      emit(LibraryError(message: e.toString()));
    }
  }

  Future<void> _onSearchGames(
    SearchGames event,
    Emitter<LibraryState> emit,
  ) async {
    // SearchGames is handled at the UI level via the repository directly.
    // This event is kept for consistency but does not mutate library state.
    _logger.d('SearchGames event received: ${event.query}');
  }

  Future<void> _onCreateGame(
    CreateGame event,
    Emitter<LibraryState> emit,
  ) async {
    // CreateGame is handled at the UI level via the repository directly.
    // This event is kept for consistency but does not mutate library state.
    _logger.d('CreateGame event received: ${event.title}');
  }

  /// Reloads the library list with the current status filter.
  Future<void> _reload(Emitter<LibraryState> emit) async {
    final response = await _libraryRepository.listLibrary(
      status: _currentStatusFilter,
    );

    final hasMore = response.offset + response.items.length < response.total;

    emit(
      LibraryLoaded(
        groups: response.items,
        total: response.total,
        hasMore: hasMore,
      ),
    );
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
