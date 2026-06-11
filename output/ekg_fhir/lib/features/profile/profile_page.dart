// lib/features/profile/profile_page.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/models/user_model.dart';
import '../../core/router/app_router.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _isEditing = false;
  bool _isSavingLocal = false; // Mengunci loading lokal agar rendering bersifat parsial
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  String _selectedGender = 'unknown';

  final List<Map<String, dynamic>> _genderOptions = [
    {'value': 'male',   'label': 'Laki-laki',  'icon': Icons.man},
    {'value': 'female', 'label': 'Perempuan',  'icon': Icons.woman},
    {'value': 'unknown', 'label': 'Dirahasiakan', 'icon': Icons.help_outline_rounded},
  ];

  @override
  void initState() {
    super.initState();
    _initFields();
  }

  void _initFields() {
    final user = context.read<AuthProvider>().currentUser;
    
    // Jika 'user' bisa null (karena tidak ada guard clause di atasnya), 
    // pastikan property internal seperti gender (yang bertipe String, bukan String?) menggunakan '.' biasa
    if (user != null) {
      _nameCtrl.text = user.name;
      _phoneCtrl.text = user.phoneNumber;
      
      // PERBAIKAN: Ganti 'user?.gender?.trim()' menjadi 'user.gender.trim()'
      // Karena di user_model.dart, 'gender' didefinisikan sebagai String (bukan String?)
      final rawGender = user.gender.trim().toLowerCase();
      if (rawGender == 'm' || rawGender == 'laki-laki' || rawGender == 'male') {
        _selectedGender = 'male';
      } else if (rawGender == 'f' || rawGender == 'perempuan' || rawGender == 'female') {
        _selectedGender = 'female';
      } else {
        _selectedGender = 'unknown';
      }
    } else {
      // Fallback jika user benar-benar null saat inisialisasi
      _nameCtrl.text = '';
      _phoneCtrl.text = '';
      _selectedGender = 'unknown';
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  Color _roleColor(UserRole role) {
    switch (role) {
      case UserRole.patient: return AppColors.rolePatient;
      case UserRole.nakes: return AppColors.roleNakes;
      case UserRole.admin: return AppColors.roleAdmin;
    }
  }

  IconData _roleIconData(UserRole role) {
    switch (role) {
      case UserRole.patient: return Icons.person_rounded;
      case UserRole.nakes: return Icons.medical_services_rounded;
      case UserRole.admin: return Icons.admin_panel_settings_rounded;
    }
  }

  /// Menampilkan popup sukses kustom dengan durasi transisi in/out
  void _showAnimatedSuccessDialog(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: true,
      barrierColor: Colors.black.withOpacity(0.2), // Membuat transparansi background luar menjadi lebih terang/tidak terlalu gelap
      builder: (BuildContext dialogContext) {
        return const _SuccessAnimatedDialog();
      },
    );
  }

  Future<void> _saveProfileChanges() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSavingLocal = true;
    });

    final authProvider = context.read<AuthProvider>();
    
    // Kirim payload perubahan data murni ke database di latar belakang (Mekanisme AJAX-like)
    final success = await authProvider.updateProfile(
      name: _nameCtrl.text,
      phoneNumber: _phoneCtrl.text,
      gender: _selectedGender,
    );

    if (mounted) {
      setState(() {
        _isSavingLocal = false;
      });

      if (success) {
        // Pemicu tampilan popup kustom
        _showAnimatedSuccessDialog(context);
        
        setState(() {
          _isEditing = false; // Kembalikan komponen text ke mode baca parsial
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(authProvider.errorMessage ?? 'Gagal memperbarui profil.'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authWatch = context.watch<AuthProvider>();
    final user = authWatch.currentUser;
    if (user == null) return const SizedBox.shrink();

    final roleColor = _roleColor(user.role);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch, 
        children: [
          // 1. ATAS: Card Ringkasan Profil Utama
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.surface, 
              borderRadius: BorderRadius.circular(16), 
              border: Border.all(color: AppColors.borderLight),
            ),
            child: Row(
              children: [
                Container(
                  width: 72, height: 72,
                  decoration: BoxDecoration(
                    gradient: AppColors.primaryGradient,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary.withOpacity(0.25), 
                        blurRadius: 16, 
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Center(
                    child: Text(
                      user.name.split(' ').take(2).map((w) => w.isNotEmpty ? w[0] : '').join(),
                      style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                const SizedBox(width: 20),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.name.trim().isEmpty ? '-' : user.name, 
                        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
                      ),
                      const SizedBox(height: 4),
                      Text(user.email, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                      decoration: BoxDecoration(
                        color: roleColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(_roleIconData(user.role), size: 16, color: roleColor),
                          const SizedBox(width: 6),
                          Text(
                            user.role.displayName, 
                            style: TextStyle(fontSize: 13, color: roleColor, fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: _isSavingLocal ? null : () {
                        context.read<AuthProvider>().logout();
                        context.go(AppRoutes.login);
                      },
                      icon: const Icon(Icons.logout_rounded, size: 14, color: AppColors.danger),
                      label: const Text('Keluar', style: TextStyle(fontSize: 12, color: AppColors.danger)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppColors.danger),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          
          // 2. TENGAH: Form Detil Informasi Akun
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.surface, 
              borderRadius: BorderRadius.circular(16), 
              border: Border.all(color: AppColors.borderLight),
            ),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Text(
                        'Informasi Akun', 
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: _isSavingLocal ? null : () {
                          setState(() {
                            if (_isEditing) {
                              _initFields(); 
                            }
                            _isEditing = !_isEditing;
                          });
                        },
                        icon: Icon(_isEditing ? Icons.close_rounded : Icons.edit_rounded, size: 16),
                        label: Text(_isEditing ? 'Batal' : 'Edit Profil'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  
                  if (_isEditing) ...[
                    TextFormField(
                      controller: _nameCtrl,
                      decoration: const InputDecoration(labelText: 'Nama Lengkap', prefixIcon: Icon(Icons.person_outline, size: 18)),
                      validator: (v) => v == null || v.trim().isEmpty ? 'Nama wajib diisi' : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _phoneCtrl,
                      keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(labelText: 'No. Telepon', prefixIcon: Icon(Icons.phone_outlined, size: 18)),
                      validator: (v) => v == null || v.trim().isEmpty ? 'Nomor telepon wajib diisi' : null,
                    ),
                    const SizedBox(height: 20),
                    
                    const Text(
                      'Jenis Kelamin',
                      style: TextStyle(fontSize: 14, color: AppColors.textSecondary, fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(height: 10),
                    
                    Wrap(
                      spacing: 12,
                      runSpacing: 10,
                      children: _genderOptions.map((opt) {
                        final isSelected = _selectedGender == opt['value'];
                        return GestureDetector(
                          onTap: () => setState(() => _selectedGender = opt['value']),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 150),
                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                            decoration: BoxDecoration(
                              color: isSelected ? AppColors.primary.withOpacity(0.12) : AppColors.surfaceVariant,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: isSelected ? AppColors.primary : Colors.transparent,
                                width: 1.5,
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  opt['icon'] as IconData,
                                  size: 18,
                                  color: isSelected ? AppColors.primary : AppColors.textSecondary,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  opt['label'] as String,
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                                    color: isSelected ? AppColors.primary : AppColors.textSecondary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 24),
                    
                    Row(
                      children: [
                        ElevatedButton(
                          onPressed: _isSavingLocal ? null : _saveProfileChanges,
                          child: _isSavingLocal
                              ? const SizedBox(
                                  height: 16, width: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                )
                              : const Text('Simpan Perubahan'),
                        ),
                      ],
                    ),
                  ] else ...[
                    _ProfileRow(
                      label: 'Nama Lengkap', 
                      value: (user.name.trim().isEmpty || user.name.toLowerCase() == 'unknown') ? '-' : user.name,
                    ),
                    _ProfileRow(
                      label: 'Email', 
                      value: (user.email.trim().isEmpty || user.email.toLowerCase() == 'unknown') ? '-' : user.email,
                    ),
                    _ProfileRow(
                      label: 'Jenis Kelamin', 
                      value: () {
                        final g = user.gender.trim().toLowerCase();
                        if (g == 'male' || g == 'm' || g == 'laki-laki') return 'Laki-laki';
                        if (g == 'female' || g == 'f' || g == 'perempuan') return 'Perempuan';
                        return 'Rahasia';
                      }(),
                    ),
                    _ProfileRow(
                      label: 'User ID', 
                      value: user.userId.trim().isEmpty ? '-' : user.userId, 
                      mono: true,
                    ),
                    _ProfileRow(
                      label: 'No. Telepon', 
                      value: (user.phoneNumber.trim().isEmpty || user.phoneNumber.toLowerCase() == 'unknown') ? '-' : user.phoneNumber,
                    ),
                    _ProfileRow(
                      label: 'Terdaftar', 
                      value: '${user.createdAt.day}/${user.createdAt.month}/${user.createdAt.year}',
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          
          // 3. BAWAH: Card Keamanan Akun
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.surface, 
              borderRadius: BorderRadius.circular(16), 
              border: Border.all(color: AppColors.borderLight),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Keamanan', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                const SizedBox(height: 16),
                ListTile(
                  leading: const Icon(Icons.lock_outlined, color: AppColors.primary),
                  title: const Text('Ganti Password', style: TextStyle(fontSize: 14, color: AppColors.textPrimary)),
                  trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.textMuted),
                  onTap: () {},
                  contentPadding: EdgeInsets.zero,
                ),
                const Divider(color: AppColors.borderLight),
                ListTile(
                  leading: const Icon(Icons.history_rounded, color: AppColors.secondary),
                  title: const Text('Riwayat Login', style: TextStyle(fontSize: 14, color: AppColors.textPrimary)),
                  trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.textMuted),
                  onTap: () {},
                  contentPadding: EdgeInsets.zero,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── CUSTOM ANIMATED DIALOG CLASS (DURASI 1 DETIK + TRANSPARANSI TERANG) ───
class _SuccessAnimatedDialog extends StatefulWidget {
  const _SuccessAnimatedDialog();

  @override
  State<_SuccessAnimatedDialog> createState() => _SuccessAnimatedDialogState();
}

class _SuccessAnimatedDialogState extends State<_SuccessAnimatedDialog> with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _fadeAnimation;
  Timer? _autoDismissTimer;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );

    _scaleAnimation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutBack,
    );

    _fadeAnimation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeIn,
    );

    _animController.forward();

    // Diubah durasinya menjadi 1 detik saja sesuai permintaan
    _autoDismissTimer = Timer(const Duration(seconds: 1), () {
      _closeWithAnimation();
    });
  }

  @override
  void dispose() {
    _autoDismissTimer?.cancel();
    _animController.dispose();
    super.dispose();
  }

  void _closeWithAnimation() {
    if (!mounted) return;
    _animController.reverse().then((_) {
      if (mounted) {
        Navigator.of(context).pop();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: Material(
            color: Colors.transparent,
            child: Container(
              width: 310,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
              decoration: BoxDecoration(
                color: Colors.white, // Background solid putih terang
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  )
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Icon Lingkaran Centang Hijau Elegan
                  Stack(
                    alignment: Alignment.center,
                    children: [
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F8F0),
                          shape: BoxShape.circle,
                          border: Border.all(color: const Color(0xFF22C55E).withOpacity(0.2), width: 1.5),
                        ),
                      ),
                      const Icon(
                        Icons.check_circle_outline_rounded,
                        color: Color(0xFF22C55E),
                        size: 60,
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  
                  // Text Judul SUCCESS!
                  const Text(
                    'SUCCESS!',
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF22C55E),
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 12),
                  
                  // Deskripsi Subtitle
                  const Text(
                    'Informasi berhasil disimpan.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: Color(0xFF64748B),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 28),
                  
                  // Tombol DONE Kustom Capsule
                  SizedBox(
                    width: double.infinity,
                    height: 46,
                    child: ElevatedButton(
                      onPressed: _closeWithAnimation,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF22C55E),
                        foregroundColor: Colors.white,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(24),
                        ),
                      ),
                      child: const Text(
                        'DONE',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ProfileRow extends StatelessWidget {
  final String label;
  final String value;
  final bool mono;
  const _ProfileRow({required this.label, required this.value, this.mono = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          SizedBox(width: 160, child: Text(label, style: const TextStyle(fontSize: 13, color: AppColors.textMuted))),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 13, 
                color: AppColors.textPrimary, 
                fontWeight: FontWeight.w500, 
                fontFamily: mono ? 'monospace' : null,
              ),
            ),
          ),
        ],
      ),
    );
  }
}