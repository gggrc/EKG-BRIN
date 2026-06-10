// lib/features/dashboard/dashboard_page.dart
// Dashboard berbeda berdasarkan role user
// Justifikasi: Shneiderman & Plaisant (2010) — "Overview first, zoom and filter,
// then details on demand" — prinsip Visual Information Seeking Mantra

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/data_provider.dart';
import '../../core/models/user_model.dart';
import '../../core/models/ecg_models.dart';
import '../../core/mock/mock_data.dart';
import '../../core/router/app_router.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

class DashboardPage extends StatelessWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthProvider>().userRole;
    switch (role) {
      case UserRole.patient:
        return const _PatientDashboard();
      case UserRole.clinician:
        return const _ClinicianDashboard();
      case UserRole.admin:
        return const _AdminDashboard();
      default:
        return const SizedBox.shrink();
    }
  }
}

// ============================================================
// PATIENT DASHBOARD
// ============================================================
class _PatientDashboard extends StatelessWidget {
  const _PatientDashboard();

  @override
  Widget build(BuildContext context) {
    final user = context.read<AuthProvider>().currentUser;
    final patient = MockData.patients.firstWhere((p) => p.patientId == 'p-001');
    final sessions = MockData.ecgSessions.where((s) => s.patientId == 'p-001').toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _GreetingBanner(user: user, subtitle: 'Pantau kesehatan jantung Anda'),
          const SizedBox(height: 24),
          // Quick stats
          Row(
            children: [
              Expanded(child: _StatCard(
                label: 'Total Rekaman EKG',
                value: '${patient.totalEcgSessions}',
                icon: Icons.monitor_heart_rounded,
                color: AppColors.primary,
              )),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(
                label: 'EKG Terakhir',
                value: 'Jun 8, 2026',
                icon: Icons.calendar_today_rounded,
                color: AppColors.secondary,
              )),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(
                label: 'Detak Jantung Terakhir',
                value: '75 bpm',
                icon: Icons.favorite_rounded,
                color: AppColors.success,
                isNormal: true,
              )),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: Column(
                  children: [
                    _SectionHeader(title: 'EKG Terbaru', onViewAll: () => context.go(AppRoutes.history)),
                    const SizedBox(height: 12),
                    ...sessions.take(3).map((s) => _EcgSessionCard(session: s)),
                  ],
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  children: [
                    _SectionHeader(title: 'Info Kesehatan'),
                    const SizedBox(height: 12),
                    _HealthInfoCard(patient: patient),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ============================================================
// CLINICIAN DASHBOARD (merged Nakes + Dokter)
// ============================================================
class _ClinicianDashboard extends StatelessWidget {
  const _ClinicianDashboard();

  @override
  Widget build(BuildContext context) {
    final user = context.read<AuthProvider>().currentUser;
    final data = context.watch<DataProvider>();
    final analytics = data.analytics;
    final sessions = data.ecgSessions;
    final pending = sessions.where((s) => s.status == EcgSessionStatus.pending).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          _GreetingBanner(user: user, subtitle: 'Kelola pasien, rekam EKG, dan tinjau laporan klinis'),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(child: _StatCard(label: 'Total Pasien', value: '${analytics['totalPatients']}', icon: Icons.people_rounded, color: AppColors.primary)),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(label: 'Sesi Bulan Ini', value: '${analytics['sessionsThisMonth']}', icon: Icons.monitor_heart_rounded, color: AppColors.secondary)),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(label: 'Menunggu Diagnosis', value: '${pending.length}', icon: Icons.pending_actions_rounded, color: AppColors.warning, isAlert: pending.isNotEmpty)),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(label: 'HR Rata-rata', value: '${analytics['avgHeartRate']} bpm', icon: Icons.favorite_rounded, color: AppColors.success)),
            ],
          ),
          const SizedBox(height: 20),
          // Quick actions
          Row(
            children: [
              Expanded(
                child: _QuickActionCard(
                  icon: Icons.person_add_rounded,
                  title: 'Tambah Pasien',
                  subtitle: 'Daftar pasien baru',
                  color: AppColors.primary,
                  onTap: () => context.go(AppRoutes.patientNew),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _QuickActionCard(
                  icon: Icons.upload_file_rounded,
                  title: 'Rekam EKG',
                  subtitle: 'Upload data EKG baru',
                  color: AppColors.secondary,
                  onTap: () => context.go(AppRoutes.acquisition),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _QuickActionCard(
                  icon: Icons.medical_information_rounded,
                  title: 'Diagnosis',
                  subtitle: 'Tinjau & setujui laporan',
                  color: AppColors.roleClinician,
                  onTap: () {
                    if (pending.isNotEmpty) {
                      context.go('/diagnosis/${pending.first.sessionId}');
                    } else {
                      context.go(AppRoutes.history);
                    }
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          // Pending approvals alert
          if (pending.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.warningContainer,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.warning),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.pending_actions_rounded, color: AppColors.warning, size: 18),
                      const SizedBox(width: 8),
                      Text(
                        '${pending.length} Sesi Menunggu Ditinjau',
                        style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.warning),
                      ),
                      const Spacer(),
                      TextButton(
                        onPressed: () => context.go(AppRoutes.history),
                        child: const Text('Lihat Semua'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  ...pending.take(2).map((s) => _EcgSessionCard(session: s, compact: true)),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 3,
                child: Column(
                  children: [
                    _SectionHeader(title: 'Sesi EKG Terbaru', onViewAll: () => context.go(AppRoutes.history)),
                    const SizedBox(height: 12),
                    ...sessions.take(5).map((s) => _EcgSessionCard(session: s)),
                  ],
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  children: [
                    _SectionHeader(title: 'Distribusi Irama'),
                    const SizedBox(height: 12),
                    _RhythmPieChart(data: Map<String, int>.from(analytics['rhythmDistribution'])),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ============================================================
// ADMIN DASHBOARD
// ============================================================
class _AdminDashboard extends StatelessWidget {
  const _AdminDashboard();

  @override
  Widget build(BuildContext context) {
    final user = context.read<AuthProvider>().currentUser;
    final data = context.watch<DataProvider>();
    final analytics = data.analytics;
    final logs = data.activityLogs;

    void exportDataset() {
      final csvData = [
        ['ID', 'User', 'Action', 'Target', 'Time', 'Type'],
        ...logs.map((l) => [
          l.id,
          '"${l.userName}"',
          '"${l.action}"',
          '"${l.target}"',
          l.time.toString(),
          l.type
        ])
      ].map((row) => row.join(',')).join('\n');

      final blob = html.Blob([csvData], 'text/csv');
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute("download", "audit_log_export.csv")
        ..click();
      html.Url.revokeObjectUrl(url);

      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Dataset Audit Log berhasil di-export')));
      
      data.addActivityLog(ActivityLogModel(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        userName: user?.name ?? 'Admin',
        action: 'Export dataset',
        target: '${logs.length} rekam aktivitas',
        time: DateTime.now(),
        type: 'export',
      ));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _GreetingBanner(user: user, subtitle: 'Overview sistem EKG-BRIN nasional'),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(child: _StatCard(label: 'Total Pasien', value: '${analytics['totalPatients']}', icon: Icons.people_rounded, color: AppColors.primary)),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(label: 'Total Sesi EKG', value: '${analytics['totalSessions']}', icon: Icons.monitor_heart_rounded, color: AppColors.secondary)),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(label: 'FHIR Synced', value: '${analytics['fhirSyncedCount']}', icon: Icons.sync_rounded, color: AppColors.success)),
              const SizedBox(width: 16),
              Expanded(child: _StatCard(label: 'Pending Diagnosis', value: '${analytics['pendingDiagnosis']}', icon: Icons.pending_rounded, color: AppColors.warning)),
            ],
          ),
          const SizedBox(height: 24),
          // Quick actions for admin
          Row(
            children: [
              Expanded(child: _QuickActionCard(icon: Icons.manage_accounts_rounded, title: 'Kelola User', subtitle: 'Tambah/edit/hapus akun', color: AppColors.primary, onTap: () => context.go(AppRoutes.adminUsers))),
              const SizedBox(width: 16),
              Expanded(child: _QuickActionCard(icon: Icons.bar_chart_rounded, title: 'Analytics', subtitle: 'Laporan & statistik', color: AppColors.secondary, onTap: () => context.go(AppRoutes.analytics))),
              const SizedBox(width: 16),
              Expanded(child: _QuickActionCard(icon: Icons.download_rounded, title: 'Export Dataset', subtitle: 'Download data riset', color: AppColors.roleAdmin, onTap: exportDataset)),
              const SizedBox(width: 16),
              Expanded(child: _QuickActionCard(icon: Icons.receipt_long_rounded, title: 'Audit Log', subtitle: 'Riwayat aktivitas sistem', color: AppColors.success, onTap: () => context.go(AppRoutes.adminPanel))),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: Column(
                  children: [
                    _SectionHeader(title: 'Sesi EKG per Bulan'),
                    const SizedBox(height: 12),
                    _MonthlySessionsChart(data: List<int>.from(analytics['sessionsByMonth'])),
                  ],
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  children: [
                    _SectionHeader(title: 'Distribusi Irama'),
                    const SizedBox(height: 12),
                    _RhythmPieChart(data: Map<String, int>.from(analytics['rhythmDistribution'])),
                  ],
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  children: [
                    _SectionHeader(title: 'Sumber Data'),
                    const SizedBox(height: 12),
                    _SourceTypePieChart(data: Map<String, int>.from(analytics['sourceTypeDistribution'])),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ============================================================
// SHARED DASHBOARD WIDGETS
// ============================================================

class _GreetingBanner extends StatelessWidget {
  final UserModel? user;
  final String subtitle;
  const _GreetingBanner({required this.user, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    final hour = DateTime.now().hour;
    final greeting = hour < 12 ? 'Selamat Pagi' : hour < 15 ? 'Selamat Siang' : hour < 18 ? 'Selamat Sore' : 'Selamat Malam';

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0EA5E9), Color(0xFF14B8A6)],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '$greeting, ${user?.name.split(' ').first ?? 'Pengguna'}!',
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Colors.white),
              ),
              const SizedBox(height: 4),
              Text(subtitle, style: TextStyle(fontSize: 14, color: Colors.white.withOpacity(0.85))),
            ],
          ),
          const Spacer(),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                _formatDate(DateTime.now()),
                style: TextStyle(fontSize: 13, color: Colors.white.withOpacity(0.85)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.circle, size: 8, color: Colors.white),
                    const SizedBox(width: 6),
                    Text(
                      user?.role.displayName ?? '',
                      style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime d) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Ags', 'Sep', 'Okt', 'Nov', 'Des'];
    return '${d.day} ${months[d.month - 1]} ${d.year}';
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final bool isNormal;
  final bool isAlert;

  const _StatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    this.isNormal = false,
    this.isAlert = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isAlert ? AppColors.warning : AppColors.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 20),
              ),
              const Spacer(),
              if (isNormal)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.successContainer,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text('Normal', style: TextStyle(fontSize: 10, color: AppColors.success, fontWeight: FontWeight.w600)),
                ),
              if (isAlert)
                const Icon(Icons.warning_amber_rounded, color: AppColors.warning, size: 16),
            ],
          ),
          const SizedBox(height: 16),
          Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.borderLight),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                  Text(subtitle, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final VoidCallback? onViewAll;

  const _SectionHeader({required this.title, this.onViewAll});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
        const Spacer(),
        if (onViewAll != null)
          TextButton(onPressed: onViewAll, child: const Text('Lihat Semua', style: TextStyle(fontSize: 12))),
      ],
    );
  }
}

class _EcgSessionCard extends StatelessWidget {
  final dynamic session;
  final bool compact;

  const _EcgSessionCard({required this.session, this.compact = false});

  @override
  Widget build(BuildContext context) {
    final statusColor = session.status.name == 'completed'
        ? AppColors.success
        : session.status.name == 'processing'
            ? AppColors.warning
            : AppColors.danger;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.monitor_heart_rounded, color: AppColors.primary, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  session.patientName as String,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
                ),
                Text(
                  '${session.leadConfigDisplay} • ${session.deviceName}',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
                if (!compact)
                  Text(
                    '${(session.examinationTime as DateTime).day}/${(session.examinationTime as DateTime).month}/${(session.examinationTime as DateTime).year}',
                    style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                  ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  session.statusDisplay as String,
                  style: TextStyle(fontSize: 10, color: statusColor, fontWeight: FontWeight.w600),
                ),
              ),
              if (!compact) ...[
                const SizedBox(height: 4),
                TextButton(
                  onPressed: () => context.go('/ecg/${session.sessionId}'),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Lihat EKG', style: TextStyle(fontSize: 11)),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _HealthInfoCard extends StatelessWidget {
  final dynamic patient;
  const _HealthInfoCard({required this.patient});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        children: [
          _InfoRow(label: 'Umur', value: '${patient.ageYears} tahun'),
          _InfoRow(label: 'Jenis Kelamin', value: patient.genderDisplay as String),
          _InfoRow(label: 'Golongan Darah', value: patient.bloodType ?? '-'),
          if (patient.bmi != null)
            _InfoRow(label: 'BMI', value: '${patient.bmi!.toStringAsFixed(1)} kg/m²'),
          if (patient.allergies.isNotEmpty)
            _InfoRow(label: 'Alergi', value: (patient.allergies as List).join(', ')),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: AppColors.textPrimary)),
        ],
      ),
    );
  }
}

class _LeadDistributionChart extends StatelessWidget {
  final Map<String, int> data;
  const _LeadDistributionChart({required this.data});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        children: data.entries.map((e) {
          final total = data.values.fold(0, (a, b) => a + b);
          final pct = (e.value / total * 100).round();
          final color = e.key.contains('12') ? AppColors.primary : AppColors.secondary;
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(e.key, style: const TextStyle(fontSize: 12, color: AppColors.textPrimary)),
                    Text('$pct%', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
                  ],
                ),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: pct / 100,
                    backgroundColor: AppColors.surfaceVariant,
                    valueColor: AlwaysStoppedAnimation<Color>(color),
                    minHeight: 6,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _RhythmPieChart extends StatelessWidget {
  final Map<String, int> data;
  const _RhythmPieChart({required this.data});

  @override
  Widget build(BuildContext context) {
    final colors = [AppColors.success, AppColors.danger, AppColors.secondary, AppColors.warning, AppColors.roleDoctor, AppColors.textMuted];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        children: [
          SizedBox(
            height: 160,
            child: PieChart(
              PieChartData(
                sections: data.entries.toList().asMap().entries.map((entry) {
                  final i = entry.key;
                  final e = entry.value;
                  return PieChartSectionData(
                    value: e.value.toDouble(),
                    title: '${e.value}%',
                    color: colors[i % colors.length],
                    radius: 55,
                    titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Colors.white),
                  );
                }).toList(),
                sectionsSpace: 2,
                centerSpaceRadius: 30,
              ),
            ),
          ),
          const SizedBox(height: 12),
          ...data.entries.toList().asMap().entries.take(4).map((entry) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(
              children: [
                Container(width: 8, height: 8, decoration: BoxDecoration(color: colors[entry.key % colors.length], shape: BoxShape.circle)),
                const SizedBox(width: 6),
                Expanded(child: Text(entry.value.key, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary))),
                Text('${entry.value.value}%', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
              ],
            ),
          )),
        ],
      ),
    );
  }
}

class _SourceTypePieChart extends StatelessWidget {
  final Map<String, int> data;
  const _SourceTypePieChart({required this.data});

  @override
  Widget build(BuildContext context) {
    final colors = [AppColors.primary, AppColors.secondary, AppColors.warning, AppColors.success];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        children: [
          SizedBox(
            height: 160,
            child: PieChart(
              PieChartData(
                sections: data.entries.toList().asMap().entries.map((entry) {
                  final i = entry.key;
                  final e = entry.value;
                  return PieChartSectionData(
                    value: e.value.toDouble(),
                    title: '${e.value}%',
                    color: colors[i % colors.length],
                    radius: 55,
                    titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Colors.white),
                  );
                }).toList(),
                sectionsSpace: 2,
                centerSpaceRadius: 30,
              ),
            ),
          ),
          const SizedBox(height: 12),
          ...data.entries.toList().asMap().entries.map((entry) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(
              children: [
                Container(width: 8, height: 8, decoration: BoxDecoration(color: colors[entry.key % colors.length], shape: BoxShape.circle)),
                const SizedBox(width: 6),
                Expanded(child: Text(entry.value.key, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary))),
                Text('${entry.value.value}%', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
              ],
            ),
          )),
        ],
      ),
    );
  }
}

class _MonthlySessionsChart extends StatelessWidget {
  final List<int> data;
  const _MonthlySessionsChart({required this.data});

  @override
  Widget build(BuildContext context) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun'];
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: SizedBox(
        height: 180,
        child: BarChart(
          BarChartData(
            alignment: BarChartAlignment.spaceAround,
            maxY: (data.reduce((a, b) => a > b ? a : b) * 1.2).toDouble(),
            gridData: FlGridData(
              show: true,
              drawVerticalLine: false,
              horizontalInterval: 20,
              getDrawingHorizontalLine: (v) => FlLine(color: AppColors.borderLight, strokeWidth: 1),
            ),
            borderData: FlBorderData(show: false),
            titlesData: FlTitlesData(
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  getTitlesWidget: (v, _) => Text(months[v.toInt()], style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                ),
              ),
              leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
              topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            ),
            barGroups: data.asMap().entries.map((e) => BarChartGroupData(
              x: e.key,
              barRods: [
                BarChartRodData(
                  toY: e.value.toDouble(),
                  color: AppColors.primary,
                  width: 24,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                  backDrawRodData: BackgroundBarChartRodData(
                    show: true,
                    toY: (data.reduce((a, b) => a > b ? a : b) * 1.2).toDouble(),
                    color: AppColors.surfaceVariant,
                  ),
                ),
              ],
            )).toList(),
          ),
        ),
      ),
    );
  }
}
