import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// User-facing copy for the email-verification surface. Kept here (rather than
/// inline) so there are no scattered hardcoded strings.
abstract final class VerifyEmailStrings {
  static const String title = 'Verify your email';
  static const String body =
      'Check your inbox and tap the verification link to unlock '
      'AI features like loadouts, briefings and the concierge.';
  static const String resend = 'Resend email';
  static const String refresh = "I've verified — refresh";
  static const String resentFallback =
      'Verification email sent. Check your inbox.';
  static const String stillUnverified =
      'Not verified yet. Tap the link in your email, then refresh.';
  static const String nowVerified = "Email verified — you're all set!";
}

/// A persistent banner shown whenever the authenticated user has not yet
/// verified their email. It explains why verification matters and offers two
/// actions: resend the verification email, and re-check the profile after the
/// user has clicked the link in the web app.
///
/// Renders nothing (zero height) when the user is verified or unauthenticated,
/// so it is safe to mount unconditionally in the app shell.
class VerifyEmailBanner extends StatelessWidget {
  const VerifyEmailBanner({super.key});

  void _onResend(BuildContext context) {
    context.read<AuthBloc>().add(const ResendVerificationRequested());
  }

  void _onRefresh(BuildContext context) {
    context.read<AuthBloc>().add(const RefreshUserRequested());
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AuthBloc, AuthState>(
      // Only react to states that carry resend/refresh feedback or a change in
      // the verification flag.
      listenWhen: (previous, current) =>
          current is VerificationEmailSent ||
          current is VerificationEmailFailed ||
          (previous is AuthenticatedState &&
              current is AuthenticatedState &&
              previous.user.emailVerified != current.user.emailVerified),
      listener: (context, state) {
        final messenger = ScaffoldMessenger.of(context);
        if (state is VerificationEmailSent) {
          messenger
            ..hideCurrentSnackBar()
            ..showSnackBar(SnackBar(content: Text(state.message)));
        } else if (state is VerificationEmailFailed) {
          messenger
            ..hideCurrentSnackBar()
            ..showSnackBar(SnackBar(content: Text(state.message)));
        } else if (state is AuthenticatedState && state.user.emailVerified) {
          messenger
            ..hideCurrentSnackBar()
            ..showSnackBar(
              const SnackBar(content: Text(VerifyEmailStrings.nowVerified)),
            );
        }
      },
      buildWhen: (previous, current) =>
          _isUnverified(previous) != _isUnverified(current),
      builder: (context, state) {
        if (!_isUnverified(state)) return const SizedBox.shrink();
        return _Banner(
          onResend: () => _onResend(context),
          onRefresh: () => _onRefresh(context),
        );
      },
    );
  }

  static bool _isUnverified(AuthState state) =>
      state is AuthenticatedState && !state.user.emailVerified;
}

class _Banner extends StatelessWidget {
  const _Banner({required this.onResend, required this.onRefresh});

  final VoidCallback onResend;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: DLColors.surface2,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.mark_email_unread_outlined,
                    color: DLColors.coral,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      VerifyEmailStrings.title,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                VerifyEmailStrings.body,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  TextButton(
                    onPressed: onResend,
                    child: const Text(VerifyEmailStrings.resend),
                  ),
                  const SizedBox(width: 4),
                  TextButton(
                    onPressed: onRefresh,
                    child: const Text(VerifyEmailStrings.refresh),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
