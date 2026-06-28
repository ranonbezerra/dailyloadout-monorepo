import 'package:equatable/equatable.dart';

/// Who authored a chat message.
enum ChatRole { user, assistant }

/// A validated game pick surfaced by the Concierge (Epic 16).
class Recommendation extends Equatable {
  const Recommendation({required this.id, required this.title});

  factory Recommendation.fromJson(Map<String, dynamic> json) {
    return Recommendation(
      id: json['id'] as String,
      title: json['title'] as String,
    );
  }

  final String id;
  final String title;

  @override
  List<Object?> get props => [id, title];
}

/// A single message in a Concierge conversation.
class ChatMessage extends Equatable {
  const ChatMessage({
    required this.role,
    required this.text,
    this.recommendation,
  });

  final ChatRole role;
  final String text;

  /// A validated pick attached to an assistant message — rendered as a CTA.
  final Recommendation? recommendation;

  ChatMessage copyWith({String? text, Recommendation? recommendation}) {
    return ChatMessage(
      role: role,
      text: text ?? this.text,
      recommendation: recommendation ?? this.recommendation,
    );
  }

  @override
  List<Object?> get props => [role, text, recommendation];
}

/// One Server-Sent Event from `POST /v1/concierge/chat` (ROADMAP Epic 16).
///
/// As a turn streams, events carry a [token] of prose, a [tool] call (with
/// [phase]), a validated [recommendation], or a [degrade] nudge. The final
/// event has [done] set and supplies the [threadId] for the next turn.
class ConciergeDelta extends Equatable {
  const ConciergeDelta({
    this.token,
    this.tool,
    this.phase,
    this.recommendation,
    this.degrade,
    this.error,
    this.done = false,
    this.threadId,
  });

  factory ConciergeDelta.fromJson(Map<String, dynamic> json) {
    final rec = json['recommendation'] as Map<String, dynamic>?;
    return ConciergeDelta(
      token: json['token'] as String?,
      tool: json['tool'] as String?,
      phase: json['phase'] as String?,
      recommendation: rec != null ? Recommendation.fromJson(rec) : null,
      degrade: json['degrade'] as String?,
      error: json['error'] as String?,
      done: json['done'] as bool? ?? false,
      threadId: json['thread_id'] as String?,
    );
  }

  /// A chunk of user-facing prose to append live.
  final String? token;

  /// A tool call name, paired with [phase] (`start` | `end`).
  final String? tool;
  final String? phase;

  /// A validated game pick.
  final Recommendation? recommendation;

  /// The pick failed the library guard; a clarifying nudge to show instead.
  final String? degrade;

  /// Set when the server reports a failure mid-stream (e.g. model unavailable).
  final String? error;
  final bool done;
  final String? threadId;

  @override
  List<Object?> get props => [
    token,
    tool,
    phase,
    recommendation,
    degrade,
    error,
    done,
    threadId,
  ];
}
