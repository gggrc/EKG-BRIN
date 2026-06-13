// lib/features/acquisition/acquisition_page.dart
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart' show kIsWeb; 
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide MultipartFile; 
import 'package:file_picker/file_picker.dart'; 
import 'package:desktop_drop/desktop_drop.dart'; 
import 'package:dio/dio.dart'; 
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
  late Future<List<Map<String, dynamic>>> _devicesFuture; // State Future untuk data Device Sumber
  
  String? _selectedPatientId;
  String? _selectedDeviceId; // Menyimpan UUID Device terpilih
  bool _isUploading = false;
  double _uploadProgress = 0;
  
  PlatformFile? _pickedFile;
  bool _isDraggingOver = false;
  
  // State Overlay Dropdown Pasien
  String _dropdownSearchQuery = '';
  final LayerLink _patientLayerLink = LayerLink();
  OverlayEntry? _patientOverlayEntry;
  bool _isPatientDropdownOpen = false;
  final TextEditingController _patientSearchController = TextEditingController();
  List<PatientModel> _allPatients = [];
  final GlobalKey _patientDropdownKey = GlobalKey();

  // State Overlay Dropdown Device Kustom
  String _deviceDropdownSearchQuery = '';
  final LayerLink _deviceLayerLink = LayerLink();
  OverlayEntry? _deviceOverlayEntry;
  bool _isDeviceDropdownOpen = false;
  final TextEditingController _deviceSearchController = TextEditingController();
  List<Map<String, dynamic>> _allDevices = [];
  final GlobalKey _deviceDropdownKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _fetchPatientsFromDatabase();
    _fetchDevicesFromDatabase(); // Memuat data awal perangkat perekam dari tabel devices berhuruf kecil
  }

  @override
  void dispose() {
    _removePatientOverlay();
    _removeDeviceOverlay();
    _patientSearchController.dispose();
    _deviceSearchController.dispose();
    super.dispose();
  }

  // =========================================================================
  // MANAJEMEN OVERLAY DROPDOWN PASIEN
  // =========================================================================
  void _removePatientOverlay() {
    _patientOverlayEntry?.remove();
    _patientOverlayEntry = null;
    _isPatientDropdownOpen = false;
  }

  void _togglePatientDropdown(List<PatientModel> patients) {
    if (_isDeviceDropdownOpen) _removeDeviceOverlay();
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
                  onTap: () {},
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
                                        hintText: 'Cari pasien...',
                                        hintStyle: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                                        contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                        filled: true,
                                        fillColor: const Color(0xFF252B3B),
                                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: BorderSide(color: AppColors.borderLight)),
                                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: BorderSide(color: AppColors.borderLight)),
                                        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.primary)),
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
                                            p.fullName, // PERBAIKAN: Menghapus nomor rekam medis dari list dropdown
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

  // =========================================================================
  // MANAJEMEN OVERLAY DROPDOWN PERANGKAT (DEVICES) KUSTOM
  // =========================================================================
  void _removeDeviceOverlay() {
    _deviceOverlayEntry?.remove();
    _deviceOverlayEntry = null;
    _isDeviceDropdownOpen = false;
  }

  void _toggleDeviceDropdown(List<Map<String, dynamic>> devices) {
    if (_isPatientDropdownOpen) _removePatientOverlay();
    if (_isDeviceDropdownOpen) {
      _removeDeviceOverlay();
      setState(() {});
      return;
    }
    _allDevices = devices;
    _deviceDropdownSearchQuery = '';
    _deviceSearchController.clear();
    _showDeviceOverlay(devices);
    setState(() { _isDeviceDropdownOpen = true; });
  }

  void _showDeviceOverlay(List<Map<String, dynamic>> devices) {
    final overlay = Overlay.of(context);
    final showSearch = devices.length > 5;

    double dropdownWidth = 300;
    final renderBox = _deviceDropdownKey.currentContext?.findRenderObject() as RenderBox?;
    if (renderBox != null) {
      dropdownWidth = renderBox.size.width;
    }

    _deviceOverlayEntry = OverlayEntry(
      builder: (ctx) {
        return GestureDetector(
          behavior: HitTestBehavior.translucent,
          onTap: () {
            _removeDeviceOverlay();
            setState(() {});
          },
          child: Stack(
            children: [
              Positioned.fill(child: Container(color: Colors.transparent)),
              CompositedTransformFollower(
                link: _deviceLayerLink,
                showWhenUnlinked: false,
                offset: const Offset(0, 48),
                child: GestureDetector(
                  onTap: () {},
                  child: SizedBox(
                    width: dropdownWidth,
                    child: Material(
                      elevation: 6,
                      borderRadius: BorderRadius.circular(10),
                      color: const Color(0xFF1E2433),
                      child: StatefulBuilder(
                        builder: (ctx2, setOverlayState) {
                          final filtered = _allDevices.where((d) =>
                            (d['device_name'] ?? '').toString().toLowerCase().contains(_deviceDropdownSearchQuery.toLowerCase())
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
                                      controller: _deviceSearchController,
                                      autofocus: true,
                                      style: const TextStyle(fontSize: 13, color: AppColors.textPrimary),
                                      decoration: InputDecoration(
                                        hintText: 'Cari nama perangkat...',
                                        hintStyle: const TextStyle(fontSize: 13, color: AppColors.textMuted),
                                        contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                        filled: true,
                                        fillColor: const Color(0xFF252B3B),
                                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: BorderSide(color: AppColors.borderLight)),
                                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: BorderSide(color: AppColors.borderLight)),
                                        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.primary)),
                                      ),
                                      onChanged: (val) {
                                        setState(() => _deviceDropdownSearchQuery = val);
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
                                      final d = filtered[i];
                                      final id = d['device_id']?.toString();
                                      final name = d['device_name']?.toString() ?? 'Alat Tidak Diketahui';
                                      final isSelected = _selectedDeviceId == id;
                                      return InkWell(
                                        onTap: () {
                                          setState(() => _selectedDeviceId = id);
                                          _removeDeviceOverlay();
                                          setState(() {});
                                        },
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                          color: isSelected ? AppColors.primary.withOpacity(0.15) : Colors.transparent,
                                          child: Text(
                                            name,
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

    overlay.insert(_deviceOverlayEntry!);
  }

  // =========================================================================
  // LOGIK FETCH DATA SUPABASE
  // =========================================================================
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

  void _fetchDevicesFromDatabase() {
    setState(() {
      _devicesFuture = _supabase
          .from('devices')
          .select('device_id, device_name')
          .order('device_name', ascending: true)
          .then((response) {
            final List data = response as List;
            return data.map((item) => item as Map<String, dynamic>).toList();
          });
    });
  }

  // =========================================================================
  // LOGIK PEMROSESAN FILE & UPLOAD
  // =========================================================================
  Future<void> _pickFileViaClick() async {
    if (_selectedPatientId == null) {
      _showSnackBar('Pilih pasien terlebih dahulu');
      return;
    }
    if (_selectedDeviceId == null) {
      _showSnackBar('Pilih perangkat perekam (device) terlebih dahulu');
      return;
    }

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf'],
      );

      if (result != null && result.files.isNotEmpty) {
        _processSelectedFile(result.files.first);
      }
    } catch (e) {
      _showSnackBar('Gagal mengambil file: $e');
    }
  }

  Future<void> _handleRawDroppedFiles(List<dynamic> files) async {
    if (_selectedPatientId == null) {
      _showSnackBar('Pilih pasien terlebih dahulu');
      return;
    }
    if (_selectedDeviceId == null) {
      _showSnackBar('Pilih perangkat perekam terlebih dahulu');
      return;
    }

    try {
      if (files.isNotEmpty) {
        final dropFile = files.first;
        final String name = dropFile.name.toString();
        
        if (!name.toLowerCase().endsWith('.pdf')) {
          _showSnackBar('Format tidak didukung! Hanya mendukung file PDF');
          return;
        }

        final bytes = await dropFile.readAsBytes();
        final size = await dropFile.length();

        final platformFile = PlatformFile(
          name: name,
          size: size,
          bytes: bytes,
          path: kIsWeb ? null : dropFile.path.toString(),
        );

        _processSelectedFile(platformFile);
      }
    } catch (e) {
      _showSnackBar('Gagal memproses drop file: $e');
    }
  }

  void _processSelectedFile(PlatformFile file) {
    setState(() {
      _pickedFile = file;
      _uploadProgress = 0;
    });
  }

  String _getBackendUrl() {
    if (kIsWeb) {
      return 'http://127.0.0.1:8000/api/v1/process-ecg';
    } else if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1/process-ecg'; 
    } else {
      return 'http://127.0.0.1:8000/api/v1/process-ecg'; 
    }
  }

  Future<void> _handleSubmit() async {
    if (_selectedPatientId == null) {
      _showSnackBar('Pilih pasien terlebih dahulu sebelum memproses EKG.');
      return;
    }
    if (_selectedDeviceId == null) {
      _showSnackBar('Pilih perangkat perekam (device) sebelum memproses EKG.');
      return;
    }
    if (_pickedFile == null) {
      _pickFileViaClick();
      return;
    }

    setState(() {
      _isUploading = true;
      _uploadProgress = 0;
    });

    try {
      final dio = Dio();

      MultipartFile? uploadFile;
      if (_pickedFile!.bytes != null) {
        uploadFile = MultipartFile.fromBytes(
          _pickedFile!.bytes!,
          filename: _pickedFile!.name,
        );
      } else if (_pickedFile!.path != null) {
        uploadFile = await MultipartFile.fromFile(
          _pickedFile!.path!,
          filename: _pickedFile!.name,
        );
      }

      if (uploadFile == null) {
        throw Exception('File tidak dapat dibaca. Coba pilih file lagi.');
      }

      // Mengirim payload terintegrasi (patient_id, device_id, user_id, file)
      final formData = FormData.fromMap({
        'patient_id': _selectedPatientId!,
        'device_id': _selectedDeviceId!,
        'user_id': _supabase.auth.currentUser?.id ?? '',
        'file': uploadFile,
      });

      final response = await dio.post(
        _getBackendUrl(),
        data: formData,
        onSendProgress: (sent, total) {
          if (total > 0 && mounted) {
            setState(() => _uploadProgress = sent / total);
          }
        },
        options: Options(
          sendTimeout: const Duration(seconds: 60),
          receiveTimeout: const Duration(seconds: 180),
        ),
      );

      if (!mounted) return;
      setState(() => _isUploading = false);

      if (response.statusCode == 200 || response.statusCode == 202) {
        _showSnackBar('EKG berhasil masuk antrean digitalisasi! Silakan pantau halaman riwayat.');
        setState(() {
          _pickedFile = null;
          _selectedPatientId = null;
          _selectedDeviceId = null;
          _uploadProgress = 0;
        });
        context.go(AppRoutes.history);
      } else {
        _showSnackBar('Backend merespons dengan status tidak terduga: ${response.statusCode}');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isUploading = false;
        _uploadProgress = 0;
      });

      if (e is DioException) {
        final dynamic rawDetail = e.response?.data;
        String detail;
        if (rawDetail is Map && rawDetail.containsKey('detail')) {
          detail = rawDetail['detail'].toString();
        } else if (rawDetail != null) {
          detail = rawDetail.toString();
        } else {
          detail = e.message ?? 'Tidak dapat terhubung ke backend.';
        }
        _showSnackBar('Gagal: $detail');
      } else {
        _showSnackBar('Gagal terhubung ke backend Python: $e');
      }
    }
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  // =========================================================================
  // TAMPILAN INTERFACE (UI)
  // =========================================================================
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F131E),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // STEP 1: PILIH PASIEN
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
                                  Material(
                                    type: MaterialType.transparency,
                                    child: SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                                  ),
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
                                child: Text("Pasien", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.textSecondary)),
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
                                      border: Border.all(color: _isPatientDropdownOpen ? AppColors.primary : AppColors.borderLight),
                                    ),
                                    child: Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            selectedPatient != null
                                                ? selectedPatient.fullName // PERBAIKAN: Menghapus nomor rekam medis dari teks utama button
                                                : 'Pilih Subjek Pasien',
                                            style: TextStyle(fontSize: 14, color: selectedPatient != null ? AppColors.textPrimary : AppColors.textMuted),
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

                  // STEP 2: PILIH PERANGKAT (DEVICES) DENGAN STRUKTUR OVERLAY KUSTOM IDENTIK
                  _StepCard(
                    step: 2,
                    title: 'Pilih Perangkat (Device Source)',
                    children: [
                      FutureBuilder<List<Map<String, dynamic>>>(
                        future: _devicesFuture,
                        builder: (context, snapshot) {
                          if (snapshot.connectionState == ConnectionState.waiting) {
                            return const Padding(
                              padding: EdgeInsets.symmetric(vertical: 12),
                              child: Row(
                                children: [
                                  Material(
                                    type: MaterialType.transparency,
                                    child: SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                                  ),
                                  SizedBox(width: 12),
                                  Text('Memuat tipe mesin EKG...', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                                ],
                              ),
                            );
                          }
                          if (snapshot.hasError) {
                            return Text('Error: ${snapshot.error}', style: const TextStyle(color: AppColors.danger));
                          }

                          final allDevices = snapshot.data ?? [];
                          final selectedDevice = allDevices.firstWhere(
                            (d) => d['device_id']?.toString() == _selectedDeviceId,
                            orElse: () => {},
                          );

                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Padding(
                                padding: EdgeInsets.only(bottom: 8),
                                child: Text("Perangkat Medis Pencetak PDF", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.textSecondary)),
                              ),
                              CompositedTransformTarget(
                                link: _deviceLayerLink,
                                child: GestureDetector(
                                  onTap: () => _toggleDeviceDropdown(allDevices),
                                  child: Container(
                                    key: _deviceDropdownKey,
                                    height: 48,
                                    padding: const EdgeInsets.symmetric(horizontal: 14),
                                    decoration: BoxDecoration(
                                      color: AppColors.surfaceVariant,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(color: _isDeviceDropdownOpen ? AppColors.primary : AppColors.borderLight),
                                    ),
                                    child: Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            selectedDevice.isNotEmpty
                                                ? '${selectedDevice['device_name']}'
                                                : 'Pilih Model Alat Rekam EKG',
                                            style: TextStyle(fontSize: 14, color: selectedDevice.isNotEmpty ? AppColors.textPrimary : AppColors.textMuted),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                        AnimatedRotation(
                                          turns: _isDeviceDropdownOpen ? 0.5 : 0,
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
                    ],
                  ),

                  const SizedBox(height: 16),

                  // STEP 3: UPLOAD FILE PDF EKG
                  _StepCard(
                    step: 3,
                    title: 'Upload File EKG',
                    children: [
                      if (_pickedFile == null)
                        SafeDropWrapper(
                          onDragEntered: () => setState(() => _isDraggingOver = true),
                          onDragExited: () => setState(() => _isDraggingOver = false),
                          onFilesDropped: (files) {
                            setState(() => _isDraggingOver = false);
                            _handleRawDroppedFiles(files);
                          },
                          child: GestureDetector(
                            onTap: _isUploading ? null : _pickFileViaClick,
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(vertical: 40),
                              decoration: BoxDecoration(
                                color: _isDraggingOver ? AppColors.primary.withOpacity(0.08) : AppColors.surfaceVariant,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: _isDraggingOver ? AppColors.primary : AppColors.borderLight,
                                  style: BorderStyle.solid,
                                  width: _isDraggingOver ? 2 : 1,
                                ),
                              ),
                              child: Column(
                                children: [
                                  Icon(
                                    Icons.cloud_upload_rounded,
                                    size: 48,
                                    color: (_isUploading || _isDraggingOver) ? AppColors.primary : AppColors.textMuted
                                  ),
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
                                    Text('${(_uploadProgress * 100).round()}% - Mengupload berkas...', style: const TextStyle(fontSize: 12, color: AppColors.primary)),
                                  ] else ...[
                                    Text(
                                      _isDraggingOver ? 'Lepaskan file di sini...' : 'Klik atau seret file PDF ke sini',
                                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.textSecondary)
                                    ),
                                    const SizedBox(height: 4),
                                    const Text('Mendukung konversi otomatis biner gelombang EKG', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                                    const SizedBox(height: 12),
                                    ElevatedButton.icon(
                                      onPressed: _pickFileViaClick,
                                      icon: const Icon(Icons.upload_rounded, size: 16),
                                      label: const Text('Pilih File PDF'),
                                    ),
                                  ],
                                ],
                              ),
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
                                    Text(_pickedFile!.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.successLight)),
                                    Text('${(_pickedFile!.size / 1024).toStringAsFixed(1)} KB', style: const TextStyle(fontSize: 11, color: AppColors.success)),
                                  ],
                                ),
                              ),
                              IconButton(
                                onPressed: () => setState(() => _pickedFile = null),
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
                            : const Text('Proses EKG'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 24),
            SizedBox(
              width: 280,
              child: Column(
                children: [
                  const _InfoCard(
                    title: 'Format yang Didukung',
                    items: [
                      _FormatInfo(icon: Icons.picture_as_pdf_rounded, label: 'PDF', desc: 'Hasil cetak EKG digital dari perangkat'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const _InfoCard(
                    title: 'Proses Setelah Upload',
                    items: [
                      _FormatInfo(icon: Icons.search_rounded, label: 'Ekstraksi FHIR', desc: 'Identifikasi format dan ekstraksi sinyal ke JSON'),
                      _FormatInfo(icon: Icons.cloud_sync_rounded, label: 'Database Sync', desc: 'Otomatis tersimpan ke tabel ecg_sessions & ecg_signal_data'),
                    ],
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

class SafeDropWrapper extends StatelessWidget {
  final Widget child;
  final VoidCallback onDragEntered;
  final VoidCallback onDragExited;
  final Function(List<dynamic>) onFilesDropped;

  const SafeDropWrapper({
    super.key,
    required this.child,
    required this.onDragEntered,
    required this.onDragExited,
    required this.onFilesDropped,
  });

  @override
  Widget build(BuildContext context) {
    return DropTarget(
      onDragEntered: (_) => onDragEntered(),
      onDragExited: (_) => onDragExited(),
      onDragDone: (DropDoneDetails details) {
        if (details.files.isNotEmpty) {
          onFilesDropped(details.files);
        }
      },
      child: child,
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