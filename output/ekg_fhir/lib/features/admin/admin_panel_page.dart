// lib/features/admin/admin_panel_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/router/app_router.dart';

class AdminPanelPage extends StatelessWidget {
  const AdminPanelPage({super.key});

  @override
  Widget build(BuildContext context) {
    final analytics = MockData.analyticsData;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('System Overview', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 6),
          const Text('Ringkasan kondisi sistem EKG-BRIN', style: TextStyle(fontSize: 14, color: AppColors.textSecondary)),
          const SizedBox(height: 24),
          // Quick nav
          Row(
            children: [
              _AdminNavCard(icon: Icons.manage_accounts_rounded, title: 'Kelola User', subtitle: '${MockData.allUsersList.length} pengguna terdaftar', color: AppColors.primary, onTap: () => context.go(AppRoutes.adminUsers)),
              const SizedBox(width: 16),
              _AdminNavCard(icon: Icons.bar_chart_rounded, title: 'Analytics', subtitle: 'Laporan & statistik', color: AppColors.secondary, onTap: () => context.go(AppRoutes.analytics)),
              const SizedBox(width: 16),
              _AdminNavCard(icon: Icons.cloud_sync_rounded, title: 'FHIR Export', subtitle: '${analytics['fhirSyncedCount']} tersinkron', color: AppColors.success, onTap: () => context.go(AppRoutes.fhirExport)),
              const SizedBox(width: 16),
              _AdminNavCard(icon: Icons.download_rounded, title: 'Export Dataset', subtitle: 'Download untuk riset', color: AppColors.roleAdmin, onTap: () {}),
            ],
          ),
          const SizedBox(height: 24),
          // Audit log
          const Text('Audit Log — Aktivitas Terbaru', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 12),
          ...(_auditLogs().map((log) => _AuditLogItem(log: log))),
          const SizedBox(height: 24),
          // System status
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: _SystemStatusCard()),
              const SizedBox(width: 24),
              Expanded(child: _ConfigCard()),
            ],
          ),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> _auditLogs() => [
    {'user': 'dr. Andi Prasetyo, Sp.JP', 'action': 'Menyetujui diagnosis', 'target': 'Sesi s-001 (Budi Santoso)', 'time': '08/06/2026 10:45', 'type': 'approve'},
    {'user': 'Siti Rahayu, Amd.Kep', 'action': 'Upload EKG baru', 'target': 'Hendra Wijaya (RM-2025-002)', 'time': '08/06/2026 11:00', 'type': 'upload'},
    {'user': 'System', 'action': 'Sinkronisasi SATUSEHAT', 'target': '3 rekam EKG berhasil dikirim', 'time': '08/06/2026 06:00', 'type': 'sync'},
    {'user': 'Peneliti BRIN', 'action': 'Export dataset', 'target': '247 rekam EKG (Jan-Jun 2026)', 'time': '07/06/2026 17:30', 'type': 'export'},
    {'user': 'Peneliti BRIN', 'action': 'Tambah user baru', 'target': 'dr. Maya Kusuma, Sp.PD', 'time': '07/06/2026 09:15', 'type': 'user'},
    {'user': 'System', 'action': 'Backup database', 'target': 'Backup otomatis harian', 'time': '07/06/2026 00:00', 'type': 'system'},
  ];
}

class _AdminNavCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;
  const _AdminNavCard({required this.icon, required this.title, required this.subtitle, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.borderLight),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(10)),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(height: 12),
              Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
              Text(subtitle, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
            ],
          ),
        ),
      ),
    );
  }
}

class _AuditLogItem extends StatelessWidget {
  final Map<String, dynamic> log;
  const _AuditLogItem({required this.log});

  @override
  Widget build(BuildContext context) {
    final colors = {'approve': AppColors.success, 'upload': AppColors.primary, 'sync': AppColors.secondary, 'export': AppColors.roleAdmin, 'user': AppColors.warning, 'system': AppColors.textMuted};
    final icons = {'approve': Icons.check_circle_rounded, 'upload': Icons.upload_rounded, 'sync': Icons.cloud_sync_rounded, 'export': Icons.download_rounded, 'user': Icons.person_add_rounded, 'system': Icons.settings_rounded};
    final color = colors[log['type']] ?? AppColors.textMuted;
    final icon = icons[log['type']] ?? Icons.info_rounded;

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Row(
        children: [
          Container(
            width: 32, height: 32,
            decoration: BoxDecoration(color: color.withOpacity(0.12), shape: BoxShape.circle),
            child: Icon(icon, color: color, size: 16),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Text(log['user'] as String, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                const Text(' • ', style: TextStyle(color: AppColors.textMuted)),
                Text(log['action'] as String, style: TextStyle(fontSize: 12, color: color)),
              ]),
              Text(log['target'] as String, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
            ],
          )),
          Text(log['time'] as String, style: const TextStyle(fontSize: 11, color: AppColors.textMuted, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}

class _SystemStatusCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Status Sistem', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 16),
          ...([
            {'label': 'Database PostgreSQL', 'status': 'online'},
            {'label': 'SATUSEHAT API', 'status': 'online'},
            {'label': 'Backend Express.js', 'status': 'online'},
            {'label': 'AI Model Service', 'status': 'offline'},
            {'label': 'Storage (Supabase)', 'status': 'online'},
          ].map((item) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              children: [
                Container(
                  width: 8, height: 8,
                  decoration: BoxDecoration(
                    color: item['status'] == 'online' ? AppColors.success : AppColors.danger,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(item['label']!, style: const TextStyle(fontSize: 12, color: AppColors.textPrimary))),
                Text(item['status']!, style: TextStyle(fontSize: 11, color: item['status'] == 'online' ? AppColors.success : AppColors.danger, fontWeight: FontWeight.w600)),
              ],
            ),
          ))),
        ],
      ),
    );
  }
}

class _ConfigCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Konfigurasi Sistem', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 16),
          ...([
            {'label': 'FHIR Version', 'value': 'R4'},
            {'label': 'Sampling Rate', 'value': '500 Hz'},
            {'label': 'Auto Sync', 'value': 'Aktif (06:00 WIB)'},
            {'label': 'Backup', 'value': 'Harian (00:00 WIB)'},
            {'label': 'Max Upload', 'value': '50 MB'},
            {'label': 'Versi Sistem', 'value': 'v1.0.0-prototype'},
          ].map((item) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              children: [
                Expanded(child: Text(item['label']!, style: const TextStyle(fontSize: 12, color: AppColors.textMuted))),
                Text(item['value']!, style: const TextStyle(fontSize: 12, color: AppColors.textPrimary, fontWeight: FontWeight.w500, fontFamily: 'monospace')),
              ],
            ),
          ))),
        ],
      ),
    );
  }
}
