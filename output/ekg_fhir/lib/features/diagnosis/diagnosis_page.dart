// lib/features/diagnosis/diagnosis_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/models/ecg_models.dart';
import '../../core/providers/data_provider.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/router/app_router.dart';

class DiagnosisPage extends StatefulWidget {
  final String sessionId;
  const DiagnosisPage({super.key, required this.sessionId});

  @override
  State<DiagnosisPage> createState() => _DiagnosisPageState();
}

class _DiagnosisPageState extends State<DiagnosisPage> {
  final _diagnosisCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    final sessions = context.read<DataProvider>().ecgSessions;
    final session = sessions.firstWhere((s) => s.sessionId == widget.sessionId, orElse: () => sessions.first);
    if (session.analysis?.doctorDiagnosis != null) {
      _diagnosisCtrl.text = session.analysis!.doctorDiagnosis!;
    }
    }

  Future<void> _handleSave({bool approve = false}) async {
    if (_diagnosisCtrl.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Tulis diagnosis terlebih dahulu')));
      return;
    }
    setState(() => _isLoading = true);
    setState(() { _isLoading = false; });
    if (mounted) {
      final dataProvider = context.read<DataProvider>();
      final authProvider = context.read<AuthProvider>();
      final user = authProvider.currentUser;

      dataProvider.updateDiagnosis(widget.sessionId, _diagnosisCtrl.text, approve);

      if (user != null) {
        final session = dataProvider.ecgSessions.firstWhere((s) => s.sessionId == widget.sessionId);
        dataProvider.addActivityLog(ActivityLogModel(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          userName: user.name,
          action: approve ? 'Menyetujui diagnosis' : 'Menyimpan draft diagnosis',
          target: 'Sesi ${session.sessionId} (${session.patientName})',
          time: DateTime.now(),
          type: approve ? 'approve' : 'system',
        ));
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(approve ? 'Diagnosis disetujui dan laporan dibuat' : 'Diagnosis disimpan sebagai draft')),
      );

      if (approve) {
        // Find next pending session
        final sessions = dataProvider.ecgSessions;
        final pending = sessions.where((s) => s.status == EcgSessionStatus.pending && s.sessionId != widget.sessionId).toList();
        
        if (pending.isNotEmpty) {
          context.go('/diagnosis/${pending.first.sessionId}');
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Melanjutkan ke pasien berikutnya')));
        } else {
          context.go(AppRoutes.dashboard);
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Semua antrean diagnosis selesai!')));
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final sessions = context.watch<DataProvider>().ecgSessions;
    final session = sessions.firstWhere((s) => s.sessionId == widget.sessionId, orElse: () => sessions.first);
    final analysis = session.analysis;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 3,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    IconButton(onPressed: () => context.go(AppRoutes.history), icon: const Icon(Icons.arrow_back_rounded), color: AppColors.textSecondary),
                    const SizedBox(width: 8),
                    const Text('Diagnosis & Laporan', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                  ],
                ),
                const SizedBox(height: 20),
                // Patient + session info
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
                  child: Row(
                    children: [
                      Expanded(child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Pasien', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          Text(session.patientName, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                        ],
                      )),
                      Expanded(child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Perangkat', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          Text(session.deviceName, style: const TextStyle(fontSize: 13, color: AppColors.textPrimary)),
                        ],
                      )),
                      Expanded(child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Konfigurasi', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          Text(session.leadConfigDisplay, style: const TextStyle(fontSize: 13, color: AppColors.textPrimary)),
                        ],
                      )),
                      Expanded(child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Waktu Perekaman', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          Text('${session.examinationTime.day}/${session.examinationTime.month}/${session.examinationTime.year}', style: const TextStyle(fontSize: 13, color: AppColors.textPrimary)),
                        ],
                      )),
                      OutlinedButton.icon(
                        onPressed: () => context.go('/ecg/${session.sessionId}'),
                        icon: const Icon(Icons.monitor_heart_rounded, size: 14),
                        label: const Text('Buka EKG', style: TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                // AI Interpretation
                if (analysis?.aiInterpretation != null)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.roleDoctor.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.roleDoctor.withOpacity(0.2)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.psychology_rounded, color: AppColors.roleDoctor, size: 16),
                            SizedBox(width: 8),
                            Text('Interpretasi AI (Referensi)', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.roleDoctor)),
                            SizedBox(width: 8),
                            Text('— Perlu verifikasi dokter', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                          ],
                        ),
                        const SizedBox(height: 12),
                        // Measurements
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            if (analysis?.heartRateBpm != null) _MeasurePill(label: 'HR: ${analysis!.heartRateBpm} bpm', isNormal: analysis.isHeartRateNormal),
                            if (analysis?.rhythmType != null) _MeasurePill(label: analysis!.rhythmType!, isNormal: analysis.rhythmType == 'Sinus Normal'),
                            if (analysis?.prIntervalMs != null) _MeasurePill(label: 'PR: ${analysis!.prIntervalMs!.round()} ms', isNormal: analysis.prIntervalMs! >= 120 && analysis.prIntervalMs! <= 200),
                            if (analysis?.qrsDurationMs != null) _MeasurePill(label: 'QRS: ${analysis!.qrsDurationMs!.round()} ms', isNormal: analysis.qrsDurationMs! <= 120),
                            if (analysis?.qtcIntervalMs != null) _MeasurePill(label: 'QTc: ${analysis!.qtcIntervalMs!.round()} ms', isNormal: analysis.isQtcNormal),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(analysis!.aiInterpretation!, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, height: 1.6)),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),
                // Doctor diagnosis form
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Diagnosis Dokter', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(height: 4),
                      const Text('Tulis interpretasi klinis dan diagnosis final berdasarkan tinjauan EKG', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _diagnosisCtrl,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: 'Diagnosis / Interpretasi Klinis',
                          hintText: 'Contoh: Sinus normal. Tidak ada indikasi iskemia atau aritmia. HR 75 bpm...',
                          prefixIcon: Padding(padding: EdgeInsets.only(top: 12), child: Icon(Icons.medical_information_rounded, size: 18)),
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _notesCtrl,
                        maxLines: 2,
                        decoration: const InputDecoration(
                          labelText: 'Catatan Tambahan (opsional)',
                          prefixIcon: Padding(padding: EdgeInsets.only(top: 12), child: Icon(Icons.note_outlined, size: 18)),
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 20),
                      Row(
                        children: [
                          OutlinedButton.icon(
                            onPressed: _isLoading ? null : () => _handleSave(approve: false),
                            icon: const Icon(Icons.save_outlined, size: 16),
                            label: const Text('Simpan Draft'),
                          ),
                          const SizedBox(width: 12),
                          ElevatedButton.icon(
                            onPressed: _isLoading ? null : () => _handleSave(approve: true),
                            icon: _isLoading
                                ? const SizedBox(height: 14, width: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                : const Icon(Icons.check_circle_rounded, size: 16),
                            label: const Text('Setujui & Buat Laporan'),
                            style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 24),
          SizedBox(
            width: 280,
            child: Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Antrean Diagnosis', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                  const SizedBox(height: 12),
                  _buildPendingDropdown(context, sessions),
                  const Divider(height: 32, color: AppColors.borderLight),
                  const Text('Panduan Diagnosis', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                  const SizedBox(height: 12),
                  const _GuideItem(icon: Icons.info_outline_rounded, text: 'Interpretasi AI hanya sebagai referensi, bukan pengganti penilaian klinis'),
                  const _GuideItem(icon: Icons.check_circle_outline_rounded, text: 'Klik "Setujui & Buat Laporan" untuk lanjut ke antrean berikutnya'),
                  const _GuideItem(icon: Icons.cloud_sync_rounded, text: 'Laporan yang disetujui akan diarsipkan dan dapat diekspor ke FHIR'),
                  const _GuideItem(icon: Icons.history_rounded, text: 'Semua perubahan dicatat dalam audit log'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPendingDropdown(BuildContext context, List<EcgSession> allSessions) {
    final pending = allSessions.where((s) => s.status == EcgSessionStatus.pending).toList();
    if (pending.isEmpty) {
      return const Text('Tidak ada antrean', style: TextStyle(fontSize: 12, color: AppColors.textMuted));
    }

    // Pastikan session saat ini ada di list dropdown (biarpun sudah selesai, agar dropdown tidak error jika value tidak ada di item)
    final currentInPending = pending.any((s) => s.sessionId == widget.sessionId);
    final items = List<EcgSession>.from(pending);
    if (!currentInPending) {
      final currentSession = allSessions.firstWhere((s) => s.sessionId == widget.sessionId, orElse: () => allSessions.first);
      items.add(currentSession);
    }

    return DropdownButtonFormField<String>(
      value: widget.sessionId,
      isExpanded: true,
      dropdownColor: AppColors.surface,
      decoration: const InputDecoration(
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      items: items.map((s) => DropdownMenuItem(
        value: s.sessionId,
        child: Text('${s.patientName} (${s.sessionId})', style: const TextStyle(fontSize: 12), overflow: TextOverflow.ellipsis),
      )).toList(),
      onChanged: (val) {
        if (val != null && val != widget.sessionId) {
          context.go('/diagnosis/$val');
        }
      },
    );
  }
}

class _MeasurePill extends StatelessWidget {
  final String label;
  final bool isNormal;
  const _MeasurePill({required this.label, required this.isNormal});

  @override
  Widget build(BuildContext context) {
    final color = isNormal ? AppColors.success : AppColors.warning;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: color.withOpacity(0.12), borderRadius: BorderRadius.circular(6)),
      child: Text(label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _GuideItem extends StatelessWidget {
  final IconData icon;
  final String text;
  const _GuideItem({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: AppColors.textMuted),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: const TextStyle(fontSize: 12, color: AppColors.textMuted, height: 1.5))),
        ],
      ),
    );
  }
}
