import 'package:app/core/capture/capture_models.dart';
import 'package:app/features/library_import/bloc/library_import_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('LibraryImportEvent equality', () {
    test('SubmitLibraryImport compares by image paths', () {
      const a = SubmitLibraryImport(imagePaths: ['a.jpg', 'b.jpg']);
      const b = SubmitLibraryImport(imagePaths: ['a.jpg', 'b.jpg']);
      const c = SubmitLibraryImport(imagePaths: ['a.jpg']);

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a.props, [
        ['a.jpg', 'b.jpg'],
      ]);
    });

    test('BulkConfirmImport compares by all fields incl. default status', () {
      const a = BulkConfirmImport(
        captureId: 'cap-1',
        confirmIds: ['x'],
        platformId: 3,
      );
      const b = BulkConfirmImport(
        captureId: 'cap-1',
        confirmIds: ['x'],
        platformId: 3,
      );
      const c = BulkConfirmImport(
        captureId: 'cap-1',
        confirmIds: ['x'],
        platformId: 3,
        status: 'playing',
      );

      expect(a, equals(b));
      expect(a.status, 'backlog');
      expect(a, isNot(equals(c)));
      expect(a.props, [
        'cap-1',
        ['x'],
        3,
        'backlog',
      ]);
    });
  });

  group('LibraryImportState equality', () {
    final capture = Capture(
      publicId: 'cap-1',
      inputType: 'library_import',
      status: 'review',
      candidates: const [],
      createdAt: DateTime(2025),
      updatedAt: DateTime(2025),
    );

    test('Review compares by capture', () {
      expect(
        LibraryImportReview(capture: capture),
        equals(LibraryImportReview(capture: capture)),
      );
    });

    test('Done compares by counts', () {
      expect(
        const LibraryImportDone(confirmed: 2, rejected: 1),
        equals(const LibraryImportDone(confirmed: 2, rejected: 1)),
      );
      expect(
        const LibraryImportDone(confirmed: 2, rejected: 1),
        isNot(equals(const LibraryImportDone(confirmed: 1, rejected: 1))),
      );
    });

    test('Error compares by message', () {
      expect(
        const LibraryImportError(message: 'x'),
        equals(const LibraryImportError(message: 'x')),
      );
    });
  });
}
