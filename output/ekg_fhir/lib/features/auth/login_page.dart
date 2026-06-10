// lib/features/auth/login_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/models/user_model.dart';
import '../../core/router/app_router.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _obscurePass = true;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;
    final auth = context.read<AuthProvider>();
    final success = await auth.login(_emailCtrl.text.trim(), _passCtrl.text);
    if (success && mounted) {
      context.go(AppRoutes.dashboard);
    }
  }

  Future<void> _loginAsRole(UserRole role) async {
    final auth = context.read<AuthProvider>();
    final success = await auth.loginAsRole(role);
    if (success && mounted) context.go(AppRoutes.dashboard);
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        children: [
          // Background orbs
          Positioned(
            top: -80,
            right: -80,
            child: Container(
              width: 400,
              height: 400,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [AppColors.primary.withOpacity(0.12), Colors.transparent],
                ),
              ),
            ),
          ),
          Positioned(
            bottom: -100,
            left: -100,
            child: Container(
              width: 500,
              height: 500,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [AppColors.secondary.withOpacity(0.08), Colors.transparent],
                ),
              ),
            ),
          ),
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  // Back to landing
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () => context.go(AppRoutes.landing),
                      icon: const Icon(Icons.arrow_back, size: 16),
                      label: const Text('Kembali'),
                    ),
                  ),
                  const SizedBox(height: 24),
                  // Login card
                  Container(
                    width: 440,
                    padding: const EdgeInsets.all(40),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppColors.borderLight),
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.primary.withOpacity(0.08),
                          blurRadius: 40,
                          offset: const Offset(0, 20),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Logo
                        Row(
                          children: [
                            Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                gradient: AppColors.primaryGradient,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Icon(Icons.monitor_heart, color: Colors.white, size: 24),
                            ),
                            const SizedBox(width: 12),
                            const Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('EKG-BRIN', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                                Text('Sistem HL7 FHIR', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                              ],
                            ),
                          ],
                        ),
                        const SizedBox(height: 32),
                        const Text('Masuk ke Akun', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                        const SizedBox(height: 6),
                        const Text('Masukkan email dan password Anda', style: TextStyle(fontSize: 14, color: AppColors.textSecondary)),
                        const SizedBox(height: 32),

                        if (auth.errorMessage != null)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            margin: const EdgeInsets.only(bottom: 20),
                            decoration: BoxDecoration(
                              color: AppColors.dangerContainer,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppColors.danger.withOpacity(0.3)),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.error_outline, color: AppColors.danger, size: 16),
                                const SizedBox(width: 8),
                                Expanded(child: Text(auth.errorMessage!, style: const TextStyle(color: AppColors.dangerLight, fontSize: 13))),
                              ],
                            ),
                          ),

                        Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              TextFormField(
                                controller: _emailCtrl,
                                keyboardType: TextInputType.emailAddress,
                                decoration: const InputDecoration(
                                  labelText: 'Email',
                                  prefixIcon: Icon(Icons.email_outlined, size: 18),
                                ),
                                validator: (v) {
                                  if (v == null || v.isEmpty) return 'Email wajib diisi';
                                  if (!v.contains('@')) return 'Format email tidak valid';
                                  return null;
                                },
                               ),
                              const SizedBox(height: 16),
                              TextFormField(
                                controller: _passCtrl,
                                obscureText: _obscurePass,
                                decoration: InputDecoration(
                                  labelText: 'Password',
                                  prefixIcon: const Icon(Icons.lock_outlined, size: 18),
                                  suffixIcon: IconButton(
                                    onPressed: () => setState(() => _obscurePass = !_obscurePass),
                                    icon: Icon(_obscurePass ? Icons.visibility_outlined : Icons.visibility_off_outlined, size: 18),
                                  ),
                                ),
                                validator: (v) {
                                  if (v == null || v.isEmpty) return 'Password wajib diisi';
                                  return null;
                                },
                                onFieldSubmitted: (_) => _handleLogin(),
                              ),
                              const SizedBox(height: 12),
                              Align(
                                alignment: Alignment.centerRight,
                                child: TextButton(onPressed: () {}, child: const Text('Lupa password?')),
                              ),
                              const SizedBox(height: 8),
                              SizedBox(
                                width: double.infinity,
                                child: ElevatedButton(
                                  onPressed: auth.isLoading ? null : _handleLogin,
                                  style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                                  child: auth.isLoading
                                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                      : const Text('Masuk', style: TextStyle(fontSize: 15)),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Demo login buttons
                        const Row(
                          children: [
                            Expanded(child: Divider(color: AppColors.borderLight)),
                            Padding(
                              padding: EdgeInsets.symmetric(horizontal: 12),
                              child: Text('Demo Login', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                            ),
                            Expanded(child: Divider(color: AppColors.borderLight)),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: UserRole.values.map((role) => _DemoRoleButton(
                            role: role,
                            onTap: () => _loginAsRole(role),
                            isLoading: auth.isLoading,
                          )).toList(),
                        ),
                        const SizedBox(height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text('Belum punya akun? ', style: TextStyle(fontSize: 14, color: AppColors.textSecondary)),
                            TextButton(
                              onPressed: () => context.go(AppRoutes.register),
                              child: const Text('Daftar'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DemoRoleButton extends StatelessWidget {
  final UserRole role;
  final VoidCallback onTap;
  final bool isLoading;

  const _DemoRoleButton({required this.role, required this.onTap, required this.isLoading});

  Color get color {
    switch (role) {
      case UserRole.patient: return AppColors.rolePatient;
      case UserRole.clinician: return AppColors.roleClinician;
      case UserRole.admin: return AppColors.roleAdmin;
    }
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: isLoading ? null : onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(role.icon, style: const TextStyle(fontSize: 14)),
            const SizedBox(width: 6),
            Text(role.shortName, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}
