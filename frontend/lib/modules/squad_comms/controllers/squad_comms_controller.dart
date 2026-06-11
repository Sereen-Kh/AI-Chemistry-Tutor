import 'package:flutter/material.dart';
import 'package:get/get.dart';

class SquadMessage {
  final String id;
  final String sender;
  final String content;
  final String time;
  final bool isMe;

  const SquadMessage({
    required this.id,
    required this.sender,
    required this.content,
    required this.time,
    this.isMe = false,
  });
}

class SquadMember {
  final String emoji;
  final String name;
  final bool isOnline;

  const SquadMember({
    required this.emoji,
    required this.name,
    this.isOnline = false,
  });
}

class SquadCommsController extends GetxController {
  final messages = <SquadMessage>[].obs;
  final memberCount = 4.obs;
  final squadXp = 12400.obs;
  final squadXpGoal = 15000.obs;
  final selectedTab = 0.obs;
  final messageController = TextEditingController();

  final members = const [
    SquadMember(emoji: '🚀', name: 'NovaStar99', isOnline: true),
    SquadMember(emoji: '⚛️', name: 'QuantumKid', isOnline: true),
    SquadMember(emoji: '🧙', name: 'ChemWizard', isOnline: false),
    SquadMember(emoji: '🎯', name: 'You',        isOnline: true),
  ];

  @override
  void onInit() {
    super.onInit();
    messages.addAll(const [
      SquadMessage(
        id: '1',
        sender: 'NovaStar99',
        content: 'Just finished the Stoichiometry Sprint! 250 XP incoming 🔥',
        time: '14:02',
      ),
      SquadMessage(
        id: '2',
        sender: 'QuantumKid',
        content: 'Nice! Let\'s tackle the Quantum Gauntlet together next.',
        time: '14:05',
      ),
      SquadMessage(
        id: '3',
        sender: 'You',
        content: 'I\'m in! Give me 5 minutes.',
        time: '14:06',
        isMe: true,
      ),
    ]);
  }

  void sendMessage() {
    final text = messageController.text.trim();
    if (text.isEmpty) return;
    messages.add(SquadMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      sender: 'You',
      content: text,
      time: _now(),
      isMe: true,
    ));
    messageController.clear();
  }

  void switchTab(int i) => selectedTab.value = i;

  String _now() {
    final t = DateTime.now();
    return '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  @override
  void onClose() {
    messageController.dispose();
    super.onClose();
  }
}
