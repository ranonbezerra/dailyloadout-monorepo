import 'package:app/core/auth/email_verification.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

DioException _dioError({int? statusCode, Object? data}) => DioException(
  requestOptions: RequestOptions(),
  response: statusCode == null
      ? null
      : Response(
          requestOptions: RequestOptions(),
          statusCode: statusCode,
          data: data,
        ),
);

void main() {
  group('EmailVerification.isUnverifiedError', () {
    test('true for a 403 with the email-not-verified detail', () {
      final error = _dioError(
        statusCode: 403,
        data: <String, dynamic>{'detail': 'Email not verified'},
      );

      expect(EmailVerification.isUnverifiedError(error), isTrue);
    });

    test('false for a 403 with a different detail', () {
      final error = _dioError(
        statusCode: 403,
        data: <String, dynamic>{'detail': 'Forbidden'},
      );

      expect(EmailVerification.isUnverifiedError(error), isFalse);
    });

    test('false for a non-403 status', () {
      final error = _dioError(
        statusCode: 401,
        data: <String, dynamic>{'detail': 'Email not verified'},
      );

      expect(EmailVerification.isUnverifiedError(error), isFalse);
    });

    test('false when there is no response', () {
      expect(EmailVerification.isUnverifiedError(_dioError()), isFalse);
    });

    test('false when the body is not a map', () {
      final error = _dioError(statusCode: 403, data: 'plain body');

      expect(EmailVerification.isUnverifiedError(error), isFalse);
    });
  });
}
