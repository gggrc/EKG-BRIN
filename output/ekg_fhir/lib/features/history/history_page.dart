// lib/features/history/history_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/models/user_model.dart';
import '../../core/models/ecg_models.dart';
import '../../core/mock/mock_data.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  String _search = '';
  String _statusFilter = 'Semua';
  String _leadFilter = 'Semua';

  List<EcgSession> _getFilteredSessions(UserModel? user) {
    final all = MockData.ecgSessions;
    return all.where((s) {
      // Jika user adalah pasien, hanya tampilkan data milik dirinya sendiri
      if (user?.role == UserRole.patient) {
        if (s.patientId != user?.userId) return false;
      }
      
      final matchSearch = s.patientName.toLowerCase().contains(_search.toLowerCase()) ||
          s.sessionId.toLowerCase().contains(_search.toLowerCase());
      final matchStatus = _statusFilter == 'Semua' || s.statusDisplay == _statusFilter;
      final matchLead = _leadFilter == 'Semua' || s.leadConfigDisplay == _leadFilter;
      return matchSearch && matchStatus && matchLead;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    // Mengambil data user langsung dari AuthProvider
    final user = context.watch<AuthProvider>().currentUser;
    final sessions = _getFilteredSessions(user);

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Filters
          Row(
            children: [
              Expanded(
                child: TextField(
                  onChanged: (v) => setState(() => _search = v),
                  decoration: const InputDecoration(
                    hintText: 'Cari nama pasien atau session ID...',
                    prefixIcon: Icon(Icons.search, size: 18),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              DropdownButton<String>(
                value: _statusFilter,
                dropdownColor: AppColors.surface,
                underline: const SizedBox(),
                style: const TextStyle(color: AppColors.textPrimary, fontSize: 13),
                items: ['Semua', 'Selesai', 'Diproses', 'Menunggu', 'Error']
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: (v) => setState(() => _statusFilter = v!),
              ),
              const SizedBox(width: 12),
              DropdownButton<String>(
                value: _leadFilter,
                dropdownColor: AppColors.surface,
                underline: const SizedBox(),
                style: const TextStyle(color: AppColors.textPrimary, fontSize: 13),
                items: ['Semua', '6-Lead', '12-Lead']
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: (v) => setState(() => _leadFilter = v!),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text('${sessions.length} rekaman EKG', style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
          const SizedBox(height: 12),
          // Session list
          Expanded(
            child: ListView.separated(
              itemCount: sessions.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, i) => _SessionCard(session: sessions[i], user: user),
            ),
          ),
        ],
      ),
    );
  }
}

class _SessionCard extends StatelessWidget {
  final EcgSession session;
  final UserModel? user;
  const _SessionCard({required this.session, required this.user});

  @override
  Widget build(BuildContext context) {
    final a = session.analysis;
    final statusColor = session.status == EcgSessionStatus.completed
        ? AppColors.success
        : session.status == EcgSessionStatus.processing
            ? AppColors.warning
            : AppColors.textMuted;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.monitor_heart_rounded, color: AppColors.primary, size: 24),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(session.patientName, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                    Row(
                      children: [
                        Text(session.leadConfigDisplay, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                        const Text(' • ', style: TextStyle(color: AppColors.textMuted)),
                        Text(session.deviceName, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                        const Text(' • ', style: TextStyle(color: AppColors.textMuted)),
                        Text(session.sourceType.name.toUpperCase(), style: const TextStyle(fontSize: 11, color: AppColors.textMuted, fontFamily: 'monospace')),
                      ],
                    ),
                    Text(
                      '${session.examinationTime.day}/${session.examinationTime.month}/${session.examinationTime.year}  ${session.examinationTime.hour.toString().padLeft(2, '0')}:${session.examinationTime.minute.toString().padLeft(2, '0')}',
                      style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(session.statusDisplay, style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w600)),
              ),
            ],
          ),
          if (a != null) ...[
            const SizedBox(height: 16),
            const Divider(color: AppColors.borderLight, height: 1),
            const SizedBox(height: 12),
            Row(
              children: [
                if (a.heartRateBpm != null)
                  _Measure(label: 'HR', value: '${a.heartRateBpm} bpm', isNormal: a.isHeartRateNormal),
                const SizedBox(width: 8),
                if (a.rhythmType != null)
                  _Measure(label: 'Irama', value: a.rhythmType!, isNormal: a.rhythmType == 'Sinus Normal'),
                const SizedBox(width: 8),
                if (a.qrsDurationMs != null)
                  _Measure(label: 'QRS', value: '${a.qrsDurationMs!.round()} ms', isNormal: a.qrsDurationMs! <= 120),
                const SizedBox(width: 8),
                if (a.qtcIntervalMs != null)
                  _Measure(label: 'QTc', value: '${a.qtcIntervalMs!.round()} ms', isNormal: a.isQtcNormal),
                const Spacer(),
                if (a.isApproved == true)
                  Row(
                    children: const [
                      Icon(Icons.verified_rounded, size: 14, color: AppColors.success),
                      SizedBox(width: 4),
                      Text('Disetujui Dokter', style: TextStyle(fontSize: 11, color: AppColors.success)),
                    ],
                  )
                // Memanfaatkan helper dari UserModel
                else if (user?.canWriteDiagnosis == true)
                  ElevatedButton(
                    onPressed: () => context.go('/diagnosis/${session.sessionId}'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.warning,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: const Text('Tulis Diagnosis', style: TextStyle(fontSize: 11, color: Colors.white)),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              ElevatedButton.icon(
                onPressed: () => context.go('/ecg/${session.sessionId}'),
                icon: const Icon(Icons.monitor_heart_rounded, size: 14),
                label: const Text('Buka EKG Viewer', style: TextStyle(fontSize: 12)),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
              const SizedBox(width: 8),
              // Memanfaatkan helper dari UserModel untuk akses laporan (Nakes & Admin)
              if (user?.canViewAllPatients == true)
                OutlinedButton.icon(
                  onPressed: () => context.go('/report/${session.sessionId}'),
                  icon: const Icon(Icons.description_rounded, size: 14),
                  label: const Text('Laporan', style: TextStyle(fontSize: 12)),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                ),
              const Spacer(),
              if (session.recordedByName != null)
                Text('Direkam oleh: ${session.recordedByName}', style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
            ],
          ),
        ],
      ),
    );
  }
}

class _Measure extends StatelessWidget {
  final String label;
  final String value;
  final bool isNormal;
  const _Measure({required this.label, required this.value, required this.isNormal});

  @override
  Widget build(BuildContext context) {
    final color = isNormal ? AppColors.success : AppColors.warning;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Text(label, style: const TextStyle(fontSize: 9, color: AppColors.textMuted)),
          Text(value, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}