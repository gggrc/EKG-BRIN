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
}
