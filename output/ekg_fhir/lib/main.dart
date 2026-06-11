// lib/main.dart

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

// Import library universal HTML secara aman agar tidak error saat dicompile ke Android/iOS
import 'package:universal_html/html.dart' as html;

import 'core/theme/app_theme.dart';
import 'core/providers/auth_provider.dart';
import 'core/router/app_router.dart';

Future<void> main() async {
  // Wajib dipanggil sebelum async initialization
  WidgetsFlutterBinding.ensureInitialized();

  // ── SCRIPT PENGAMAN UTAMA WEB URL (MENGHANCURKAN REDIRECT LOOP SECARA NATIVE) ──
  // Berjalan di level paling luar sebelum engine Flutter dan GoRouter dibangun
  if (kIsWeb) {
    final currentUrl = html.window.location.href;
    if (currentUrl.contains('error=') || currentUrl.contains('error_code=')) {
      // Ambil origin (http://localhost:5000) lalu paksa bersihkan URL ke path login
      final origin = html.window.location.origin;
      html.window.history.replaceState(null, 'Login', '$origin/#/login');
    }
  }
  // ─────────────────────────────────────────────────────────────────────────────

  // Load environment variables
  await dotenv.load(fileName: ".env");

  // Initialize Supabase
  await Supabase.initialize(
    url: dotenv.env['SUPABASE_URL']!,
    anonKey: dotenv.env['SUPABASE_ANON_KEY']!,
  );

  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthProvider(),
      child: const EkgBrinApp(),
    ),
  );
}

class EkgBrinApp extends StatefulWidget {
  const EkgBrinApp({super.key});

  @override
  State<EkgBrinApp> createState() => _EkgBrinAppState();
}

class _EkgBrinAppState extends State<EkgBrinApp> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    // Inisialisasi router dengan menyuntikkan AuthProvider
    _router = createRouter(
      context.read<AuthProvider>(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'EKG-BRIN — Sistem HL7 FHIR',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      routerConfig: _router,
    );
  }
}