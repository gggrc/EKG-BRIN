// lib/features/admin/user_management_page.dart
import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/models/user_model.dart';

class UserManagementPage extends StatefulWidget {
  const UserManagementPage({super.key});

  @override
  State<UserManagementPage> createState() => _UserManagementPageState();
}

class _UserManagementPageState extends State<UserManagementPage> {
  String _search = '';
  UserRole? _roleFilter;

  @override
  Widget build(BuildContext context) {
    final allUsers = MockData.allUsersList;
    final filtered = allUsers.where((u) {
      final user = u['user'] as UserModel;
      final matchSearch = user.name.toLowerCase().contains(_search.toLowerCase()) ||
          user.email.toLowerCase().contains(_search.toLowerCase());
      final matchRole = _roleFilter == null || user.role == _roleFilter;
      return matchSearch && matchRole;
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  onChanged: (v) => setState(() => _search = v),
                  decoration: const InputDecoration(
                    hintText: 'Cari nama atau email...',
                    prefixIcon: Icon(Icons.search, size: 18),
                    contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              DropdownButton<UserRole?>(
                value: _roleFilter,
                dropdownColor: AppColors.surface,
                hint: const Text('Semua Role', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                underline: const SizedBox(),
                items: [
                  const DropdownMenuItem(value: null, child: Text('Semua Role')),
                  ...UserRole.values.map((r) => DropdownMenuItem(value: r, child: Text(r.displayName))),
                ],
                onChanged: (v) => setState(() => _roleFilter = v),
              ),
              const SizedBox(width: 16),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.person_add_rounded, size: 16),
                label: const Text('Tambah User'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Header row
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(color: AppColors.surfaceVariant, borderRadius: BorderRadius.circular(8)),
            child: const Row(
              children: [
                Expanded(flex: 3, child: Text('Nama', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted))),
                Expanded(flex: 3, child: Text('Email', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted))),
                Expanded(flex: 2, child: Text('Role', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted))),
                Expanded(flex: 2, child: Text('Institusi', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted))),
                Expanded(child: Text('Login Terakhir', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted))),
                SizedBox(width: 80, child: Text('Aksi', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textMuted))),
              ],
            ),
          ),
          const SizedBox(height: 4),
          Expanded(
            child: ListView.separated(
              itemCount: filtered.length,
              separatorBuilder: (_, __) => const SizedBox(height: 4),
              itemBuilder: (context, i) {
                final userData = filtered[i];
                final user = userData['user'] as UserModel;
                final lastLogin = userData['lastLogin'] as DateTime;
                final isActive = userData['isActive'] as bool;
                final roleColor = _roleColor(user.role);

                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.borderLight),
                  ),
                  child: Row(
                    children: [
                      Expanded(flex: 3, child: Row(
                        children: [
                          CircleAvatar(
                            radius: 16,
                            backgroundColor: roleColor.withOpacity(0.15),
                            child: Text(user.name[0], style: TextStyle(color: roleColor, fontWeight: FontWeight.w700, fontSize: 13)),
                          ),
                          const SizedBox(width: 10),
                          Expanded(child: Text(user.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: AppColors.textPrimary), overflow: TextOverflow.ellipsis)),
                        ],
                      )),
                      Expanded(flex: 3, child: Text(user.email, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary), overflow: TextOverflow.ellipsis)),
                      Expanded(flex: 2, child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(color: roleColor.withOpacity(0.12), borderRadius: BorderRadius.circular(4)),
                        child: Text(user.role.shortName, style: TextStyle(fontSize: 11, color: roleColor, fontWeight: FontWeight.w600)),
                      )),
                      Expanded(flex: 2, child: Text(user.institution ?? '-', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary), overflow: TextOverflow.ellipsis)),
                      Expanded(child: Text(
                        _timeAgo(lastLogin),
                        style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                      )),
                      SizedBox(
                        width: 80,
                        child: Row(
                          children: [
                            IconButton(
                              icon: const Icon(Icons.edit_rounded, size: 16),
                              onPressed: () {},
                              color: AppColors.textSecondary,
                              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                              padding: EdgeInsets.zero,
                              tooltip: 'Edit',
                            ),
                            IconButton(
                              icon: Icon(isActive ? Icons.block_rounded : Icons.check_circle_rounded, size: 16),
                              onPressed: () {},
                              color: isActive ? AppColors.warning : AppColors.success,
                              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                              padding: EdgeInsets.zero,
                              tooltip: isActive ? 'Nonaktifkan' : 'Aktifkan',
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Color _roleColor(UserRole role) {
    switch (role) {
      case UserRole.patient: return AppColors.rolePatient;
      case UserRole.clinician: return AppColors.roleClinician;
      case UserRole.admin: return AppColors.roleAdmin;
    }
  }

  String _timeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inHours < 1) return '${diff.inMinutes} menit lalu';
    if (diff.inHours < 24) return '${diff.inHours} jam lalu';
    return '${diff.inDays} hari lalu';
  }
}
