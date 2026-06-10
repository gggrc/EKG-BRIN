// lib/core/models/user_model.dart
// Justifikasi role unification: dalam praktik klinis Indonesia, perawat (Amd.Kep)
// dan dokter sama-sama berhak melakukan rekam EKG, input data pasien, dan
// memberikan catatan klinis. Pemisahan role tidak diperlukan untuk prototype ini.

enum UserRole {
  patient,
  clinician, // Mencakup: Perawat, Dokter, Bidan, Dokter Spesialis
  admin,
}

extension UserRoleExtension on UserRole {
  String get displayName {
    switch (this) {
      case UserRole.patient:
        return 'Pasien';
      case UserRole.clinician:
        return 'Tenaga Medis / Klinisi';
      case UserRole.admin:
        return 'Admin / Peneliti';
    }
  }

  String get shortName {
    switch (this) {
      case UserRole.patient:
        return 'Pasien';
      case UserRole.clinician:
        return 'Klinisi';
      case UserRole.admin:
        return 'Admin';
    }
  }

  String get icon {
    switch (this) {
      case UserRole.patient:
        return '🧑‍💼';
      case UserRole.clinician:
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
  final String? specialty; // for clinicians (e.g. "Kardiologi", "Penyakit Dalam")
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
      role == UserRole.clinician || role == UserRole.admin;

  bool get canInputPatient => role == UserRole.clinician;

  bool get canAcquireSignal => role == UserRole.clinician;

  bool get canWriteDiagnosis => role == UserRole.clinician;

  bool get canApproveDiagnosis => role == UserRole.clinician;

  bool get canExportFHIR =>
      role == UserRole.clinician || role == UserRole.admin;

  bool get canAccessAdmin => role == UserRole.admin;

  bool get canViewAIInterpretation =>
      role == UserRole.clinician || role == UserRole.admin;

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
