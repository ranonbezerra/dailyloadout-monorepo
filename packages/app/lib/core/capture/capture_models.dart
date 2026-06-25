import 'package:equatable/equatable.dart';

/// Represents a single extracted game candidate from a capture.
class CaptureCandidate extends Equatable {
  const CaptureCandidate({
    required this.publicId,
    required this.title,
    required this.status,
    this.platformHint,
    this.igdbTitle,
    this.igdbCoverUrl,
    this.igdbSummary,
    this.igdbGenres,
    this.confidence,
  });

  factory CaptureCandidate.fromJson(Map<String, dynamic> json) {
    return CaptureCandidate(
      publicId: json['public_id'] as String,
      title: json['title'] as String,
      platformHint: json['platform_hint'] as String?,
      igdbTitle: json['igdb_title'] as String?,
      igdbCoverUrl: json['igdb_cover_url'] as String?,
      igdbSummary: json['igdb_summary'] as String?,
      igdbGenres: (json['igdb_genres'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      confidence: (json['confidence'] as num?)?.toDouble(),
      status: json['status'] as String,
    );
  }

  final String publicId;
  final String title;
  final String? platformHint;
  final String? igdbTitle;
  final String? igdbCoverUrl;
  final String? igdbSummary;
  final List<String>? igdbGenres;
  final double? confidence;
  final String status; // pending, confirmed, rejected

  @override
  List<Object?> get props => [
    publicId,
    title,
    platformHint,
    igdbTitle,
    igdbCoverUrl,
    igdbSummary,
    igdbGenres,
    confidence,
    status,
  ];
}

/// Represents a text/voice/photo capture with its extracted candidates.
class Capture extends Equatable {
  const Capture({
    required this.publicId,
    required this.inputType,
    required this.status,
    required this.candidates,
    required this.createdAt,
    required this.updatedAt,
    this.rawText,
    this.errorMessage,
  });

  factory Capture.fromJson(Map<String, dynamic> json) {
    return Capture(
      publicId: json['public_id'] as String,
      inputType: json['input_type'] as String,
      rawText: json['raw_text'] as String?,
      status: json['status'] as String,
      errorMessage: json['error_message'] as String?,
      candidates:
          (json['candidates'] as List<dynamic>?)
              ?.map((e) => CaptureCandidate.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  final String publicId;
  final String inputType;
  final String? rawText;
  final String status; // queued, processing, review, committed, etc.
  final String? errorMessage;
  final List<CaptureCandidate> candidates;
  final DateTime createdAt;
  final DateTime updatedAt;

  @override
  List<Object?> get props => [
    publicId,
    inputType,
    rawText,
    status,
    errorMessage,
    candidates,
    createdAt,
    updatedAt,
  ];
}

/// Result of a bulk candidate confirmation.
class BulkConfirmResult extends Equatable {
  const BulkConfirmResult({required this.confirmed, required this.rejected});

  factory BulkConfirmResult.fromJson(Map<String, dynamic> json) {
    return BulkConfirmResult(
      confirmed: json['confirmed'] as int,
      rejected: json['rejected'] as int,
    );
  }

  final int confirmed;
  final int rejected;

  @override
  List<Object?> get props => [confirmed, rejected];
}

/// Result of transcribing an audio file.
class TranscribeResult extends Equatable {
  const TranscribeResult({
    required this.text,
    this.language,
    this.durationSeconds,
  });

  factory TranscribeResult.fromJson(Map<String, dynamic> json) {
    return TranscribeResult(
      text: json['text'] as String,
      language: json['language'] as String?,
      durationSeconds: (json['duration_seconds'] as num?)?.toDouble(),
    );
  }

  final String text;
  final String? language;
  final double? durationSeconds;

  @override
  List<Object?> get props => [text, language, durationSeconds];
}

/// Paginated response for capture listings.
class CaptureListResponse extends Equatable {
  const CaptureListResponse({required this.items, required this.total});

  factory CaptureListResponse.fromJson(Map<String, dynamic> json) {
    return CaptureListResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => Capture.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  final List<Capture> items;
  final int total;

  @override
  List<Object?> get props => [items, total];
}
