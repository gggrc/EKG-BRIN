// lib/core/models/ecg_models.dart

import 'user_model.dart';


enum LeadConfiguration { sixLead, twelveLead }

enum EcgSessionStatus { pending, processing, completed, error }

enum SourceType { deviceUpload, imageUpload, pdfUpload, csvUpload, manual }

class EcgSession {
  final String sessionId;
  final String patientId;
  final String patientName;
  final String deviceId;
  final String deviceName;
  final DateTime examinationTime;
  final int durationSec;
  final LeadConfiguration leadConfiguration;
  final EcgSessionStatus status;
  final SourceType sourceType;
  final EcgSignalData? signalData;
  final EcgAnalysis? analysis;
  final String? recordedBy; // userId of nakes/dokter
  final String? recordedByName;

  const EcgSession({
    required this.sessionId,
    required this.patientId,
    required this.patientName,
    required this.deviceId,
    required this.deviceName,
    required this.examinationTime,
    required this.durationSec,
    required this.leadConfiguration,
    required this.status,
    required this.sourceType,
    this.signalData,
    this.analysis,
    this.recordedBy,
    this.recordedByName,
  });

  String get leadConfigDisplay =>
      leadConfiguration == LeadConfiguration.sixLead ? '6-Lead' : '12-Lead';

  String get statusDisplay {
    switch (status) {
      case EcgSessionStatus.pending:
        return 'Menunggu';
      case EcgSessionStatus.processing:
        return 'Diproses';
      case EcgSessionStatus.completed:
        return 'Selesai';
      case EcgSessionStatus.error:
        return 'Error';
    }
  }

  EcgSession copyWith({
    String? sessionId,
    String? patientId,
    String? patientName,
    String? deviceId,
    String? deviceName,
    DateTime? examinationTime,
    int? durationSec,
    LeadConfiguration? leadConfiguration,
    EcgSessionStatus? status,
    SourceType? sourceType,
    EcgSignalData? signalData,
    EcgAnalysis? analysis,
    String? recordedBy,
    String? recordedByName,
  }) {
    return EcgSession(
      sessionId: sessionId ?? this.sessionId,
      patientId: patientId ?? this.patientId,
      patientName: patientName ?? this.patientName,
      deviceId: deviceId ?? this.deviceId,
      deviceName: deviceName ?? this.deviceName,
      examinationTime: examinationTime ?? this.examinationTime,
      durationSec: durationSec ?? this.durationSec,
      leadConfiguration: leadConfiguration ?? this.leadConfiguration,
      status: status ?? this.status,
      sourceType: sourceType ?? this.sourceType,
      signalData: signalData ?? this.signalData,
      analysis: analysis ?? this.analysis,
      recordedBy: recordedBy ?? this.recordedBy,
      recordedByName: recordedByName ?? this.recordedByName,
    );
  }
}

class EcgSignalData {
  final int signalId;
  final String sessionId;
  final String leadType;
  final int samplingRate;
  final int sampleCount;
  // signal_data: Map<leadName, List<double>>
  // e.g. {'I': [...], 'II': [...], 'III': [...], ...}
  final Map<String, List<double>> signalData;
  final double? minVoltageMv;
  final double? maxVoltageMv;

  const EcgSignalData({
    required this.signalId,
    required this.sessionId,
    required this.leadType,
    required this.samplingRate,
    required this.sampleCount,
    required this.signalData,
    this.minVoltageMv,
    this.maxVoltageMv,
  });

  List<String> get availableLeads => signalData.keys.toList();
}

class EcgAnalysis {
  final String analysisId;
  final String sessionId;
  final int? heartRateBpm;
  final String? rhythmType;
  final double? prIntervalMs;
  final double? qrsDurationMs;
  final double? qtIntervalMs;
  final double? qtcIntervalMs;
  final double? electricalAxisDeg;
  final String? aiInterpretation;
  final String? doctorDiagnosis;
  final bool? isApproved;
  final String? approvedBy;
  final DateTime? approvedAt;

  const EcgAnalysis({
    required this.analysisId,
    required this.sessionId,
    this.heartRateBpm,
    this.rhythmType,
    this.prIntervalMs,
    this.qrsDurationMs,
    this.qtIntervalMs,
    this.qtcIntervalMs,
    this.electricalAxisDeg,
    this.aiInterpretation,
    this.doctorDiagnosis,
    this.isApproved,
    this.approvedBy,
    this.approvedAt,
  });

  String get heartRateCategory {
    if (heartRateBpm == null) return 'Tidak diketahui';
    if (heartRateBpm! < 60) return 'Bradikardia';
    if (heartRateBpm! > 100) return 'Takikardia';
    return 'Normal';
  }

  bool get isHeartRateNormal =>
      heartRateBpm != null && heartRateBpm! >= 60 && heartRateBpm! <= 100;

  bool get isQtcNormal =>
      qtcIntervalMs != null && qtcIntervalMs! >= 350 && qtcIntervalMs! <= 440;

  EcgAnalysis copyWith({
    String? analysisId,
    String? sessionId,
    int? heartRateBpm,
    String? rhythmType,
    double? prIntervalMs,
    double? qrsDurationMs,
    double? qtIntervalMs,
    double? qtcIntervalMs,
    double? electricalAxisDeg,
    String? aiInterpretation,
    String? doctorDiagnosis,
    bool? isApproved,
    String? approvedBy,
    DateTime? approvedAt,
  }) {
    return EcgAnalysis(
      analysisId: analysisId ?? this.analysisId,
      sessionId: sessionId ?? this.sessionId,
      heartRateBpm: heartRateBpm ?? this.heartRateBpm,
      rhythmType: rhythmType ?? this.rhythmType,
      prIntervalMs: prIntervalMs ?? this.prIntervalMs,
      qrsDurationMs: qrsDurationMs ?? this.qrsDurationMs,
      qtIntervalMs: qtIntervalMs ?? this.qtIntervalMs,
      qtcIntervalMs: qtcIntervalMs ?? this.qtcIntervalMs,
      electricalAxisDeg: electricalAxisDeg ?? this.electricalAxisDeg,
      aiInterpretation: aiInterpretation ?? this.aiInterpretation,
      doctorDiagnosis: doctorDiagnosis ?? this.doctorDiagnosis,
      isApproved: isApproved ?? this.isApproved,
      approvedBy: approvedBy ?? this.approvedBy,
      approvedAt: approvedAt ?? this.approvedAt,
    );
  }
}

class FhirExportStatus {
  final String exportId;
  final String sessionId;
  final DateTime exportedAt;
  final String status; // 'success', 'failed', 'pending'
  final String? fhirResourceId;
  final String? errorMessage;

  const FhirExportStatus({
    required this.exportId,
    required this.sessionId,
    required this.exportedAt,
    required this.status,
    this.fhirResourceId,
    this.errorMessage,
  });
}

class NotificationModel {
  final String notificationId;
  final String title;
  final String body;
  final String type; // 'ecg_result', 'diagnosis', 'system', 'alert'
  final bool isRead;
  final DateTime createdAt;
  final String? relatedSessionId;

  // Security: role-based filtering
  // targetRoles: null = semua role, jika diisi = hanya role tersebut yang melihat
  final List<UserRole>? targetRoles;
  // targetPatientId: jika diisi, hanya pasien dengan patientId ini yang melihat
  final String? targetPatientId;

  const NotificationModel({
    required this.notificationId,
    required this.title,
    required this.body,
    required this.type,
    required this.isRead,
    required this.createdAt,
    this.relatedSessionId,
    this.targetRoles,
    this.targetPatientId,
  });

  /// Cek apakah notifikasi ini relevan untuk user tertentu
  bool isVisibleTo(UserModel user) {
    // Pasien hanya boleh lihat notif yang ditujukan ke patientId mereka
    if (user.role == UserRole.patient) {
      if (targetPatientId != null) {
        return targetPatientId == user.patientId;
      }
      // Jika tidak ada targetPatientId, pasien tidak boleh melihat notif klinis
      return false;
    }
    // Untuk non-pasien: cek targetRoles
    // Jika targetPatientId terisi, ini KHUSUS untuk pasien tersebut, jadi non-pasien tidak boleh melihatnya
    if (targetPatientId != null) {
      return false;
    }
    
    if (targetRoles != null) {
      return targetRoles!.contains(user.role);
    }
    // Jika targetRoles null dan targetPatientId null = visible untuk semua (non-patient)
    return true;
  }

  NotificationModel copyWith({
    String? notificationId,
    String? title,
    String? body,
    String? type,
    bool? isRead,
    DateTime? createdAt,
    String? relatedSessionId,
    List<UserRole>? targetRoles,
    String? targetPatientId,
  }) {
    return NotificationModel(
      notificationId: notificationId ?? this.notificationId,
      title: title ?? this.title,
      body: body ?? this.body,
      type: type ?? this.type,
      isRead: isRead ?? this.isRead,
      createdAt: createdAt ?? this.createdAt,
      relatedSessionId: relatedSessionId ?? this.relatedSessionId,
      targetRoles: targetRoles ?? this.targetRoles,
      targetPatientId: targetPatientId ?? this.targetPatientId,
    );
  }
}

class ActivityLogModel {
  final String id;
  final String userName;
  final String action;
  final String target;
  final DateTime time;
  final String type; // 'approve', 'upload', 'sync', 'export', 'user', 'system'

  const ActivityLogModel({
    required this.id,
    required this.userName,
    required this.action,
    required this.target,
    required this.time,
    required this.type,
  });
}
