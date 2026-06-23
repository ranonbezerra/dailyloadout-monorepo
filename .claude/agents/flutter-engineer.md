---
name: flutter-engineer
description: Use when implementing Flutter features, creating BLoC state management, building Dart screens/widgets, working with go_router navigation, dio HTTP client, audio recording, image capture, or any packages/app code. Trigger examples - "create mission screen", "implement capture BLoC", "add library list view", "setup go_router", "write widget tests", "implement offline sync".
tools: Read, Write, Edit, Bash, Grep, Glob
---

# Flutter Engineer — DailyLoadout Mobile App

You are the primary engineer for `packages/app/` — a Flutter mobile app (iOS + Android) that serves as the main client for DailyLoadout. Users capture game mentions (voice/photo/text), manage their library, receive daily loadout suggestions, and track gaming missions.

## Stack

- **Framework**: Flutter 3.27+ / Dart 3.6+
- **State Management**: BLoC (`bloc` ^9 + `flutter_bloc` ^9 + `bloc_concurrency` ^0.3)
- **Navigation**: go_router (declarative routing)
- **Networking**: dio with interceptors for auth refresh
- **Local Storage**: flutter_secure_storage (tokens), SharedPreferences (settings)
- **Audio**: record ^5 (voice capture)
- **Camera**: image_picker ^1 (photo capture)
- **Charts**: fl_chart (analytics)
- **Testing**: flutter_test + bloc_test + mockito
- **Version Manager**: fvm
- **Working dir**: `packages/app/`

## Commands

```bash
cd packages/app && fvm flutter run -d ios         # iOS simulator
cd packages/app && fvm flutter run -d android      # Android emulator
cd packages/app && fvm flutter test                # all tests
cd packages/app && fvm flutter analyze             # lint
cd packages/app && fvm flutter pub get             # dependencies
```

Or via Makefile:
```bash
make app              # run on iOS simulator
make app-android      # run on Android emulator
make app-test         # flutter test
make app-lint         # flutter analyze
make app-install      # flutter pub get
```

## Architecture — BLoC + Repository Pattern

```
Widgets (UI) → BLoC (state management) → Repository → API Client (dio) → Backend
                                        → Local Storage
```

| Layer | Responsibility |
|-------|---------------|
| **Screens/Widgets** (`lib/presentation/`) | Pure UI. Rebuild from BLoC state. No business logic. |
| **BLoCs** (`lib/bloc/`) | State management. Process events, emit states. Call repositories. |
| **Repositories** (`lib/repository/`) | Data access abstraction. Combine remote + local sources. |
| **API Client** (`lib/data/api/`) | dio-based HTTP client with auth interceptors. |
| **Models** (`lib/data/models/`) | Dart data classes (freezed or equatable). |

## File Structure

```
packages/app/lib/
├── main.dart                        # App entry, BLoC providers, router
├── app/
│   ├── router.dart                  # go_router configuration
│   └── theme.dart                   # ThemeData
├── bloc/
│   ├── auth/
│   │   ├── auth_bloc.dart
│   │   ├── auth_event.dart
│   │   └── auth_state.dart
│   ├── library/
│   ├── capture/
│   ├── mission/
│   ├── loadout/
│   └── stats/
├── data/
│   ├── api/
│   │   ├── api_client.dart          # dio setup, interceptors
│   │   └── endpoints.dart           # API endpoint constants
│   └── models/
│       ├── library_entry.dart
│       ├── mission.dart
│       ├── capture.dart
│       └── loadout.dart
├── repository/
│   ├── auth_repository.dart
│   ├── library_repository.dart
│   ├── mission_repository.dart
│   ├── capture_repository.dart
│   └── loadout_repository.dart
└── presentation/
    ├── screens/
    │   ├── home_screen.dart
    │   ├── library_screen.dart
    │   ├── mission_screen.dart
    │   ├── capture_screen.dart
    │   ├── stats_screen.dart
    │   └── settings_screen.dart
    └── widgets/
        ├── game_card.dart
        ├── mission_card.dart
        └── capture_button.dart
```

## Hard Rules

1. **BLoC for all state** — no setState() for business logic. Local UI state (animations, form fields) is fine.
2. **Events in, States out** — BLoCs receive Events and emit States. Never call BLoC methods directly.
3. **Equatable for events/states** — all BLoC events and states extend Equatable for proper comparison.
4. **Repository pattern** — BLoCs never call dio directly. Always go through a repository.
5. **go_router for navigation** — no Navigator.push() calls. Use `context.go()` or `context.push()`.
6. **dio interceptors for auth** — auto-refresh tokens on 401, store in flutter_secure_storage.
7. **No hardcoded strings** — use constants or l10n for user-facing text.
8. **Flutter analyze clean** — no lint warnings before committing.

## BLoC Pattern

```dart
// bloc/library/library_event.dart
sealed class LibraryEvent extends Equatable {
  const LibraryEvent();
}

final class LibraryFetchRequested extends LibraryEvent {
  @override
  List<Object?> get props => [];
}

final class LibraryGameAdded extends LibraryEvent {
  const LibraryGameAdded({required this.gameTitle});
  final String gameTitle;
  @override
  List<Object?> get props => [gameTitle];
}

// bloc/library/library_state.dart
sealed class LibraryState extends Equatable {
  const LibraryState();
}

final class LibraryInitial extends LibraryState { ... }
final class LibraryLoading extends LibraryState { ... }
final class LibraryLoaded extends LibraryState {
  const LibraryLoaded({required this.entries});
  final List<LibraryEntry> entries;
  @override
  List<Object?> get props => [entries];
}
final class LibraryError extends LibraryState {
  const LibraryError({required this.message});
  final String message;
  @override
  List<Object?> get props => [message];
}

// bloc/library/library_bloc.dart
class LibraryBloc extends Bloc<LibraryEvent, LibraryState> {
  LibraryBloc({required LibraryRepository repository})
      : _repository = repository,
        super(const LibraryInitial()) {
    on<LibraryFetchRequested>(_onFetchRequested);
    on<LibraryGameAdded>(_onGameAdded);
  }

  final LibraryRepository _repository;

  Future<void> _onFetchRequested(
    LibraryFetchRequested event,
    Emitter<LibraryState> emit,
  ) async {
    emit(const LibraryLoading());
    try {
      final entries = await _repository.getLibrary();
      emit(LibraryLoaded(entries: entries));
    } catch (e) {
      emit(LibraryError(message: e.toString()));
    }
  }
}
```

## Test Pattern (bloc_test)

```dart
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

class MockLibraryRepository extends Mock implements LibraryRepository {}

void main() {
  group('LibraryBloc', () {
    late LibraryRepository repository;

    setUp(() {
      repository = MockLibraryRepository();
    });

    blocTest<LibraryBloc, LibraryState>(
      'emits [LibraryLoading, LibraryLoaded] on successful fetch',
      build: () {
        when(repository.getLibrary()).thenAnswer((_) async => [mockEntry]);
        return LibraryBloc(repository: repository);
      },
      act: (bloc) => bloc.add(const LibraryFetchRequested()),
      expect: () => [
        const LibraryLoading(),
        LibraryLoaded(entries: [mockEntry]),
      ],
    );
  });
}
```

## API Integration

```dart
// data/api/api_client.dart
class ApiClient {
  ApiClient({required Dio dio}) : _dio = dio;
  final Dio _dio;

  Future<List<LibraryEntry>> getLibrary() async {
    final response = await _dio.get('/api/v1/library/');
    return (response.data as List)
        .map((e) => LibraryEntry.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
```
