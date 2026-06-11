import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../data/models/chat_message_model.dart';

class AskAiController extends GetxController {
  final messages = <ChatMessage>[].obs;
  final messageController = TextEditingController();
  final isTyping = false.obs;
  final teachingStyle = 'Socratic'.obs;
  final scrollController = ScrollController();

  @override
  void onInit() {
    super.onInit();
    messages.addAll([
      ChatMessage(
        id: '1',
        content:
            'Let\'s look at the reaction between Hydrogen and Oxygen.\n\n2H₂ + O₂ → 2H₂O',
        isBot: true,
        time: '14:00',
      ),
      ChatMessage(
        id: '2',
        content: 'What kind of bond is that?',
        isBot: false,
        time: '14:02',
        isRead: true,
      ),
    ]);
  }

  Future<void> sendMessage() async {
    final text = messageController.text.trim();
    if (text.isEmpty) return;

    messages.add(ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: text,
      isBot: false,
      time: _now(),
    ));
    messageController.clear();
    isTyping.value = true;
    _scrollToBottom();

    await Future.delayed(const Duration(seconds: 2));
    isTyping.value = false;

    messages.add(ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: teachingStyle.value == 'Socratic'
          ? 'Interesting question! What do you think happens when atoms share electrons between two non-metals? 🤔'
          : 'That\'s a covalent bond. Hydrogen and oxygen share electrons to form water molecules.',
      isBot: true,
      time: _now(),
    ));
    _scrollToBottom();
  }

  void setStyle(String style) => teachingStyle.value = style;

  String _now() {
    final t = DateTime.now();
    return '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 120), () {
      if (scrollController.hasClients) {
        scrollController.animateTo(
          scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void onClose() {
    messageController.dispose();
    scrollController.dispose();
    super.onClose();
  }
}
