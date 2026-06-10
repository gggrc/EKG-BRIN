// lib/features/ecg_viewer/ecg_viewer_page.dart
// Halaman utama EKG Viewer — 6-lead dan 12-lead
// Justifikasi layout: Goldberger et al. (2000) "Clinical Electrocardiography" —
// standar klinis 12-lead dalam 3 kolom × 4 baris. Cai et al. (2022) — dokter
// perlu zoom 2-4x untuk analisis gelombang P, QRS, T.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/data_provider.dart';
import '../../core/models/user_model.dart';
import '../../core/models/ecg_models.dart';
import '../../core/mock/mock_data.dart';
import 'widgets/six_lead_view.dart';
import 'widgets/twelve_lead_view.dart';

class EcgViewerPage extends StatefulWidget {
  final String sessionId;
  const EcgViewerPage({super.key, required this.sessionId});

  @override
  State<EcgViewerPage> createState() => _EcgViewerPageState();
}

class _EcgViewerPageState extends State<EcgViewerPage> with TickerProviderStateMixin {
  late TabController _tabController;
  EcgSession? _session;
  double _zoomLevel = 1.0;
  bool _showGrid = true;
  bool _showAnnotations = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadSession();
  }

  void _loadSession() {
    final sessions = context.read<DataProvider>().ecgSessions;
    try {
      _session = sessions.firstWhere((s) => s.sessionId == widget.sessionId);
    } catch (_) {
      _session = sessions.first;
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthProvider>().userRole;

    if (_session == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Column(
      children: [
        // Header with session info + controls
        _buildHeader(role),
        // Tabs: 6-Lead / 12-Lead
        Container(
          color: AppColors.surface,
          child: TabBar(
            controller: _tabController,
            tabs: const [
              Tab(text: '6-Lead'),
              Tab(text: '12-Lead'),
            ],
          ),
        ),
        // Content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              SixLeadView(
                session: _session!,
                zoomLevel: _zoomLevel,
                showGrid: _showGrid,
                showAnnotations: _showAnnotations,
              ),
              TwelveLeadView(
                session: _session!,
                zoomLevel: _zoomLevel,
                showGrid: _showGrid,
                showAnnotations: _showAnnotations,
              ),
            ],
          ),
        ),
        // Bottom: Analysis panel
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
          // Patient info
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
          // Controls
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
          _ToggleButton(
            icon: Icons.grid_4x4_rounded,
            label: 'Grid',
            active: _showGrid,
            onTap: () => setState(() => _showGrid = !_showGrid),
          ),
          const SizedBox(width: 8),
          _ToggleButton(
            icon: Icons.label_rounded,
            label: 'Anotasi',
            active: _showAnnotations,
            onTap: () => setState(() => _showAnnotations = !_showAnnotations),
          ),
          const SizedBox(width: 16),
          if (role == UserRole.clinician || role == UserRole.admin)
            OutlinedButton.icon(
              onPressed: () => context.push('/report/${s.sessionId}'),
              icon: const Icon(Icons.download_rounded, size: 16),
              label: const Text('Export PDF', style: TextStyle(fontSize: 12)),
            ),
          if (role == UserRole.clinician || role == UserRole.admin) ...[
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: () => context.push('/report/${s.sessionId}'),
              icon: const Icon(Icons.share_rounded, size: 16),
              label: const Text('FHIR Export', style: TextStyle(fontSize: 12)),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAnalysisPanel(UserRole? role) {
    final a = _session!.analysis!;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.borderLight)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Analisis', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
              const SizedBox(width: 12),
              if (a.isApproved == true)
                _StatusBadge(label: 'Disetujui Dokter', color: AppColors.success)
              else
                _StatusBadge(label: 'Belum Disetujui', color: AppColors.warning),
            ],
          ),
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
                _MeasureChip(label: 'Irama', value: a.rhythmType ?? '-', isNormal: a.rhythmType == 'Sinus Normal'),
                const SizedBox(width: 8),
                _MeasureChip(label: 'PR Interval', value: a.prIntervalMs != null ? '${a.prIntervalMs!.round()} ms' : '-', isNormal: a.prIntervalMs != null && a.prIntervalMs! >= 120 && a.prIntervalMs! <= 200),
                const SizedBox(width: 8),
                _MeasureChip(label: 'QRS', value: a.qrsDurationMs != null ? '${a.qrsDurationMs!.round()} ms' : '-', isNormal: a.qrsDurationMs != null && a.qrsDurationMs! <= 120),
                const SizedBox(width: 8),
                _MeasureChip(label: 'QTc', value: a.qtcIntervalMs != null ? '${a.qtcIntervalMs!.round()} ms' : '-', isNormal: a.isQtcNormal),
                const SizedBox(width: 8),
                _MeasureChip(label: 'Axis', value: a.electricalAxisDeg != null ? '${a.electricalAxisDeg!.round()}°' : '-', isNormal: true),
                const SizedBox(width: 16),
                if (a.aiInterpretation != null && (role == UserRole.clinician || role == UserRole.admin))
                  Container(
                    constraints: const BoxConstraints(maxWidth: 400),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppColors.roleClinician.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.roleClinician.withOpacity(0.25)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.psychology_rounded, color: AppColors.roleClinician, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            a.aiInterpretation!,
                            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary, height: 1.4),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          if (a.doctorDiagnosis != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.successContainer,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.success.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.local_hospital_rounded, color: AppColors.success, size: 16),
                  const SizedBox(width: 8),
                  const Text('Diagnosis: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.success)),
                  Expanded(
                    child: Text(a.doctorDiagnosis!, style: const TextStyle(fontSize: 12, color: AppColors.success)),
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
          decoration: BoxDecoration(
            color: AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(6),
          ),
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
          mainAxisSize: MainAxisSize.min,
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

class _StatusBadge extends StatelessWidget {
  final String label;
  final Color color;
  const _StatusBadge({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
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
          if (subtext != null)
            Text(subtext!, style: TextStyle(fontSize: 9, color: color.withOpacity(0.7))),
        ],
      ),
    );
  }
}
