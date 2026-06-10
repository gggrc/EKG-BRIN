// lib/features/admin/analytics_page.dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';

class AnalyticsPage extends StatelessWidget {
  const AnalyticsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final analytics = MockData.analyticsData;
    final rhythmData = Map<String, int>.from(analytics['rhythmDistribution']);
    final monthlyData = List<int>.from(analytics['sessionsByMonth']);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun'];
    final colors = [AppColors.success, AppColors.danger, AppColors.secondary, AppColors.warning, AppColors.roleDoctor, AppColors.textMuted];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Analytics & Statistik', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 6),
          const Text('Data agregat sistem EKG-BRIN (Jan–Jun 2026)', style: TextStyle(fontSize: 14, color: AppColors.textSecondary)),
          const SizedBox(height: 24),
          // KPI row
          Row(
            children: [
              Expanded(child: _KpiCard(label: 'Total Pasien', value: '${analytics['totalPatients']}', icon: Icons.people_rounded, color: AppColors.primary, trend: '+12%')),
              const SizedBox(width: 16),
              Expanded(child: _KpiCard(label: 'Total Sesi EKG', value: '${analytics['totalSessions']}', icon: Icons.monitor_heart_rounded, color: AppColors.secondary, trend: '+23%')),
              const SizedBox(width: 16),
              Expanded(child: _KpiCard(label: 'HR Rata-rata', value: '${analytics['avgHeartRate']} bpm', icon: Icons.favorite_rounded, color: AppColors.success, trend: 'Normal')),
              const SizedBox(width: 16),
              Expanded(child: _KpiCard(label: 'FHIR Synced', value: '${analytics['fhirSyncedCount']}', icon: Icons.cloud_done_rounded, color: AppColors.warning, trend: '86.3%')),
            ],
          ),
          const SizedBox(height: 24),
          // Charts
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Monthly bar chart
              Expanded(
                flex: 2,
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Sesi EKG per Bulan', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(height: 4),
                      const Text('Total sesi perekaman EKG Jan–Jun 2026', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 220,
                        child: BarChart(
                          BarChartData(
                            alignment: BarChartAlignment.spaceAround,
                            maxY: (monthlyData.reduce((a, b) => a > b ? a : b) * 1.25).toDouble(),
                            gridData: FlGridData(
                              show: true,
                              drawVerticalLine: false,
                              horizontalInterval: 20,
                              getDrawingHorizontalLine: (v) => FlLine(color: AppColors.borderLight, strokeWidth: 1),
                            ),
                            borderData: FlBorderData(show: false),
                            titlesData: FlTitlesData(
                              bottomTitles: AxisTitles(sideTitles: SideTitles(
                                showTitles: true,
                                getTitlesWidget: (v, _) => Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(months[v.toInt()], style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                                ),
                              )),
                              leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, getTitlesWidget: (v, _) => Text('${v.toInt()}', style: const TextStyle(fontSize: 10, color: AppColors.textMuted)), reservedSize: 28)),
                              topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                              rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                            ),
                            barGroups: monthlyData.asMap().entries.map((e) => BarChartGroupData(
                              x: e.key,
                              barRods: [BarChartRodData(
                                toY: e.value.toDouble(),
                                gradient: const LinearGradient(
                                  begin: Alignment.bottomCenter,
                                  end: Alignment.topCenter,
                                  colors: [AppColors.primary, AppColors.secondary],
                                ),
                                width: 32,
                                borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                                backDrawRodData: BackgroundBarChartRodData(
                                  show: true,
                                  toY: (monthlyData.reduce((a, b) => a > b ? a : b) * 1.25).toDouble(),
                                  color: AppColors.surfaceVariant,
                                ),
                              )],
                              showingTooltipIndicators: [],
                            )).toList(),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 24),
              // Rhythm pie chart
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Distribusi Irama', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(height: 4),
                      const Text('Pola irama dari seluruh rekaman', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 180,
                        child: PieChart(PieChartData(
                          sections: rhythmData.entries.toList().asMap().entries.map((e) {
                            final i = e.key;
                            final entry = e.value;
                            return PieChartSectionData(
                              value: entry.value.toDouble(),
                              title: '${entry.value}%',
                              color: colors[i % colors.length],
                              radius: 60,
                              titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Colors.white),
                            );
                          }).toList(),
                          sectionsSpace: 2,
                          centerSpaceRadius: 35,
                        )),
                      ),
                      const SizedBox(height: 16),
                      ...rhythmData.entries.toList().asMap().entries.map((e) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          children: [
                            Container(width: 10, height: 10, decoration: BoxDecoration(color: colors[e.key % colors.length], borderRadius: BorderRadius.circular(2))),
                            const SizedBox(width: 8),
                            Expanded(child: Text(e.value.key, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary))),
                            Text('${e.value.value}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                          ],
                        ),
                      )),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          // Source type + Lead distribution
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Distribusi Sumber Data', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(height: 16),
                      ...Map<String, int>.from(analytics['sourceTypeDistribution']).entries.toList().asMap().entries.map((e) {
                        final color = [AppColors.primary, AppColors.secondary, AppColors.warning, AppColors.success][e.key % 4];
                        final total = Map<String, int>.from(analytics['sourceTypeDistribution']).values.fold(0, (a, b) => a + b);
                        final pct = (e.value.value / total * 100).round();
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(e.value.key, style: const TextStyle(fontSize: 12, color: AppColors.textPrimary)),
                                  const Spacer(),
                                  Text('$pct%', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color)),
                                ],
                              ),
                              const SizedBox(height: 4),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(4),
                                child: LinearProgressIndicator(value: pct / 100, backgroundColor: AppColors.surfaceVariant, valueColor: AlwaysStoppedAnimation<Color>(color), minHeight: 6),
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Konfigurasi Lead', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(height: 16),
                      ...Map<String, int>.from(analytics['leadConfigDistribution']).entries.toList().asMap().entries.map((e) {
                        final color = [AppColors.primary, AppColors.secondary][e.key % 2];
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(children: [
                                Text(e.value.key, style: const TextStyle(fontSize: 12, color: AppColors.textPrimary)),
                                const Spacer(),
                                Text('${e.value.value}%', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color)),
                              ]),
                              const SizedBox(height: 4),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(4),
                                child: LinearProgressIndicator(value: e.value.value / 100, backgroundColor: AppColors.surfaceVariant, valueColor: AlwaysStoppedAnimation<Color>(color), minHeight: 8),
                              ),
                            ],
                          ),
                        );
                      }),
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

class _KpiCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final String trend;

  const _KpiCard({required this.label, required this.value, required this.icon, required this.color, required this.trend});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(width: 40, height: 40, decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(10)), child: Icon(icon, color: color, size: 20)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
              decoration: BoxDecoration(color: AppColors.success.withOpacity(0.12), borderRadius: BorderRadius.circular(4)),
              child: Text(trend, style: const TextStyle(fontSize: 10, color: AppColors.success, fontWeight: FontWeight.w600)),
            ),
          ]),
          const SizedBox(height: 12),
          Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}
