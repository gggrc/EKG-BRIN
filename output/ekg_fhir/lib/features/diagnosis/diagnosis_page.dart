// lib/features/diagnosis/diagnosis_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
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
  bool _isApproved = false;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    final session = MockData.ecgSessions.firstWhere((s) => s.sessionId == widget.sessionId, orElse: () => MockData.ecgSessions.first);
    if (session.analysis?.doctorDiagnosis != null) {
      _diagnosisCtrl.text = session.analysis!.doctorDiagnosis!;
    }
    _isApproved = session.analysis?.isApproved ?? false;
  }

  Future<void> _handleSave({bool approve = false}) async {
    if (_diagnosisCtrl.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Tulis diagnosis terlebih dahulu')));
      return;
    }
    setState(() => _isLoading = true);
    await Future.delayed(const Duration(milliseconds: 800));
    setState(() { _isLoading = false; _isApproved = approve; });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(approve ? 'Diagnosis disetujui dan laporan dibuat' : 'Diagnosis disimpan sebagai draft')),
      );
      if (approve) context.go('/report/${widget.sessionId}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = MockData.ecgSessions.firstWhere((s) => s.sessionId == widget.sessionId, orElse: () => MockData.ecgSessions.first);
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
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Panduan Diagnosis', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                  SizedBox(height: 12),
                  _GuideItem(icon: Icons.info_outline_rounded, text: 'Interpretasi AI hanya sebagai referensi, bukan pengganti penilaian klinis'),
                  _GuideItem(icon: Icons.check_circle_outline_rounded, text: 'Klik "Setujui & Buat Laporan" untuk finalisasi dan membuat PDF'),
                  _GuideItem(icon: Icons.cloud_sync_rounded, text: 'Laporan yang disetujui akan otomatis dikirim ke SATUSEHAT'),
                  _GuideItem(icon: Icons.history_rounded, text: 'Semua perubahan dicatat dalam audit log'),
                ],
              ),
            ),
          ),
        ],
      ),
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
