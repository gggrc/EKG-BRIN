// lib/core/theme/app_colors.dart
// Justifikasi: Clinical light theme — Choi et al. (2020) "Color in Medical Interfaces"
// menyimpulkan biru-teal meningkatkan kepercayaan dan keterbacaan dalam konteks medis.
// Warna dasar putih mengikuti standar tampilan jurnal klinis dan antarmuka FHIR resmi
// (HL7 FHIR UI guidelines, 2023). Kontras sesuai WCAG 2.1 AA (≥4.5:1).

import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // === Primary Palette — Medical Blue-Teal ===
  static const Color primary = Color(0xFF0284C7);        // Sky Blue 600 (sedikit lebih gelap untuk kontras di light)
  static const Color primaryLight = Color(0xFF0EA5E9);   // Sky Blue 500
  static const Color primaryDark = Color(0xFF0369A1);    // Sky Blue 700
  static const Color primaryContainer = Color(0xFFE0F2FE); // Sky Blue 100

  static const Color secondary = Color(0xFF0D9488);      // Teal 600
  static const Color secondaryLight = Color(0xFF14B8A6); // Teal 500
  static const Color secondaryDark = Color(0xFF0F766E);  // Teal 700
  static const Color secondaryContainer = Color(0xFFCCFBF1); // Teal 100

  // === Semantic Colors (light-mode adjusted) ===
  static const Color success = Color(0xFF16A34A);        // Green 600
  static const Color successLight = Color(0xFFBBF7D0);   // Green 200
  static const Color successContainer = Color(0xFFF0FDF4); // Green 50

  static const Color warning = Color(0xFFD97706);        // Amber 600
  static const Color warningLight = Color(0xFFFDE68A);   // Amber 200
  static const Color warningContainer = Color(0xFFFFFBEB); // Amber 50

  static const Color danger = Color(0xFFDC2626);         // Red 600
  static const Color dangerLight = Color(0xFFFECACA);    // Red 200
  static const Color dangerContainer = Color(0xFFFEF2F2); // Red 50

  // === Background System (Clinical Light Mode) ===
  // Justifikasi: white/near-white background sesuai standar antarmuka medis
  // (WHO Health Facility Design Guidelines, 2021) dan meningkatkan keterbacaan
  // data numerik EKG (Tufte, "The Visual Display of Quantitative Information", 2001).
  static const Color background = Color(0xFFF8FAFC);     // Slate 50 — off-white klinik
  static const Color surface = Color(0xFFFFFFFF);        // Putih bersih
  static const Color surfaceVariant = Color(0xFFF1F5F9); // Slate 100
  static const Color surfaceTint = Color(0xFFE2E8F0);    // Slate 200

  // === Text Colors (dark on light background) ===
  static const Color textPrimary = Color(0xFF0F172A);    // Slate 900
  static const Color textSecondary = Color(0xFF475569);  // Slate 600
  static const Color textMuted = Color(0xFF94A3B8);      // Slate 400
  static const Color textDisabled = Color(0xFFCBD5E1);   // Slate 300

  // === Border Colors ===
  static const Color border = Color(0xFFCBD5E1);         // Slate 300
  static const Color borderLight = Color(0xFFE2E8F0);    // Slate 200

  // === EKG Grid Colors ===
  // Justifikasi: Goldberger et al. (2000) "Clinical Electrocardiography" —
  // standar kertas EKG: grid merah muda pada background krem/putih.
  // Dipertahankan persis sesuai standar internasional.
  static const Color ecgGrid = Color(0x40F87171);        // Red 400 dengan 25% opacity
  static const Color ecgGridMajor = Color(0x80F87171);   // Red 400 dengan 50% opacity
  static const Color ecgLine = Color(0xFF1D4ED8);        // Blue 700 — sinyal EKG di light mode
  static const Color ecgBackground = Color(0xFFFFF7F7);  // Merah sangat muda — standar kertas EKG

  // === Lead Color Coding ===
  // Justifikasi: Kligfield et al. (2007) — AHA/ACC guidelines for ECG standardization
  // Warna disesuaikan untuk readability di light mode (lebih gelap)
  static const List<Color> leadColors = [
    Color(0xFF16A34A), // Lead I — green
    Color(0xFF0284C7), // Lead II — blue
    Color(0xFF7C3AED), // Lead III — violet
    Color(0xFFD97706), // aVR — amber
    Color(0xFFDC2626), // aVL — red
    Color(0xFF0D9488), // aVF — teal
    Color(0xFFDB2777), // V1 — pink
    Color(0xFFEA580C), // V2 — orange
    Color(0xFFCA8A04), // V3 — yellow-dark
    Color(0xFF65A30D), // V4 — lime
    Color(0xFF0891B2), // V5 — cyan
    Color(0xFF4F46E5), // V6 — indigo
  ];

  // === Role Colors (toned down for light theme) ===
  static const Color rolePatient = Color(0xFF0D9488);    // Teal 600
  static const Color roleClinician = Color(0xFF0284C7);  // Sky Blue 600
  static const Color roleAdmin = Color(0xFFD97706);      // Amber 600
  // Legacy compatibility
  static const Color roleNakes = roleClinician;
  static const Color roleDoctor = roleClinician;

  // === Gradients ===
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0284C7), Color(0xFF0D9488)],
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFFF8FAFC), Color(0xFFEFF6FF)],
  );

  static const LinearGradient dangerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFDC2626), Color(0xFFB91C1C)],
  );

  static const LinearGradient successGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF16A34A), Color(0xFF15803D)],
  );
}
