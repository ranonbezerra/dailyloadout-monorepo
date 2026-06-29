import 'dart:async';

import 'package:app/core/pick/pick_models.dart';
import 'package:app/core/theme/slate_theme.dart';
import 'package:app/features/pick/bloc/pick_bloc.dart';
import 'package:app/features/pick/view/pick_questionnaire.dart';
import 'package:app/features/pick/view/pick_result_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Main pick page combining the questionnaire form
/// and the results section.
class PickPage extends StatefulWidget {
  const PickPage({super.key});

  @override
  State<PickPage> createState() => _PickPageState();
}

class _PickPageState extends State<PickPage> {
  // Questionnaire state
  String _mood = 'chill';
  double _minutes = 60;
  String _mentalEnergy = 'medium';
  bool _multiMode = false;
  final _contextController = TextEditingController();

  // Tracks which pick is currently being actioned
  String? _actioningId;

  // Tracks which pick is currently generating a recap.
  String? _recapId;

  // Generated recap text keyed by pick public id.
  final Map<String, String> _recaps = {};

  // Keeps a local copy of results so we can update
  // individual items after accept / reject without
  // losing the full list.
  List<Pick> _results = [];

  bool get _allActioned =>
      _results.isNotEmpty &&
      _results.every((l) => l.action == 'accepted' || l.action == 'rejected');

  bool get _showResults => _results.isNotEmpty && !_allActioned;

  @override
  void dispose() {
    _contextController.dispose();
    super.dispose();
  }

  void _onRoll() {
    final ctx = _contextController.text.trim();
    context.read<PickBloc>().add(
      CreatePick(
        mood: _mood,
        availableMinutes: _minutes.round(),
        mentalEnergy: _mentalEnergy,
        count: _multiMode ? 3 : 1,
        context: ctx.isEmpty ? null : ctx,
      ),
    );
  }

  void _onAccept(Pick pick) {
    setState(() => _actioningId = pick.publicId);
    context.read<PickBloc>().add(AcceptPick(publicId: pick.publicId));
  }

  void _onReject(Pick pick) {
    setState(() => _actioningId = pick.publicId);
    context.read<PickBloc>().add(RejectPick(publicId: pick.publicId));
  }

  void _onGetRecap(Pick pick, String mode) {
    final entryId = pick.libraryEntry?.publicId;
    if (entryId == null) return;
    setState(() => _recapId = pick.publicId);
    context.read<PickBloc>().add(
      GeneratePickRecap(
        publicId: pick.publicId,
        libraryEntryPublicId: entryId,
        mode: mode,
      ),
    );
  }

  void _onStartWithRecap(Pick pick) {
    setState(() => _actioningId = pick.publicId);
    context.read<PickBloc>().add(
      AcceptPick(publicId: pick.publicId, recapText: _recaps[pick.publicId]),
    );
  }

  /// Replaces a pick in the local results list
  /// after an accept/reject response.
  void _replaceInResults(Pick updated) {
    final idx = _results.indexWhere((l) => l.publicId == updated.publicId);
    if (idx != -1) {
      setState(() {
        _results = List.of(_results)..[idx] = updated;
        _actioningId = null;
      });
    }
  }

  Future<void> _navigateToPlayHubAfterDelay() async {
    await Future<void>.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    context.go('/play');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Daily Pick')),
      body: BlocConsumer<PickBloc, PickState>(
        listener: _onStateChange,
        builder: (context, state) {
          if (state is PickLoading) {
            return const _LoadingView();
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_showResults)
                  _buildResults(context)
                else
                  PickQuestionnaire(
                    mood: _mood,
                    minutes: _minutes,
                    mentalEnergy: _mentalEnergy,
                    multiMode: _multiMode,
                    contextController: _contextController,
                    isLoading: false,
                    error: state is PickError ? state.message : null,
                    onMoodChanged: (v) => setState(() => _mood = v),
                    onMinutesChanged: (v) => setState(() => _minutes = v),
                    onEnergyChanged: (v) => setState(() => _mentalEnergy = v),
                    onMultiModeChanged: (v) => setState(() => _multiMode = v),
                    onRoll: _onRoll,
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _onStateChange(BuildContext context, PickState state) {
    if (state is PickResultsLoaded) {
      setState(() {
        _results = state.results;
        _actioningId = null;
      });
    }

    if (state is PickAccepted) {
      _replaceInResults(state.pick);
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(
            content: Text('Session started!'),
            backgroundColor: SlateColors.green,
          ),
        );
      _navigateToPlayHubAfterDelay();
    }

    if (state is PickRejected) {
      _replaceInResults(state.pick);
    }

    if (state is PickRecapReady) {
      setState(() {
        _recaps[state.publicId] = state.recapText;
        _recapId = null;
      });
    }

    if (state is PickError && (_actioningId != null || _recapId != null)) {
      setState(() {
        _actioningId = null;
        _recapId = null;
      });
    }
  }

  // -- Results -----------------------------------------------

  Widget _buildResults(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Your picks', style: theme.textTheme.titleLarge),
        const SizedBox(height: 16),
        for (var i = 0; i < _results.length; i++)
          PickResultCard(
            pick: _results[i],
            rank: i,
            totalResults: _results.length,
            isActioning: _actioningId == _results[i].publicId,
            isGeneratingRecap: _recapId == _results[i].publicId,
            recapText: _recaps[_results[i].publicId],
            onAccept: () => _onAccept(_results[i]),
            onReject: () => _onReject(_results[i]),
            onGetRecap: (mode) => _onGetRecap(_results[i], mode),
            onStartWithRecap: () => _onStartWithRecap(_results[i]),
          ),
        const SizedBox(height: 16),
        Center(
          child: TextButton.icon(
            onPressed: () => setState(() {
              _results = [];
              _actioningId = null;
            }),
            icon: const Icon(Icons.refresh),
            label: const Text('Roll again'),
          ),
        ),
      ],
    );
  }
}

/// Full-screen loading state with rotating messages
/// shown while the LLM picks games.
class _LoadingView extends StatefulWidget {
  const _LoadingView();

  @override
  State<_LoadingView> createState() => _LoadingViewState();
}

class _LoadingViewState extends State<_LoadingView> {
  static const _messages = [
    'Scanning your library...',
    'Analyzing your mood...',
    'Consulting the AI...',
    'Finding the perfect match...',
    'Almost there...',
  ];

  int _index = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(
      const Duration(seconds: 3),
      (_) => setState(() => _index = (_index + 1) % _messages.length),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 48,
            height: 48,
            child: CircularProgressIndicator(
              strokeWidth: 3,
              color: SlateColors.coral,
            ),
          ),
          const SizedBox(height: 24),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 400),
            transitionBuilder: (child, animation) {
              final isIncoming = child.key == ValueKey(_index);
              final offsetTween = Tween<Offset>(
                begin: Offset(0, isIncoming ? 0.5 : -0.5),
                end: Offset.zero,
              );
              return SlideTransition(
                position: offsetTween.animate(animation),
                child: FadeTransition(opacity: animation, child: child),
              );
            },
            child: Text(
              _messages[_index],
              key: ValueKey(_index),
              style: theme.textTheme.titleMedium?.copyWith(
                color: SlateColors.textMuted,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}
