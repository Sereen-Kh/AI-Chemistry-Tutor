import 'package:go_router/go_router.dart';
import 'package:ai_chemistry_tutor/features/auth/providers/auth_provider.dart';
import 'package:ai_chemistry_tutor/features/auth/screens/login_screen.dart';
import 'package:ai_chemistry_tutor/features/auth/screens/register_screen.dart';
import 'package:ai_chemistry_tutor/features/home/screens/home_screen.dart';

/// Factory that takes the [AuthProvider] so the router can react to auth state
/// changes via [refreshListenable] and redirect unauthenticated users.
GoRouter buildAppRouter(AuthProvider authProvider) => GoRouter(
      initialLocation: '/login',
      refreshListenable: authProvider,
      redirect: (context, state) {
        final isLoggedIn = authProvider.isAuthenticated;
        final loc = state.matchedLocation;
        final isAuthRoute = loc == '/login' || loc == '/register';

        if (!isLoggedIn && !isAuthRoute) return '/login';
        if (isLoggedIn && isAuthRoute) return '/home';
        return null;
      },
      routes: [
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(),
        ),
        GoRoute(
          path: '/register',
          builder: (context, state) => const RegisterScreen(),
        ),
        GoRoute(
          path: '/home',
          builder: (context, state) => const HomeScreen(),
        ),
      ],
    );

