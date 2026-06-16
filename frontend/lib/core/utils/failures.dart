sealed class Failure {
  final String message;
  const Failure(this.message);
}

final class NetworkFailure  extends Failure { const NetworkFailure([super.message = 'No internet connection.']); }
final class ServerFailure   extends Failure {
  final int? statusCode;
  const ServerFailure(super.message, {this.statusCode});
}
final class TimeoutFailure  extends Failure { const TimeoutFailure([super.message  = 'Request timed out.']); }
final class ParseFailure    extends Failure { const ParseFailure([super.message    = 'Unexpected response format.']); }
final class UnknownFailure  extends Failure { const UnknownFailure([super.message  = 'Something went wrong.']); }
