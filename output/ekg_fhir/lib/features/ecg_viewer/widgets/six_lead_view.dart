// lib/features/ecg_viewer/widgets/six_lead_view.dart
// Layout 6-lead: Lead I, II, III, aVR, aVL, aVF dalam 2 kolom × 3 baris
// Justifikasi: standar klinis 6-lead limb leads (Kligfield et al., 2007 — AHA/ACC)

import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/models/ecg_models.dart';
import 'ecg_chart_widget.dart';

class SixLeadView extends StatelessWidget {
  final EcgSession session;
  final double zoomLevel;
  final bool showGrid;
  final bool showAnnotations;

  const SixLeadView({
    super.key,
    required this.session,
    required this.zoomLevel,
    required this.showGrid,
    required this.showAnnotations,
  });

  @override
  Widget build(BuildContext context) {
    final signalData = session.signalData;
    final leads6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF'];

    if (signalData == null) {
      return const Center(
        child: Text('Data sinyal belum tersedia', style: TextStyle(color: AppColors.textMuted)),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 2 column × 3 rows layout
          for (int row = 0; row < 3; row++)
            Row(
              children: [
                for (int col = 0; col < 2; col++)
                  Builder(builder: (context) {
                    final leadIdx = row * 2 + col;
                    if (leadIdx >= leads6.length) return const Expanded(child: SizedBox());
                    final lead = leads6[leadIdx];
                    final data = signalData.signalData[lead] ?? [];
                    final color = AppColors.leadColors[leadIdx % AppColors.leadColors.length];

                    return Expanded(
                      child: Padding(
                        padding: EdgeInsets.only(
                          right: col == 0 ? 8 : 0,
                          bottom: 8,
                        ),
                        child: _LeadPanel(
                          lead: lead,
                          data: data,
                          color: color,
                          zoomLevel: zoomLevel,
                          showGrid: showGrid,
                          showAnnotations: showAnnotations,
                        ),
                      ),
                    );
                  }),
              ],
            ),
          // Rhythm strip (Lead II full width)
          const SizedBox(height: 8),
          _RhythmStrip(
            data: signalData.signalData['II'] ?? [],
            zoomLevel: zoomLevel,
            showGrid: showGrid,
          ),
        ],
      ),
    );
  }
}

class _LeadPanel extends StatelessWidget {
  final String lead;
  final List<double> data;
  final Color color;
  final double zoomLevel;
  final bool showGrid;
  final bool showAnnotations;

  const _LeadPanel({
    required this.lead,
    required this.data,
    required this.color,
    required this.zoomLevel,
    required this.showGrid,
    required this.showAnnotations,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.ecgBackground,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                ),
                const SizedBox(width: 6),
                Text(
                  lead,
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color, fontFamily: 'monospace'),
                ),
              ],
            ),
          ),
          EcgChartWidget(
            signalData: data,
            leadName: lead,
            zoomLevel: zoomLevel,
            showGrid: showGrid,
            showAnnotations: false, // Label already shown above
            lineColor: color,
            height: 100,
          ),
        ],
      ),
    );
  }
}

class _RhythmStrip extends StatelessWidget {
  final List<double> data;
  final double zoomLevel;
  final bool showGrid;

  const _RhythmStrip({required this.data, required this.zoomLevel, required this.showGrid});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.ecgBackground,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: Row(
              children: [
                Icon(Icons.linear_scale_rounded, size: 12, color: AppColors.ecgLine),
                SizedBox(width: 6),
                Text('Ritme Strip — Lead II', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.ecgLine, fontFamily: 'monospace')),
                Spacer(),
                Text('500 Hz • 25 mm/s • 10 mm/mV', style: TextStyle(fontSize: 10, color: AppColors.textMuted, fontFamily: 'monospace')),
              ],
            ),
          ),
          EcgChartWidget(
            signalData: data,
            leadName: 'Ritme II',
            zoomLevel: zoomLevel,
            showGrid: showGrid,
            showAnnotations: false,
            lineColor: AppColors.ecgLine,
            height: 70,
          ),
        ],
      ),
    );
  }
}
