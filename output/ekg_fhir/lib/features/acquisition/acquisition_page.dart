// lib/features/acquisition/acquisition_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../core/theme/app_colors.dart';
import '../../core/router/app_router.dart';
import '../../core/models/patient_model.dart';

class AcquisitionPage extends StatefulWidget {
  const AcquisitionPage({super.key});

  @override
  State<AcquisitionPage> createState() => _AcquisitionPageState();
}

class _AcquisitionPageState extends State<AcquisitionPage> {
  final _supabase = Supabase.instance.client;
  late Future<List<PatientModel>> _patientsFuture;
  
  String? _selectedPatientId;
  bool _isUploading = false;
  double _uploadProgress = 0;
  String? _uploadedFile;
  
  String _dropdownSearchQuery = '';
  final LayerLink _patientLayerLink = LayerLink();
  OverlayEntry? _patientOverlayEntry;
  bool _isPatientDropdownOpen = false;
  final TextEditingController _patientSearchController = TextEditingController();
  List<PatientModel> _allPatients = [];
  final GlobalKey _patientDropdownKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _fetchPatientsFromDatabase();
  }

  @override
  void dispose() {
    _removePatientOverlay();
    _patientSearchController.dispose();
    super.dispose();
  }

  void _removePatientOverlay() {
    _patientOverlayEntry?.remove();
    _patientOverlayEntry = null;
    _isPatientDropdownOpen = false;
  }

  void _togglePatientDropdown(List<PatientModel> patients) {
    if (_isPatientDropdownOpen) {
      _removePatientOverlay();
      setState(() {});
      return;
    }
    _allPatients = patients;
    _dropdownSearchQuery = '';
    _patientSearchController.clear();
    _showPatientOverlay(patients);
    setState(() { _isPatientDropdownOpen = true; });
  }

  void _showPatientOverlay(List<PatientModel> patients) {
    final overlay = Overlay.of(context);
    final showSearch = patients.length > 5;

    // Measure the trigger widget width
    double dropdownWidth = 300;
    final renderBox = _patientDropdownKey.currentContext?.findRenderObject() as RenderBox?;
    if (renderBox != null) {
      dropdownWidth = renderBox.size.width;
    }

    _patientOverlayEntry = OverlayEntry(
      builder: (ctx) {
        return GestureDetector(
          behavior: HitTestBehavior.translucent,
          onTap: () {
            _removePatientOverlay();
            setState(() {});
          },
          child: Stack(
            children: [
              Positioned.fill(child: Container(color: Colors.transparent)),
              CompositedTransformFollower(
                link: _patientLayerLink,
                showWhenUnlinked: false,
                offset: const Offset(0, 48),
                child: GestureDetector(
                  onTap: () {}, // prevent tap-through
                  child: SizedBox(
                    width: dropdownWidth,
                    child: Material(
                      elevation: 6,
                      borderRadius: BorderRadius.circular(10),
                      color: const Color(0xFF1E2433),
                    child: StatefulBuilder(
                      builder: (ctx2, setOverlayState) {
                        final filtered = _allPatients.where((p) =>
                          p.fullName.toLowerCase().contains(_dropdownSearchQuery.toLowerCase()) ||
                          p.medicalRecordNumber.toLowerCase().contains(_dropdownSearchQuery.toLowerCase())
                        ).toList();

                        return Container(
                          constraints: const BoxConstraints(maxHeight: 280),
                          decoration: BoxDecoration(
                            color: const Color(0xFF1E2433),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppColors.borderLight),
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (showSearch)
                                Container(
                                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
                                  child: TextField(
                                    controller: _patientSearchController,
                                    autofocus: true,
                                    style: const TextStyle(fontSize: 13, color: AppColors.textPrimary),
                                    decoration: InputDecoration(
                                      hintText: 'Search...',
                                      hintStyle: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                                      contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                      filled: true,
                                      fillColor: const Color(0xFF252B3B),
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(6),
                                        borderSide: BorderSide(color: AppColors.borderLight),
                                      ),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(6),
                                        borderSide: BorderSide(color: AppColors.borderLight),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(6),
                                        borderSide: const BorderSide(color: AppColors.primary),
                                      ),
                                    ),
                                    onChanged: (val) {
                                      setState(() => _dropdownSearchQuery = val);
                                      setOverlayState(() {});
                                    },
                                  ),
                                ),
                              Flexible(
                                child: ListView.builder(
                                  shrinkWrap: true,
                                  padding: const EdgeInsets.symmetric(vertical: 4),
                                  itemCount: filtered.length,
                                  itemBuilder: (_, i) {
                                    final p = filtered[i];
                                    final isSelected = _selectedPatientId == p.patientId;
                                    return InkWell(
                                      onTap: () {
                                        setState(() => _selectedPatientId = p.patientId);
                                        _removePatientOverlay();
                                        setState(() {});
                                      },
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                        color: isSelected ? AppColors.primary.withOpacity(0.15) : Colors.transparent,
                                        child: Text(
                                          '${p.fullName} (${p.medicalRecordNumber})',
                                          style: TextStyle(
                                            fontSize: 13,
                                            color: isSelected ? AppColors.primary : AppColors.textPrimary,
                                            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                                          ),
                                        ),
                                      ),
                                    );
                                  },
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );

    overlay.insert(_patientOverlayEntry!);
  }

  void _fetchPatientsFromDatabase() {
    setState(() {
      _patientsFuture = _supabase
          .from('patients')
          .select()
          .order('full_name', ascending: true)
          .then((response) {
            final List data = response as List;
            return data.map((json) => PatientModel.fromJson(json)).toList();
          });
    });
  }

  Future<void> _simulateUpload() async {
    if (_selectedPatientId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pilih pasien terlebih dahulu')),
      );
      return;
    }
    setState(() { _isUploading = true; _uploadProgress = 0; });
    for (int i = 1; i <= 10; i++) {
      await Future.delayed(const Duration(milliseconds: 150));
      setState(() => _uploadProgress = i / 10);
    }
    setState(() { _isUploading = false; _uploadedFile = 'ecg_rekam_${DateTime.now().millisecondsSinceEpoch}.pdf'; });
  }

  Future<void> _handleSubmit() async {
    if (_uploadedFile == null) { _simulateUpload(); return; }
    setState(() => _isUploading = true);
    await Future.delayed(const Duration(milliseconds: 1200));
    setState(() => _isUploading = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('EKG berhasil direkam dan diproses!')),
      );
      context.go(AppRoutes.history);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StepCard(
                  step: 1,
                    title: 'Pilih Pasien',
                    children: [
                      FutureBuilder<List<PatientModel>>(
                        future: _patientsFuture,
                        builder: (context, snapshot) {
                        if (snapshot.connectionState == ConnectionState.waiting) {
                          return const Padding(
                            padding: EdgeInsets.symmetric(vertical: 12),
                            child: Row(
                              children: [
                                SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                                SizedBox(width: 12),
                                Text('Memuat data pasien...', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                              ],
                            ),
                          );
                        }

                        if (snapshot.hasError) {
                          return Text('Error: ${snapshot.error}', style: const TextStyle(color: AppColors.danger));
                        }

                        final allPatients = snapshot.data ?? [];

                        final selectedPatient = allPatients.cast<PatientModel?>().firstWhere(
                          (p) => p?.patientId == _selectedPatientId,
                          orElse: () => null,
                        );

                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Padding(
                              padding: EdgeInsets.only(bottom: 8),
                              child: Text(
                                "Pasien",
                                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.textSecondary),
                              ),
                            ),
                            CompositedTransformTarget(
                              link: _patientLayerLink,
                              child: GestureDetector(
                                onTap: () => _togglePatientDropdown(allPatients),
                                child: Container(
                                  key: _patientDropdownKey,
                                  height: 48,
                                  padding: const EdgeInsets.symmetric(horizontal: 14),
                                  decoration: BoxDecoration(
                                    color: AppColors.surfaceVariant,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: _isPatientDropdownOpen ? AppColors.primary : AppColors.borderLight,
                                    ),
                                  ),
                                  child: Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          selectedPatient != null
                                              ? '${selectedPatient.fullName} (${selectedPatient.medicalRecordNumber})'
                                              : 'Pilih Pasien',
                                          style: TextStyle(
                                            fontSize: 14,
                                            color: selectedPatient != null ? AppColors.textPrimary : AppColors.textMuted,
                                          ),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      AnimatedRotation(
                                        turns: _isPatientDropdownOpen ? 0.5 : 0,
                                        duration: const Duration(milliseconds: 200),
                                        child: const Icon(Icons.keyboard_arrow_down_rounded, size: 20, color: AppColors.textMuted),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                    const SizedBox(height: 12),
                    TextButton.icon(
                      onPressed: () => context.go(AppRoutes.patientNew),
                      icon: const Icon(Icons.person_add_rounded, size: 16),
                      label: const Text('Daftarkan Pasien Baru'),
                    ),
                  ],
                ),
                    
                const SizedBox(height: 16),

                // Step 2: Upload file
                _StepCard(
                  step: 2,
                  title: 'Upload File EKG',
                  children: [
                    if (_uploadedFile == null)
                      GestureDetector(
                        onTap: _isUploading ? null : _simulateUpload,
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(vertical: 40),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceVariant,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppColors.borderLight, style: BorderStyle.solid),
                          ),
                          child: Column(
                            children: [
                              Icon(Icons.cloud_upload_rounded, size: 48, color: _isUploading ? AppColors.primary : AppColors.textMuted),
                              const SizedBox(height: 12),
                              if (_isUploading) ...[
                                Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 32),
                                  child: LinearProgressIndicator(
                                    value: _uploadProgress,
                                    backgroundColor: AppColors.surfaceVariant,
                                    valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
                                    minHeight: 6,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text('${(_uploadProgress * 100).round()}% - Mengupload...', style: const TextStyle(fontSize: 12, color: AppColors.primary)),
                              ] else ...[
                                const Text('Klik atau seret file ke sini', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.textSecondary)),
                                const SizedBox(height: 4),
                                Text('Mendukung: PDF, PNG, JPG, CSV, XLS, HL7', style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                                const SizedBox(height: 12),
                                ElevatedButton.icon(
                                  onPressed: _simulateUpload,
                                  icon: const Icon(Icons.upload_rounded, size: 16),
                                  label: const Text('Pilih File'),
                                ),
                              ],
                            ],
                          ),
                        ),
                      )
                    else
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.successContainer,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppColors.success.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.check_circle_rounded, color: AppColors.success, size: 24),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(_uploadedFile!, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.successLight)),
                                  const Text('File berhasil diupload', style: TextStyle(fontSize: 11, color: AppColors.success)),
                                ],
                              ),
                            ),
                            IconButton(
                              onPressed: () => setState(() => _uploadedFile = null),
                              icon: const Icon(Icons.close_rounded, size: 16, color: AppColors.textMuted),
                            ),
                          ],
                        ),
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
                      onPressed: _isUploading ? null : _handleSubmit,
                      child: _isUploading
                          ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : Text(_uploadedFile == null ? 'Upload File Dulu' : 'Proses EKG'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 24),
          // Info sidebar
          SizedBox(
            width: 280,
            child: Column(
              children: [
                _InfoCard(
                  title: 'Format yang Didukung',
                  items: [
                    _FormatInfo(icon: Icons.picture_as_pdf_rounded, label: 'PDF', desc: 'Hasil cetak EKG digital dari perangkat'),
                    _FormatInfo(icon: Icons.image_rounded, label: 'PNG / JPG', desc: 'Foto atau scan kertas EKG'),
                    _FormatInfo(icon: Icons.table_chart_rounded, label: 'CSV / Excel', desc: 'Data numerik sinyal EKG'),
                    _FormatInfo(icon: Icons.medical_information_rounded, label: 'HL7 / XML', desc: 'Format interoperabilitas medis'),
                  ],
                ),
                const SizedBox(height: 16),
                _InfoCard(
                  title: 'Proses Setelah Upload',
                  items: [
                    _FormatInfo(icon: Icons.search_rounded, label: 'Ekstraksi', desc: 'Identifikasi format dan ekstraksi sinyal'),
                    _FormatInfo(icon: Icons.auto_fix_high_rounded, label: 'Standardisasi', desc: 'Konversi ke format numerik standar'),
                    _FormatInfo(icon: Icons.psychology_rounded, label: 'Analisis AI', desc: 'Interpretasi otomatis (jika tersedia)'),
                    _FormatInfo(icon: Icons.cloud_sync_rounded, label: 'FHIR Export', desc: 'Siap dikirim ke SATUSEHAT'),
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

class _StepCard extends StatelessWidget {
  final int step;
  final String title;
  final List<Widget> children;
  const _StepCard({required this.step, required this.title, required this.children});

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
          Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: const BoxDecoration(
                  gradient: AppColors.primaryGradient,
                  shape: BoxShape.circle,
                ),
                child: Center(child: Text('$step', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w700))),
              ),
              const SizedBox(width: 10),
              Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
            ],
          ),
          const SizedBox(height: 16),
          ...children,
        ],
      ),
    );
  }
}

class _UploadTypeChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final bool selected;
  final VoidCallback onTap;
  const _UploadTypeChip({required this.icon, required this.label, required this.value, required this.selected, required this.onTap});

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
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 18, color: selected ? AppColors.primary : AppColors.textMuted),
            const SizedBox(width: 8),
            Text(label, style: TextStyle(fontSize: 13, color: selected ? AppColors.primary : AppColors.textSecondary, fontWeight: selected ? FontWeight.w600 : FontWeight.w400)),
          ],
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final String title;
  final List<Widget> items;
  const _InfoCard({required this.title, required this.items});

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
          Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 12),
          ...items,
        ],
      ),
    );
  }
}

class _FormatInfo extends StatelessWidget {
  final IconData icon;
  final String label;
  final String desc;
  const _FormatInfo({required this.icon, required this.label, required this.desc});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                Text(desc, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}