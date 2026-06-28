part of 'concierge_bloc.dart';

sealed class ConciergeEvent extends Equatable {
  const ConciergeEvent();

  @override
  List<Object?> get props => [];
}

/// Send a user message and stream the Concierge's guarded reply.
final class SendConciergeMessage extends ConciergeEvent {
  const SendConciergeMessage(this.message);

  final String message;

  @override
  List<Object?> get props => [message];
}

/// Cancel the in-flight turn mid-stream, keeping the partial reply.
final class CancelConciergeStream extends ConciergeEvent {
  const CancelConciergeStream();
}
