// lib/core/models/patient_model.dart

class PatientModel {
  final String patientId;
  final String fullName;
  final String medicalRecordNumber;
  final String gender;
  final DateTime birthDate;
  final double? heightCm;
  final double? weightKg;
  final String? bloodType;
  final String? address;
  final String? phoneNumber;
  final String? emergencyContact;
  final List<String> allergies;
  final List<String> currentMedications;
  final String? nik; // Nomor Induk Kependudukan
  final DateTime? lastEcgDate;
  final int totalEcgSessions;

  const PatientModel({
    required this.patientId,
    required this.fullName,
    required this.medicalRecordNumber,
    required this.gender,
    required this.birthDate,
    this.heightCm,
    this.weightKg,
    this.bloodType,
    this.address,
    this.phoneNumber,
    this.emergencyContact,
    this.allergies = const [],
    this.currentMedications = const [],
    this.nik,
    this.lastEcgDate,
    this.totalEcgSessions = 0,
  });

  int get ageYears {
    final now = DateTime.now();
    int age = now.year - birthDate.year;
    if (now.month < birthDate.month ||
        (now.month == birthDate.month && now.day < birthDate.day)) {
      age--;
    }
    return age;
  }

  double? get bmi {
    if (heightCm != null && weightKg != null && heightCm! > 0) {
      return weightKg! / ((heightCm! / 100) * (heightCm! / 100));
    }
    return null;
  }

  String get genderDisplay => gender == 'M' ? 'Laki-laki' : 'Perempuan';

  PatientModel copyWith({
    String? patientId,
    String? fullName,
    String? medicalRecordNumber,
    String? gender,
    DateTime? birthDate,
    double? heightCm,
    double? weightKg,
    String? bloodType,
    String? address,
    String? phoneNumber,
    String? emergencyContact,
    List<String>? allergies,
    List<String>? currentMedications,
    String? nik,
    DateTime? lastEcgDate,
    int? totalEcgSessions,
  }) {
    return PatientModel(
      patientId: patientId ?? this.patientId,
      fullName: fullName ?? this.fullName,
      medicalRecordNumber: medicalRecordNumber ?? this.medicalRecordNumber,
      gender: gender ?? this.gender,
      birthDate: birthDate ?? this.birthDate,
      heightCm: heightCm ?? this.heightCm,
      weightKg: weightKg ?? this.weightKg,
      bloodType: bloodType ?? this.bloodType,
      address: address ?? this.address,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      emergencyContact: emergencyContact ?? this.emergencyContact,
      allergies: allergies ?? this.allergies,
      currentMedications: currentMedications ?? this.currentMedications,
      nik: nik ?? this.nik,
      lastEcgDate: lastEcgDate ?? this.lastEcgDate,
      totalEcgSessions: totalEcgSessions ?? this.totalEcgSessions,
    );
  }
}
