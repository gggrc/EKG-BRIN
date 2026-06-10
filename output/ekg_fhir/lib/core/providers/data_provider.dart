import 'package:flutter/material.dart';
import '../models/patient_model.dart';
import '../models/ecg_models.dart';
import '../mock/mock_data.dart';

class DataProvider extends ChangeNotifier {
  final List<PatientModel> _patients = List.from(MockData.patients);
  final List<EcgSession> _ecgSessions = List.from(MockData.ecgSessions);
  final List<NotificationModel> _notifications = List.from(MockData.notifications);
  final List<ActivityLogModel> _activityLogs = [
    ActivityLogModel(id: '1', userName: 'dr. Andi Prasetyo, Sp.JP', action: 'Menyetujui diagnosis', target: 'Sesi s-001 (Budi Santoso)', time: DateTime.parse('2026-06-08 10:45:00'), type: 'approve'),
    ActivityLogModel(id: '2', userName: 'Siti Rahayu, Amd.Kep', action: 'Upload EKG baru', target: 'Hendra Wijaya (RM-2025-002)', time: DateTime.parse('2026-06-08 11:00:00'), type: 'upload'),
    ActivityLogModel(id: '3', userName: 'System', action: 'Sinkronisasi SATUSEHAT', target: '3 rekam EKG berhasil dikirim', time: DateTime.parse('2026-06-08 06:00:00'), type: 'sync'),
    ActivityLogModel(id: '4', userName: 'Peneliti BRIN', action: 'Export dataset', target: '247 rekam EKG (Jan-Jun 2026)', time: DateTime.parse('2026-06-07 17:30:00'), type: 'export'),
  ];

  List<PatientModel> get patients => List.unmodifiable(_patients);
  List<EcgSession> get ecgSessions => List.unmodifiable(_ecgSessions);
  List<NotificationModel> get notifications => List.unmodifiable(_notifications);
  List<ActivityLogModel> get activityLogs => List.unmodifiable(_activityLogs);

  Map<String, dynamic> get analytics {
    final pendingCount = _ecgSessions.where((s) => s.status == EcgSessionStatus.pending).length;
    return {
      ...MockData.analyticsData,
      'totalPatients': _patients.length,
      'sessionsThisMonth': _ecgSessions.length,
      'pendingApprovals': pendingCount,
    };
  }

  void addPatient(PatientModel patient) {
    _patients.insert(0, patient);
    notifyListeners();
  }

  void updatePatient(PatientModel patient) {
    final index = _patients.indexWhere((p) => p.patientId == patient.patientId);
    if (index != -1) {
      _patients[index] = patient;
      notifyListeners();
    }
  }

  void addEcgSession(EcgSession session) {
    _ecgSessions.insert(0, session);
    notifyListeners();
  }

  void updateDiagnosis(String sessionId, String diagnosis, bool isApproved) {
    final index = _ecgSessions.indexWhere((s) => s.sessionId == sessionId);
    if (index != -1) {
      final session = _ecgSessions[index];
      
      EcgAnalysis newAnalysis;
      if (session.analysis != null) {
        newAnalysis = session.analysis!.copyWith(
          doctorDiagnosis: diagnosis,
          isApproved: isApproved,
          approvedAt: isApproved ? DateTime.now() : null,
        );
      } else {
        newAnalysis = EcgAnalysis(
          analysisId: 'a-${DateTime.now().millisecondsSinceEpoch}',
          sessionId: session.sessionId,
          doctorDiagnosis: diagnosis,
          isApproved: isApproved,
          approvedAt: isApproved ? DateTime.now() : null,
        );
      }

      _ecgSessions[index] = session.copyWith(
        analysis: newAnalysis,
        status: isApproved ? EcgSessionStatus.completed : EcgSessionStatus.pending,
      );
      
      notifyListeners();
    }
  }

  void markAllNotificationsAsRead(String userId) {
    for (var i = 0; i < _notifications.length; i++) {
      if (!_notifications[i].isRead) {
        _notifications[i] = _notifications[i].copyWith(isRead: true);
      }
    }
    notifyListeners();
  }

  void markNotificationAsRead(String notificationId) {
    final index = _notifications.indexWhere((n) => n.notificationId == notificationId);
    if (index != -1 && !_notifications[index].isRead) {
      _notifications[index] = _notifications[index].copyWith(isRead: true);
      notifyListeners();
    }
  }

  void addActivityLog(ActivityLogModel log) {
    _activityLogs.insert(0, log);
    notifyListeners();
  }
}
