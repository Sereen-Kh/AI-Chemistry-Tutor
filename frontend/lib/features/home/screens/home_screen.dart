import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:ai_chemistry_tutor/features/auth/providers/auth_provider.dart';

/// Placeholder home screen — features (rack, chatbot, reels) will be added here.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.science, size: 24),
            SizedBox(width: 8),
            Text('AI Chemistry Tutor'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: const Center(
        child: Text(
          'Welcome! Features coming soon.',
          style: TextStyle(fontSize: 18),
        ),
      ),
    );
  }
}
