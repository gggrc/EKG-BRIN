// lib/features/history/history_page.dart
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:intl/intl.dart';
import 'package:intl/date_symbol_data_local.dart'; 
import 'package:dio/dio.dart';

import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/models/user_model.dart';
import '../ecg_viewer/ecg_viewer_page.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  final _supabase = Supabase.instance.client;
  late Future<List<Map<String, dynamic>>> _historyFuture;
  String _searchQuery = ''; // Filter pencarian Daftar Pasien Utama
  String _sessionSearchQuery = ''; // Filter MURNI berdasarkan tanggal folder sesi rekam medis
  bool _isLocaleInitialized = false;

  Map<String, dynamic>? _selectedPatient;

  @override
  void initState() {
    super.initState();
    _initializeLocaleAndFetch();
  }

  Future<void> _initializeLocaleAndFetch() async {
    try {
      await initializeDateFormatting('id_ID', null);
      if (mounted) {
        setState(() {
          _isLocaleInitialized = true;
        });
      }
    } catch (e) {
      debugPrint('Gagal menginisialisasi date formatting: $e');
    }
    _fetchHistoryData();
  }

  void _fetchHistoryData() {
    final user = context.read<AuthProvider>().currentUser;

    var query = _supabase.from('patients').select('''
      patient_id,
      full_name,
      medical_record_number,
      gender,
      birth_date,
      height_cm,
      weight_kg,
      ecg_sessions (
        session_id,
        examination_time,
        duration_sec,
        lead_configuration,
        status,
        source_type,
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
          signal_data,
          min_voltage_mv,
          max_voltage_mv
        )
      )
    ''');

    if (user?.role == UserRole.patient) {
      query = query.eq('user_id', user!.userId);
    }

    setState(() {
      _historyFuture = query.then((response) {
        final List data = response as List;
        return data.map((e) => e as Map<String, dynamic>).toList();
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_isLocaleInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_selectedPatient != null) {
      return _buildPatientSessionsDetailPage(_selectedPatient!);
    }

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 450),
                  child: TextField(
                    onChanged: (v) => setState(() => _searchQuery = v.toLowerCase()),
                    decoration: const InputDecoration(
                      hintText: 'Cari nama pasien atau nomor rekam medis...',
                      prefixIcon: Icon(Icons.search, size: 18),
                      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              IconButton(
                onPressed: _fetchHistoryData,
                icon: const Icon(Icons.refresh_rounded),
                tooltip: 'Refresh Riwayat',
              ),
            ],
          ),
          const SizedBox(height: 24),
          const Text(
            'Daftar Pasien Rekam Medis',
            style: TextStyle(fontSize: 16, color: AppColors.textPrimary, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),

          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              future: _historyFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: Text(
                      'Gagal memuat database: ${snapshot.error}',
                      style: const TextStyle(color: AppColors.danger),
                    ),
                  );
                }

                final rawPatients = snapshot.data ?? [];
                final filteredPatients = rawPatients.where((p) {
                  final name = (p['full_name'] ?? '').toString().toLowerCase();
                  final rm = (p['medical_record_number'] ?? '').toString().toLowerCase();
                  return name.contains(_searchQuery) || rm.contains(_searchQuery);
                }).toList();

                if (filteredPatients.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.people_outline_rounded, size: 48, color: AppColors.textMuted.withOpacity(0.4)),
                        const SizedBox(height: 12),
                        const Text('Tidak ada pasien rekam medis ditemukan.', style: TextStyle(color: AppColors.textSecondary)),
                      ],
                    ),
                  );
                }

                return GridView.builder(
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 320,
                    mainAxisSpacing: 16,
                    crossAxisSpacing: 16,
                    mainAxisExtent: 160,
                  ),
                  itemCount: filteredPatients.length,
                  itemBuilder: (context, index) {
                    final patient = filteredPatients[index];
                    final String fullName = patient['full_name'] ?? 'Tidak diketahui';
                    final String mrn = patient['medical_record_number'] ?? '-';
                    final List sessions = patient['ecg_sessions'] ?? [];

                    return InkWell(
                      onTap: () {
                        setState(() {
                          _selectedPatient = patient;
                          _sessionSearchQuery = ''; // Reset keyword pencarian tanggal ketika berganti pasien
                        });
                      },
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.borderLight, width: 1.2),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: AppColors.primary.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Icon(Icons.assignment_ind_rounded, color: AppColors.primary, size: 20),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        fullName,
                                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        'RM: $mrn',
                                        style: const TextStyle(fontSize: 11, color: AppColors.textMuted, fontFamily: 'monospace'),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppColors.secondary.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    '${sessions.length} EKG Sesi',
                                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.secondary),
                                  ),
                                ),
                                const Icon(Icons.arrow_forward_rounded, size: 16, color: AppColors.textMuted),
                              ],
                            )
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  /// SUB-HALAMAN: Detail Sesi Kotak-Kotak Pasien Berdasarkan Tanggal
  Widget _buildPatientSessionsDetailPage(Map<String, dynamic> patient) {
    final String fullName = patient['full_name'] ?? '';
    final String mrn = patient['medical_record_number'] ?? '';
    final List allSessions = List.from(patient['ecg_sessions'] ?? []);

    // Urutkan sesi: Pemeriksaan terbaru berada di urutan paling awal
    allSessions.sort((a, b) => DateTime.parse(b['examination_time']).compareTo(DateTime.parse(a['examination_time'])));

    // LOGIKA FILTER DIPERBAIKI: HANYA menyaring berdasarkan string tanggal utama ("dd MMMM yyyy")
    final filteredSessions = allSessions.where((session) {
      if (_sessionSearchQuery.isEmpty) return true;
      
      final DateTime examTime = DateTime.parse(session['examination_time']);
      // Ekstraksi string tanggal murni tanpa menyertakan jam, teks diagnosis, ataupun status di dalam card
      final String formattedDateOnly = DateFormat('dd MMMM yyyy', 'id_ID').format(examTime).toLowerCase();
      
      return formattedDateOnly.contains(_sessionSearchQuery);
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextButton.icon(
            onPressed: () {
              setState(() {
                _selectedPatient = null;
              });
            },
            icon: const Icon(Icons.arrow_back_rounded, size: 18),
            label: const Text('Kembali ke Daftar Pasien'),
            style: TextButton.styleFrom(foregroundColor: AppColors.textSecondary, padding: EdgeInsets.zero),
          ),
          const SizedBox(height: 16),

          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant.withOpacity(0.4),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.borderLight),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(fullName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
                const SizedBox(height: 4),
                Text(
                  'No. Rekam Medis: $mrn • Gender: ${patient['gender'] ?? "-"}',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontFamily: 'monospace'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Kotak Sesi Riwayat Pemeriksaan EKG Pasien',
                style: TextStyle(fontSize: 14, color: AppColors.textPrimary, fontWeight: FontWeight.bold),
              ),
              // Search Bar untuk filter pencarian tanggal rekam medis murni di dalam kotak merah
              SizedBox(
                width: 320,
                height: 40,
                child: TextField(
                  onChanged: (value) {
                    setState(() {
                      _sessionSearchQuery = value.toLowerCase().trim();
                    });
                  },
                  style: const TextStyle(fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Cari tanggal murni (cth: 14 Juni 2026)...',
                    prefixIcon: const Icon(Icons.calendar_today_rounded, size: 14),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppColors.primary, width: 1.2),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppColors.borderLight, width: 1.2),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          Expanded(
            child: filteredSessions.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.folder_off_rounded, size: 44, color: AppColors.textMuted.withOpacity(0.5)),
                        const SizedBox(height: 8),
                        Text(
                          _sessionSearchQuery.isEmpty 
                              ? 'Pasien ini belum memiliki riwayat sesi pemeriksaan EKG.'
                              : 'Tidak ada riwayat rekam medis pada tanggal tersebut.',
                          style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                        ),
                      ],
                    ),
                  )
                : GridView.builder(
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 280,
                      mainAxisSpacing: 16,
                      crossAxisSpacing: 16,
                      mainAxisExtent: 175, 
                    ),
                    itemCount: filteredSessions.length,
                    itemBuilder: (context, index) {
                      final session = filteredSessions[index];
                      final String sessionId = session['session_id'];
                      final DateTime examTime = DateTime.parse(session['examination_time']);
                      final String leadConfig = session['lead_configuration'] ?? '12-Lead';
                      final String status = session['status'] ?? 'completed';

                      Map<String, dynamic>? analysisMap;
                      final rawAnalysis = session['ecg_analysis'];
                      if (rawAnalysis is List && rawAnalysis.isNotEmpty) {
                        analysisMap = rawAnalysis.first as Map<String, dynamic>?;
                      } else if (rawAnalysis is Map<String, dynamic>) {
                        analysisMap = rawAnalysis;
                      }

                      final String diagnosisText = analysisMap?['diagnosis'] ?? analysisMap?['rhythm_type'] ?? 'Belum ada diagnosis';

                      final String formattedDate = DateFormat('dd MMMM yyyy', 'id_ID').format(examTime);
                      final String formattedTime = DateFormat('HH:mm WIB', 'id_ID').format(examTime);

                      return InkWell(
                        onTap: () {
                          // Klik kotak langsung membuka Halaman EcgViewerPage dari riwayat rekam medis
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => Scaffold(
                                appBar: AppBar(
                                  title: const Text('Sinyal Monitor Viewer EKG'),
                                  backgroundColor: AppColors.surface,
                                  foregroundColor: AppColors.textPrimary,
                                  elevation: 0.5,
                                ),
                                body: EcgViewerPage(sessionId: sessionId),
                              ),
                            ),
                          );
                        },
                        borderRadius: BorderRadius.circular(12),
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.surface,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppColors.borderLight, width: 1.2),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.folder_special_rounded, color: AppColors.warning, size: 22),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      formattedDate,
                                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ],
                              ),
                              
                              // Kotak Ringkasan Diagnosis Medis Pasien
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                                decoration: BoxDecoration(
                                  color: analysisMap?['diagnosis'] != null 
                                      ? AppColors.successContainer.withOpacity(0.4)
                                      : AppColors.surfaceVariant,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  'Dx: $diagnosisText',
                                  style: TextStyle(
                                    fontSize: 11, 
                                    fontWeight: FontWeight.w500,
                                    color: analysisMap?['diagnosis'] != null 
                                        ? AppColors.success
                                        : AppColors.textSecondary,
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),

                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Waktu: $formattedTime',
                                    style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Config: $leadConfig • Status: $status',
                                    style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              )
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}