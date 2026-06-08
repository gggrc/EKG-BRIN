// lib/core/router/app_router.dart
// Justifikasi: Ziefle & Bay (2005) — navigasi sidebar lebih efisien dari tab 
// untuk aplikasi dengan ≥7 menu item. go_router untuk declarative routing
// yang mendukung deep linking di web.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../models/user_model.dart';
import '../../features/auth/login_page.dart';
import '../../features/auth/register_page.dart';
import '../../features/landing/landing_page.dart';
import '../../features/dashboard/dashboard_page.dart';
import '../../features/ecg_viewer/ecg_viewer_page.dart';
import '../../features/patient/patient_list_page.dart';
import '../../features/patient/patient_form_page.dart';
import '../../features/patient/patient_detail_page.dart';
import '../../features/acquisition/acquisition_page.dart';
import '../../features/history/history_page.dart';
import '../../features/diagnosis/diagnosis_page.dart';
import '../../features/diagnosis/report_page.dart';
import '../../features/fhir/fhir_export_page.dart';
import '../../features/admin/admin_panel_page.dart';
import '../../features/admin/user_management_page.dart';
import '../../features/admin/analytics_page.dart';
import '../../features/notifications/notifications_page.dart';
import '../../features/profile/profile_page.dart';
import '../../shared/widgets/app_shell.dart';

// Route names
class AppRoutes {
  static const landing = '/';
  static const login = '/login';
  static const register = '/register';
  static const dashboard = '/dashboard';
  static const ecgViewer = '/ecg/:sessionId';
  static const patients = '/patients';
  static const patientNew = '/patients/new';
  static const patientEdit = '/patients/:patientId/edit';
  static const patientDetail = '/patients/:patientId';
  static const acquisition = '/acquisition';
  static const history = '/history';
  static const diagnosis = '/diagnosis/:sessionId';
  static const report = '/report/:sessionId';
  static const fhirExport = '/fhir';
  static const adminPanel = '/admin';
  static const adminUsers = '/admin/users';
  static const analytics = '/admin/analytics';
  static const notifications = '/notifications';
  static const profile = '/profile';
}

GoRouter createRouter(AuthProvider authProvider) {
  return GoRouter(
    initialLocation: AppRoutes.landing,
    redirect: (context, state) {
      final isAuth = authProvider.isAuthenticated;
      final isAuthRoute = state.matchedLocation == AppRoutes.login ||
          state.matchedLocation == AppRoutes.register ||
          state.matchedLocation == AppRoutes.landing;

      if (!isAuth && !isAuthRoute) return AppRoutes.login;
      if (isAuth && state.matchedLocation == AppRoutes.landing) {
        return AppRoutes.dashboard;
      }
      return null;
    },
    refreshListenable: authProvider,
    routes: [
      // Public routes
      GoRoute(
        path: AppRoutes.landing,
        builder: (context, state) => const LandingPage(),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: AppRoutes.register,
        builder: (context, state) => const RegisterPage(),
      ),

      // Protected routes with Shell (sidebar + topbar)
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: AppRoutes.dashboard,
            builder: (context, state) => const DashboardPage(),
          ),
          GoRoute(
            path: '/ecg/:sessionId',
            builder: (context, state) {
              final sessionId = state.pathParameters['sessionId']!;
              return EcgViewerPage(sessionId: sessionId);
            },
          ),
          GoRoute(
            path: AppRoutes.patients,
            builder: (context, state) => const PatientListPage(),
          ),
          GoRoute(
            path: AppRoutes.patientNew,
            builder: (context, state) => const PatientFormPage(),
          ),
          GoRoute(
            path: '/patients/:patientId/edit',
            builder: (context, state) {
              final patientId = state.pathParameters['patientId']!;
              return PatientFormPage(patientId: patientId);
            },
          ),
          GoRoute(
            path: '/patients/:patientId',
            builder: (context, state) {
              final patientId = state.pathParameters['patientId']!;
              return PatientDetailPage(patientId: patientId);
            },
          ),
          GoRoute(
            path: AppRoutes.acquisition,
            builder: (context, state) => const AcquisitionPage(),
          ),
          GoRoute(
            path: AppRoutes.history,
            builder: (context, state) => const HistoryPage(),
          ),
          GoRoute(
            path: '/diagnosis/:sessionId',
            builder: (context, state) {
              final sessionId = state.pathParameters['sessionId']!;
              return DiagnosisPage(sessionId: sessionId);
            },
          ),
          GoRoute(
            path: '/report/:sessionId',
            builder: (context, state) {
              final sessionId = state.pathParameters['sessionId']!;
              return ReportPage(sessionId: sessionId);
            },
          ),
          GoRoute(
            path: AppRoutes.fhirExport,
            builder: (context, state) => const FhirExportPage(),
          ),
          GoRoute(
            path: AppRoutes.adminPanel,
            builder: (context, state) => const AdminPanelPage(),
          ),
          GoRoute(
            path: AppRoutes.adminUsers,
            builder: (context, state) => const UserManagementPage(),
          ),
          GoRoute(
            path: AppRoutes.analytics,
            builder: (context, state) => const AnalyticsPage(),
          ),
          GoRoute(
            path: AppRoutes.notifications,
            builder: (context, state) => const NotificationsPage(),
          ),
          GoRoute(
            path: AppRoutes.profile,
            builder: (context, state) => const ProfilePage(),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Text('Halaman tidak ditemukan: ${state.error}'),
      ),
    ),
  );
}

// RBAC Guard helper
class RoleGuard extends StatelessWidget {
  final Widget child;
  final List<UserRole> allowedRoles;
  final Widget? fallback;

  const RoleGuard({
    super.key,
    required this.child,
    required this.allowedRoles,
    this.fallback,
  });

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthProvider>().userRole;
    if (role != null && allowedRoles.contains(role)) return child;
    return fallback ??
        const Center(
          child: Text('Akses tidak diizinkan untuk role Anda.'),
        );
  }
}
