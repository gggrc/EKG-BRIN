// lib/features/ecg_viewer/widgets/twelve_lead_view.dart
// Layout 12-lead: 3 kolom × 4 baris (standar klinis internasional)
// Justifikasi: Goldberger et al. (2000) — standar 12-lead dalam 3 kolom × 4 baris
// memungkinkan perbandingan simultan semua lead.

import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/models/ecg_models.dart';
import 'ecg_chart_widget.dart';

class TwelveLeadView extends StatelessWidget {
  final EcgSession session;
  final double zoomLevel;
  final bool showGrid;
  final bool showAnnotations;

  const TwelveLeadView({
    super.key,
    required this.session,
    required this.zoomLevel,
    required this.showGrid,
    required this.showAnnotations,
  });

  // Standard 12-lead layout: 3 columns × 4 rows
  // Col 1: I, II, III, (rhythm II)
  // Col 2: aVR, aVL, aVF, (rhythm II cont.)
  // Col 3: V1-V2, V3-V4, V5-V6, (rhythm II cont.)
  static const List<List<String>> _layout = [
    ['I', 'aVR', 'V1', 'V4'],
    ['II', 'aVL', 'V2', 'V5'],
    ['III', 'aVF', 'V3', 'V6'],
  ];

  @override
  Widget build(BuildContext context) {
    final signalData = session.signalData;

    if (signalData == null) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.signal_wifi_off_rounded, size: 48, color: AppColors.textMuted),
            SizedBox(height: 16),
            Text('Data sinyal 12-lead belum tersedia', style: TextStyle(color: AppColors.textMuted)),
          ],
        ),
      );
    }

    final allLeads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Standard speed/gain info bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Row(
              children: [
                Icon(Icons.info_outline_rounded, size: 14, color: AppColors.textMuted),
                SizedBox(width: 8),
                Text(
                  'Kecepatan: 25 mm/s  •  Gain: 10 mm/mV  •  Filter: 0.05–150 Hz  •  Format: 3 kolom × 4 baris (standar AHA)',
                  style: TextStyle(fontSize: 11, color: AppColors.textMuted, fontFamily: 'monospace'),
                ),
              ],
            ),
          ),
          // 3-column layout with 4 rows
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Column 1: I, II, III, aVF(rhythm)
              Expanded(
                child: Column(
                  children: [
                    _buildLeadCell('I', signalData.signalData['I'] ?? [], 0),
                    const SizedBox(height: 4),
                    _buildLeadCell('II', signalData.signalData['II'] ?? [], 1),
                    const SizedBox(height: 4),
                    _buildLeadCell('III', signalData.signalData['III'] ?? [], 2),
                    const SizedBox(height: 4),
                    _buildLeadCell('aVF', signalData.signalData['aVF'] ?? [], 5),
                  ],
                ),
              ),
              const SizedBox(width: 4),
              // Column 2: aVR, aVL, aVF, V1
              Expanded(
                child: Column(
                  children: [
                    _buildLeadCell('aVR', signalData.signalData['aVR'] ?? [], 3),
                    const SizedBox(height: 4),
                    _buildLeadCell('aVL', signalData.signalData['aVL'] ?? [], 4),
                    const SizedBox(height: 4),
                    _buildLeadCell('V1', signalData.signalData['V1'] ?? [], 6),
                    const SizedBox(height: 4),
                    _buildLeadCell('V2', signalData.signalData['V2'] ?? [], 7),
                  ],
                ),
              ),
              const SizedBox(width: 4),
              // Column 3: V3, V4, V5, V6
              Expanded(
                child: Column(
                  children: [
                    _buildLeadCell('V3', signalData.signalData['V3'] ?? [], 8),
                    const SizedBox(height: 4),
                    _buildLeadCell('V4', signalData.signalData['V4'] ?? [], 9),
                    const SizedBox(height: 4),
                    _buildLeadCell('V5', signalData.signalData['V5'] ?? [], 10),
                    const SizedBox(height: 4),
                    _buildLeadCell('V6', signalData.signalData['V6'] ?? [], 11),
                  ],
                ),
              ),
            ],
          ),
          // Full-width rhythm strip
          const SizedBox(height: 8),
          _buildRhythmStrip(signalData.signalData['II'] ?? []),
        ],
      ),
    );
  }

  Widget _buildLeadCell(String lead, List<double> data, int colorIdx) {
    final color = AppColors.leadColors[colorIdx % AppColors.leadColors.length];
    return Container(
      decoration: BoxDecoration(
        color: AppColors.ecgBackground,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.borderLight, width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
            child: Text(lead, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: color, fontFamily: 'monospace')),
          ),
          EcgChartWidget(
            signalData: data,
            leadName: lead,
            zoomLevel: zoomLevel,
            showGrid: showGrid,
            showAnnotations: false,
            lineColor: color,
            height: 80,
          ),
        ],
      ),
    );
  }

  Widget _buildRhythmStrip(List<double> data) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.ecgBackground,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: Row(
              children: [
                Text('Ritme Strip — II', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.ecgLine, fontFamily: 'monospace')),
                Spacer(),
                Text('Kontinu 10 detik', style: TextStyle(fontSize: 10, color: AppColors.textMuted)),
              ],
            ),
          ),
          EcgChartWidget(
            signalData: data,
            leadName: 'II',
            zoomLevel: zoomLevel,
            showGrid: showGrid,
            showAnnotations: false,
            lineColor: AppColors.ecgLine,
            height: 60,
          ),
        ],
      ),
    );
  }
}
