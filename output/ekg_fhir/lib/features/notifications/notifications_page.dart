// lib/features/notifications/notifications_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/mock/mock_data.dart';
import '../../core/models/ecg_models.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  List<NotificationModel> _notifications = [];

  @override
  void initState() {
    super.initState();
    _notifications = List.from(MockData.notifications);
  }

  void _markAllRead() {
    setState(() {
      _notifications = _notifications.map((n) => NotificationModel(
        notificationId: n.notificationId,
        title: n.title,
        body: n.body,
        type: n.type,
        isRead: true,
        createdAt: n.createdAt,
        relatedSessionId: n.relatedSessionId,
      )).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    final unread = _notifications.where((n) => !n.isRead).length;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Notifikasi', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
              if (unread > 0) ...[
                const SizedBox(width: 10),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: AppColors.danger, borderRadius: BorderRadius.circular(10)),
                  child: Text('$unread baru', style: const TextStyle(fontSize: 11, color: Colors.white, fontWeight: FontWeight.w700)),
                ),
              ],
              const Spacer(),
              if (unread > 0)
                TextButton.icon(
                  onPressed: _markAllRead,
                  icon: const Icon(Icons.done_all_rounded, size: 16),
                  label: const Text('Tandai Semua Dibaca'),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.separated(
              itemCount: _notifications.length,
              separatorBuilder: (_, __) => const SizedBox(height: 6),
              itemBuilder: (context, i) {
                final n = _notifications[i];
                return _NotifCard(
                  notification: n,
                  onTap: () {
                    setState(() {
                      _notifications[i] = NotificationModel(
                        notificationId: n.notificationId,
                        title: n.title,
                        body: n.body,
                        type: n.type,
                        isRead: true,
                        createdAt: n.createdAt,
                        relatedSessionId: n.relatedSessionId,
                      );
                    });
                    if (n.relatedSessionId != null) {
                      context.go('/ecg/${n.relatedSessionId}');
                    }
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _NotifCard extends StatelessWidget {
  final NotificationModel notification;
  final VoidCallback onTap;
  const _NotifCard({required this.notification, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final n = notification;
    final typeColors = {
      'ecg_result': AppColors.primary,
      'alert': AppColors.danger,
      'diagnosis': AppColors.success,
      'system': AppColors.textMuted,
    };
    final typeIcons = {
      'ecg_result': Icons.monitor_heart_rounded,
      'alert': Icons.warning_amber_rounded,
      'diagnosis': Icons.medical_information_rounded,
      'system': Icons.settings_rounded,
    };
    final color = typeColors[n.type] ?? AppColors.textMuted;
    final icon = typeIcons[n.type] ?? Icons.notifications_rounded;

    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: n.isRead ? AppColors.surface : color.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: n.isRead ? AppColors.borderLight : color.withOpacity(0.3)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44, height: 44,
              decoration: BoxDecoration(color: color.withOpacity(0.12), borderRadius: BorderRadius.circular(10)),
              child: Icon(icon, color: color, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          n.title,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: n.isRead ? FontWeight.w500 : FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ),
                      if (!n.isRead)
                        Container(
                          width: 8, height: 8,
                          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(n.body, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, height: 1.5)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Text(
                        '${n.createdAt.day}/${n.createdAt.month}/${n.createdAt.year}  ${n.createdAt.hour.toString().padLeft(2, '0')}:${n.createdAt.minute.toString().padLeft(2, '0')}',
                        style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                      ),
                      if (n.relatedSessionId != null) ...[
                        const Spacer(),
                        Text('Lihat Detail →', style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500)),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
