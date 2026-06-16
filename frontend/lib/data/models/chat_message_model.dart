class ChatMessage {
  final String id;
  final String content;
  final bool isBot;
  final String time;
  final bool isRead;

  const ChatMessage({
    required this.id,
    required this.content,
    required this.isBot,
    required this.time,
    this.isRead = false,
  });
}
