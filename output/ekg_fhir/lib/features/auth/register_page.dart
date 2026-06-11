// lib/features/auth/register_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../core/theme/app_colors.dart';
import '../../core/models/user_model.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/router/app_router.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key});

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _confirmPassCtrl = TextEditingController();

  UserRole _selectedRole = UserRole.patient;
  String? _selectedGender;
  bool _obscurePass = true;
  bool _obscureConfirm = true;
  bool _isLoading = false;

  static const List<Map<String, dynamic>> _genderOptions = [
    {'value': 'male',   'label': 'Laki-laki',  'icon': Icons.man},
    {'value': 'female', 'label': 'Perempuan',  'icon': Icons.woman},
    {'value': 'other',  'label': 'Lainnya',    'icon': Icons.person},
  ];

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _passCtrl.dispose();
    _confirmPassCtrl.dispose();
    super.dispose();
  }

  // ─── Email/Password Register ──────────────────────────────────────────────
  //
  // FIX: Masalah "Database error saving new user" terjadi karena:
  //   - signUp() pada Supabase dengan email confirmation ENABLED mengembalikan
  //     user tanpa session aktif. Insert langsung ke tabel `users` gagal
  //     karena RLS memblokir request tanpa JWT yang valid.
  //
  // SOLUSI: Simpan data profil ke dalam metadata signUp (`data` field).
  //   Buat database trigger di Supabase (handle_new_user) yang membaca
  //   raw_user_meta_data dan menginsert ke tabel `users` secara server-side.
  //   Jika trigger belum ada, gunakan service role key via Edge Function,
  //   ATAU nonaktifkan email confirmation sementara di Auth settings.
  //
  //   Untuk fallback client-side: coba insert, jika gagal karena RLS
  //   (kode 42501 / PGRST301), tampilkan pesan "cek email" dan arahkan
  //   ke login — profil akan dibuat saat user pertama kali sign in
  //   melalui _loadUserProfile() di AuthProvider.

  Future<void> _handleRegister() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedGender == null) {
      _showError('Silakan pilih jenis kelamin.');
      return;
    }

    setState(() => _isLoading = true);
    try {
      final supabase = Supabase.instance.client;

      // 1. Buat auth user + simpan metadata profil sekaligus
      final authResponse = await supabase.auth.signUp(
        email: _emailCtrl.text.trim(),
        password: _passCtrl.text,
        data: {
          'full_name'   : _nameCtrl.text.trim(),
          'role'        : _selectedRole.dbValue.toUpperCase(), // Pastikan dikirim UPPERCASE ('PATIENT', 'NAKES', 'ADMIN')
          'gender'      : _selectedGender ?? 'unknown',
          'phone_number': _phoneCtrl.text.trim().isNotEmpty ? _phoneCtrl.text.trim() : 'unknown',
        },
      );

      final authUser = authResponse.user;
      if (authUser == null) {
        _showError('Registrasi gagal. Coba lagi.');
        return;
      }

      // 2a. Jika ada session aktif (email confirmation DINONAKTIFKAN di Supabase),
      //     insert profil langsung karena RLS sudah lewat dengan JWT valid.
      if (authResponse.session != null) {
        try {
          await supabase.from('users').upsert(
            {
              'user_id'     : authUser.id,
              'full_name'   : _nameCtrl.text.trim(),
              'email'       : _emailCtrl.text.trim(),
              'gender'      : _selectedGender,
              'phone_number': _phoneCtrl.text.trim(),
              'role'        : _selectedRole.dbValue,
            },
            onConflict      : 'user_id',
            ignoreDuplicates: false,
          );
        } on PostgrestException catch (e) {
          // Jika RLS tetap memblokir, lanjutkan saja —
          // _loadUserProfile() di AuthProvider akan upsert saat login nanti.
          debugPrint('Upsert profil gagal (akan dicoba saat login): ${e.message}');
        }

        // Session aktif → GoRouter otomatis redirect ke /dashboard
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Registrasi berhasil! Selamat datang.'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        // 2b. Tidak ada session → email confirmation aktif.
        //     Profil akan dibuat oleh trigger DB atau saat login nanti.
        if (mounted) {
          _showSuccessDialog();
        }
      }
    } on AuthException catch (e) {
      _showError(_mapAuthError(e.message));
    } on PostgrestException catch (e) {
      // Tangkap error DB yang lebih spesifik
      final msg = e.message.toLowerCase();
      if (msg.contains('row-level security') ||
          msg.contains('rls') ||
          e.code == '42501' ||
          e.code == 'PGRST301') {
        // RLS memblokir insert → arahkan ke cek email saja,
        // profil akan dibuat oleh trigger DB atau saat pertama login
        if (mounted) _showSuccessDialog();
      } else {
        _showError('Gagal menyimpan data: ${e.message}');
      }
    } catch (e) {
      _showError('Terjadi kesalahan: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showSuccessDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.mark_email_read_outlined, color: Colors.green, size: 28),
            SizedBox(width: 12),
            Text('Cek Email Anda', style: TextStyle(fontSize: 18)),
          ],
        ),
        content: Text(
          'Kami telah mengirim link verifikasi ke\n${_emailCtrl.text.trim()}\n\n'
          'Klik link di email tersebut, lalu masuk dengan akun yang baru dibuat.',
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 14, height: 1.5),
        ),
        actions: [
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              context.go(AppRoutes.login);
            },
            child: const Text('Ke Halaman Login'),
          ),
        ],
      ),
    );
  }

  // ─── Google Sign-Up ───────────────────────────────────────────────────────

  Future<void> _handleGoogleRegister() async {
    await context.read<AuthProvider>().loginWithGoogle();
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red.shade700),
    );
  }

  String _mapAuthError(String message) {
    if (message.contains('already registered') ||
        message.contains('already been registered') ||
        message.contains('User already registered')) {
      return 'Email sudah terdaftar. Silakan masuk.';
    }
    if (message.contains('Password should be at least')) {
      return 'Password minimal 6 karakter.';
    }
    if (message.contains('invalid email')) {
      return 'Format email tidak valid.';
    }
    return message;
  }


  // ─── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final authLoading = context.watch<AuthProvider>().isLoading;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => context.go(AppRoutes.login),
                  icon: const Icon(Icons.arrow_back, size: 16),
                  label: const Text('Kembali ke Login'),
                ),
              ),
              const SizedBox(height: 24),
              Container(
                width: 480,
                padding: const EdgeInsets.all(40),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.borderLight),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withOpacity(0.06),
                      blurRadius: 40,
                      offset: const Offset(0, 20),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // ── Header ──
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
                            Text('EKG-BRIN',
                                style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.textPrimary)),
                            Text('Sistem HL7 FHIR',
                                style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 28),
                    const Text(
                      'Buat Akun Baru',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Daftar untuk mengakses sistem EKG-BRIN',
                      style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 28),

                    // ── Google Sign-Up ──
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: (authLoading || _isLoading) ? null : _handleGoogleRegister,
                        icon: (authLoading)
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Image.asset(
                                'icons/google_logo.png',
                                height: 18,
                                width: 18,
                                errorBuilder: (_, __, ___) =>
                                    const Icon(Icons.g_mobiledata, size: 20),
                              ),
                        label: const Text('Daftar dengan Google'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          side: const BorderSide(color: AppColors.borderLight),
                          foregroundColor: AppColors.textPrimary,
                        ),
                      ),
                    ),

                    // ── Divider ──
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 20),
                      child: Row(
                        children: [
                          const Expanded(child: Divider()),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            child: Text(
                              'atau daftar dengan email',
                              style: TextStyle(
                                fontSize: 12,
                                color: AppColors.textSecondary.withOpacity(0.7),
                              ),
                            ),
                          ),
                          const Expanded(child: Divider()),
                        ],
                      ),
                    ),

                    // ── Form ──
                    Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [

                          // Nama Lengkap
                          TextFormField(
                            controller: _nameCtrl,
                            textCapitalization: TextCapitalization.words,
                            decoration: const InputDecoration(
                              labelText: 'Nama Lengkap',
                              prefixIcon: Icon(Icons.person_outline, size: 18),
                            ),
                            validator: (v) =>
                                v == null || v.isEmpty ? 'Nama wajib diisi' : null,
                          ),
                          const SizedBox(height: 16),

                          // Email
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

                          // No. Telepon
                          TextFormField(
                            controller: _phoneCtrl,
                            keyboardType: TextInputType.phone,
                            decoration: const InputDecoration(
                              labelText: 'Nomor Telepon',
                              prefixIcon: Icon(Icons.phone_outlined, size: 18),
                              hintText: 'Contoh: 081234567890',
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) return 'Nomor telepon wajib diisi';
                              if (v.length < 9 || v.length > 15) {
                                return 'Nomor telepon tidak valid';
                              }
                              if (!RegExp(r'^[0-9+\-\s]+$').hasMatch(v)) {
                                return 'Nomor telepon hanya boleh berisi angka';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),

                          // Jenis Kelamin
                          const Text(
                            'Jenis Kelamin',
                            style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            children: _genderOptions.map((g) {
                              final isSelected = _selectedGender == g['value'];
                              return GestureDetector(
                                onTap: () => setState(() => _selectedGender = g['value'] as String),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 150),
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 14,
                                    vertical: 10,
                                  ),
                                  decoration: BoxDecoration(
                                    color: isSelected
                                        ? AppColors.primary.withOpacity(0.12)
                                        : AppColors.surfaceVariant,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: isSelected
                                          ? AppColors.primary
                                          : Colors.transparent,
                                      width: 1.5,
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(g['icon'] as IconData,
                                          size: 18, color: AppColors.textSecondary),
                                      const SizedBox(width: 6),
                                      Text(
                                        g['label'] as String,
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.w500,
                                          color: isSelected
                                              ? AppColors.primary
                                              : AppColors.textSecondary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            }).toList(),
                          ),
                          const SizedBox(height: 16),

                          // Password
                          TextFormField(
                            controller: _passCtrl,
                            obscureText: _obscurePass,
                            decoration: InputDecoration(
                              labelText: 'Password',
                              prefixIcon: const Icon(Icons.lock_outlined, size: 18),
                              suffixIcon: IconButton(
                                onPressed: () =>
                                    setState(() => _obscurePass = !_obscurePass),
                                icon: Icon(
                                  _obscurePass
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined,
                                  size: 18,
                                ),
                              ),
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) return 'Password wajib diisi';
                              if (v.length < 6) return 'Password minimal 6 karakter';
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),

                          // Konfirmasi Password
                          TextFormField(
                            controller: _confirmPassCtrl,
                            obscureText: _obscureConfirm,
                            decoration: InputDecoration(
                              labelText: 'Konfirmasi Password',
                              prefixIcon: const Icon(Icons.lock_outlined, size: 18),
                              suffixIcon: IconButton(
                                onPressed: () =>
                                    setState(() => _obscureConfirm = !_obscureConfirm),
                                icon: Icon(
                                  _obscureConfirm
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined,
                                  size: 18,
                                ),
                              ),
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) {
                                return 'Konfirmasi password wajib diisi';
                              }
                              if (v != _passCtrl.text) return 'Password tidak cocok';
                              return null;
                            },
                          ),
                          const SizedBox(height: 24),

                          // Submit
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _isLoading ? null : _handleRegister,
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 16),
                              ),
                              child: _isLoading
                                  ? const SizedBox(
                                      height: 18,
                                      width: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.white,
                                      ),
                                    )
                                  : const Text(
                                      'Daftar Sekarang',
                                      style: TextStyle(fontSize: 15),
                                    ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    // ── Footer ──
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text(
                          'Sudah punya akun? ',
                          style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
                        ),
                        TextButton(
                          onPressed: () => context.go(AppRoutes.login),
                          child: const Text('Masuk'),
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
    );
  }
}