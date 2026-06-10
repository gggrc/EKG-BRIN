// lib/core/mock/mock_data.dart
// Data sintetik untuk prototype/mockup. Semua data adalah fiktif.

import 'dart:math';
import '../models/user_model.dart';
import '../models/patient_model.dart';
import '../models/ecg_models.dart';

class MockData {
  MockData._();

  // === MOCK USERS ===
  static final List<UserModel> users = [
    UserModel(
      userId: 'u-001',
      email: 'budi.pasien@email.com',
      name: 'Budi Santoso',
      role: UserRole.patient,
      patientId: 'p-001',
      phoneNumber: '08123456789',
      createdAt: DateTime(2024, 1, 15),
    ),
    UserModel(
      userId: 'u-002',
      email: 'siti.nakes@rsud.id',
      name: 'Siti Rahayu, Amd.Kep',
      role: UserRole.healthcareWorker,
      institution: 'RSUD Dr. Soetomo Surabaya',
      phoneNumber: '08234567890',
      createdAt: DateTime(2024, 2, 1),
    ),
    UserModel(
      userId: 'u-003',
      email: 'dr.andi@rsud.id',
      name: 'dr. Andi Prasetyo, Sp.JP',
      role: UserRole.doctor,
      specialty: 'Kardiologi',
      institution: 'RSUD Dr. Soetomo Surabaya',
      phoneNumber: '08345678901',
      createdAt: DateTime(2023, 8, 10),
    ),
    UserModel(
      userId: 'u-004',
      email: 'admin.brin@brin.go.id',
      name: 'Peneliti BRIN',
      role: UserRole.admin,
      institution: 'BRIN — Badan Riset dan Inovasi Nasional',
      phoneNumber: '08456789012',
      createdAt: DateTime(2023, 1, 1),
    ),
  ];

  // Demo login presets
  static final Map<UserRole, Map<String, String>> demoCredentials = {
    UserRole.patient: {'email': 'budi.pasien@email.com', 'password': 'demo123'},
    UserRole.healthcareWorker: {
      'email': 'siti.nakes@rsud.id',
      'password': 'demo123'
    },
    UserRole.doctor: {'email': 'dr.andi@rsud.id', 'password': 'demo123'},
    UserRole.admin: {'email': 'admin.brin@brin.go.id', 'password': 'demo123'},
  };

  // === MOCK PATIENTS ===
  static final List<PatientModel> patients = [
    PatientModel(
      patientId: 'p-001',
      fullName: 'Budi Santoso',
      medicalRecordNumber: 'RM-2024-001',
      gender: 'M',
      birthDate: DateTime(1975, 3, 15),
      heightCm: 168,
      weightKg: 72,
      bloodType: 'B+',
      address: 'Jl. Raya Gubeng No. 12, Surabaya',
      phoneNumber: '08123456789',
      nik: '3578010315750001',
      allergies: ['Penisilin'],
      currentMedications: ['Amlodipine 5mg', 'Metformin 500mg'],
      lastEcgDate: DateTime(2026, 6, 5),
      totalEcgSessions: 8,
    ),
    PatientModel(
      patientId: 'p-002',
      fullName: 'Dewi Lestari',
      medicalRecordNumber: 'RM-2024-002',
      gender: 'F',
      birthDate: DateTime(1982, 7, 22),
      heightCm: 157,
      weightKg: 58,
      bloodType: 'A+',
      address: 'Jl. Diponegoro No. 45, Surabaya',
      phoneNumber: '08234567891',
      nik: '3578017207820002',
      allergies: [],
      currentMedications: ['Bisoprolol 5mg'],
      lastEcgDate: DateTime(2026, 6, 3),
      totalEcgSessions: 5,
    ),
    PatientModel(
      patientId: 'p-003',
      fullName: 'Ahmad Fauzi',
      medicalRecordNumber: 'RM-2024-003',
      gender: 'M',
      birthDate: DateTime(1968, 11, 8),
      heightCm: 172,
      weightKg: 85,
      bloodType: 'O+',
      address: 'Jl. Ahmad Yani No. 67, Sidoarjo',
      phoneNumber: '08345678902',
      nik: '3515010811680003',
      allergies: ['Aspirin', 'Sulfa'],
      currentMedications: ['Warfarin 5mg', 'Atorvastatin 20mg', 'Ramipril 5mg'],
      lastEcgDate: DateTime(2026, 6, 7),
      totalEcgSessions: 23,
    ),
    PatientModel(
      patientId: 'p-004',
      fullName: 'Rina Wulandari',
      medicalRecordNumber: 'RM-2025-001',
      gender: 'F',
      birthDate: DateTime(1990, 5, 30),
      heightCm: 160,
      weightKg: 54,
      bloodType: 'AB+',
      address: 'Jl. Pemuda No. 89, Surabaya',
      phoneNumber: '08456789013',
      nik: '3578015305900004',
      allergies: [],
      currentMedications: [],
      lastEcgDate: DateTime(2026, 5, 28),
      totalEcgSessions: 2,
    ),
    PatientModel(
      patientId: 'p-005',
      fullName: 'Hendra Wijaya',
      medicalRecordNumber: 'RM-2025-002',
      gender: 'M',
      birthDate: DateTime(1955, 9, 12),
      heightCm: 165,
      weightKg: 78,
      bloodType: 'B-',
      address: 'Jl. Kertajaya No. 23, Surabaya',
      phoneNumber: '08567890124',
      nik: '3578011209550005',
      allergies: ['Ibuprofen'],
      currentMedications: ['Digoxin 0.25mg', 'Furosemide 40mg', 'Spironolakton 25mg'],
      lastEcgDate: DateTime(2026, 6, 8),
      totalEcgSessions: 41,
    ),
  ];

  // === MOCK ECG SIGNAL GENERATOR ===
  // Menghasilkan sinyal EKG sintetik yang realistis
  // Justifikasi: prototype membutuhkan data sintetik untuk demonstrasi visual
  static List<double> generateEcgSignal({
    int samples = 500,
    double heartRateBpm = 72,
    bool hasNoise = false,
    double amplitude = 1.0,
    String leadType = 'II',
  }) {
    final List<double> signal = [];
    final random = Random(leadType.hashCode);
    final double samplingRate = 500.0;
    final double rrInterval = 60.0 / heartRateBpm * samplingRate;

    // Lead-specific amplitude modifiers
    final Map<String, double> leadAmplitudes = {
      'I': 0.7,
      'II': 1.0,
      'III': 0.5,
      'aVR': -0.8,
      'aVL': 0.4,
      'aVF': 0.9,
      'V1': -0.6,
      'V2': 0.3,
      'V3': 0.8,
      'V4': 1.2,
      'V5': 1.1,
      'V6': 0.9,
    };
    final double leadMod = leadAmplitudes[leadType] ?? 1.0;

    for (int i = 0; i < samples; i++) {
      final double t = (i % rrInterval) / rrInterval;
      double value = 0.0;

      // P wave (atrial depolarization)
      value += amplitude * leadMod * 0.25 * _gaussian(t, 0.1, 0.04);

      // QRS complex (ventricular depolarization)
      // Q wave
      value += amplitude * leadMod * -0.15 * _gaussian(t, 0.25, 0.01);
      // R wave (dominant)
      value += amplitude * leadMod * 1.0 * _gaussian(t, 0.28, 0.015);
      // S wave
      value += amplitude * leadMod * -0.25 * _gaussian(t, 0.32, 0.01);

      // T wave (ventricular repolarization)
      value += amplitude * leadMod * 0.35 * _gaussian(t, 0.55, 0.07);

      // Noise
      if (hasNoise) {
        value += (random.nextDouble() - 0.5) * 0.05;
      }

      signal.add(value);
    }

    return signal;
  }

  static double _gaussian(double x, double mean, double std) {
    return exp(-0.5 * pow((x - mean) / std, 2));
  }

  // === MOCK ECG SESSIONS ===
  static List<EcgSession> get ecgSessions {
    final leadNames12 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
    final leadNames6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF'];

    Map<String, List<double>> generate12LeadSignal(double hr) {
      return {for (var l in leadNames12) l: generateEcgSignal(heartRateBpm: hr, leadType: l)};
    }

    Map<String, List<double>> generate6LeadSignal(double hr) {
      return {for (var l in leadNames6) l: generateEcgSignal(heartRateBpm: hr, leadType: l)};
    }

    return [
      EcgSession(
        sessionId: 's-001',
        patientId: 'p-001',
        patientName: 'Budi Santoso',
        deviceId: 'd-001',
        deviceName: 'Nihon Kohden ECG-2350',
        examinationTime: DateTime(2026, 6, 8, 9, 30),
        durationSec: 10,
        leadConfiguration: LeadConfiguration.twelveLead,
        status: EcgSessionStatus.completed,
        sourceType: SourceType.pdfUpload,
        recordedBy: 'u-002',
        recordedByName: 'Siti Rahayu, Amd.Kep',
        signalData: EcgSignalData(
          signalId: 1,
          sessionId: 's-001',
          leadType: '12-lead',
          samplingRate: 500,
          sampleCount: 5000,
          signalData: generate12LeadSignal(75),
          minVoltageMv: -1.2,
          maxVoltageMv: 1.8,
        ),
        analysis: const EcgAnalysis(
          analysisId: 'a-001',
          sessionId: 's-001',
          heartRateBpm: 75,
          rhythmType: 'Sinus Normal',
          prIntervalMs: 160,
          qrsDurationMs: 90,
          qtIntervalMs: 380,
          qtcIntervalMs: 415,
          electricalAxisDeg: 45,
          aiInterpretation: 'Tidak ditemukan kelainan bermakna. Irama sinus reguler. Interval PR, QRS, dan QT dalam batas normal.',
          doctorDiagnosis: 'EKG normal. Tidak ada indikasi aritmia atau iskemia. Disarankan kontrol rutin.',
          isApproved: true,
          approvedBy: 'dr. Andi Prasetyo, Sp.JP',
        ),
      ),
      EcgSession(
        sessionId: 's-002',
        patientId: 'p-003',
        patientName: 'Ahmad Fauzi',
        deviceId: 'd-002',
        deviceName: 'GE MAC 5500 HD',
        examinationTime: DateTime(2026, 6, 7, 14, 15),
        durationSec: 10,
        leadConfiguration: LeadConfiguration.twelveLead,
        status: EcgSessionStatus.completed,
        sourceType: SourceType.deviceUpload,
        recordedBy: 'u-002',
        recordedByName: 'Siti Rahayu, Amd.Kep',
        signalData: EcgSignalData(
          signalId: 2,
          sessionId: 's-002',
          leadType: '12-lead',
          samplingRate: 500,
          sampleCount: 5000,
          signalData: generate12LeadSignal(110),
          minVoltageMv: -1.5,
          maxVoltageMv: 2.1,
        ),
        analysis: EcgAnalysis(
          analysisId: 'a-002',
          sessionId: 's-002',
          heartRateBpm: 110,
          rhythmType: 'Atrial Fibrilasi',
          prIntervalMs: null,
          qrsDurationMs: 95,
          qtIntervalMs: 340,
          qtcIntervalMs: 448,
          electricalAxisDeg: 75,
          aiInterpretation: 'Terdeteksi irama tidak teratur tanpa gelombang P yang jelas. Konsisten dengan atrial fibrilasi. QTc sedikit memanjang (448ms). Diperlukan evaluasi dokter.',
          doctorDiagnosis: null,
          isApproved: false,
        ),
      ),
      EcgSession(
        sessionId: 's-003',
        patientId: 'p-005',
        patientName: 'Hendra Wijaya',
        deviceId: 'd-001',
        deviceName: 'Nihon Kohden ECG-2350',
        examinationTime: DateTime(2026, 6, 8, 11, 0),
        durationSec: 10,
        leadConfiguration: LeadConfiguration.twelveLead,
        status: EcgSessionStatus.completed,
        sourceType: SourceType.csvUpload,
        recordedBy: 'u-002',
        recordedByName: 'Siti Rahayu, Amd.Kep',
        signalData: EcgSignalData(
          signalId: 3,
          sessionId: 's-003',
          leadType: '12-lead',
          samplingRate: 500,
          sampleCount: 5000,
          signalData: generate12LeadSignal(55),
          minVoltageMv: -0.8,
          maxVoltageMv: 1.5,
        ),
        analysis: const EcgAnalysis(
          analysisId: 'a-003',
          sessionId: 's-003',
          heartRateBpm: 55,
          rhythmType: 'Sinus Bradikardia',
          prIntervalMs: 200,
          qrsDurationMs: 110,
          qtIntervalMs: 440,
          qtcIntervalMs: 422,
          electricalAxisDeg: 30,
          aiInterpretation: 'Irama sinus dengan laju jantung 55 bpm (bradikardia ringan). LBBB (Left Bundle Branch Block) tidak dikesampingkan. Perlu perhatian klinis lebih lanjut.',
          doctorDiagnosis: 'Sinus bradikardia dengan LBBB. Pasien sudah dalam terapi digoxin. Monitor dan evaluasi dosis.',
          isApproved: true,
          approvedBy: 'dr. Andi Prasetyo, Sp.JP',
        ),
      ),
      EcgSession(
        sessionId: 's-004',
        patientId: 'p-002',
        patientName: 'Dewi Lestari',
        deviceId: 'd-003',
        deviceName: 'Philips PageWriter TC70',
        examinationTime: DateTime(2026, 6, 3, 10, 0),
        durationSec: 10,
        leadConfiguration: LeadConfiguration.sixLead,
        status: EcgSessionStatus.completed,
        sourceType: SourceType.imageUpload,
        recordedBy: 'u-002',
        recordedByName: 'Siti Rahayu, Amd.Kep',
        signalData: EcgSignalData(
          signalId: 4,
          sessionId: 's-004',
          leadType: '6-lead',
          samplingRate: 500,
          sampleCount: 5000,
          signalData: generate6LeadSignal(82),
          minVoltageMv: -0.9,
          maxVoltageMv: 1.3,
        ),
        analysis: const EcgAnalysis(
          analysisId: 'a-004',
          sessionId: 's-004',
          heartRateBpm: 82,
          rhythmType: 'Sinus Normal',
          prIntervalMs: 155,
          qrsDurationMs: 88,
          qtIntervalMs: 365,
          qtcIntervalMs: 428,
          electricalAxisDeg: 60,
          aiInterpretation: 'EKG 6-lead menunjukkan irama sinus normal. Tidak ada ST elevation atau depresi bermakna.',
          isApproved: false,
        ),
      ),
      EcgSession(
        sessionId: 's-005',
        patientId: 'p-004',
        patientName: 'Rina Wulandari',
        deviceId: 'd-002',
        deviceName: 'GE MAC 5500 HD',
        examinationTime: DateTime(2026, 5, 28, 8, 45),
        durationSec: 10,
        leadConfiguration: LeadConfiguration.twelveLead,
        status: EcgSessionStatus.processing,
        sourceType: SourceType.pdfUpload,
        recordedBy: 'u-002',
        recordedByName: 'Siti Rahayu, Amd.Kep',
      ),
    ];
  }

  // === MOCK NOTIFICATIONS ===
  static List<NotificationModel> get notifications => [
    NotificationModel(
      notificationId: 'n-001',
      title: 'Hasil EKG Tersedia',
      body: 'Hasil pemeriksaan EKG Anda pada 08 Juni 2026 telah dianalisis. Silakan lihat di Riwayat EKG.',
      type: 'ecg_result',
      isRead: false,
      createdAt: DateTime(2026, 6, 8, 10, 30),
      relatedSessionId: 's-001',
    ),
    NotificationModel(
      notificationId: 'n-002',
      title: 'Diagnosis Memerlukan Perhatian',
      body: 'Pasien Ahmad Fauzi (RM-2024-003) memiliki hasil EKG yang perlu ditinjau. QTc memanjang.',
      type: 'alert',
      isRead: false,
      createdAt: DateTime(2026, 6, 7, 15, 0),
      relatedSessionId: 's-002',
    ),
    NotificationModel(
      notificationId: 'n-003',
      title: 'Diagnosis Disetujui',
      body: 'dr. Andi Prasetyo telah menyetujui diagnosis untuk sesi EKG s-003.',
      type: 'diagnosis',
      isRead: true,
      createdAt: DateTime(2026, 6, 6, 9, 0),
      relatedSessionId: 's-003',
    ),
    NotificationModel(
      notificationId: 'n-004',
      title: 'Sinkronisasi SATUSEHAT',
      body: '3 rekam EKG berhasil dikirim ke SATUSEHAT hari ini.',
      type: 'system',
      isRead: true,
      createdAt: DateTime(2026, 6, 5, 18, 0),
    ),
  ];

  // === MOCK ANALYTICS DATA ===
  static Map<String, dynamic> get analyticsData => {
    'totalPatients': 247,
    'totalSessions': 1283,
    'sessionsThisMonth': 87,
    'avgHeartRate': 74.2,
    'rhythmDistribution': {
      'Sinus Normal': 68,
      'Atrial Fibrilasi': 12,
      'Sinus Bradikardia': 8,
      'Sinus Takikardia': 7,
      'LBBB': 3,
      'Lainnya': 2,
    },
    'leadConfigDistribution': {
      '12-Lead': 73,
      '6-Lead': 27,
    },
    'sourceTypeDistribution': {
      'PDF Upload': 42,
      'Device Upload': 31,
      'CSV Upload': 18,
      'Image Upload': 9,
    },
    'sessionsByMonth': [45, 52, 61, 78, 82, 87],
    'fhirSyncedCount': 1107,
    'pendingDiagnosis': 14,
    'approvedDiagnosis': 1102,
  };

  // === MOCK DEVICES ===
  static final List<Map<String, String>> devices = [
    {'id': 'd-001', 'name': 'Nihon Kohden ECG-2350', 'serial': 'NK-2350-001'},
    {'id': 'd-002', 'name': 'GE MAC 5500 HD', 'serial': 'GE-5500-002'},
    {'id': 'd-003', 'name': 'Philips PageWriter TC70', 'serial': 'PH-TC70-003'},
    {'id': 'd-004', 'name': 'Mortara ELI 280', 'serial': 'MO-280-004'},
  ];

  // === MOCK ALL USERS (for admin) ===
  static List<Map<String, dynamic>> get allUsersList => [
    ...users.map((u) => {
      'user': u,
      'lastLogin': DateTime.now().subtract(Duration(hours: Random().nextInt(48))),
      'isActive': true,
    }),
    {
      'user': UserModel(
        userId: 'u-005',
        email: 'perawat.budi@puskesmas.id',
        name: 'Budi Hermawan, Amd.Kep',
        role: UserRole.healthcareWorker,
        institution: 'Puskesmas Gubeng',
        createdAt: DateTime(2025, 3, 1),
      ),
      'lastLogin': DateTime.now().subtract(const Duration(days: 2)),
      'isActive': true,
    },
    {
      'user': UserModel(
        userId: 'u-006',
        email: 'dr.maya@rs-islam.id',
        name: 'dr. Maya Kusuma, Sp.PD',
        role: UserRole.doctor,
        specialty: 'Penyakit Dalam',
        institution: 'RS Islam Surabaya',
        createdAt: DateTime(2025, 5, 15),
      ),
      'lastLogin': DateTime.now().subtract(const Duration(hours: 3)),
      'isActive': true,
    },
  ];
}
