// lib/core/models/patient_model.dart

class PatientModel {
  final String patientId;
  final String? userId; 
  final String fullName; 
  final String medicalRecordNumber; 
  final String gender; 
  final DateTime birthDate; 
  final double? heightCm; 
  final double? weightKg; 

  const PatientModel({
    required this.patientId,
    this.userId,
    required this.fullName,
    required this.medicalRecordNumber,
    required this.gender,
    required this.birthDate,
    this.heightCm,
    this.weightKg,
  });

  // Getter untuk menghitung Usia (Mengembalikan int)
  int get ageYears {
    final now = DateTime.now();
    int age = now.year - birthDate.year;
    if (now.month < birthDate.month ||
        (now.month == birthDate.month && now.day < birthDate.day)) {
      age--;
    }
    return age;
  }

  // Getter untuk menghitung BMI secara otomatis
  double? get bmi {
    if (heightCm != null && weightKg != null && heightCm! > 0) {
      return weightKg! / ((heightCm! / 100) * (heightCm! / 100));
    }
    return null;
  }

  // Getter untuk tampilan teks jenis kelamin yang rapi
  String get genderDisplay {
    final g = gender.trim().toUpperCase();
    if (g == 'M' || g == 'MALE' || g == 'LAKI-LAKI' || g == 'L') return 'Laki-laki';
    if (g == 'F' || g == 'FEMALE' || g == 'PEREMPUAN' || g == 'P') return 'Perempuan';
    return 'Dirahasiakan';
  }

  factory PatientModel.fromJson(Map<String, dynamic> json) {
    return PatientModel(
      // Mengantisipasi jika database menggunakan 'patient_id' (snake_case)
      patientId: json['patient_id'] ?? json['patientId'] ?? '', 
      fullName: json['full_name'] ?? json['fullName'] ?? '',
      medicalRecordNumber: json['medical_record_number'] ?? json['medicalRecordNumber'] ?? '',
      gender: json['gender'] ?? 'M',
      birthDate: json['birth_date'] != null 
          ? DateTime.parse(json['birth_date']) 
          : (json['birthDate'] is DateTime ? json['birthDate'] : DateTime.now()),
      heightCm: (json['height_cm'] ?? json['heightCm'])?.toDouble(),
      weightKg: (json['weight_kg'] ?? json['weightKg'])?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
    if (patientId.isNotEmpty) 'patient_id': patientId,
    'user_id': userId,
    'full_name': fullName.trim(),
    'medical_record_number': medicalRecordNumber.trim(),
    'gender': gender,
    'birth_date': birthDate.toIso8601String(),
    'height_cm': heightCm,
    'weight_kg': weightKg,
  };

  PatientModel copyWith({
    String? patientId,
    String? userId,
    String? fullName,
    String? medicalRecordNumber,
    String? gender,
    DateTime? birthDate,
    double? heightCm,
    double? weightKg,
  }) {
    return PatientModel(
      patientId: patientId ?? this.patientId,
      userId: userId ?? this.userId,
      fullName: fullName ?? this.fullName,
      medicalRecordNumber: medicalRecordNumber ?? this.medicalRecordNumber,
      gender: gender ?? this.gender,
      birthDate: birthDate ?? this.birthDate,
      heightCm: heightCm ?? this.heightCm,
      weightKg: weightKg ?? this.weightKg,
    );
  }
}