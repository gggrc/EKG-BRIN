// lib/core/models/user_model.dart

enum UserRole {
  patient,
  healthcareWorker,
  doctor,
  admin,
}

extension UserRoleExtension on UserRole {
  String get displayName {
    switch (this) {
      case UserRole.patient:
        return 'Pasien';
      case UserRole.healthcareWorker:
        return 'Tenaga Kesehatan';
      case UserRole.doctor:
        return 'Dokter / Spesialis';
      case UserRole.admin:
        return 'Admin / Peneliti';
    }
  }

  String get shortName {
    switch (this) {
      case UserRole.patient:
        return 'Pasien';
      case UserRole.healthcareWorker:
        return 'Nakes';
      case UserRole.doctor:
        return 'Dokter';
      case UserRole.admin:
        return 'Admin';
    }
  }

  String get icon {
    switch (this) {
      case UserRole.patient:
        return '🧑‍💼';
      case UserRole.healthcareWorker:
        return '👩‍⚕️';
      case UserRole.doctor:
        return '🩺';
      case UserRole.admin:
        return '🔧';
    }
  }
}

class UserModel {
  final String userId;
  final String email;
  final String name;
  final UserRole role;
  final String? patientId;
  final String? specialty; // for doctors
  final String? institution;
  final String? phoneNumber;
  final String? avatarUrl;
  final DateTime createdAt;
  final bool isActive;

  const UserModel({
    required this.userId,
    required this.email,
    required this.name,
    required this.role,
    this.patientId,
    this.specialty,
    this.institution,
    this.phoneNumber,
    this.avatarUrl,
    required this.createdAt,
    this.isActive = true,
  });

  bool get canViewAllPatients =>
      role == UserRole.healthcareWorker ||
      role == UserRole.doctor ||
      role == UserRole.admin;

  bool get canInputPatient =>
      role == UserRole.healthcareWorker || role == UserRole.doctor;

  bool get canAcquireSignal =>
      role == UserRole.healthcareWorker || role == UserRole.doctor;

  bool get canWriteDiagnosis => role == UserRole.doctor;

  bool get canApproveDiagnosis => role == UserRole.doctor;

  bool get canExportFHIR =>
      role == UserRole.doctor || role == UserRole.admin;

  bool get canAccessAdmin => role == UserRole.admin;

  bool get canViewAIInterpretation => role == UserRole.doctor;

  bool get canExportDataset => role == UserRole.admin;

  UserModel copyWith({
    String? name,
    String? email,
    String? specialty,
    String? institution,
    String? phoneNumber,
    String? avatarUrl,
  }) {
    return UserModel(
      userId: userId,
      email: email ?? this.email,
      name: name ?? this.name,
      role: role,
      patientId: patientId,
      specialty: specialty ?? this.specialty,
      institution: institution ?? this.institution,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      createdAt: createdAt,
      isActive: isActive,
    );
  }
}
