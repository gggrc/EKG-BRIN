// lib/shared/widgets/app_shell.dart
// Sidebar + TopBar layout shell
// Justifikasi: Ziefle & Bay (2005) — sidebar navigation lebih efisien dari tab
// navigation untuk aplikasi dengan ≥7 menu item. F-pattern reading (Nielsen, 2006)
// menempatkan navigasi di kiri untuk scanning alami.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/models/user_model.dart';
import '../../core/router/app_router.dart';

class AppShell extends StatefulWidget {
  final Widget child;
  const AppShell({super.key, required this.child});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  bool _sidebarExpanded = true;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.currentUser;
    final isNarrow = MediaQuery.of(context).size.width < 900;

    if (isNarrow) {
      return _buildMobileLayout(context, user);
    }
    return _buildDesktopLayout(context, user);
  }

  Widget _buildDesktopLayout(BuildContext context, UserModel? user) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Row(
        children: [
          // Sidebar — selalu tampil; expand/collapse diatur di dalam widget
          AnimatedContainer(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeInOut,
            width: _sidebarExpanded ? 260 : 68,
            child: _Sidebar(
              expanded: _sidebarExpanded,
              user: user,
              onToggle: () => setState(() => _sidebarExpanded = !_sidebarExpanded),
            ),
          ),
          // Main content
          Expanded(
            child: Column(
              children: [
                _TopBar(user: user),
                Expanded(
                  child: widget.child,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMobileLayout(BuildContext context, UserModel? user) {
    return Scaffold(
      backgroundColor: AppColors.background,
      drawer: Drawer(
        backgroundColor: AppColors.surface,
        child: _Sidebar(expanded: true, user: user, onToggle: () {}),
      ),
      appBar: _MobileTopBar(user: user),
      body: widget.child,
    );
  }
}

class _Sidebar extends StatelessWidget {
  final bool expanded;
  final UserModel? user;
  final VoidCallback onToggle;

  const _Sidebar({
    required this.expanded,
    required this.user,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final u = user;
    final role = u?.role;
    final currentPath = GoRouterState.of(context).matchedLocation;

    return Container(
      color: AppColors.surface,
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(
          right: BorderSide(color: AppColors.borderLight),
        ),
      ),
      child: Column(
        children: [
          // Logo area — tombol toggle SELALU tampil di sini
          Container(
            height: 64,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: AppColors.borderLight),
              ),
            ),
            child: Row(
              children: [
                // Toggle button — selalu tampil pertama
                IconButton(
                  onPressed: onToggle,
                  icon: Icon(
                    expanded ? Icons.menu_open_rounded : Icons.menu_rounded,
                    size: 24,
                    color: AppColors.primaryDark,
                  ),
                  tooltip: expanded ? 'Tutup sidebar' : 'Buka sidebar',
                ),
                if (expanded) ...[
                  const SizedBox(width: 4),
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      gradient: AppColors.primaryGradient,
                      borderRadius: BorderRadius.circular(7),
                    ),
                    child: const Icon(Icons.monitor_heart, color: Colors.white, size: 17),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'EKG-BRIN',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        Text(
                          'Sistem HL7 FHIR',
                          style: TextStyle(
                            fontSize: 10,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

          // User info chip — hanya saat expanded
          if (expanded && u != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.borderLight),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 16,
                      backgroundColor: _roleColor(role).withOpacity(0.15),
                      child: Text(
                        u.name.split(' ').first[0],
                        style: TextStyle(
                          color: _roleColor(role),
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            u.name.split(',').first,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 3),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: _roleColor(role).withOpacity(0.12),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              role?.shortName ?? '',
                              style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: _roleColor(role),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            )
          else if (!expanded && u != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: CircleAvatar(
                radius: 16,
                backgroundColor: _roleColor(role).withOpacity(0.15),
                child: Text(
                  u.name.split(' ').first[0],
                  style: TextStyle(
                    color: _roleColor(role),
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
              ),
            ),

          // Navigation items
          Expanded(
            child: SingleChildScrollView(
              padding: EdgeInsets.symmetric(
                horizontal: expanded ? 8 : 6,
                vertical: 4,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (expanded) _SectionLabel('UTAMA'),
                  _NavItem(
                    icon: Icons.dashboard_rounded,
                    label: 'Dashboard',
                    route: AppRoutes.dashboard,
                    currentPath: currentPath,
                    expanded: expanded,
                  ),
                  if (role != UserRole.admin)
                    _NavItem(
                      icon: Icons.monitor_heart_rounded,
                      label: 'EKG Viewer',
                      route: '/ecg/s-001',
                      currentPath: currentPath,
                      expanded: expanded,
                      matchPrefix: '/ecg',
                    ),
                  _NavItem(
                    icon: Icons.history_rounded,
                    label: 'Riwayat EKG',
                    route: AppRoutes.history,
                    currentPath: currentPath,
                    expanded: expanded,
                  ),

                  if (role != UserRole.patient) ...[
                    const SizedBox(height: 4),
                    if (expanded) _SectionLabel('KLINIS'),
                    _NavItem(
                      icon: Icons.people_rounded,
                      label: 'Data Pasien',
                      route: AppRoutes.patients,
                      currentPath: currentPath,
                      expanded: expanded,
                      matchPrefix: '/patients',
                    ),
                    if (role != UserRole.admin) ...[
                      _NavItem(
                        icon: Icons.upload_file_rounded,
                        label: 'Akuisisi Sinyal',
                        route: AppRoutes.acquisition,
                        currentPath: currentPath,
                        expanded: expanded,
                      ),
                      _NavItem(
                        icon: Icons.medical_information_rounded,
                        label: 'Diagnosis',
                        route: '/diagnosis/s-001',
                        currentPath: currentPath,
                        expanded: expanded,
                        matchPrefix: '/diagnosis',
                      ),
                    ],
                    _NavItem(
                      icon: Icons.share_rounded,
                      label: 'FHIR Export',
                      route: AppRoutes.fhirExport,
                      currentPath: currentPath,
                      expanded: expanded,
                    ),
                  ],

                  if (role == UserRole.admin) ...[
                    const SizedBox(height: 4),
                    if (expanded) _SectionLabel('ADMINISTRASI'),
                    _NavItem(
                      icon: Icons.admin_panel_settings_rounded,
                      label: 'Admin Panel',
                      route: AppRoutes.adminPanel,
                      currentPath: currentPath,
                      expanded: expanded,
                    ),
                    _NavItem(
                      icon: Icons.manage_accounts_rounded,
                      label: 'Kelola User',
                      route: AppRoutes.adminUsers,
                      currentPath: currentPath,
                      expanded: expanded,
                    ),
                    _NavItem(
                      icon: Icons.bar_chart_rounded,
                      label: 'Analytics',
                      route: AppRoutes.analytics,
                      currentPath: currentPath,
                      expanded: expanded,
                    ),
                  ],

                  const SizedBox(height: 4),
                  if (expanded) _SectionLabel('AKUN'),
                  _NavItem(
                    icon: Icons.notifications_rounded,
                    label: 'Notifikasi',
                    route: AppRoutes.notifications,
                    currentPath: currentPath,
                    expanded: expanded,
                    badge: 2,
                  ),
                  _NavItem(
                    icon: Icons.person_rounded,
                    label: 'Profil',
                    route: AppRoutes.profile,
                    currentPath: currentPath,
                    expanded: expanded,
                  ),
                ],
              ),
            ),
          ),

          // Logout
          Container(
            padding: const EdgeInsets.all(10),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.borderLight)),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: () {
                context.read<AuthProvider>().logout();
                context.go(AppRoutes.login);
              },
              child: Container(
                padding: EdgeInsets.symmetric(
                  horizontal: expanded ? 12 : 8,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: expanded ? MainAxisAlignment.start : MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.logout_rounded, color: AppColors.danger, size: 20),
                    if (expanded) ...[
                      const SizedBox(width: 12),
                      const Text(
                        'Keluar',
                        style: TextStyle(
                          color: AppColors.danger,
                          fontWeight: FontWeight.w500,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _roleColor(UserRole? role) {
    switch (role) {
      case UserRole.patient:
        return AppColors.rolePatient;
      case UserRole.clinician:
        return AppColors.roleClinician;
      case UserRole.admin:
        return AppColors.roleAdmin;
      default:
        return AppColors.primary;
    }
  }
}

class _SectionLabel extends StatelessWidget {
  final String label;
  const _SectionLabel(this.label);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 12, top: 10, bottom: 4),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w700,
          color: AppColors.textMuted,
          letterSpacing: 1.4,
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String route;
  final String currentPath;
  final bool expanded;
  final String? matchPrefix;
  final int badge;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.route,
    required this.currentPath,
    required this.expanded,
    this.matchPrefix,
    this.badge = 0,
  });

  bool get isActive {
    final prefix = matchPrefix ?? route;
    return currentPath.startsWith(prefix);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Tooltip(
        message: expanded ? '' : label,
        preferBelow: false,
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: () => context.go(route),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            padding: EdgeInsets.symmetric(
              horizontal: expanded ? 12 : 14,
              vertical: 9,
            ),
            decoration: BoxDecoration(
              color: isActive
                  ? AppColors.primary.withOpacity(0.10)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              border: isActive
                  ? Border.all(color: AppColors.primary.withOpacity(0.2))
                  : Border.all(color: Colors.transparent),
            ),
            child: Row(
              mainAxisAlignment: expanded ? MainAxisAlignment.start : MainAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  size: 19,
                  color: isActive ? AppColors.primary : AppColors.textSecondary,
                ),
                if (expanded) ...[
                  const SizedBox(width: 11),
                  Expanded(
                    child: Text(
                      label,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                        color: isActive ? AppColors.primary : AppColors.textPrimary,
                      ),
                    ),
                  ),
                  if (badge > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.danger,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        badge.toString(),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                ] else if (badge > 0)
                  // Dot badge saat collapsed
                  Container(
                    margin: const EdgeInsets.only(left: 2, top: 2),
                    width: 7,
                    height: 7,
                    decoration: const BoxDecoration(
                      color: AppColors.danger,
                      shape: BoxShape.circle,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  final UserModel? user;
  const _TopBar({required this.user});

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final title = _routeTitle(location);

    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.borderLight)),
      ),
      child: Row(
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          // Search bar placeholder
          MouseRegion(
            cursor: SystemMouseCursors.click,
            child: GestureDetector(
              onTap: () => context.go(AppRoutes.patients),
              child: Container(
                width: 220,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.borderLight),
                ),
                child: const Row(
                  children: [
                    SizedBox(width: 12),
                    Icon(Icons.search, size: 16, color: AppColors.textMuted),
                    SizedBox(width: 8),
                    Text(
                      'Cari pasien...',
                      style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Notification bell
          Stack(
            children: [
              IconButton(
                onPressed: () => context.go(AppRoutes.notifications),
                icon: const Icon(Icons.notifications_outlined, color: AppColors.textSecondary),
                tooltip: 'Notifikasi',
              ),
              Positioned(
                top: 8,
                right: 8,
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: AppColors.danger,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(width: 4),
          // Avatar
          GestureDetector(
            onTap: () => context.go(AppRoutes.profile),
            child: CircleAvatar(
              radius: 17,
              backgroundColor: AppColors.primaryContainer,
              child: Text(
                user?.name.split(' ').first[0] ?? '?',
                style: const TextStyle(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w700,
                  fontSize: 14,
                ),
              ),
            ),
          ),
          const SizedBox(width: 4),
        ],
      ),
    );
  }

  String _routeTitle(String path) {
    if (path.startsWith('/dashboard')) return 'Dashboard';
    if (path.startsWith('/ecg')) return 'EKG Viewer';
    if (path.startsWith('/patients/new')) return 'Tambah Pasien';
    if (path.contains('/edit')) return 'Edit Pasien';
    if (path.startsWith('/patients/')) return 'Detail Pasien';
    if (path.startsWith('/patients')) return 'Data Pasien';
    if (path.startsWith('/acquisition')) return 'Akuisisi Sinyal EKG';
    if (path.startsWith('/history')) return 'Riwayat EKG';
    if (path.startsWith('/diagnosis')) return 'Diagnosis & Laporan';
    if (path.startsWith('/report')) return 'Laporan EKG';
    if (path.startsWith('/fhir')) return 'FHIR Export — SATUSEHAT';
    if (path.startsWith('/admin/users')) return 'Kelola User';
    if (path.startsWith('/admin/analytics')) return 'Analytics';
    if (path.startsWith('/admin')) return 'Admin Panel';
    if (path.startsWith('/notifications')) return 'Notifikasi';
    if (path.startsWith('/profile')) return 'Profil';
    return 'EKG-BRIN';
  }
}

class _MobileTopBar extends StatelessWidget implements PreferredSizeWidget {
  final UserModel? user;
  const _MobileTopBar({required this.user});

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      backgroundColor: AppColors.surface,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
      leading: Builder(
        builder: (ctx) => IconButton(
          icon: const Icon(Icons.menu_rounded, color: AppColors.textPrimary),
          onPressed: () => Scaffold.of(ctx).openDrawer(),
        ),
      ),
      title: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Icon(Icons.monitor_heart, color: Colors.white, size: 16),
          ),
          const SizedBox(width: 8),
          const Text(
            'EKG-BRIN',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
          ),
        ],
      ),
      actions: [
        IconButton(
          onPressed: () => context.go(AppRoutes.notifications),
          icon: const Icon(Icons.notifications_outlined, color: AppColors.textSecondary),
        ),
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: CircleAvatar(
            radius: 16,
            backgroundColor: AppColors.primaryContainer,
            child: Text(
              user?.name.split(' ').first[0] ?? '?',
              style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700, fontSize: 12),
            ),
          ),
        ),
      ],
    );
  }
}
