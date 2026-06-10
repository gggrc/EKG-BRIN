// lib/features/acquisition/acquisition_page.dart
// Halaman akuisisi / upload data EKG
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/models/ecg_models.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/data_provider.dart';
import 'package:provider/provider.dart';
import '../../core/router/app_router.dart';

class AcquisitionPage extends StatefulWidget {
  const AcquisitionPage({super.key});

  @override
  State<AcquisitionPage> createState() => _AcquisitionPageState();
}

class _AcquisitionPageState extends State<AcquisitionPage> {
  String? _selectedPatientId;
  String? _selectedDeviceId;
  String _uploadType = 'pdf';
  bool _isUploading = false;
  double _uploadProgress = 0;
  PlatformFile? _pickedFile;

  // Mapping upload type ke allowed extensions
  static const Map<String, List<String>> _allowedExtensions = {
    'pdf': ['pdf'],
    'image': ['png', 'jpg', 'jpeg', 'bmp'],
    'csv': ['csv', 'xls', 'xlsx'],
    'hl7': ['xml', 'hl7', 'txt'],
  };

  static const Map<String, String> _uploadTypeLabel = {
    'pdf': 'PDF',
    'image': 'Gambar (PNG/JPG)',
    'csv': 'CSV / Excel',
    'hl7': 'HL7 / XML',
  };

  Future<void> _pickFile() async {
    final exts = _allowedExtensions[_uploadType] ?? [];
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: exts,
        allowMultiple: false,
        withData: true, // Penting untuk Flutter Web
      );
      if (result != null && result.files.isNotEmpty) {
        final file = result.files.first;
        setState(() {
          _pickedFile = file;
          _isUploading = false;
          _uploadProgress = 0;
        });
        // Simulasikan parsing setelah pilih file
        await _simulateParsing();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal memilih file: ${e.toString()}'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    }
  }

  Future<void> _simulateParsing() async {
    setState(() {
      _isUploading = true;
      _uploadProgress = 0;
    });
    // Simulasikan proses parsing/upload bertahap
    for (int i = 1; i <= 12; i++) {
      await Future.delayed(const Duration(milliseconds: 120));
      if (mounted) setState(() => _uploadProgress = i / 12);
    }
    if (mounted) setState(() => _isUploading = false);
  }

  Future<void> _handleSubmit() async {
    if (_selectedPatientId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pilih pasien terlebih dahulu')),
      );
      return;
    }
    if (_pickedFile == null) {
      await _pickFile();
      return;
    }
    setState(() => _isUploading = true);
    await Future.delayed(const Duration(milliseconds: 1400));
    setState(() => _isUploading = false);
    if (mounted) {
      final user = context.read<AuthProvider>().currentUser;
      final patient = context.read<DataProvider>().patients.firstWhere((p) => p.patientId == _selectedPatientId, orElse: () => context.read<DataProvider>().patients.first);
      final newSession = EcgSession(
        sessionId: 's-${DateTime.now().millisecondsSinceEpoch}',
        patientId: patient.patientId,
        patientName: patient.fullName,
        deviceId: _selectedDeviceId ?? 'dev-unk',
        deviceName: 'ECG Device (${_selectedDeviceId ?? "Unknown"})',
        examinationTime: DateTime.now(),
        durationSec: 10,
        leadConfiguration: LeadConfiguration.twelveLead,
        status: EcgSessionStatus.pending,
        sourceType: _uploadType == 'pdf' ? SourceType.pdfUpload : (_uploadType == 'image' ? SourceType.imageUpload : SourceType.csvUpload),
        recordedBy: user?.userId,
        recordedByName: user?.name,
        signalData: EcgSignalData(
          signalId: DateTime.now().millisecondsSinceEpoch,
          sessionId: 's-${DateTime.now().millisecondsSinceEpoch}',
          leadType: '12-lead',
          samplingRate: 500,
          sampleCount: 5000,
          signalData: {
            for (var l in ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']) 
              l: MockData.generateEcgSignal(heartRateBpm: 75, leadType: l)
          },
          minVoltageMv: -2.5,
          maxVoltageMv: 2.5,
        ),
      );
      context.read<DataProvider>().addEcgSession(newSession);

      if (user != null) {
        context.read<DataProvider>().addActivityLog(ActivityLogModel(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          userName: user.name,
          action: 'Akuisisi Sinyal / Upload EKG',
          target: '${patient.fullName} (${_pickedFile!.name})',
          time: DateTime.now(),
          type: 'upload',
        ));
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle_outline_rounded, color: Colors.white, size: 18),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'EKG "${_pickedFile!.name}" berhasil diproses dan masuk antrian analisis.',
                ),
              ),
            ],
          ),
          backgroundColor: AppColors.success,
          behavior: SnackBarBehavior.floating,
        ),
      );
      context.go(AppRoutes.history);
    }
  }

  String _formatFileSize(int? bytes) {
    if (bytes == null) return '';
    if (bytes < 1024) return '${bytes} B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Main form
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Step 1: Select patient
                _StepCard(
                  step: 1,
                  title: 'Pilih Pasien',
                  children: [
                    DropdownButtonFormField<String>(
                      value: _selectedPatientId,
                      dropdownColor: AppColors.surface,
                      decoration: const InputDecoration(
                        labelText: 'Pasien',
                        prefixIcon: Icon(Icons.person_search_rounded, size: 18),
                      ),
                      items: context.watch<DataProvider>().patients.map((p) => DropdownMenuItem(
                        value: p.patientId,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(p.fullName, style: const TextStyle(fontSize: 13)),
                            Text(
                              '${p.medicalRecordNumber} • ${p.gender == 'M' ? 'L' : 'P'}',
                              style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                            ),
                          ],
                        ),
                      )).toList(),
                      onChanged: (v) => setState(() => _selectedPatientId = v),
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

                // Step 2: Select device
                _StepCard(
                  step: 2,
                  title: 'Pilih Perangkat EKG',
                  children: [
                    DropdownButtonFormField<String>(
                      value: _selectedDeviceId,
                      dropdownColor: AppColors.surface,
                      decoration: const InputDecoration(
                        labelText: 'Perangkat EKG',
                        prefixIcon: Icon(Icons.devices_rounded, size: 18),
                      ),
                      items: MockData.devices.map((d) => DropdownMenuItem(
                        value: d['id'],
                        child: Text('${d['name']} (${d['serial']})'),
                      )).toList(),
                      onChanged: (v) => setState(() => _selectedDeviceId = v),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Step 3: Upload type
                _StepCard(
                  step: 3,
                  title: 'Pilih Format File',
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _UploadTypeChip(
                          icon: Icons.picture_as_pdf_rounded,
                          label: 'PDF',
                          value: 'pdf',
                          selected: _uploadType == 'pdf',
                          onTap: () => setState(() {
                            _uploadType = 'pdf';
                            _pickedFile = null;
                          }),
                        ),
                        _UploadTypeChip(
                          icon: Icons.image_rounded,
                          label: 'Gambar',
                          value: 'image',
                          selected: _uploadType == 'image',
                          onTap: () => setState(() {
                            _uploadType = 'image';
                            _pickedFile = null;
                          }),
                        ),
                        _UploadTypeChip(
                          icon: Icons.table_chart_rounded,
                          label: 'CSV / Excel',
                          value: 'csv',
                          selected: _uploadType == 'csv',
                          onTap: () => setState(() {
                            _uploadType = 'csv';
                            _pickedFile = null;
                          }),
                        ),
                        _UploadTypeChip(
                          icon: Icons.medical_information_rounded,
                          label: 'HL7/XML',
                          value: 'hl7',
                          selected: _uploadType == 'hl7',
                          onTap: () => setState(() {
                            _uploadType = 'hl7';
                            _pickedFile = null;
                          }),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Ekstensi yang diterima: ${_allowedExtensions[_uploadType]!.map((e) => '.$e').join(', ')}',
                      style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Step 4: Upload file
                _StepCard(
                  step: 4,
                  title: 'Upload File EKG',
                  children: [
                    if (_pickedFile == null && !_isUploading)
                      // Drop zone / pick button
                      GestureDetector(
                        onTap: _pickFile,
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(vertical: 44),
                          decoration: BoxDecoration(
                            color: AppColors.primaryContainer.withOpacity(0.4),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: AppColors.primary.withOpacity(0.3),
                              style: BorderStyle.solid,
                              width: 1.5,
                            ),
                          ),
                          child: Column(
                            children: [
                              Container(
                                width: 56,
                                height: 56,
                                decoration: BoxDecoration(
                                  color: AppColors.primaryContainer,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: const Icon(
                                  Icons.cloud_upload_rounded,
                                  size: 28,
                                  color: AppColors.primary,
                                ),
                              ),
                              const SizedBox(height: 14),
                              const Text(
                                'Klik untuk memilih file',
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Format: ${_uploadTypeLabel[_uploadType]}',
                                style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                              ),
                              const SizedBox(height: 16),
                              ElevatedButton.icon(
                                onPressed: _pickFile,
                                icon: const Icon(Icons.folder_open_rounded, size: 16),
                                label: const Text('Buka File Picker'),
                              ),
                            ],
                          ),
                        ),
                      )
                    else if (_isUploading)
                      // Progress bar
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: AppColors.primaryContainer.withOpacity(0.3),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.primary.withOpacity(0.2)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.sync_rounded, color: AppColors.primary, size: 18),
                                const SizedBox(width: 8),
                                const Text(
                                  'Menganalisis file EKG...',
                                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.primary),
                                ),
                                const Spacer(),
                                Text(
                                  '${(_uploadProgress * 100).round()}%',
                                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.primary),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: _uploadProgress,
                                backgroundColor: AppColors.borderLight,
                                valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
                                minHeight: 8,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Mengekstrak sinyal, standardisasi format, dan persiapan analisis AI...',
                              style: TextStyle(fontSize: 11, color: AppColors.textMuted),
                            ),
                          ],
                        ),
                      )
                    else
                      // File berhasil dipilih
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.successContainer,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.success.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                color: AppColors.success.withOpacity(0.12),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Icon(
                                _pickedFile!.extension == 'pdf'
                                    ? Icons.picture_as_pdf_rounded
                                    : _pickedFile!.extension == 'csv' || _pickedFile!.extension == 'xlsx'
                                        ? Icons.table_chart_rounded
                                        : Icons.insert_drive_file_rounded,
                                color: AppColors.success,
                                size: 22,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _pickedFile!.name,
                                    style: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.textPrimary,
                                    ),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${_formatFileSize(_pickedFile!.size)} · .${_pickedFile!.extension?.toUpperCase() ?? ''}',
                                    style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                                  ),
                                  const SizedBox(height: 2),
                                  const Text(
                                    '✓ File siap diproses',
                                    style: TextStyle(fontSize: 11, color: AppColors.success, fontWeight: FontWeight.w600),
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              onPressed: () => setState(() => _pickedFile = null),
                              icon: const Icon(Icons.close_rounded, size: 18, color: AppColors.textMuted),
                              tooltip: 'Hapus file',
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 24),

                // Action buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton(
                      onPressed: () => context.go(AppRoutes.patients),
                      child: const Text('Batal'),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      onPressed: _isUploading ? null : _handleSubmit,
                      icon: _isUploading
                          ? const SizedBox(
                              height: 16,
                              width: 16,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : Icon(
                              _pickedFile == null ? Icons.folder_open_rounded : Icons.send_rounded,
                              size: 16,
                            ),
                      label: Text(
                        _isUploading
                            ? 'Memproses...'
                            : _pickedFile == null
                                ? 'Pilih File Dulu'
                                : 'Proses EKG',
                      ),
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
                    _FormatInfo(
                      icon: Icons.picture_as_pdf_rounded,
                      label: 'PDF',
                      desc: 'Hasil cetak EKG digital dari perangkat',
                      color: AppColors.danger,
                    ),
                    _FormatInfo(
                      icon: Icons.image_rounded,
                      label: 'PNG / JPG / BMP',
                      desc: 'Foto atau scan kertas EKG',
                      color: AppColors.secondary,
                    ),
                    _FormatInfo(
                      icon: Icons.table_chart_rounded,
                      label: 'CSV / Excel',
                      desc: 'Data numerik sinyal EKG',
                      color: AppColors.success,
                    ),
                    _FormatInfo(
                      icon: Icons.medical_information_rounded,
                      label: 'HL7 / XML',
                      desc: 'Format interoperabilitas medis',
                      color: AppColors.warning,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _InfoCard(
                  title: 'Proses Setelah Upload',
                  items: [
                    _FormatInfo(
                      icon: Icons.search_rounded,
                      label: 'Ekstraksi',
                      desc: 'Identifikasi format dan ekstraksi sinyal',
                      color: AppColors.primary,
                    ),
                    _FormatInfo(
                      icon: Icons.auto_fix_high_rounded,
                      label: 'Standardisasi',
                      desc: 'Konversi ke format numerik standar',
                      color: AppColors.primary,
                    ),
                    _FormatInfo(
                      icon: Icons.psychology_rounded,
                      label: 'Analisis AI',
                      desc: 'Interpretasi otomatis (jika tersedia)',
                      color: AppColors.primary,
                    ),
                    _FormatInfo(
                      icon: Icons.cloud_sync_rounded,
                      label: 'FHIR Export',
                      desc: 'Siap dikirim ke SATUSEHAT',
                      color: AppColors.primary,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                // Privacy note
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.warningContainer,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.warning.withOpacity(0.3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.info_outline_rounded, size: 16, color: AppColors.warning),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'File EKG yang diupload hanya diproses secara lokal. Tidak ada data yang dikirim tanpa persetujuan eksplisit melalui FHIR Export.',
                          style: TextStyle(fontSize: 11, color: AppColors.textSecondary, height: 1.5),
                        ),
                      ),
                    ],
                  ),
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
        boxShadow: const [
          BoxShadow(color: Color(0x0D000000), blurRadius: 4, offset: Offset(0, 1)),
        ],
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
                child: Center(
                  child: Text(
                    '$step',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
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
  const _UploadTypeChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.primaryContainer : AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: selected ? AppColors.primary : AppColors.borderLight,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 17,
              color: selected ? AppColors.primary : AppColors.textMuted,
            ),
            const SizedBox(width: 7),
            Text(
              label,
              style: TextStyle(
                fontSize: 13,
                color: selected ? AppColors.primary : AppColors.textSecondary,
                fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
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
        boxShadow: const [
          BoxShadow(color: Color(0x0D000000), blurRadius: 4, offset: Offset(0, 1)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
              letterSpacing: 0.2,
            ),
          ),
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
  final Color color;
  const _FormatInfo({
    required this.icon,
    required this.label,
    required this.desc,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: color.withOpacity(0.10),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Icon(icon, size: 15, color: color),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  desc,
                  style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
