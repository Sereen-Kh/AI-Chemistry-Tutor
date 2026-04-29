import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:ai_chemistry_tutor/core/router/app_router.dart';
import 'package:ai_chemistry_tutor/features/auth/providers/auth_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final authProvider = AuthProvider();
  await authProvider.loadToken();
  runApp(AiChemistryTutorApp(authProvider: authProvider));
}

class AiChemistryTutorApp extends StatelessWidget {
  final AuthProvider authProvider;

  const AiChemistryTutorApp({super.key, required this.authProvider});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: authProvider,
      child: MaterialApp.router(
        title: 'AI Chemistry Tutor',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF1A73E8),
          ),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF1A73E8),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        themeMode: ThemeMode.system,
        routerConfig: buildAppRouter(authProvider),
      ),
    );
  }
}
