// lib/features/patient/patient_detail_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../core/theme/app_colors.dart';
import '../../core/router/app_router.dart';
import '../../core/models/patient_model.dart';

class PatientDetailPage extends StatefulWidget {
  final String patientId;
  const PatientDetailPage({super.key, required this.patientId});

  @override
  State<PatientDetailPage> createState() => _PatientDetailPageState();
}

class _PatientDetailPageState extends State<PatientDetailPage> {
  final _supabase = Supabase.instance.client;
  late Future<PatientModel?> _patientFuture;
  late Future<List<dynamic>> _ecgSessionsFuture;

  @override
  void initState() {
    super.initState();
    _loadPatientData();
  }

  void _loadPatientData() {
    // FIX: Menghapus 'as Map<String, dynamic>' atau cast manual yang tidak perlu di baris ini
    _patientFuture = _supabase
        .from('patients')
        .select()
        .eq('patient_id', widget.patientId)
        .maybeSingle()
        .then((response) {
          if (response == null) return null;
          return PatientModel.fromJson(response);
        });

    _ecgSessionsFuture = _supabase
        .from('ecg_sessions')
        .select()
        .eq('patient_id', widget.patientId)
        .order('examination_time', ascending: false)
        .then((response) => response as List<dynamic>);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<PatientModel?>(
      future: _patientFuture,
      builder: (context, patientSnapshot) {
        if (patientSnapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        if (patientSnapshot.hasError || !patientSnapshot.hasData || patientSnapshot.data == null) {
          return Scaffold(
            backgroundColor: AppColors.background,
            body: Center(
              child: Container(
                padding: const EdgeInsets.all(32),
                margin: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.borderLight),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline_rounded, size: 48, color: AppColors.warning),
                    const SizedBox(height: 16),
                    const Text(
                      'Data Gagal Dimuat',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Pasien dengan ID "${widget.patientId}" tidak ditemukan di database Supabase.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton.icon(
                      onPressed: () => context.go(AppRoutes.patients),
                      icon: const Icon(Icons.arrow_back, size: 16),
                      label: const Text('Kembali ke Daftar Pasien'),
                    ),
                  ],
                ),
              ),
            ),
          );
        }

        final patient = patientSnapshot.data!;
        final isMale = patient.gender.trim().toUpperCase() == 'M' || patient.gender.trim().toUpperCase() == 'L';

        return FutureBuilder<List<dynamic>>(
          future: _ecgSessionsFuture,
          builder: (context, sessionsSnapshot) {
            final sessions = sessionsSnapshot.data ?? [];

            return SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header kontrol atas
                  Row(
                    children: [
                      IconButton(
                        onPressed: () => context.go(AppRoutes.patients), 
                        icon: const Icon(Icons.arrow_back_rounded), 
                        color: AppColors.textSecondary
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'Detail Pasien', 
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)
                      ),
                      const Spacer(),
                      OutlinedButton.icon(
                        onPressed: () => context.go('/patients/${widget.patientId}/edit'),
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
                  
                  // Layout Grid Utama
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Kolom Kiri: Kartu Informasi Utama Pasien
                      Expanded(
                        flex: 1,
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
                                mainAxisAlignment: MainAxisAlignment.start,
                                children: [
                                  CircleAvatar(
                                    radius: 32,
                                    backgroundColor: (isMale ? AppColors.primary : AppColors.secondary).withValues(alpha: 0.15),
                                    child: Text(
                                      patient.fullName.isNotEmpty ? patient.fullName[0].toUpperCase() : 'P', 
                                      style: TextStyle(
                                        fontSize: 28, 
                                        fontWeight: FontWeight.w700, 
                                        color: isMale ? AppColors.primary : AppColors.secondary
                                      )
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          patient.fullName, 
                                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        Text(
                                          "No. RM: ${patient.medicalRecordNumber}", 
                                          style: const TextStyle(fontSize: 13, color: AppColors.textMuted, fontFamily: 'monospace')
                                        ),
                                        const SizedBox(height: 6),
                                        Row(
                                          children: [
                                            _Badge(text: patient.genderDisplay, color: isMale ? AppColors.primary : AppColors.secondary),
                                            const SizedBox(width: 8),
                                            _Badge(text: '${patient.ageYears} tahun', color: AppColors.textSecondary),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 20),
                              const Divider(color: AppColors.borderLight),
                              const SizedBox(height: 16),
                              
                              // Blok Informasi Fisik & Medis
                              _Grid(
                                children: [
                                  _InfoTile(
                                    label: 'Tanggal Lahir', 
                                    value: '${patient.birthDate.day} ${_getMonthName(patient.birthDate.month)} ${patient.birthDate.year}'
                                  ),
                                  // FIX: Memeriksa kondisi null sebelum menggunakan properti .round()
                                  _InfoTile(
                                    label: 'Tinggi Badan', 
                                    value: patient.heightCm != null ? '${patient.heightCm!.round()} cm' : '-'
                                  ),
                                  _InfoTile(
                                    label: 'Berat Badan', 
                                    value: patient.weightKg != null ? '${patient.weightKg} kg' : '-'
                                  ),
                                  _InfoTile(
                                    label: 'Indeks BMI', 
                                    value: patient.bmi != null ? '${patient.bmi!.toStringAsFixed(1)} kg/m²' : '-'
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 24),
                      
                      // Kolom Kanan: Daftar Riwayat Sesi EKG
                      Expanded(
                        flex: 1,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Text(
                                  'Riwayat Pemeriksaan EKG', 
                                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)
                                ),
                                const SizedBox(width: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: AppColors.primary.withValues(alpha: 0.1), 
                                    borderRadius: BorderRadius.circular(4)
                                  ),
                                  child: Text(
                                    '${sessions.length}', 
                                    style: const TextStyle(fontSize: 11, color: AppColors.primary, fontWeight: FontWeight.w700)
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            
                            if (sessions.isEmpty)
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(32),
                                decoration: BoxDecoration(
                                  color: AppColors.surface,
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: AppColors.borderLight),
                                ),
                                child: const Center(
                                  child: Text(
                                    'Belum ada riwayat rekaman EKG di database.', 
                                    style: TextStyle(color: AppColors.textMuted, fontSize: 13)
                                  )
                                ),
                              )
                            else
                              ...sessions.map((s) {
                                final time = s['examination_time'] != null ? DateTime.parse(s['examination_time']) : DateTime.now();
                                final config = s['lead_configuration'] ?? 'twelveLead';
                                final displayConfig = config == 'sixLead' ? '6-Lead' : '12-Lead';
                                
                                return Container(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color: AppColors.surface,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: AppColors.borderLight),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.monitor_heart_rounded, color: AppColors.primary, size: 24),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              displayConfig, 
                                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)
                                            ),
                                            Text(
                                              'Perangkat: ${s['device_name'] ?? '-'}', 
                                              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)
                                            ),
                                            Text(
                                              'Waktu: ${time.day}/${time.month}/${time.year} ${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}',
                                              style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                                            ),
                                          ],
                                        ),
                                      ),
                                      ElevatedButton(
                                        onPressed: () => context.go('/ecg/${s['session_id']}'),
                                        style: ElevatedButton.styleFrom(
                                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                          minimumSize: Size.zero,
                                        ),
                                        child: const Text('Lihat', style: TextStyle(fontSize: 12)),
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
          },
        );
      },
    );
  }

  String _getMonthName(int month) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    if (month >= 1 && month <= 12) return months[month - 1];
    return '';
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
        color: color.withValues(alpha: 0.12),
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
      spacing: 16,
      runSpacing: 16,
      children: children.map((widget) => SizedBox(width: 140, child: widget)).toList(),
    );
  }
}

class _InfoTile extends StatelessWidget {
  final String label;
  final String value;
  const _InfoTile({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontSize: 13, color: AppColors.textPrimary, fontWeight: FontWeight.w600)),
      ],
    );
  }
}