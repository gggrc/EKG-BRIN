// lib/features/landing/landing_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/router/app_router.dart';

class LandingPage extends StatelessWidget {
  const LandingPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        children: [
          // Animated background gradient orbs
          Positioned(
            top: -100,
            right: -100,
            child: Container(
              width: 500,
              height: 500,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.primary.withOpacity(0.15),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            bottom: -150,
            left: -100,
            child: Container(
              width: 600,
              height: 600,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.secondary.withOpacity(0.1),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          // Content
          SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minHeight: MediaQuery.of(context).size.height,
              ),
              child: Column(
                children: [
                  _Navbar(onLogin: () => context.go(AppRoutes.login)),
                  _HeroSection(onLogin: () => context.go(AppRoutes.login)),
                  _FeaturesSection(),
                  _RolesSection(),
                  _Footer(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Navbar extends StatelessWidget {
  final VoidCallback onLogin;
  const _Navbar({required this.onLogin});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 72,
      padding: const EdgeInsets.symmetric(horizontal: 48),
      decoration: BoxDecoration(
        color: AppColors.surface.withOpacity(0.8),
        border: const Border(bottom: BorderSide(color: AppColors.borderLight)),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.monitor_heart, color: Colors.white, size: 20),
          ),
          const SizedBox(width: 12),
          const Text(
            'EKG-BRIN',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: AppColors.primaryContainer,
              borderRadius: BorderRadius.circular(4),
            ),
            child: const Text(
              'PROTOTYPE',
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.primary, letterSpacing: 1),
            ),
          ),
          const Spacer(),
          Text('Tentang', style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
          const SizedBox(width: 32),
          Text('Dokumentasi', style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
          const SizedBox(width: 32),
          ElevatedButton(
            onPressed: onLogin,
            child: const Text('Masuk'),
          ),
        ],
      ),
    );
  }
}

class _HeroSection extends StatelessWidget {
  final VoidCallback onLogin;
  const _HeroSection({required this.onLogin});

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width > 900;
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isWide ? 80 : 24,
        vertical: isWide ? 80 : 48,
      ),
      child: isWide
          ? Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(flex: 5, child: _HeroText(onLogin: onLogin)),
                const SizedBox(width: 64),
                Expanded(flex: 4, child: _EcgPreviewCard()),
              ],
            )
          : Column(
              children: [
                _HeroText(onLogin: onLogin),
                const SizedBox(height: 40),
                _EcgPreviewCard(),
              ],
            ),
    );
  }
}

class _HeroText extends StatelessWidget {
  final VoidCallback onLogin;
  const _HeroText({required this.onLogin});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [AppColors.primary.withOpacity(0.2), AppColors.secondary.withOpacity(0.2)],
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.primary.withOpacity(0.3)),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.verified_rounded, size: 14, color: AppColors.primary),
              SizedBox(width: 6),
              Text(
                'Berbasis HL7 FHIR • Terintegrasi SATUSEHAT',
                style: TextStyle(fontSize: 12, color: AppColors.primary, fontWeight: FontWeight.w500),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Sistem EKG\nDigital Nasional',
          style: TextStyle(
            fontSize: 52,
            fontWeight: FontWeight.w800,
            color: AppColors.textPrimary,
            height: 1.1,
          ),
        ),
        const SizedBox(height: 16),
        ShaderMask(
          shaderCallback: (bounds) => AppColors.primaryGradient.createShader(bounds),
          child: const Text(
            'Untuk Indonesia',
            style: TextStyle(
              fontSize: 52,
              fontWeight: FontWeight.w800,
              color: Colors.white,
              height: 1.1,
            ),
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Platform end-to-end untuk digitalisasi, transformasi, dan integrasi data EKG '
          '(6-lead & 12-lead) dari berbagai perangkat ke platform SATUSEHAT Kemenkes RI '
          'berbasis standar HL7 FHIR.',
          style: TextStyle(
            fontSize: 16,
            color: AppColors.textSecondary,
            height: 1.7,
          ),
        ),
        const SizedBox(height: 40),
        Row(
          children: [
            ElevatedButton.icon(
              onPressed: onLogin,
              icon: const Icon(Icons.login_rounded, size: 18),
              label: const Text('Masuk ke Sistem'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
                textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(width: 16),
            OutlinedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.description_rounded, size: 18),
              label: const Text('Baca Dokumentasi'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
                textStyle: const TextStyle(fontSize: 16),
              ),
            ),
          ],
        ),
        const SizedBox(height: 48),
        Row(
          children: [
            _StatBadge(value: '12-Lead', label: 'EKG Support'),
            const SizedBox(width: 32),
            _StatBadge(value: 'HL7 R4', label: 'FHIR Standard'),
            const SizedBox(width: 32),
            _StatBadge(value: 'BRIN', label: 'Research Grade'),
          ],
        ),
      ],
    );
  }
}

class _StatBadge extends StatelessWidget {
  final String value;
  final String label;
  const _StatBadge({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w800,
            color: AppColors.primary,
          ),
        ),
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
        ),
      ],
    );
  }
}

class _EcgPreviewCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderLight),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withOpacity(0.1),
            blurRadius: 40,
            offset: const Offset(0, 20),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(color: AppColors.success, shape: BoxShape.circle),
              ),
              const SizedBox(width: 6),
              const Text('Live EKG Preview', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.successContainer,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text('Normal', style: TextStyle(fontSize: 11, color: AppColors.success, fontWeight: FontWeight.w600)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 120,
            child: CustomPaint(
              size: const Size(double.infinity, 120),
              painter: _MiniEcgPainter(),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: const [
              _MiniStat(label: 'HR', value: '75', unit: 'bpm'),
              _MiniStat(label: 'PR', value: '160', unit: 'ms'),
              _MiniStat(label: 'QRS', value: '90', unit: 'ms'),
              _MiniStat(label: 'QTc', value: '415', unit: 'ms'),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  final String label;
  final String value;
  final String unit;
  const _MiniStat({required this.label, required this.value, required this.unit});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
        Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
        Text(unit, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
      ],
    );
  }
}

class _MiniEcgPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.ecgLine
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final gridPaint = Paint()
      ..color = AppColors.ecgGrid
      ..strokeWidth = 0.5;

    // Grid
    for (double x = 0; x < size.width; x += 20) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y < size.height; y += 20) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    // ECG signal path
    final path = Path();
    final mid = size.height / 2;
    path.moveTo(0, mid);

    double x = 0;
    final segW = size.width / 3;

    void addEcgCycle(double startX) {
      // Baseline
      path.lineTo(startX + segW * 0.08, mid);
      // P wave
      path.quadraticBezierTo(startX + segW * 0.12, mid - 10, startX + segW * 0.16, mid);
      // PR segment
      path.lineTo(startX + segW * 0.22, mid);
      // Q
      path.lineTo(startX + segW * 0.25, mid + 5);
      // R
      path.lineTo(startX + segW * 0.30, mid - 45);
      // S
      path.lineTo(startX + segW * 0.35, mid + 10);
      // ST
      path.lineTo(startX + segW * 0.42, mid);
      // T wave
      path.quadraticBezierTo(startX + segW * 0.60, mid - 20, startX + segW * 0.72, mid);
      // End
      path.lineTo(startX + segW, mid);
    }

    addEcgCycle(0);
    addEcgCycle(segW);
    addEcgCycle(segW * 2);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _FeaturesSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final features = [
      {
        'icon': Icons.monitor_heart_rounded,
        'title': '6-Lead & 12-Lead Viewer',
        'desc': 'Visualisasi sinyal EKG standar klinis dengan zoom, pan, dan anotasi interaktif.',
        'color': AppColors.primary,
      },
      {
        'icon': Icons.upload_file_rounded,
        'title': 'Multi-Format Upload',
        'desc': 'Upload data EKG dari PDF, gambar, CSV, atau perangkat EKG berbagai vendor.',
        'color': AppColors.secondary,
      },
      {
        'icon': Icons.psychology_rounded,
        'title': 'Analisis AI',
        'desc': 'Interpretasi otomatis irama jantung, deteksi aritmia, dan pengukuran interval.',
        'color': AppColors.roleDoctor,
      },
      {
        'icon': Icons.share_rounded,
        'title': 'HL7 FHIR Export',
        'desc': 'Ekspor data EKG ke SATUSEHAT Kemenkes RI dengan standar HL7 FHIR R4.',
        'color': AppColors.success,
      },
      {
        'icon': Icons.people_rounded,
        'title': 'Multi-Role Access',
        'desc': 'Akses terpisah untuk Pasien, Nakes, Dokter, dan Admin dengan RBAC.',
        'color': AppColors.warning,
      },
      {
        'icon': Icons.security_rounded,
        'title': 'Keamanan PHI',
        'desc': 'Proteksi data kesehatan sesuai UU PDP No. 27/2022 dan standar HL7 FHIR.',
        'color': AppColors.danger,
      },
    ];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 80, vertical: 80),
      child: Column(
        children: [
          const Text('Fitur Utama', style: TextStyle(fontSize: 36, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 8),
          const Text('Platform lengkap untuk pengelolaan data EKG digital', style: TextStyle(fontSize: 16, color: AppColors.textSecondary)),
          const SizedBox(height: 48),
          Wrap(
            spacing: 24,
            runSpacing: 24,
            children: features.map((f) => SizedBox(
              width: 300,
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.borderLight),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: (f['color'] as Color).withOpacity(0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(f['icon'] as IconData, color: f['color'] as Color, size: 24),
                    ),
                    const SizedBox(height: 16),
                    Text(f['title'] as String, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                    const SizedBox(height: 8),
                    Text(f['desc'] as String, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, height: 1.6)),
                  ],
                ),
              ),
            )).toList(),
          ),
        ],
      ),
    );
  }
}

class _RolesSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final roles = [
      {'label': 'Pasien', 'icon': '🧑‍💼', 'color': AppColors.rolePatient, 'desc': 'Lihat EKG sendiri, riwayat, download laporan'},
      {'label': 'Nakes', 'icon': '👩‍⚕️', 'color': AppColors.roleNakes, 'desc': 'Input pasien, akuisisi sinyal, anotasi dasar'},
      {'label': 'Dokter', 'icon': '🩺', 'color': AppColors.roleDoctor, 'desc': 'Full 12-lead, diagnosis AI, approve laporan, FHIR export'},
      {'label': 'Admin', 'icon': '🔧', 'color': AppColors.roleAdmin, 'desc': 'Semua akses, manajemen user, dataset export, audit log'},
    ];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 80, vertical: 60),
      color: AppColors.surface.withOpacity(0.5),
      child: Column(
        children: [
          const Text('Untuk Siapa?', style: TextStyle(fontSize: 36, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 48),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: roles.map((r) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                children: [
                  Text(r['icon'] as String, style: const TextStyle(fontSize: 48)),
                  const SizedBox(height: 12),
                  Text(r['label'] as String, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: r['color'] as Color)),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: 180,
                    child: Text(r['desc'] as String, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: AppColors.textMuted, height: 1.5)),
                  ),
                ],
              ),
            )).toList(),
          ),
        ],
      ),
    );
  }
}

class _Footer extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 80, vertical: 32),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AppColors.borderLight)),
      ),
      child: Row(
        children: [
          const Text('© 2026 EKG-BRIN — Badan Riset dan Inovasi Nasional', style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
          const Spacer(),
          const Text('Berbasis HL7 FHIR R4 • SATUSEHAT Ready', style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}
