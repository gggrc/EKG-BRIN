// lib/features/patient/patient_form_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/router/app_router.dart';

class PatientFormPage extends StatefulWidget {
  final String? patientId; // null = new patient
  const PatientFormPage({super.key, this.patientId});

  @override
  State<PatientFormPage> createState() => _PatientFormPageState();
}

class _PatientFormPageState extends State<PatientFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _rmCtrl = TextEditingController();
  final _nikCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _heightCtrl = TextEditingController();
  final _weightCtrl = TextEditingController();
  String _gender = 'M';
  String? _bloodType;
  DateTime? _birthDate;
  bool _isLoading = false;

  bool get isEditing => widget.patientId != null;

  @override
  void initState() {
    super.initState();
    if (isEditing) _loadPatient();
  }

  void _loadPatient() {
    final p = MockData.patients.firstWhere((p) => p.patientId == widget.patientId, orElse: () => MockData.patients.first);
    _nameCtrl.text = p.fullName;
    _rmCtrl.text = p.medicalRecordNumber;
    _nikCtrl.text = p.nik ?? '';
    _phoneCtrl.text = p.phoneNumber ?? '';
    _addressCtrl.text = p.address ?? '';
    _heightCtrl.text = p.heightCm?.toString() ?? '';
    _weightCtrl.text = p.weightKg?.toString() ?? '';
    _gender = p.gender;
    _bloodType = p.bloodType;
    _birthDate = p.birthDate;
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);
    await Future.delayed(const Duration(milliseconds: 800));
    setState(() => _isLoading = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(isEditing ? 'Data pasien berhasil diperbarui' : 'Pasien baru berhasil ditambahkan')),
      );
      context.go(AppRoutes.patients);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Row(
            children: [
              IconButton(
                onPressed: () => context.go(AppRoutes.patients),
                icon: const Icon(Icons.arrow_back_rounded),
                color: AppColors.textSecondary,
              ),
              const SizedBox(width: 8),
              Text(
                isEditing ? 'Edit Data Pasien' : 'Tambah Pasien Baru',
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      _FormSection(
                        title: 'Data Identitas',
                        children: [
                          Row(
                            children: [
                              Expanded(child: _Field(ctrl: _nameCtrl, label: 'Nama Lengkap', icon: Icons.person_outline, required: true)),
                              const SizedBox(width: 16),
                              Expanded(child: _Field(ctrl: _rmCtrl, label: 'No. Rekam Medis', icon: Icons.badge_outlined, required: true)),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(child: _Field(ctrl: _nikCtrl, label: 'NIK', icon: Icons.credit_card_outlined)),
                              const SizedBox(width: 16),
                              Expanded(child: _Field(ctrl: _phoneCtrl, label: 'No. Telepon', icon: Icons.phone_outlined, keyboardType: TextInputType.phone)),
                            ],
                          ),
                          const SizedBox(height: 16),
                          _Field(ctrl: _addressCtrl, label: 'Alamat', icon: Icons.location_on_outlined, maxLines: 2),
                        ],
                      ),
                      const SizedBox(height: 20),
                      _FormSection(
                        title: 'Data Medis',
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('Jenis Kelamin', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                                    const SizedBox(height: 8),
                                    Row(
                                      children: [
                                        _GenderChip(label: 'Laki-laki', value: 'M', selected: _gender == 'M', onTap: () => setState(() => _gender = 'M')),
                                        const SizedBox(width: 8),
                                        _GenderChip(label: 'Perempuan', value: 'F', selected: _gender == 'F', onTap: () => setState(() => _gender = 'F')),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('Tanggal Lahir', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                                    const SizedBox(height: 8),
                                    InkWell(
                                      onTap: () async {
                                        final picked = await showDatePicker(
                                          context: context,
                                          initialDate: _birthDate ?? DateTime(1990),
                                          firstDate: DateTime(1920),
                                          lastDate: DateTime.now(),
                                        );
                                        if (picked != null) setState(() => _birthDate = picked);
                                      },
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                                        decoration: BoxDecoration(
                                          color: AppColors.surface,
                                          borderRadius: BorderRadius.circular(10),
                                          border: Border.all(color: AppColors.borderLight),
                                        ),
                                        child: Row(
                                          children: [
                                            const Icon(Icons.calendar_today_outlined, size: 16, color: AppColors.textMuted),
                                            const SizedBox(width: 8),
                                            Text(
                                              _birthDate != null ? '${_birthDate!.day}/${_birthDate!.month}/${_birthDate!.year}' : 'Pilih tanggal',
                                              style: TextStyle(fontSize: 14, color: _birthDate != null ? AppColors.textPrimary : AppColors.textMuted),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(child: _Field(ctrl: _heightCtrl, label: 'Tinggi Badan (cm)', icon: Icons.height_rounded, keyboardType: TextInputType.number)),
                              const SizedBox(width: 16),
                              Expanded(child: _Field(ctrl: _weightCtrl, label: 'Berat Badan (kg)', icon: Icons.monitor_weight_outlined, keyboardType: TextInputType.number)),
                              const SizedBox(width: 16),
                              Expanded(
                                child: DropdownButtonFormField<String>(
                                  value: _bloodType,
                                  decoration: const InputDecoration(
                                    labelText: 'Golongan Darah',
                                    prefixIcon: Icon(Icons.water_drop_outlined, size: 18),
                                  ),
                                  dropdownColor: AppColors.surface,
                                  items: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
                                      .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                                      .toList(),
                                  onChanged: (v) => setState(() => _bloodType = v),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          OutlinedButton(onPressed: () => context.go(AppRoutes.patients), child: const Text('Batal')),
                          const SizedBox(width: 12),
                          ElevatedButton(
                            onPressed: _isLoading ? null : _handleSubmit,
                            child: _isLoading
                                ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                : Text(isEditing ? 'Simpan Perubahan' : 'Tambah Pasien'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 24),
              // Side info
              SizedBox(
                width: 280,
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
                      const Text('Panduan Input', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(height: 12),
                      _GuideItem(icon: Icons.badge_outlined, text: 'No. Rekam Medis harus unik dan sesuai format faskes'),
                      _GuideItem(icon: Icons.credit_card_outlined, text: 'NIK 16 digit sesuai KTP, opsional tapi dianjurkan'),
                      _GuideItem(icon: Icons.monitor_weight_outlined, text: 'BMI dihitung otomatis dari tinggi dan berat badan'),
                      _GuideItem(icon: Icons.info_outline_rounded, text: 'Data akan disimpan ke database dan dapat diintegrasikan ke SATUSEHAT'),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _FormSection extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _FormSection({required this.title, required this.children});

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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 16),
          ...children,
        ],
      ),
    );
  }
}

class _Field extends StatelessWidget {
  final TextEditingController ctrl;
  final String label;
  final IconData icon;
  final bool required;
  final int maxLines;
  final TextInputType? keyboardType;
  const _Field({required this.ctrl, required this.label, required this.icon, this.required = false, this.maxLines = 1, this.keyboardType});

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: ctrl,
      maxLines: maxLines,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label + (required ? ' *' : ''),
        prefixIcon: Icon(icon, size: 18),
      ),
      validator: required ? (v) => v == null || v.isEmpty ? '$label wajib diisi' : null : null,
    );
  }
}

class _GenderChip extends StatelessWidget {
  final String label;
  final String value;
  final bool selected;
  final VoidCallback onTap;
  const _GenderChip({required this.label, required this.value, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: selected ? AppColors.primary.withOpacity(0.15) : AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
          border: selected ? Border.all(color: AppColors.primary) : null,
        ),
        child: Text(
          label,
          style: TextStyle(fontSize: 13, color: selected ? AppColors.primary : AppColors.textSecondary, fontWeight: selected ? FontWeight.w600 : FontWeight.w400),
        ),
      ),
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
