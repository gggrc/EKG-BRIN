// lib/core/models/ecg_models.dart

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

  const NotificationModel({
    required this.notificationId,
    required this.title,
    required this.body,
    required this.type,
    required this.isRead,
    required this.createdAt,
    this.relatedSessionId,
  });
}
