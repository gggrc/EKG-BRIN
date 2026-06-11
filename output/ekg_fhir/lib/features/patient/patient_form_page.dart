// lib/features/patient/patient_form_page.dart
import 'dart:async';
import 'dart:math'; 
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/router/app_router.dart';
import '../../core/models/patient_model.dart';

class PatientFormPage extends StatefulWidget {
  final String? patientId; // null = new patient
  const PatientFormPage({super.key, this.patientId});

  @override
  State<PatientFormPage> createState() => _PatientFormPageState();
}

class _PatientFormPageState extends State<PatientFormPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _heightCtrl = TextEditingController();
  final _weightCtrl = TextEditingController();
  
  String _gender = 'M'; 
  DateTime? _birthDate;
  bool _isSavingLocal = false; 
  bool _isLoadingData = false;

  final _supabase = Supabase.instance.client;

  final List<Map<String, dynamic>> _genderOptions = [
    {'value': 'M',   'label': 'Laki-laki',  'icon': Icons.man},
    {'value': 'F', 'label': 'Perempuan',  'icon': Icons.woman}
  ];

  bool get isEditing => widget.patientId != null;

  @override
  void initState() {
    super.initState();
    if (isEditing) _loadPatient();
  }

  // AMBIL DATA DARI SUPABASE JIKA SEBELUMNYA DATA DITAMBAH REAL-TIME
  Future<void> _loadPatient() async {
    setState(() => _isLoadingData = true);
    try {
      PatientModel? p;
      // Coba cari di pool lokal mockup dulu
      try {
        p = MockData.patients.firstWhere((p) => p.patientId == widget.patientId);
      } catch (_) {
        p = null;
      }

      // Jika tidak ada di mockup (berarti data baru dari database), fetch langsung ke Supabase
      if (p == null) {
        final response = await _supabase
            .from('patients')
            .select()
            .eq('patient_id', widget.patientId!)
            .maybeSingle();
        
        if (response != null) {
          p = PatientModel.fromJson(response);
        }
      }

      if (p != null && mounted) {
        setState(() {
          _nameCtrl.text = p!.fullName;
          _heightCtrl.text = p.heightCm?.round().toString() ?? '';
          _weightCtrl.text = p.weightKg?.toString() ?? '';
          _gender = p.gender;
          _birthDate = p.birthDate;
        });
      }
    } catch (e) {
      debugPrint('Gagal memuat data pasien untuk edit: $e');
    } finally {
      if (mounted) setState(() => _isLoadingData = false);
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _heightCtrl.dispose();
    _weightCtrl.dispose();
    super.dispose();
  }

  String _generateValidUuidV4() {
    final random = Random.secure();
    final List<int> values = List<int>.generate(16, (i) => random.nextInt(256));
    
    values[6] = (values[6] & 0x0f) | 0x40; // versi 4
    values[8] = (values[8] & 0x3f) | 0x80; // varian ndr

    final StringBuffer buffer = StringBuffer();
    for (int i = 0; i < 16; i++) {
      if (i == 4 || i == 6 || i == 8 || i == 10) {
        buffer.write('-');
      }
      buffer.write(values[i].toRadixString(16).padLeft(2, '0'));
    }
    return buffer.toString();
  }

  void _showAnimatedSuccessDialog(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: true,
      barrierColor: Colors.black.withValues(alpha: 0.2),
      builder: (BuildContext dialogContext) {
        return const _SuccessAnimatedDialog();
      },
    );
  }

  Future<void> _handleSubmit() async {
  if (!_formKey.currentState!.validate()) return;
    if (_birthDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Tanggal lahir wajib diisi'), backgroundColor: AppColors.danger),
      );
      return;
    }

    setState(() {
      _isSavingLocal = true; 
    });

    try {
      final currentAuthUser = _supabase.auth.currentUser;
      final generatedId = isEditing ? widget.patientId! : _generateValidUuidV4();

      final Map<String, dynamic> payload = {
        'patient_id': generatedId, 
        'full_name': _nameCtrl.text.trim(),
        'gender': _gender,
        'birth_date': _birthDate!.toIso8601String().split('T').first, 
        'height_cm': double.tryParse(_heightCtrl.text),
        'weight_kg': double.tryParse(_weightCtrl.text),
        'user_id': currentAuthUser?.id, 
      };

      if (isEditing) {
        await _supabase
            .from('patients')
            .update(payload)
            .eq('patient_id', widget.patientId!);
            
        final index = MockData.patients.indexWhere((p) => p.patientId == widget.patientId);
        if (index != -1) {
          MockData.patients[index] = MockData.patients[index].copyWith(
            fullName: _nameCtrl.text.trim(),
            gender: _gender,
            birthDate: _birthDate!,
            heightCm: double.tryParse(_heightCtrl.text),
            weightKg: double.tryParse(_weightCtrl.text),
            userId: currentAuthUser?.id, 
          );
        }
      } else {
        await _supabase.from('patients').insert(payload);

        final newPatient = PatientModel(
          patientId: generatedId,
          userId: currentAuthUser?.id,
          fullName: _nameCtrl.text.trim(),
          medicalRecordNumber: 'Generasi Otomatis', 
          gender: _gender,
          birthDate: _birthDate!,
          heightCm: double.tryParse(_heightCtrl.text),
          weightKg: double.tryParse(_weightCtrl.text),
        );
        MockData.patients.add(newPatient);
      }

      if (mounted) {
        // PERBAIKAN DI SINI: Baik edit maupun tambah baru, keduanya sekarang memunculkan popup sukses animasi
        _showAnimatedSuccessDialog(context);
        
        // Berikan delay 1 detik agar animasi dialog selesai diposisi diam sebelum halaman berpindah
        await Future.delayed(const Duration(seconds: 1));

        if (mounted) {
          context.go(AppRoutes.patients);
        }
      }
    } on PostgrestException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal menyimpan data database: ${e.message}'), 
            backgroundColor: AppColors.danger,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Terjadi kesalahan sistem: $e'), backgroundColor: AppColors.danger),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSavingLocal = false; 
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoadingData) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

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
                        title: 'Data Lengkap Pasien',
                        children: [
                          Row(
                            children: [
                              Expanded(child: _Field(ctrl: _nameCtrl, label: 'Nama Lengkap', icon: Icons.person_outline, required: true, enabled: !_isSavingLocal)),
                            ],
                          ),
                          const SizedBox(height: 20),
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('Jenis Kelamin', style: TextStyle(fontSize: 14, color: AppColors.textSecondary, fontWeight: FontWeight.w500)),
                                    const SizedBox(height: 10),
                                    Wrap(
                                      spacing: 12,
                                      runSpacing: 10,
                                      children: _genderOptions.map((opt) {
                                        final isSelected = _gender == opt['value'];
                                        return GestureDetector(
                                          onTap: _isSavingLocal ? null : () => setState(() => _gender = opt['value'] as String),
                                          child: AnimatedContainer(
                                            duration: const Duration(milliseconds: 150),
                                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                                            decoration: BoxDecoration(
                                              color: isSelected ? AppColors.primary.withOpacity(0.12) : AppColors.surfaceVariant,
                                              borderRadius: BorderRadius.circular(10),
                                              border: Border.all(
                                                color: isSelected ? AppColors.primary : Colors.transparent,
                                                width: 1.5,
                                              ),
                                            ),
                                            child: Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Icon(
                                                  opt['icon'] as IconData,
                                                  size: 18,
                                                  color: isSelected ? AppColors.primary : AppColors.textSecondary,
                                                ),
                                                const SizedBox(width: 8),
                                                Text(
                                                  opt['label'] as String,
                                                  style: TextStyle(
                                                    fontSize: 13,
                                                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                                                    color: isSelected ? AppColors.primary : AppColors.textSecondary,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        );
                                      }).toList(),
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
                                      onTap: _isSavingLocal ? null : () async {
                                        final picked = await showDatePicker(
                                          context: context,
                                          initialDate: _birthDate ?? DateTime(2000),
                                          firstDate: DateTime(1920),
                                          lastDate: DateTime.now(),
                                          initialEntryMode: DatePickerEntryMode.calendarOnly,
                                          helpText: 'Select date\n', 
                                          builder: (context, child) => Theme(
                                            data: Theme.of(context).copyWith(
                                              colorScheme: ColorScheme.light(
                                                primary: Colors.black,       
                                                onPrimary: Colors.white,     
                                                surface: Colors.white,       
                                                onSurface: const Color(0xFF334155), // const dipindahkan ke instansiasi warna statis jika diperlukan
                                              ),
                                              datePickerTheme: DatePickerThemeData(
                                                backgroundColor: Colors.white, 
                                                headerBackgroundColor: Colors.white,
                                                headerHelpStyle: const TextStyle(
                                                  color: Color(0xFF1E293B),
                                                  fontWeight: FontWeight.w600,
                                                  fontSize: 14,
                                                  height: 1.5,
                                                ),
                                                headerHeadlineStyle: const TextStyle(
                                                  color: Color(0xFF1E293B),
                                                  fontWeight: FontWeight.w600,
                                                  fontSize: 14, 
                                                ),
                                                yearStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w400),
                                                dividerColor: Colors.transparent, 
                                                surfaceTintColor: Colors.transparent,
                                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)), 
                                                dayStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13),
                                                weekdayStyle: const TextStyle(color: Color(0xFF94A3B8), fontWeight: FontWeight.w600, fontSize: 12),
                                              ),
                                              textButtonTheme: TextButtonThemeData(
                                                style: TextButton.styleFrom(
                                                  foregroundColor: Colors.black,
                                                  textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                                                ),
                                              ),
                                            ),
                                            child: MediaQuery(
                                              data: MediaQuery.of(context).copyWith(
                                                size: const Size(360, 640), 
                                              ),
                                              child: child!,
                                            ),
                                          ),
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
                                              _birthDate != null ? '${_birthDate!.day}/${_birthDate!.month}/${_birthDate!.year}' : 'Pilih tanggal lahir',
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
                          const SizedBox(height: 20),
                          Row(
                            children: [
                              Expanded(child: _Field(ctrl: _heightCtrl, label: 'Tinggi Badan (cm)', icon: Icons.height_rounded, keyboardType: TextInputType.number, enabled: !_isSavingLocal)),
                              const SizedBox(width: 16),
                              Expanded(child: _Field(ctrl: _weightCtrl, label: 'Berat Badan (kg)', icon: Icons.monitor_weight_outlined, keyboardType: TextInputType.number, enabled: !_isSavingLocal)),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          OutlinedButton(onPressed: _isSavingLocal ? null : () => context.go(AppRoutes.patients), child: const Text('Batal')),
                          const SizedBox(width: 12),
                          ElevatedButton(
                            onPressed: _isSavingLocal ? null : _handleSubmit,
                            child: _isSavingLocal
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
                      Theme(
                        data: ThemeData(),
                        child: Text('Panduan Sinkronisasi', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      ),
                      SizedBox(height: 12),
                      _GuideItem(icon: Icons.pin_end_rounded, text: 'No. Rekam Medis tidak perlu diinput. Sistem database akan men-generate nomor rekam medis berurutan otomatis.'),
                      _GuideItem(icon: Icons.analytics_outlined, text: 'Nilai tinggi dan berat badan digunakan untuk perhitungan indeks BMI klinis.'),
                      _GuideItem(icon: Icons.cloud_upload_outlined, text: 'Data yang tersimpan mematuhi aturan otorisasi Row-Level Security Supabase.'),
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
  final bool enabled;
  final TextInputType? keyboardType;
  const _Field({required this.ctrl, required this.label, required this.icon, this.required = false, this.enabled = true, this.keyboardType});

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: ctrl,
      enabled: enabled,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label + (required ? ' *' : ''),
        prefixIcon: Icon(icon, size: 18),
      ),
      validator: required ? (v) => v == null || v.trim().isEmpty ? '$label wajib diisi' : null : null,
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

class _SuccessAnimatedDialog extends StatefulWidget {
  const _SuccessAnimatedDialog();

  @override
  State<_SuccessAnimatedDialog> createState() => _SuccessAnimatedDialogState();
}

class _SuccessAnimatedDialogState extends State<_SuccessAnimatedDialog> with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _fadeAnimation;
  Timer? _autoDismissTimer;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );

    _scaleAnimation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutBack,
    );

    _fadeAnimation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeIn,
    );

    _animController.forward();

    _autoDismissTimer = Timer(const Duration(seconds: 1), () {
      _closeWithAnimation();
    });
  }

  @override
  void dispose() {
    _autoDismissTimer?.cancel();
    _animController.dispose();
    super.dispose();
  }

  void _closeWithAnimation() {
    if (!mounted) return;
    _animController.reverse().then((_) {
      if (mounted) {
        Navigator.of(context).pop();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: Material(
            color: Colors.transparent,
            child: Container(
              width: 310,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  )
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Stack(
                    alignment: Alignment.center,
                    children: [
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F8F0),
                          shape: BoxShape.circle,
                          border: Border.all(color: const Color(0xFF22C55E).withOpacity(0.2), width: 1.5),
                        ),
                      ),
                      const Icon(
                        Icons.check_circle_outline_rounded,
                        color: Color(0xFF22C55E),
                        size: 60,
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'SUCCESS!',
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF22C55E),
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Data pasien berhasil disimpan.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: Color(0xFF64748B),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 28),
                  SizedBox(
                    width: double.infinity,
                    height: 46,
                    child: ElevatedButton(
                      onPressed: _closeWithAnimation,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF22C55E),
                        foregroundColor: Colors.white,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(24),
                        ),
                      ),
                      child: const Text(
                        'DONE',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}