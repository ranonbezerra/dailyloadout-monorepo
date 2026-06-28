import 'package:app/core/auth/email_verification.dart';
import 'package:app/core/concierge/concierge_models.dart';
import 'package:app/core/concierge/concierge_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'concierge_event.dart';
part 'concierge_state.dart';

const _fallbackError = 'Sorry, something went wrong. Please try again.';

class ConciergeBloc extends Bloc<ConciergeEvent, ConciergeState> {
  ConciergeBloc({required ConciergeRepository conciergeRepository})
    : _conciergeRepository = conciergeRepository,
      super(const ConciergeState()) {
    on<SendConciergeMessage>(_onSendMessage);
    on<CancelConciergeStream>(_onCancel);
  }

  final ConciergeRepository _conciergeRepository;
  CancelToken? _cancelToken;

  Future<void> _onSendMessage(
    SendConciergeMessage event,
    Emitter<ConciergeState> emit,
  ) async {
    final text = event.message.trim();
    if (text.isEmpty || state.isStreaming) return;

    // Append the user message + an empty assistant placeholder to fill in.
    emit(
      state.copyWith(
        messages: [
          ...state.messages,
          ChatMessage(role: ChatRole.user, text: text),
          const ChatMessage(role: ChatRole.assistant, text: ''),
        ],
        status: ConciergeStatus.streaming,
        clearActiveTool: true,
      ),
    );

    final cancelToken = CancelToken();
    _cancelToken = cancelToken;
    final buffer = StringBuffer();
    Recommendation? recommendation;
    try {
      final stream = _conciergeRepository.streamChat(
        message: text,
        threadId: state.threadId,
        cancelToken: cancelToken,
      );
      var failed = false;
      await for (final delta in stream) {
        if (delta.error != null) {
          failed = true;
          emit(
            state.copyWith(
              messages: _withLastAssistant(delta.error!),
              status: ConciergeStatus.error,
              errorMessage: delta.error,
              clearActiveTool: true,
            ),
          );
          // Stop here so the trailing done event can't clear the error.
          break;
        }
        if (delta.token != null) {
          buffer.write(delta.token);
          emit(
            state.copyWith(
              messages: _withLastAssistant(buffer.toString(), recommendation),
            ),
          );
        }
        if (delta.tool != null) {
          emit(
            delta.phase == 'end'
                ? state.copyWith(clearActiveTool: true)
                : state.copyWith(activeTool: delta.tool),
          );
        }
        if (delta.recommendation != null) {
          recommendation = delta.recommendation;
          emit(
            state.copyWith(
              messages: _withLastAssistant(buffer.toString(), recommendation),
            ),
          );
        }
        if (delta.degrade != null) {
          buffer
            ..write('\n\n')
            ..write(delta.degrade);
          emit(
            state.copyWith(
              messages: _withLastAssistant(buffer.toString(), recommendation),
            ),
          );
        }
        if (delta.done && delta.threadId != null) {
          emit(state.copyWith(threadId: delta.threadId));
        }
      }
      if (!failed) {
        emit(
          state.copyWith(status: ConciergeStatus.idle, clearActiveTool: true),
        );
      }
    } on DioException catch (error) {
      if (CancelToken.isCancel(error)) {
        // User cancelled: keep the partial reply, just stop streaming.
        emit(
          state.copyWith(status: ConciergeStatus.idle, clearActiveTool: true),
        );
      } else if (EmailVerification.isUnverifiedError(error)) {
        // The concierge is a cost-bearing route; 403 until email is verified.
        _emitError(emit, message: EmailVerification.friendlyMessage);
      } else {
        _emitError(emit);
      }
    } on Exception {
      _emitError(emit);
    } finally {
      _cancelToken = null;
    }
  }

  void _onCancel(CancelConciergeStream event, Emitter<ConciergeState> emit) {
    // Aborts the dio request; the send handler catches the cancellation and
    // settles the state (keeping the partial reply).
    _cancelToken?.cancel();
  }

  /// Replaces the trailing assistant placeholder with [text] and an optional
  /// validated [recommendation].
  List<ChatMessage> _withLastAssistant(
    String text, [
    Recommendation? recommendation,
  ]) {
    final messages = [...state.messages];
    messages[messages.length - 1] = ChatMessage(
      role: ChatRole.assistant,
      text: text,
      recommendation: recommendation,
    );
    return messages;
  }

  void _emitError(Emitter<ConciergeState> emit, {String? message}) {
    final text = message ?? _fallbackError;
    emit(
      state.copyWith(
        messages: _withLastAssistant(text),
        status: ConciergeStatus.error,
        errorMessage: text,
        clearActiveTool: true,
      ),
    );
  }
}
