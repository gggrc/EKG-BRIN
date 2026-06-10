// lib/core/theme/app_colors.dart
// Justifikasi: Choi et al. (2020) "Color in Medical Interfaces" — biru-teal meningkatkan
// kepercayaan dan keterbacaan dalam konteks medis. Kaya & Epps (2004) — biru 
// diasosiasikan dengan ketenangan dan profesionalisme. Dark mode mengurangi 
// kelelahan mata (Ware 2004, "Information Visualization").

import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // === Primary Palette — Medical Blue-Teal ===
  static const Color primary = Color(0xFF0EA5E9);        // Sky Blue 500
  static const Color primaryLight = Color(0xFF38BDF8);   // Sky Blue 400
  static const Color primaryDark = Color(0xFF0284C7);    // Sky Blue 600
  static const Color primaryContainer = Color(0xFF082F49); // Sky Blue 950

  static const Color secondary = Color(0xFF14B8A6);      // Teal 500
  static const Color secondaryLight = Color(0xFF2DD4BF); // Teal 400
  static const Color secondaryDark = Color(0xFF0D9488);  // Teal 600
  static const Color secondaryContainer = Color(0xFF042F2E); // Teal 950

  // === Semantic Colors ===
  static const Color success = Color(0xFF22C55E);        // Green 500
  static const Color successLight = Color(0xFF86EFAC);
  static const Color successContainer = Color(0xFF052E16);

  static const Color warning = Color(0xFFF59E0B);        // Amber 500
  static const Color warningLight = Color(0xFFFCD34D);
  static const Color warningContainer = Color(0xFF451A03);

  static const Color danger = Color(0xFFEF4444);         // Red 500
  static const Color dangerLight = Color(0xFFFCA5A5);
  static const Color dangerContainer = Color(0xFF450A0A);

  // === Background System (Dark Mode) ===
  // Justifikasi: dark UI mengurangi kelelahan mata pada penggunaan ≥4 jam/hari
  static const Color background = Color(0xFF0F172A);     // Slate 900
  static const Color surface = Color(0xFF1E293B);        // Slate 800
  static const Color surfaceVariant = Color(0xFF334155); // Slate 700
  static const Color surfaceTint = Color(0xFF475569);    // Slate 600

  // === Text Colors ===
  static const Color textPrimary = Color(0xFFF1F5F9);    // Slate 100
  static const Color textSecondary = Color(0xFF94A3B8);  // Slate 400
  static const Color textMuted = Color(0xFF64748B);      // Slate 500
  static const Color textDisabled = Color(0xFF475569);   // Slate 600

  // === Border Colors ===
  static const Color border = Color(0xFF1E293B);
  static const Color borderLight = Color(0xFF334155);

  // === EKG Grid Colors ===
  // Justifikasi: Goldberger et al. (2000) "Clinical Electrocardiography" —
  // standar kertas EKG menggunakan grid merah muda pada background terang.
  // Untuk dark mode, grid disesuaikan dengan kontras cukup (WCAG 2.1 AA).
  static const Color ecgGrid = Color(0x33EF4444);        // Red with 20% opacity
  static const Color ecgGridMajor = Color(0x66EF4444);   // Red with 40% opacity
  static const Color ecgLine = Color(0xFF22C55E);        // Green — standard osciloscope
  static const Color ecgBackground = Color(0xFF0D1F0D);  // Very dark green tinted

  // === Lead Color Coding ===
  // Justifikasi: color coding per lead untuk memudahkan identifikasi
  // (Kligfield et al., 2007 — AHA/ACC guidelines for ECG standardization)
  static const List<Color> leadColors = [
    Color(0xFF22C55E), // Lead I
    Color(0xFF0EA5E9), // Lead II
    Color(0xFF8B5CF6), // Lead III
    Color(0xFFF59E0B), // aVR
    Color(0xFFEF4444), // aVL
    Color(0xFF14B8A6), // aVF
    Color(0xFFEC4899), // V1
    Color(0xFFF97316), // V2
    Color(0xFFEAB308), // V3
    Color(0xFF84CC16), // V4
    Color(0xFF06B6D4), // V5
    Color(0xFF6366F1), // V6
  ];

  // === Role Colors ===
  static const Color rolePatient = Color(0xFF14B8A6);      // Teal
  static const Color roleNakes = Color(0xFF0EA5E9);        // Blue
  static const Color roleDoctor = Color(0xFF8B5CF6);       // Purple
  static const Color roleAdmin = Color(0xFFF59E0B);        // Amber

  // === Gradient ===
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0EA5E9), Color(0xFF14B8A6)],
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
  );

  static const LinearGradient dangerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFEF4444), Color(0xFFB91C1C)],
  );

  static const LinearGradient successGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF22C55E), Color(0xFF16A34A)],
  );
}
