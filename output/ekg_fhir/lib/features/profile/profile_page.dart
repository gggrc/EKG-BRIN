// lib/features/profile/profile_page.dart
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
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _institutionCtrl = TextEditingController();
  final _specialtyCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    final user = context.read<AuthProvider>().currentUser;
    _nameCtrl.text = user?.name ?? '';
    _phoneCtrl.text = user?.phoneNumber ?? '';
    _institutionCtrl.text = user?.institution ?? '';
    _specialtyCtrl.text = user?.specialty ?? '';
  }

  Color _roleColor(UserRole role) {
    switch (role) {
      case UserRole.patient: return AppColors.rolePatient;
      case UserRole.clinician: return AppColors.roleClinician;
      case UserRole.admin: return AppColors.roleAdmin;
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().currentUser;
    if (user == null) return const SizedBox.shrink();

    final roleColor = _roleColor(user.role);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Profile card
          Container(
            width: 300,
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.borderLight)),
            child: Column(
              children: [
                // Avatar
                Container(
                  width: 80, height: 80,
                  decoration: BoxDecoration(
                    gradient: AppColors.primaryGradient,
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(color: AppColors.primary.withOpacity(0.3), blurRadius: 20, offset: const Offset(0, 8))],
                  ),
                  child: Center(
                    child: Text(
                      user.name.split(' ').take(2).map((w) => w[0]).join(),
                      style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(user.name, textAlign: TextAlign.center, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                const SizedBox(height: 6),
                Text(user.email, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: roleColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(user.role.icon, style: const TextStyle(fontSize: 16)),
                      const SizedBox(width: 6),
                      Text(user.role.displayName, style: TextStyle(fontSize: 13, color: roleColor, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
                if (user.institution != null) ...[
                  const SizedBox(height: 12),
                  Text(user.institution!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                ],
                if (user.specialty != null) ...[
                  const SizedBox(height: 4),
                  Text(user.specialty!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: AppColors.primary)),
                ],
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () {
                      context.read<AuthProvider>().logout();
                      context.go(AppRoutes.login);
                    },
                    icon: const Icon(Icons.logout_rounded, size: 16, color: AppColors.danger),
                    label: const Text('Keluar', style: TextStyle(color: AppColors.danger)),
                    style: OutlinedButton.styleFrom(side: const BorderSide(color: AppColors.danger)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 24),
          // Settings / Edit form
          Expanded(
            child: Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.borderLight)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text('Informasi Akun', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                          const Spacer(),
                          TextButton.icon(
                            onPressed: () => setState(() => _isEditing = !_isEditing),
                            icon: Icon(_isEditing ? Icons.close_rounded : Icons.edit_rounded, size: 16),
                            label: Text(_isEditing ? 'Batal' : 'Edit Profil'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      if (_isEditing) ...[
                        TextFormField(
                          controller: _nameCtrl,
                          decoration: const InputDecoration(labelText: 'Nama Lengkap', prefixIcon: Icon(Icons.person_outline, size: 18)),
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _phoneCtrl,
                          decoration: const InputDecoration(labelText: 'No. Telepon', prefixIcon: Icon(Icons.phone_outlined, size: 18)),
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _institutionCtrl,
                          decoration: const InputDecoration(labelText: 'Institusi', prefixIcon: Icon(Icons.business_outlined, size: 18)),
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _specialtyCtrl,
                          decoration: const InputDecoration(labelText: 'Spesialitas / Bidang', prefixIcon: Icon(Icons.star_outline_rounded, size: 18)),
                        ),
                        const SizedBox(height: 20),
                        Row(
                          children: [
                            ElevatedButton(
                              onPressed: () {
                                context.read<AuthProvider>().updateProfile(
                                  name: _nameCtrl.text,
                                  phone: _phoneCtrl.text.isEmpty ? null : _phoneCtrl.text,
                                  institution: _institutionCtrl.text.isEmpty ? null : _institutionCtrl.text,
                                  specialty: _specialtyCtrl.text.isEmpty ? null : _specialtyCtrl.text,
                                );
                                setState(() => _isEditing = false);
                                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Profil berhasil diperbarui')));
                              },
                              child: const Text('Simpan Perubahan'),
                            ),
                          ],
                        ),
                      ] else ...[
                        _ProfileRow(label: 'Nama', value: user.name),
                        _ProfileRow(label: 'Email', value: user.email),
                        _ProfileRow(label: 'User ID', value: user.userId, mono: true),
                        if (user.phoneNumber != null) _ProfileRow(label: 'Telepon', value: user.phoneNumber!),
                        if (user.institution != null) _ProfileRow(label: 'Institusi', value: user.institution!),
                        if (user.specialty != null) _ProfileRow(label: 'Spesialitas', value: user.specialty!),
                        _ProfileRow(label: 'Terdaftar', value: '${user.createdAt.day}/${user.createdAt.month}/${user.createdAt.year}'),
                        _ProfileRow(label: 'Status', value: user.isActive ? 'Aktif' : 'Nonaktif'),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                // Permissions card
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.borderLight)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Hak Akses Anda', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _PermChip(label: 'Lihat EKG Sendiri', granted: true),
                          _PermChip(label: 'Lihat Semua Pasien', granted: user.canViewAllPatients),
                          _PermChip(label: 'Input Pasien', granted: user.canInputPatient),
                          _PermChip(label: 'Akuisisi Sinyal', granted: user.canAcquireSignal),
                          _PermChip(label: 'Tulis Diagnosis', granted: user.canWriteDiagnosis),
                          _PermChip(label: 'Approve Diagnosis', granted: user.canApproveDiagnosis),
                          _PermChip(label: 'FHIR Export', granted: user.canExportFHIR),
                          _PermChip(label: 'Interpretasi AI', granted: user.canViewAIInterpretation),
                          _PermChip(label: 'Admin Panel', granted: user.canAccessAdmin),
                          _PermChip(label: 'Export Dataset', granted: user.canExportDataset),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                // Security card
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.borderLight)),
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
          ),
        ],
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
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          SizedBox(width: 140, child: Text(label, style: const TextStyle(fontSize: 13, color: AppColors.textMuted))),
          Expanded(
            child: Text(
              value,
              style: TextStyle(fontSize: 13, color: AppColors.textPrimary, fontWeight: FontWeight.w500, fontFamily: mono ? 'monospace' : null),
            ),
          ),
        ],
      ),
    );
  }
}

class _PermChip extends StatelessWidget {
  final String label;
  final bool granted;
  const _PermChip({required this.label, required this.granted});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: granted ? AppColors.successContainer : AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(granted ? Icons.check_rounded : Icons.close_rounded, size: 12, color: granted ? AppColors.success : AppColors.textMuted),
          const SizedBox(width: 5),
          Text(label, style: TextStyle(fontSize: 11, color: granted ? AppColors.success : AppColors.textMuted, fontWeight: granted ? FontWeight.w600 : FontWeight.w400)),
        ],
      ),
    );
  }
}
