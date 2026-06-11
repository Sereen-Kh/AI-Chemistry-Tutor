import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:get/get.dart';

import '../core/controllers/language_controller.dart';
import 'routes/app_pages.dart';
import 'routes/app_routes.dart';
import 'theme/app_theme.dart';
import 'translations/app_translations.dart';

class ChemAIApp extends StatelessWidget {
  const ChemAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    final lc = Get.find<LanguageController>();
    return GetMaterialApp(
      title: 'CHEMAI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      translations: AppTranslations(),
      locale: lc.locale.value,
      fallbackLocale: const Locale('en'),
      supportedLocales: const [Locale('en'), Locale('ar')],
      // Provides MaterialLocalizations for every supported locale (including ar).
      // Without these delegates, switching to Arabic crashes DrawerController
      // because DefaultMaterialLocalizations.delegate only covers 'en'.
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      initialRoute: AppRoutes.splash,
      getPages: AppPages.routes,
      defaultTransition: Transition.fadeIn,
    );
  }
}
