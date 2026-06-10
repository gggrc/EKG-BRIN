// lib/features/fhir/fhir_export_page.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/models/ecg_models.dart';
import '../../core/providers/data_provider.dart';
import '../../core/providers/auth_provider.dart';

class FhirExportPage extends StatefulWidget {
  const FhirExportPage({super.key});

  @override
  State<FhirExportPage> createState() => _FhirExportPageState();
}

class _FhirExportPageState extends State<FhirExportPage> {
  final List<String> _selectedSessions = [];
  bool _isSyncing = false;

  Future<void> _handleSync() async {
    if (_selectedSessions.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pilih minimal satu sesi EKG untuk disinkronisasi')));
      return;
    }
    setState(() => _isSyncing = true);
    await Future.delayed(const Duration(seconds: 2));
    setState(() => _isSyncing = false);
    if (mounted) {
      final authProvider = context.read<AuthProvider>();
      final user = authProvider.currentUser;

      if (user != null) {
        context.read<DataProvider>().addActivityLog(ActivityLogModel(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          userName: user.name,
          action: 'Sinkronisasi SATUSEHAT',
          target: '${_selectedSessions.length} rekam EKG berhasil dikirim',
          time: DateTime.now(),
          type: 'sync',
        ));
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${_selectedSessions.length} sesi berhasil dikirim ke SATUSEHAT!')),
      );
      setState(() => _selectedSessions.clear());
    }
  }

  @override
  Widget build(BuildContext context) {
    final sessions = context.watch<DataProvider>().ecgSessions.where((s) => s.status == EcgSessionStatus.completed).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header info
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [AppColors.primary.withOpacity(0.15), AppColors.secondary.withOpacity(0.1)]),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.primary.withOpacity(0.2)),
            ),
            child: Row(
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(children: [
                      Icon(Icons.verified_rounded, color: AppColors.primary, size: 18),
                      SizedBox(width: 8),
                      Text('SATUSEHAT — HL7 FHIR R4', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                    ]),
                    const SizedBox(height: 4),
                    const Text('Platform integrasi data kesehatan nasional Kemenkes RI', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                  ],
                ),
                const Spacer(),
                _StatPill(label: 'Sudah Tersinkron', value: '1.107', color: AppColors.success),
                const SizedBox(width: 16),
                _StatPill(label: 'Belum Tersinkron', value: '${sessions.where((s) => true).length}', color: AppColors.warning),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Session table
              Expanded(
                flex: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text('Pilih Sesi untuk Diekspor', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                        const Spacer(),
                        TextButton.icon(
                          onPressed: () {
                            setState(() {
                              if (_selectedSessions.length == sessions.length) {
                                _selectedSessions.clear();
                              } else {
                                _selectedSessions.clear();
                                _selectedSessions.addAll(sessions.map((s) => s.sessionId));
                              }
                            });
                          },
                          icon: const Icon(Icons.select_all_rounded, size: 16),
                          label: Text(_selectedSessions.length == sessions.length ? 'Batal Pilih Semua' : 'Pilih Semua'),
                        ),
                        const SizedBox(width: 12),
                        ElevatedButton.icon(
                          onPressed: _isSyncing ? null : _handleSync,
                          icon: _isSyncing
                              ? const SizedBox(height: 14, width: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.cloud_sync_rounded, size: 16),
                          label: Text(_isSyncing ? 'Mengirim...' : 'Kirim ke SATUSEHAT (${_selectedSessions.length})'),
                          style: ElevatedButton.styleFrom(backgroundColor: AppColors.secondary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    ...sessions.map((s) {
                      final isSelected = _selectedSessions.contains(s.sessionId);
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: isSelected ? AppColors.primary.withOpacity(0.06) : AppColors.surface,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: isSelected ? AppColors.primary.withOpacity(0.4) : AppColors.borderLight),
                        ),
                        child: Row(
                          children: [
                            Checkbox(
                              value: isSelected,
                              onChanged: (v) => setState(() {
                                if (v == true) _selectedSessions.add(s.sessionId);
                                else _selectedSessions.remove(s.sessionId);
                              }),
                              activeColor: AppColors.primary,
                            ),
                            const SizedBox(width: 8),
                            Expanded(child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(s.patientName, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                                Text('${s.leadConfigDisplay} • ${s.deviceName} • ${s.examinationTime.day}/${s.examinationTime.month}/${s.examinationTime.year}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                              ],
                            )),
                            const SizedBox(width: 12),
                            if (s.analysis?.isApproved == true)
                              const Row(children: [
                                Icon(Icons.check_circle_rounded, color: AppColors.success, size: 14),
                                SizedBox(width: 4),
                                Text('Disetujui', style: TextStyle(fontSize: 11, color: AppColors.success)),
                              ])
                            else
                              const Text('Draft', style: TextStyle(fontSize: 11, color: AppColors.warning)),
                            const SizedBox(width: 16),
                            // FHIR Resource preview
                            TextButton(
                              onPressed: () => _showFhirJson(context, s.sessionId),
                              child: const Text('Lihat FHIR JSON', style: TextStyle(fontSize: 11)),
                            ),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
              const SizedBox(width: 24),
              // FHIR info sidebar
              SizedBox(
                width: 280,
                child: Column(
                  children: [
                    _FhirInfoCard(),
                    const SizedBox(height: 16),
                    _SyncHistoryCard(),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showFhirJson(BuildContext context, String sessionId) {
    showDialog(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Container(
          width: 600,
          height: 500,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('FHIR Observation Resource', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.pop(dialogContext), icon: const Icon(Icons.close_rounded)),
                ],
              ),
              const Divider(color: AppColors.borderLight),
              Expanded(
                child: SingleChildScrollView(
                  child: Text(
                    _generateFhirJson(sessionId),
                    style: const TextStyle(fontSize: 11, color: AppColors.success, fontFamily: 'monospace', height: 1.6),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _generateFhirJson(String sessionId) {
    return '''{
  "resourceType": "Observation",
  "id": "$sessionId",
  "status": "final",
  "category": [{
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/observation-category",
      "code": "procedure",
      "display": "Procedure"
    }]
  }],
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "11524-6",
      "display": "EKG study"
    }]
  },
  "subject": {
    "reference": "Patient/p-001",
    "display": "Budi Santoso"
  },
  "effectiveDateTime": "2026-06-08T09:30:00+07:00",
  "device": {
    "display": "Nihon Kohden ECG-2350"
  },
  "component": [
    {
      "code": {
        "coding": [{
          "system": "http://loinc.org",
          "code": "8867-4",
          "display": "Heart rate"
        }]
      },
      "valueQuantity": {
        "value": 75,
        "unit": "beats/min",
        "system": "http://unitsofmeasure.org",
        "code": "/min"
      }
    },
    {
      "code": {
        "coding": [{
          "system": "http://loinc.org",
          "code": "8625-6",
          "display": "P-R interval"
        }]
      },
      "valueQuantity": {
        "value": 160,
        "unit": "ms",
        "system": "http://unitsofmeasure.org",
        "code": "ms"
      }
    }
  ]
}''';
  }
}

class _StatPill extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _StatPill({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: color)),
        Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
      ],
    );
  }
}

class _FhirInfoCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Tentang HL7 FHIR Export', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 12),
          const Text(
            'Data EKG akan diformat sebagai FHIR Observation resource (LOINC 11524-6: EKG study) dan dikirim ke endpoint SATUSEHAT.',
            style: TextStyle(fontSize: 12, color: AppColors.textMuted, height: 1.6),
          ),
          const SizedBox(height: 12),
          const _InfoItem(label: 'Standard', value: 'HL7 FHIR R4'),
          const _InfoItem(label: 'Resource', value: 'Observation'),
          const _InfoItem(label: 'LOINC Code', value: '11524-6'),
          const _InfoItem(label: 'Platform', value: 'SATUSEHAT Kemenkes'),
          const _InfoItem(label: 'Format', value: 'JSON / XML'),
        ],
      ),
    );
  }
}

class _SyncHistoryCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final history = [
      {'date': '08/06/2026', 'count': '3', 'status': 'success'},
      {'date': '07/06/2026', 'count': '5', 'status': 'success'},
      {'date': '06/06/2026', 'count': '2', 'status': 'failed'},
      {'date': '05/06/2026', 'count': '8', 'status': 'success'},
    ];

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.borderLight)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Riwayat Sinkronisasi', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
          const SizedBox(height: 12),
          ...history.map((h) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Row(
              children: [
                Icon(h['status'] == 'success' ? Icons.check_circle_rounded : Icons.error_rounded,
                    size: 14, color: h['status'] == 'success' ? AppColors.success : AppColors.danger),
                const SizedBox(width: 8),
                Text(h['date']!, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                const Spacer(),
                Text('${h['count']} sesi', style: const TextStyle(fontSize: 12, color: AppColors.textPrimary, fontWeight: FontWeight.w500)),
              ],
            ),
          )),
        ],
      ),
    );
  }
}

class _InfoItem extends StatelessWidget {
  final String label;
  final String value;
  const _InfoItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
          Text(value, style: const TextStyle(fontSize: 11, color: AppColors.primary, fontWeight: FontWeight.w600, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}
