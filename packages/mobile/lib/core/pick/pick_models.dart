import 'package:app/core/library/library_models.dart';
import 'package:equatable/equatable.dart';

/// Mood options for the pick questionnaire.
enum PickMood { chill, focused, energetic, adventurous }

/// Mental energy level for pick generation.
enum MentalEnergy { low, medium, high }

/// Full pick with optional related library entry.
class Pick extends Equatable {
  const Pick({
    required this.publicId,
    required this.mood,
    required this.availableMinutes,
    required this.mentalEnergy,
    required this.createdAt,
    required this.updatedAt,
    this.libraryEntry,
    this.context,
    this.reasoning,
    this.action,
  });

  factory Pick.fromJson(Map<String, dynamic> json) {
    return Pick(
      publicId: json['public_id'] as String,
      libraryEntry: json['library_entry'] != null
          ? LibraryEntry.fromJson(json['library_entry'] as Map<String, dynamic>)
          : null,
      mood: json['mood'] as String,
      availableMinutes: json['available_minutes'] as int,
      mentalEnergy: json['mental_energy'] as String,
      context: json['context'] as String?,
      reasoning: json['reasoning'] as String?,
      action: json['action'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  final String publicId;
  final LibraryEntry? libraryEntry;
  final String mood;
  final int availableMinutes;
  final String mentalEnergy;
  final String? context;
  final String? reasoning;
  final String? action;
  final DateTime createdAt;
  final DateTime updatedAt;

  @override
  List<Object?> get props => [
    publicId,
    libraryEntry,
    mood,
    availableMinutes,
    mentalEnergy,
    context,
    reasoning,
    action,
    createdAt,
    updatedAt,
  ];
}

/// Lightweight pick for list views.
class PickListItem extends Equatable {
  const PickListItem({
    required this.publicId,
    required this.mood,
    required this.availableMinutes,
    required this.mentalEnergy,
    required this.createdAt,
    this.libraryEntry,
    this.reasoning,
    this.action,
  });

  factory PickListItem.fromJson(Map<String, dynamic> json) {
    return PickListItem(
      publicId: json['public_id'] as String,
      libraryEntry: json['library_entry'] != null
          ? LibraryEntry.fromJson(json['library_entry'] as Map<String, dynamic>)
          : null,
      mood: json['mood'] as String,
      availableMinutes: json['available_minutes'] as int,
      mentalEnergy: json['mental_energy'] as String,
      reasoning: json['reasoning'] as String?,
      action: json['action'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String publicId;
  final LibraryEntry? libraryEntry;
  final String mood;
  final int availableMinutes;
  final String mentalEnergy;
  final String? reasoning;
  final String? action;
  final DateTime createdAt;

  @override
  List<Object?> get props => [
    publicId,
    libraryEntry,
    mood,
    availableMinutes,
    mentalEnergy,
    reasoning,
    action,
    createdAt,
  ];
}

/// Paginated response for pick listings.
class PickListResponse extends Equatable {
  const PickListResponse({required this.items, required this.total});

  factory PickListResponse.fromJson(Map<String, dynamic> json) {
    return PickListResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => PickListItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  final List<PickListItem> items;
  final int total;

  @override
  List<Object?> get props => [items, total];
}
