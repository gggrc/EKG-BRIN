// lib/core/models/user_model.dart

enum UserRole {
  patient,  // → DB: PATIENT
  nakes,    // → DB: NAKES  (Tenaga Kesehatan / dokter)
  admin,    // → DB: ADMIN
}

extension UserRoleExtension on UserRole {
  String get displayName {
    switch (this) {
      case UserRole.patient: return 'Pasien';
      case UserRole.nakes:   return 'Tenaga Kesehatan';
      case UserRole.admin:   return 'Admin / Peneliti';
    }
  }

  String get shortName {
    switch (this) {
      case UserRole.patient: return 'Pasien';
      case UserRole.nakes:   return 'Nakes';
      case UserRole.admin:   return 'Admin';
    }
  }

  String get icon {
    switch (this) {
      case UserRole.patient: return '🧑‍💼';
      case UserRole.nakes:   return '👩‍⚕️';
      case UserRole.admin:   return '🔧';
    }
  }

  /// Nilai yang disimpan ke kolom `role` di Supabase (uppercase sesuai enum DB)
  String get dbValue {
    switch (this) {
      case UserRole.patient: return 'PATIENT';
      case UserRole.nakes:   return 'NAKES';
      case UserRole.admin:   return 'ADMIN';
    }
  }

  /// Parse dari string DB ('PATIENT', 'NAKES', 'ADMIN') — null → PATIENT
  static UserRole fromString(String? value) {
    switch (value?.toUpperCase()) {
      case 'NAKES':
      case 'DOCTOR':
      case 'HEALTHCAREWORKER':
        return UserRole.nakes;
      case 'ADMIN':
        return UserRole.admin;
      case 'PATIENT':
      default:
        return UserRole.patient;
    }
  }
}

class UserModel {
  final String userId;
  final String email;
  final String name;
  final UserRole role;
  final String gender;       // tidak lagi nullable — default 'unknown'
  final String phoneNumber;  // tidak lagi nullable — default 'unknown'
  final String? avatarUrl;
  final DateTime createdAt;

  const UserModel({
    required this.userId,
    required this.email,
    required this.name,
    required this.role,
    this.gender      = 'unknown',
    this.phoneNumber = 'unknown',
    this.avatarUrl,
    required this.createdAt,
  });

  // ─── fromJson: mapping dari response tabel `users` Supabase ───────────────
  factory UserModel.fromJson(Map<String, dynamic> json) {
    // Helper: ambil string, jika null/kosong kembalikan fallback
    String str(String key, [String fallback = 'unknown']) {
      final v = json[key];
      if (v == null) return fallback;
      final s = v.toString().trim();
      return s.isEmpty ? fallback : s;
    }

    return UserModel(
      userId      : str('user_id', ''),
      email       : str('email', 'unknown'),
      name        : json['full_name'] != null
                      ? json['full_name'].toString().trim().isNotEmpty
                          ? json['full_name'].toString().trim()
                          : str('name', 'unknown')
                      : str('name', 'unknown'),
      role        : UserRoleExtension.fromString(json['role'] as String?),
      gender      : str('gender'),
      phoneNumber : str('phone_number'),
      avatarUrl   : json['avatar_url'] as String?,
      createdAt   : json['created_at'] != null
                      ? DateTime.parse(json['created_at'] as String)
                      : DateTime.now(),
    );
  }

  // ─── toJson: untuk insert / upsert ke Supabase ────────────────────────────
  // Semua kolom NOT NULL sudah dijamin non-empty karena field tidak nullable.
  Map<String, dynamic> toJson() => {
    'user_id'     : userId,
    'email'       : email.isNotEmpty        ? email       : 'unknown',
    'full_name'   : name.isNotEmpty         ? name        : 'unknown',
    'role'        : role.dbValue,
    'gender'      : gender.isNotEmpty       ? gender      : 'unknown',
    'phone_number': phoneNumber.isNotEmpty  ? phoneNumber : 'unknown',
    'avatar_url'  : avatarUrl,
  };

  // ─── RBAC helpers ─────────────────────────────────────────────────────────
  bool get canViewAllPatients => role == UserRole.nakes || role == UserRole.admin;
  bool get canInputPatient    => role == UserRole.nakes;
  bool get canAcquireSignal   => role == UserRole.nakes;
  bool get canWriteDiagnosis  => role == UserRole.nakes;
  bool get canExportFHIR      => role == UserRole.nakes || role == UserRole.admin;
  bool get canAccessAdmin     => role == UserRole.admin;
  bool get canExportDataset   => role == UserRole.admin;

  UserModel copyWith({
    String? name,
    String? email,
    String? gender,
    String? phoneNumber,
    String? avatarUrl,
  }) {
    return UserModel(
      userId      : userId,
      email       : email        ?? this.email,
      name        : name         ?? this.name,
      role        : role,
      gender      : gender       ?? this.gender,
      phoneNumber : phoneNumber  ?? this.phoneNumber,
      avatarUrl   : avatarUrl    ?? this.avatarUrl,
      createdAt   : createdAt,
    );
  }
}