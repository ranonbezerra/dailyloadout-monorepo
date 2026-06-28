import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Runtime feature flags, read from the loaded `.env` and defaulting to OFF.
///
/// Keeps experimental surfaces (e.g. the Backlog Concierge chat) hidden in
/// production builds until they are validated against a real LLM.
class FeatureFlags {
  const FeatureFlags({this.backlogConcierge = false});

  /// Builds flags from environment variables. Unknown/missing values are off.
  factory FeatureFlags.fromEnv() {
    return FeatureFlags(
      backlogConcierge: dotenv.maybeGet('ENABLE_CONCIERGE') == 'true',
    );
  }

  /// Backlog Concierge conversational chat (Epic 11).
  final bool backlogConcierge;
}
