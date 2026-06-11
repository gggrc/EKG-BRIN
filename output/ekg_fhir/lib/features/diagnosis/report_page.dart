// lib/features/diagnosis/report_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/router/app_router.dart';

class ReportPage extends StatelessWidget {
  final String sessionId;
  const ReportPage({super.key, required this.sessionId});

  @override
  Widget build(BuildContext context) {
    final session = MockData.ecgSessions.firstWhere((s) => s.sessionId == sessionId, orElse: () => MockData.ecgSessions.first);
    final patient = MockData.patients.firstWhere((p) => p.patientId == session.patientId, orElse: () => MockData.patients.first);
    final analysis = session.analysis;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(onPressed: () => context.go(AppRoutes.history), icon: const Icon(Icons.arrow_back_rounded), color: AppColors.textSecondary),
              const SizedBox(width: 8),
              const Text('Laporan EKG', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
              const Spacer(),
              OutlinedButton.icon(onPressed: () {}, icon: const Icon(Icons.share_rounded, size: 16), label: const Text('FHIR Export')),
              const SizedBox(width: 12),
              ElevatedButton.icon(onPressed: () {}, icon: const Icon(Icons.download_rounded, size: 16), label: const Text('Download PDF')),
            ],
          ),
          const SizedBox(height: 24),
          // Report card (mimics PDF)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(40),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.borderLight),
              boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 20, offset: const Offset(0, 8))], // FIX: Menggunakan withValues pengganti withOpacity
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  children: [
                    Container(
                      width: 48, height: 48,
                      decoration: BoxDecoration(gradient: AppColors.primaryGradient, borderRadius: BorderRadius.circular(10)),
                      child: const Icon(Icons.monitor_heart, color: Colors.white, size: 26),
                    ),
                    const SizedBox(width: 16),
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('EKG-BRIN', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
                        Text('Sistem Rekam EKG Nasional — BRIN', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                      ],
                    ),
                    const Spacer(),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        const Text('LAPORAN EKG', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.primary, letterSpacing: 2)),
                        Text('ID: ${session.sessionId.toUpperCase()}', style: const TextStyle(fontSize: 11, color: AppColors.textMuted, fontFamily: 'monospace')),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                const Divider(color: AppColors.borderLight),
                const SizedBox(height: 20),
                // Patient info section
                _ReportSection(title: 'DATA PASIEN', children: [
                  _ReportRow(label: 'Nama Pasien', value: patient.fullName),
                  _ReportRow(label: 'No. Rekam Medis', value: patient.medicalRecordNumber),
                  _ReportRow(label: 'Tanggal Lahir', value: '${patient.birthDate.day}/${patient.birthDate.month}/${patient.birthDate.year}'),
                  _ReportRow(label: 'Jenis Kelamin', value: patient.genderDisplay),
                  // FIX: Menghapus baris NIK karena properti nik sudah tidak ada di model baru
                ]),
                const SizedBox(height: 20),
                _ReportSection(title: 'DATA PEREKAMAN', children: [
                  _ReportRow(label: 'Waktu', value: '${session.examinationTime.day}/${session.examinationTime.month}/${session.examinationTime.year}  ${session.examinationTime.hour.toString().padLeft(2, '0')}:${session.examinationTime.minute.toString().padLeft(2, '0')}'),
                  _ReportRow(label: 'Perangkat', value: session.deviceName),
                  _ReportRow(label: 'Konfigurasi Lead', value: session.leadConfigDisplay),
                  _ReportRow(label: 'Durasi', value: '${session.durationSec} detik'),
                  if (session.recordedByName != null) _ReportRow(label: 'Direkam Oleh', value: session.recordedByName!),
                ]),
                if (analysis != null) ...[
                  const SizedBox(height: 20),
                  _ReportSection(title: 'PARAMETER EKG', children: [
                    Row(
                      children: [
                        Expanded(child: Column(
                          children: [
                            if (analysis.heartRateBpm != null) _ParamBox(label: 'HR', value: '${analysis.heartRateBpm} bpm', isNormal: analysis.isHeartRateNormal),
                            if (analysis.rhythmType != null) _ParamBox(label: 'Irama', value: analysis.rhythmType!, isNormal: analysis.rhythmType == 'Sinus Normal'),
                          ],
                        )),
                        Expanded(child: Column(
                          children: [
                            if (analysis.prIntervalMs != null) _ParamBox(label: 'PR Interval', value: '${analysis.prIntervalMs!.round()} ms', isNormal: analysis.prIntervalMs! >= 120 && analysis.prIntervalMs! <= 200),
                            if (analysis.qrsDurationMs != null) _ParamBox(label: 'QRS Duration', value: '${analysis.qrsDurationMs!.round()} ms', isNormal: analysis.qrsDurationMs! <= 120),
                          ],
                        )),
                        Expanded(child: Column(
                          children: [
                            if (analysis.qtIntervalMs != null) _ParamBox(label: 'QT Interval', value: '${analysis.qtIntervalMs!.round()} ms', isNormal: true),
                            if (analysis.qtcIntervalMs != null) _ParamBox(label: 'QTc', value: '${analysis.qtcIntervalMs!.round()} ms', isNormal: analysis.isQtcNormal),
                          ],
                        )),
                        Expanded(child: Column(
                          children: [
                            if (analysis.electricalAxisDeg != null) _ParamBox(label: 'Axis Listrik', value: '${analysis.electricalAxisDeg!.round()}°', isNormal: true),
                          ],
                        )),
                      ],
                    ),
                  ]),
                  if (analysis.aiInterpretation != null) ...[
                    const SizedBox(height: 20),
                    _ReportSection(title: 'INTERPRETASI AI', children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: AppColors.roleDoctor.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8)), // FIX: .withOpacity diganti .withValues
                        child: Text(analysis.aiInterpretation!, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, height: 1.6)),
                      ),
                    ]),
                  ],
                  if (analysis.doctorDiagnosis != null) ...[
                    const SizedBox(height: 20),
                    _ReportSection(title: 'DIAGNOSIS DOKTER', children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: AppColors.successContainer, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.success.withValues(alpha: 0.2))), // FIX: .withOpacity diganti .withValues
                        child: Text(analysis.doctorDiagnosis!, style: const TextStyle(fontSize: 13, color: AppColors.successLight, height: 1.6)),
                      ),
                      if (analysis.isApproved == true && analysis.approvedBy != null) ...[
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            const Icon(Icons.verified_rounded, color: AppColors.success, size: 16),
                            const SizedBox(width: 6),
                            Text('Disetujui oleh ${analysis.approvedBy}', style: const TextStyle(fontSize: 12, color: AppColors.success, fontWeight: FontWeight.w500)),
                          ],
                        ),
                      ],
                    ]),
                  ],
                ],
                const SizedBox(height: 30),
                const Divider(color: AppColors.borderLight),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('EKG-BRIN — Sistem HL7 FHIR', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                    const Spacer(),
                    Text('Dicetak: ${DateTime.now().day}/${DateTime.now().month}/${DateTime.now().year}', style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                    const SizedBox(width: 16),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(color: AppColors.primaryContainer, borderRadius: BorderRadius.circular(4)),
                      child: const Text('HL7 FHIR R4', style: TextStyle(fontSize: 10, color: AppColors.primary, fontWeight: FontWeight.w700)),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportSection extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _ReportSection({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.primary, letterSpacing: 1.5)),
        const SizedBox(height: 10),
        ...children,
      ],
    );
  }
}

class _ReportRow extends StatelessWidget {
  final String label;
  final String value;
  const _ReportRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(width: 160, child: Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textMuted))),
          Text(value, style: const TextStyle(fontSize: 12, color: AppColors.textPrimary, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

class _ParamBox extends StatelessWidget {
  final String label;
  final String value;
  final bool isNormal;
  const _ParamBox({required this.label, required this.value, required this.isNormal});

  @override
  Widget build(BuildContext context) {
    final color = isNormal ? AppColors.success : AppColors.warning;
    return Container(
      margin: const EdgeInsets.all(4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8)), // FIX: .withOpacity diganti .withValues
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
          Text(value, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: color, fontFamily: 'monospace')),
          Text(isNormal ? 'Normal' : 'Perlu Perhatian', style: TextStyle(fontSize: 9, color: color)),
        ],
      ),
    );
  }
}