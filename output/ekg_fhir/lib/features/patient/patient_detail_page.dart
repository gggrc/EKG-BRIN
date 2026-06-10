// lib/features/patient/patient_detail_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/router/app_router.dart';

class PatientDetailPage extends StatelessWidget {
  final String patientId;
  const PatientDetailPage({super.key, required this.patientId});

  @override
  Widget build(BuildContext context) {
    final patient = MockData.patients.firstWhere(
      (p) => p.patientId == patientId,
      orElse: () => MockData.patients.first,
    );
    final sessions = MockData.ecgSessions.where((s) => s.patientId == patientId).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(onPressed: () => context.go(AppRoutes.patients), icon: const Icon(Icons.arrow_back_rounded), color: AppColors.textSecondary),
              const SizedBox(width: 8),
              const Text('Detail Pasien', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: () => context.go('/patients/$patientId/edit'),
                icon: const Icon(Icons.edit_rounded, size: 16),
                label: const Text('Edit'),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: () => context.go(AppRoutes.acquisition),
                icon: const Icon(Icons.monitor_heart_rounded, size: 16),
                label: const Text('Rekam EKG Baru'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Patient card
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.borderLight),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 32,
                            backgroundColor: (patient.gender == 'M' ? AppColors.primary : AppColors.secondary).withOpacity(0.15),
                            child: Text(patient.fullName[0], style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: patient.gender == 'M' ? AppColors.primary : AppColors.secondary)),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(patient.fullName, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                                Text(patient.medicalRecordNumber, style: const TextStyle(fontSize: 13, color: AppColors.textMuted, fontFamily: 'monospace')),
                                const SizedBox(height: 4),
                                Row(children: [
                                  _Badge(text: patient.genderDisplay, color: patient.gender == 'M' ? AppColors.primary : AppColors.secondary),
                                  const SizedBox(width: 8),
                                  _Badge(text: '${patient.ageYears} tahun', color: AppColors.textSecondary),
                                  if (patient.bloodType != null) ...[
                                    const SizedBox(width: 8),
                                    _Badge(text: patient.bloodType!, color: AppColors.danger),
                                  ],
                                ]),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      const Divider(color: AppColors.borderLight),
                      const SizedBox(height: 16),
                      _Grid(children: [
                        _InfoTile(label: 'NIK', value: patient.nik ?? '-'),
                        _InfoTile(label: 'Tanggal Lahir', value: '${patient.birthDate.day}/${patient.birthDate.month}/${patient.birthDate.year}'),
                        _InfoTile(label: 'No. Telepon', value: patient.phoneNumber ?? '-'),
                        _InfoTile(label: 'Alamat', value: patient.address ?? '-'),
                        if (patient.heightCm != null) _InfoTile(label: 'Tinggi', value: '${patient.heightCm} cm'),
                        if (patient.weightKg != null) _InfoTile(label: 'Berat', value: '${patient.weightKg} kg'),
                        if (patient.bmi != null) _InfoTile(label: 'BMI', value: '${patient.bmi!.toStringAsFixed(1)} kg/m²'),
                      ]),
                      if (patient.allergies.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        const Text('Alergi', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 6,
                          children: patient.allergies.map((a) => Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(color: AppColors.dangerContainer, borderRadius: BorderRadius.circular(4)),
                            child: Text(a, style: const TextStyle(fontSize: 11, color: AppColors.dangerLight)),
                          )).toList(),
                        ),
                      ],
                      if (patient.currentMedications.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        const Text('Obat Saat Ini', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 6,
                          children: patient.currentMedications.map((m) => Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(color: AppColors.primaryContainer, borderRadius: BorderRadius.circular(4)),
                            child: Text(m, style: const TextStyle(fontSize: 11, color: AppColors.primaryLight)),
                          )).toList(),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 24),
              // EKG sessions
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text('Riwayat EKG', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(color: AppColors.primaryContainer, borderRadius: BorderRadius.circular(4)),
                          child: Text('${sessions.length}', style: const TextStyle(fontSize: 11, color: AppColors.primary, fontWeight: FontWeight.w700)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (sessions.isEmpty)
                      Container(
                        padding: const EdgeInsets.all(32),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.borderLight),
                        ),
                        child: const Center(child: Text('Belum ada rekaman EKG', style: TextStyle(color: AppColors.textMuted))),
                      )
                    else
                      ...sessions.map((s) {
                        final a = s.analysis;
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.surface,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppColors.borderLight),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.monitor_heart_rounded, color: AppColors.primary, size: 18),
                                  const SizedBox(width: 8),
                                  Text(s.leadConfigDisplay, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                                  const Spacer(),
                                  Text(
                                    '${s.examinationTime.day}/${s.examinationTime.month}/${s.examinationTime.year}',
                                    style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                                  ),
                                ],
                              ),
                              if (a != null) ...[
                                const SizedBox(height: 8),
                                Row(
                                  children: [
                                    if (a.heartRateBpm != null)
                                      _MiniChip(label: 'HR: ${a.heartRateBpm} bpm', isNormal: a.isHeartRateNormal),
                                    const SizedBox(width: 6),
                                    if (a.rhythmType != null)
                                      _MiniChip(label: a.rhythmType!, isNormal: a.rhythmType == 'Sinus Normal'),
                                  ],
                                ),
                              ],
                              const SizedBox(height: 8),
                              ElevatedButton(
                                onPressed: () => context.go('/ecg/${s.sessionId}'),
                                style: ElevatedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                  minimumSize: Size.zero,
                                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                ),
                                child: const Text('Lihat EKG', style: TextStyle(fontSize: 11)),
                              ),
                            ],
                          ),
                        );
                      }),
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

class _Badge extends StatelessWidget {
  final String text;
  final Color color;
  const _Badge({required this.text, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(text, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _Grid extends StatelessWidget {
  final List<Widget> children;
  const _Grid({required this.children});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 0,
      runSpacing: 0,
      children: children.asMap().entries.map((e) => SizedBox(width: 200, child: e.value)).toList(),
    );
  }
}

class _InfoTile extends StatelessWidget {
  final String label;
  final String value;
  const _InfoTile({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 13, color: AppColors.textPrimary, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

class _MiniChip extends StatelessWidget {
  final String label;
  final bool isNormal;
  const _MiniChip({required this.label, required this.isNormal});

  @override
  Widget build(BuildContext context) {
    final color = isNormal ? AppColors.success : AppColors.warning;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(label, style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w600)),
    );
  }
}
