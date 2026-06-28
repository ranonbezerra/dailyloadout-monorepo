import 'package:app/core/config/feature_flags.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('FeatureFlags', () {
    test('default constructor disables backlogConcierge', () {
      const flags = FeatureFlags();
      expect(flags.backlogConcierge, false);
    });

    test('explicit constructor enables backlogConcierge', () {
      const flags = FeatureFlags(backlogConcierge: true);
      expect(flags.backlogConcierge, true);
    });

    test('fromEnv reads ENABLE_CONCIERGE=true as enabled', () {
      dotenv.testLoad(fileInput: 'ENABLE_CONCIERGE=true');
      final flags = FeatureFlags.fromEnv();
      expect(flags.backlogConcierge, true);
    });

    test('fromEnv treats non-true value as disabled', () {
      dotenv.testLoad(fileInput: 'ENABLE_CONCIERGE=yes');
      final flags = FeatureFlags.fromEnv();
      expect(flags.backlogConcierge, false);
    });

    test('fromEnv defaults to disabled when key is missing', () {
      dotenv.testLoad();
      final flags = FeatureFlags.fromEnv();
      expect(flags.backlogConcierge, false);
    });
  });
}
