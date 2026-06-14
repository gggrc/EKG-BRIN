// lib/features/ecg_viewer/ecg_viewer_page.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/models/user_model.dart';
import '../../core/models/ecg_models.dart';
import 'widgets/six_lead_view.dart';
import 'widgets/twelve_lead_view.dart';

class EcgViewerPage extends StatefulWidget {
  final String sessionId;
  const EcgViewerPage({super.key, required this.sessionId});

  @override
  State<EcgViewerPage> createState() => _EcgViewerPageState();
}

class _EcgViewerPageState extends State<EcgViewerPage> with TickerProviderStateMixin {
  TabController? _tabController; // Diubah menjadi nullable karena diinisialisasi setelah data DB masuk
  EcgSession? _session;
  bool _isLoadingFromDb = true;
  String? _errorMessage;

  double _zoomLevel = 1.0;
  bool _showGrid = true;
  bool _showAnnotations = true;

  @override
  void initState() {
    super.initState();
    _loadSessionFromSupabase();
  }

  /// Menarik data riwayat sinyal digital dan analisis medis dari PostgreSQL via Supabase client
  Future<void> _loadSessionFromSupabase() async {
    try {
      final response = await Supabase.instance.client
          .from('ecg_sessions')
          .select('''
            session_id,
            patient_id,
            device_id,
            examination_time,
            duration_sec,
            lead_configuration,
            status,
            source_type,
            patients (full_name),
            devices (device_name),
            ecg_analysis (
              analysis_id,
              heart_rate_bpm,
              rhythm_type,
              pr_interval,
              qrs_duration,
              qt_interval,
              qtc_interval_ms,
              electrical_axis,
              diagnosis
            ),
            ecg_signal_data (
              signal_id,
              lead_type,
              sampling_rate,
              sample_count,
              signal_data
            )
          ''')
          .eq('session_id', widget.sessionId)
          .maybeSingle();

      if (response == null) {
        setState(() {
          _errorMessage = "Sesi rekam medis EKG tidak ditemukan di PostgreSQL server.";
          _isLoadingFromDb = false;
        });
        return;
      }

      final patientData = response['patients'] as Map<String, dynamic>?;
      final deviceData = response['devices'] as Map<String, dynamic>?;
      final List signalsList = response['ecg_signal_data'] as List? ?? [];

      // Menangani kembalian data ecg_analysis yang dibungkus di dalam List/JSArray oleh Supabase
      Map<String, dynamic>? analysisMap;
      final rawAnalysis = response['ecg_analysis'];
      if (rawAnalysis is List && rawAnalysis.isNotEmpty) {
        analysisMap = rawAnalysis.first as Map<String, dynamic>?;
      } else if (rawAnalysis is Map<String, dynamic>) {
        analysisMap = rawAnalysis;
      }

      // Rekonstruksi struktur data Map dari multiple row di tabel ecg_signal_data
      Map<String, List<double>> reconstructedSignals = {};
      int sampleRate = 500;
      int sampleCount = 0;

      for (var row in signalsList) {
        final String leadName = row['lead_type'] ?? 'Unknown';
        sampleRate = row['sampling_rate'] ?? 500;
        sampleCount = row['sample_count'] ?? 0;

        dynamic rawJsonData = row['signal_data'];
        List<double> signalPoints = [];

        if (rawJsonData is String) {
          rawJsonData = jsonDecode(rawJsonData);
        }
        if (rawJsonData is List) {
          signalPoints = rawJsonData.map((point) => double.tryParse(point.toString()) ?? 0.0).toList();
        }
        reconstructedSignals[leadName] = signalPoints;
      }

      // Deteksi konfigurasi lead secara dinamis dari database
      final String rawLeadConfig = (response['lead_configuration'] ?? '12-Lead').toString().toLowerCase();
      final bool isSixLead = rawLeadConfig.contains('six') || rawLeadConfig.contains('6');
      final currentLeadConfig = isSixLead ? LeadConfiguration.sixLead : LeadConfiguration.twelveLead;

      // Inisialisasi TabController secara dinamis (Hanya 1 Tab aktif sesuai konfigurasi database)
      _tabController = TabController(length: 1, vsync: this);

      setState(() {
        _session = EcgSession(
          sessionId: response['session_id'],
          patientId: response['patient_id'] ?? '',
          patientName: patientData?['full_name'] ?? 'Pasien Anonim',
          deviceId: response['device_id'] ?? '',
          deviceName: deviceData?['device_name'] ?? response['source_type'] ?? 'Digital Record',
          examinationTime: DateTime.parse(response['examination_time']),
          durationSec: response['duration_sec'] ?? 10,
          leadConfiguration: currentLeadConfig,
          status: response['status'] == 'completed' ? EcgSessionStatus.completed : EcgSessionStatus.processing,
          sourceType: SourceType.deviceUpload,
          signalData: EcgSignalData(
            signalId: 0,
            sessionId: response['session_id'],
            leadType: response['lead_configuration'] ?? '12-Lead',
            samplingRate: sampleRate,
            sampleCount: sampleCount,
            signalData: reconstructedSignals,
          ),
          analysis: analysisMap == null
              ? null
              : EcgAnalysis(
                  analysisId: analysisMap['analysis_id'] ?? '',
                  sessionId: response['session_id'],
                  heartRateBpm: analysisMap['heart_rate_bpm'],
                  rhythmType: analysisMap['rhythm_type'],
                  prIntervalMs: (analysisMap['pr_interval'] as num?)?.toDouble(),
                  qrsDurationMs: (analysisMap['qrs_duration'] as num?)?.toDouble(),
                  qtIntervalMs: (analysisMap['qt_interval'] as num?)?.toDouble(),
                  qtcIntervalMs: (analysisMap['qtc_interval_ms'] as num?)?.toDouble(),
                  electricalAxisDeg: (analysisMap['electrical_axis'] as num?)?.toDouble(),
                  doctorDiagnosis: analysisMap['diagnosis'], 
                  isApproved: true,
                ),
        );
        _isLoadingFromDb = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = "Gagal memproses gelombang EKG dari Supabase: $e";
        _isLoadingFromDb = false;
      });
    }
  }

  @override
  void dispose() {
    _tabController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthProvider>().userRole;

    if (_isLoadingFromDb) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Memuat gelombang EKG dari database...', style: TextStyle(color: AppColors.textSecondary)),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(_errorMessage!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.bold)),
        ),
      );
    }

    final isSixLeadMode = _session!.leadConfiguration == LeadConfiguration.sixLead;

    return Column(
      children: [
        // Header info pasien dan control slider zoom
        _buildHeader(role),
        
        // Tab Bar dinamis yang mengunci pilihan sesuai tipe lead_configuration dari database
        Container(
          color: AppColors.surface,
          child: TabBar(
            controller: _tabController,
            tabs: [
              Tab(text: isSixLeadMode ? '6-Lead' : '12-Lead'),
            ],
          ),
        ),
        
        // Canvas Gambar Grafik Sinyal Gelombang sesuai mode data
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              if (isSixLeadMode)
                SixLeadView(
                  session: _session!,
                  zoomLevel: _zoomLevel,
                  showGrid: _showGrid,
                  showAnnotations: _showAnnotations,
                )
              else
                TwelveLeadView(
                  session: _session!,
                  zoomLevel: _zoomLevel,
                  showGrid: _showGrid,
                  showAnnotations: _showAnnotations,
                ),
            ],
          ),
        ),
        
        // Panel Bawah: Interpretasi Algoritma & Hasil Diagnosis Dokter
        if (_session!.analysis != null) _buildAnalysisPanel(role),
      ],
    );
  }

  Widget _buildHeader(UserRole? role) {
    final s = _session!;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.borderLight)),
      ),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(s.patientName, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
              Text(
                '${s.deviceName} • ${s.leadConfigDisplay} • ${_formatDate(s.examinationTime)}',
                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
            ],
          ),
          const Spacer(),
          _ControlButton(icon: Icons.zoom_out, onTap: () => setState(() => _zoomLevel = (_zoomLevel - 0.25).clamp(0.5, 4.0)), tooltip: 'Zoom out'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Text(
              '${(_zoomLevel * 100).round()}%',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textPrimary, fontFamily: 'monospace'),
            ),
          ),
          _ControlButton(icon: Icons.zoom_in, onTap: () => setState(() => _zoomLevel = (_zoomLevel + 0.25).clamp(0.5, 4.0)), tooltip: 'Zoom in'),
          const SizedBox(width: 8),
          _ToggleButton(icon: Icons.grid_4x4_rounded, label: 'Grid', active: _showGrid, onTap: () => setState(() => _showGrid = !_showGrid)),
          const SizedBox(width: 8),
          _ToggleButton(icon: Icons.label_rounded, label: 'Anotasi', active: _showAnnotations, onTap: () => setState(() => _showAnnotations = !_showAnnotations)),
        ],
      ),
    );
  }

  Widget _buildAnalysisPanel(UserRole? role) {
    final a = _session!.analysis!;
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.borderLight)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Hasil Analisis Rekam Medis (PostgreSQL)', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _MeasureChip(
                  label: 'HR',
                  value: a.heartRateBpm != null ? '${a.heartRateBpm} bpm' : '-',
                  isNormal: a.isHeartRateNormal,
                  subtext: a.heartRateCategory,
                ),
                const SizedBox(width: 8),
                _MeasureChip(label: 'Irama', value: a.rhythmType ?? '-', isNormal: a.rhythmType?.toLowerCase() == 'normal sinus rhythm' || a.rhythmType?.toLowerCase() == 'sinus normal'),
                const SizedBox(width: 8),
                _MeasureChip(label: 'PR Interval', value: a.prIntervalMs != null ? '${a.prIntervalMs!.round()} ms' : '-', isNormal: true),
                const SizedBox(width: 8),
                _MeasureChip(label: 'QRS Duration', value: a.qrsDurationMs != null ? '${a.qrsDurationMs!.round()} ms' : '-', isNormal: true),
                const SizedBox(width: 8),
                _MeasureChip(label: 'QTc', value: a.qtcIntervalMs != null ? '${a.qtcIntervalMs!.round()} ms' : '-', isNormal: a.isQtcNormal),
                const SizedBox(width: 8),
                _MeasureChip(label: 'Electrical Axis', value: a.electricalAxisDeg != null ? '${a.electricalAxisDeg!.round()}°' : '-', isNormal: true),
              ],
            ),
          ),
          if (a.doctorDiagnosis != null && a.doctorDiagnosis!.isNotEmpty) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.successContainer,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.success.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.local_hospital_rounded, color: AppColors.success, size: 18),
                  const SizedBox(width: 8),
                  const Text('Diagnosis Klinis: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.success)),
                  Expanded(
                    child: Text(a.doctorDiagnosis!, style: const TextStyle(fontSize: 12, color: AppColors.successLight)),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _formatDate(DateTime d) {
    return '${d.day}/${d.month}/${d.year} ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
  }
}

class _ControlButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  final String tooltip;
  const _ControlButton({required this.icon, required this.onTap, required this.tooltip});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        borderRadius: BorderRadius.circular(6),
        onTap: onTap,
        child: Container(
          width: 32,
          height: 32,
          margin: const EdgeInsets.symmetric(horizontal: 2),
          decoration: BoxDecoration(color: AppColors.surfaceVariant, borderRadius: BorderRadius.circular(6)),
          child: Icon(icon, size: 16, color: AppColors.textSecondary),
        ),
      ),
    );
  }
}

class _ToggleButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _ToggleButton({required this.icon, required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(6),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: active ? AppColors.primary.withOpacity(0.15) : AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(6),
          border: active ? Border.all(color: AppColors.primary.withOpacity(0.3)) : null,
        ),
        child: Row(
          children: [
            Icon(icon, size: 14, color: active ? AppColors.primary : AppColors.textMuted),
            const SizedBox(width: 4),
            Text(label, style: TextStyle(fontSize: 11, color: active ? AppColors.primary : AppColors.textMuted, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
    );
  }
}

class _MeasureChip extends StatelessWidget {
  final String label;
  final String value;
  final bool isNormal;
  final String? subtext;
  const _MeasureChip({required this.label, required this.value, required this.isNormal, this.subtext});

  @override
  Widget build(BuildContext context) {
    final color = isNormal ? AppColors.success : AppColors.warning;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.25)),
      ),
      child: Column(
        children: [
          Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
          Text(value, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: color, fontFamily: 'monospace')),
          if (subtext != null) Text(subtext!, style: TextStyle(fontSize: 9, color: color.withOpacity(0.7))),
        ],
      ),
    );
  }
}