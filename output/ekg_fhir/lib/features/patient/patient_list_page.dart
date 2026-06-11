// lib/features/patient/patient_list_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../core/theme/app_colors.dart';
import '../../core/router/app_router.dart';
import '../../core/models/patient_model.dart';

class PatientListPage extends StatefulWidget {
  const PatientListPage({super.key});

  @override
  State<PatientListPage> createState() => _PatientListPageState();
}

class _PatientListPageState extends State<PatientListPage> {
  final _supabase = Supabase.instance.client;
  late Future<List<PatientModel>> _patientsFuture;
  String _searchQuery = '';
  String _genderFilter = 'Semua';

  @override
  void initState() {
    super.initState();
    _fetchPatientsFromSupabase();
  }

  void _fetchPatientsFromSupabase() {
    setState(() {
      _patientsFuture = _supabase
          .from('patients')
          .select()
          .order('full_name', ascending: true) 
          .limit(50) 
          .then((response) {
            final List data = response as List;
            return data.map((json) => PatientModel.fromJson(json)).toList();
          });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Toolbar Atas
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 400),
                  child: TextField(
                    onChanged: (v) => setState(() => _searchQuery = v.toLowerCase()),
                    decoration: const InputDecoration(
                      hintText: 'Cari nama atau nomor rekam medis...',
                      prefixIcon: Icon(Icons.search, size: 18),
                      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              _FilterChip(
                label: 'Semua',
                selected: _genderFilter == 'Semua',
                onTap: () => setState(() => _genderFilter = 'Semua'),
              ),
              const SizedBox(width: 6),
              _FilterChip(
                label: 'Laki-laki',
                selected: _genderFilter == 'Laki-laki',
                onTap: () => setState(() => _genderFilter = 'Laki-laki'),
              ),
              const SizedBox(width: 6),
              _FilterChip(
                label: 'Perempuan',
                selected: _genderFilter == 'Perempuan',
                onTap: () => setState(() => _genderFilter = 'Perempuan'),
              ),
              const SizedBox(width: 16),
              IconButton(
                onPressed: _fetchPatientsFromSupabase,
                icon: const Icon(Icons.refresh_rounded),
                tooltip: 'Refresh Data',
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => context.go(AppRoutes.patientNew),
                icon: const Icon(Icons.person_add_rounded, size: 16),
                label: const Text('Tambah Pasien'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Header Judul Kolom (Sesuai dengan screenshot antarmuka UI Anda)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Row(
              children: [
                Expanded(flex: 3, child: _HeaderCell('Nama Pasien')),
                Expanded(flex: 2, child: _HeaderCell('No. Rekam Medis')),
                Expanded(child: _HeaderCell('Usia')),
                Expanded(child: _HeaderCell('Gender')),
                Expanded(child: _HeaderCell('Gol. Darah')),
                Expanded(child: _HeaderCell('Sesi EKG')),
                Expanded(child: _HeaderCell('EKG Terakhir')),
                SizedBox(width: 80, child: _HeaderCell('Aksi')),
              ],
            ),
          ),
          const SizedBox(height: 4),
          
          // Builder Data Riil
          Expanded(
            child: FutureBuilder<List<PatientModel>>(
              future: _patientsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (snapshot.hasError) {
                  return Center(
                    child: Text(
                      'Gagal memuat database: ${snapshot.error}',
                      style: const TextStyle(color: AppColors.danger),
                    ),
                  );
                }

                final allPatients = snapshot.data ?? [];

                final filtered = allPatients.where((p) {
                  final matchSearch = p.fullName.toLowerCase().contains(_searchQuery) ||
                      p.medicalRecordNumber.toLowerCase().contains(_searchQuery);
                  final matchGender = _genderFilter == 'Semua' || p.genderDisplay == _genderFilter;
                  return matchSearch && matchGender;
                }).toList();

                // Status jumlah total baris ter-filter
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (mounted) {
                    // Dapat digunakan jika ingin menyinkronkan counter total eksternal
                  }
                });

                if (filtered.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.person_search_rounded, size: 48, color: AppColors.textMuted.withOpacity(0.5)),
                        const SizedBox(height: 12),
                        const Text('Tidak ada data pasien yang ditemukan.', style: TextStyle(color: AppColors.textSecondary)),
                      ],
                    ),
                  );
                }

                return ListView.separated(
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 4),
                  itemBuilder: (context, i) {
                    return _PatientRow(patient: filtered[i]);
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _HeaderCell extends StatelessWidget {
  final String text;
  const _HeaderCell(this.text);

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted, letterSpacing: 0.5),
  );
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _FilterChip({required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? AppColors.primary.withOpacity(0.15) : AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(6),
          border: selected ? Border.all(color: AppColors.primary.withOpacity(0.5)) : null,
        ),
        child: Text(
          label,
          style: TextStyle(fontSize: 12, color: selected ? AppColors.primary : AppColors.textSecondary, fontWeight: selected ? FontWeight.w600 : FontWeight.w400),
        ),
      ),
    );
  }
}

class _PatientRow extends StatelessWidget {
  final PatientModel patient;
  const _PatientRow({required this.patient});

  @override
  Widget build(BuildContext context) {
    final isMale = patient.gender.trim().toUpperCase() == 'M' || patient.gender.trim().toUpperCase() == 'MALE';

    return InkWell(
      borderRadius: BorderRadius.circular(8),
      // PERBAIKAN: Memastikan navigasi mengarah ke rute detail dengan ID pasien dari database
      onTap: () => context.go('/patients/${patient.patientId}'),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.borderLight),
        ),
        child: Row(
          children: [
            // 1. Nama Pasien
            Expanded(
              flex: 3,
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 18,
                    backgroundColor: (isMale ? AppColors.primary : AppColors.secondary).withOpacity(0.15),
                    child: Text(
                      patient.fullName.isNotEmpty ? patient.fullName[0].toUpperCase() : 'P',
                      style: TextStyle(
                        color: isMale ? AppColors.primary : AppColors.secondary,
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      patient.fullName, 
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textPrimary), 
                      overflow: TextOverflow.ellipsis
                    ),
                  ),
                ],
              ),
            ),
            // 2. No. Rekam Medis
            Expanded(
              flex: 2, 
              child: Text(
                patient.medicalRecordNumber, 
                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontFamily: 'monospace')
              )
            ),
            // 3. Usia
            Expanded(
              child: Text(
                '${patient.ageYears} th', 
                style: const TextStyle(fontSize: 12, color: AppColors.textPrimary)
              )
            ),
            // 4. Gender
            Expanded(
              child: Text(
                patient.genderDisplay, 
                style: const TextStyle(fontSize: 12, color: AppColors.textPrimary)
              )
            ),
            // 5. Gol. Darah
            Expanded(
              child: const Text(
                '-', 
                style: TextStyle(fontSize: 12, color: AppColors.textPrimary)
              )
            ),
            // 6. Sesi EKG
            Expanded(
              child: Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text(
                    '0 sesi', 
                    style: TextStyle(fontSize: 11, color: AppColors.primary, fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            ),
            // 7. EKG Terakhir
            Expanded(
              child: const Text(
                '-', 
                style: TextStyle(fontSize: 11, color: AppColors.textSecondary)
              )
            ),
            // 8. Aksi Kontrol
            SizedBox(
              width: 80,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Tooltip(
                    message: 'Detail',
                    child: IconButton(
                      icon: const Icon(Icons.visibility_rounded, size: 16),
                      // PERBAIKAN: Tombol ikon mata juga mengarah ke halaman detail yang sama
                      onPressed: () => context.go('/patients/${patient.patientId}'),
                      color: AppColors.textSecondary,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                      padding: EdgeInsets.zero,
                    ),
                  ),
                  Tooltip(
                    message: 'Edit',
                    child: IconButton(
                      icon: const Icon(Icons.edit_rounded, size: 16),
                      onPressed: () => context.go('/patients/${patient.patientId}/edit'),
                      color: AppColors.textSecondary,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                      padding: EdgeInsets.zero,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}