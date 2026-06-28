import 'dart:async';

import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/loadout/bloc/loadout_bloc.dart';
import 'package:app/features/loadout/view/loadout_questionnaire.dart';
import 'package:app/features/loadout/view/loadout_result_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Main loadout page combining the questionnaire form
/// and the results section.
class LoadoutPage extends StatefulWidget {
  const LoadoutPage({super.key});

  @override
  State<LoadoutPage> createState() => _LoadoutPageState();
}

class _LoadoutPageState extends State<LoadoutPage> {
  // Questionnaire state
  String _mood = 'chill';
  double _minutes = 60;
  String _mentalEnergy = 'medium';
  bool _multiMode = false;
  final _contextController = TextEditingController();

  // Tracks which loadout is currently being actioned
  String? _actioningId;

  // Tracks which loadout is currently generating a briefing.
  String? _briefingId;

  // Generated briefing text keyed by loadout public id.
  final Map<String, String> _briefings = {};

  // Keeps a local copy of results so we can update
  // individual items after accept / reject without
  // losing the full list.
  List<Loadout> _results = [];

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
    context.read<LoadoutBloc>().add(
      CreateLoadout(
        mood: _mood,
        availableMinutes: _minutes.round(),
        mentalEnergy: _mentalEnergy,
        count: _multiMode ? 3 : 1,
        context: ctx.isEmpty ? null : ctx,
      ),
    );
  }

  void _onAccept(Loadout loadout) {
    setState(() => _actioningId = loadout.publicId);
    context.read<LoadoutBloc>().add(AcceptLoadout(publicId: loadout.publicId));
  }

  void _onReject(Loadout loadout) {
    setState(() => _actioningId = loadout.publicId);
    context.read<LoadoutBloc>().add(RejectLoadout(publicId: loadout.publicId));
  }

  void _onGetBriefing(Loadout loadout, String mode) {
    final entryId = loadout.libraryEntry?.publicId;
    if (entryId == null) return;
    setState(() => _briefingId = loadout.publicId);
    context.read<LoadoutBloc>().add(
      GenerateLoadoutBriefing(
        publicId: loadout.publicId,
        libraryEntryPublicId: entryId,
        mode: mode,
      ),
    );
  }

  void _onStartWithBriefing(Loadout loadout) {
    setState(() => _actioningId = loadout.publicId);
    context.read<LoadoutBloc>().add(
      AcceptLoadout(
        publicId: loadout.publicId,
        briefingText: _briefings[loadout.publicId],
      ),
    );
  }

  /// Replaces a loadout in the local results list
  /// after an accept/reject response.
  void _replaceInResults(Loadout updated) {
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
      appBar: AppBar(title: const Text('Daily Loadout')),
      body: BlocConsumer<LoadoutBloc, LoadoutState>(
        listener: _onStateChange,
        builder: (context, state) {
          if (state is LoadoutLoading) {
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
                  LoadoutQuestionnaire(
                    mood: _mood,
                    minutes: _minutes,
                    mentalEnergy: _mentalEnergy,
                    multiMode: _multiMode,
                    contextController: _contextController,
                    isLoading: false,
                    error: state is LoadoutError ? state.message : null,
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

  void _onStateChange(BuildContext context, LoadoutState state) {
    if (state is LoadoutResultsLoaded) {
      setState(() {
        _results = state.results;
        _actioningId = null;
      });
    }

    if (state is LoadoutAccepted) {
      _replaceInResults(state.loadout);
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(
            content: Text('Mission started!'),
            backgroundColor: DLColors.green,
          ),
        );
      _navigateToPlayHubAfterDelay();
    }

    if (state is LoadoutRejected) {
      _replaceInResults(state.loadout);
    }

    if (state is LoadoutBriefingReady) {
      setState(() {
        _briefings[state.publicId] = state.briefingText;
        _briefingId = null;
      });
    }

    if (state is LoadoutError &&
        (_actioningId != null || _briefingId != null)) {
      setState(() {
        _actioningId = null;
        _briefingId = null;
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
          LoadoutResultCard(
            loadout: _results[i],
            rank: i,
            totalResults: _results.length,
            isActioning: _actioningId == _results[i].publicId,
            isGeneratingBriefing: _briefingId == _results[i].publicId,
            briefingText: _briefings[_results[i].publicId],
            onAccept: () => _onAccept(_results[i]),
            onReject: () => _onReject(_results[i]),
            onGetBriefing: (mode) => _onGetBriefing(_results[i], mode),
            onStartWithBriefing: () => _onStartWithBriefing(_results[i]),
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
              color: DLColors.coral,
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
                color: DLColors.textMuted,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}
