// lib/main.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'core/providers/auth_provider.dart';
import 'core/router/app_router.dart';

void main() {
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
    _router = createRouter(context.read<AuthProvider>());
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

