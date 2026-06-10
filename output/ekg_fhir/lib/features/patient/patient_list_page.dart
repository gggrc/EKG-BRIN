// lib/features/patient/patient_list_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/models/patient_model.dart';
import '../../core/router/app_router.dart';

class PatientListPage extends StatefulWidget {
  const PatientListPage({super.key});

  @override
  State<PatientListPage> createState() => _PatientListPageState();
}

class _PatientListPageState extends State<PatientListPage> {
  String _search = '';
  String _genderFilter = 'Semua';

  List<PatientModel> get _filtered {
    return MockData.patients.where((p) {
      final matchSearch = p.fullName.toLowerCase().contains(_search.toLowerCase()) ||
          p.medicalRecordNumber.toLowerCase().contains(_search.toLowerCase());
      final matchGender = _genderFilter == 'Semua' || p.genderDisplay == _genderFilter;
      return matchSearch && matchGender;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Toolbar
          Row(
            children: [
              Expanded(
                child: TextField(
                  onChanged: (v) => setState(() => _search = v),
                  decoration: const InputDecoration(
                    hintText: 'Cari nama atau nomor rekam medis...',
                    prefixIcon: Icon(Icons.search, size: 18),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
              ElevatedButton.icon(
                onPressed: () => context.go(AppRoutes.patientNew),
                icon: const Icon(Icons.person_add_rounded, size: 16),
                label: const Text('Tambah Pasien'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Summary row
          Text(
            '${_filtered.length} pasien ditemukan',
            style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 12),
          // Table header
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
          // Patient rows
          Expanded(
            child: ListView.separated(
              itemCount: _filtered.length,
              separatorBuilder: (_, __) => const SizedBox(height: 2),
              itemBuilder: (context, i) {
                final p = _filtered[i];
                return _PatientRow(patient: p);
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
    final lastEcg = patient.lastEcgDate;
    return InkWell(
      borderRadius: BorderRadius.circular(8),
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
            Expanded(
              flex: 3,
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 18,
                    backgroundColor: (patient.gender == 'M' ? AppColors.primary : AppColors.secondary).withOpacity(0.15),
                    child: Text(
                      patient.fullName[0],
                      style: TextStyle(
                        color: patient.gender == 'M' ? AppColors.primary : AppColors.secondary,
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(patient.fullName, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textPrimary), overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            ),
            Expanded(flex: 2, child: Text(patient.medicalRecordNumber, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontFamily: 'monospace'))),
            Expanded(child: Text('${patient.ageYears} th', style: const TextStyle(fontSize: 12, color: AppColors.textPrimary))),
            Expanded(child: Text(patient.genderDisplay, style: const TextStyle(fontSize: 12, color: AppColors.textPrimary))),
            Expanded(child: Text(patient.bloodType ?? '-', style: const TextStyle(fontSize: 12, color: AppColors.textPrimary))),
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '${patient.totalEcgSessions} sesi',
                  style: const TextStyle(fontSize: 11, color: AppColors.primary, fontWeight: FontWeight.w600),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            Expanded(child: Text(
              lastEcg != null ? '${lastEcg.day}/${lastEcg.month}/${lastEcg.year}' : '-',
              style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
            )),
            SizedBox(
              width: 80,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Tooltip(
                    message: 'Detail',
                    child: IconButton(
                      icon: const Icon(Icons.visibility_rounded, size: 16),
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
