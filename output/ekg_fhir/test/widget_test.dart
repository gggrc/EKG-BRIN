// test/widget_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

// Sesuaikan dengan path project asli Anda
import 'package:ekg_fhir/core/models/user_model.dart';
import 'package:ekg_fhir/core/providers/auth_provider.dart';
import 'package:ekg_fhir/features/history/history_page.dart';

/// Class pembantu untuk menyuntikkan mock user ke dalam AuthProvider saat testing.
/// Dengan melakukan `extends`, kita hanya perlu meng-override property yang dibutuhkan
/// oleh HistoryPage (yaitu `currentUser`) tanpa merusak fungsi auth lainnya.
class TestAuthProvider extends AuthProvider {
  final UserModel? _mockUser;

  TestAuthProvider(this._mockUser);

  @override
  UserModel? get currentUser => _mockUser;
}

void main() {
  // Helper widget untuk membungkus HistoryPage dengan Provider dan Router
  Widget createWidgetUnderTest({required UserModel user, required GoRouter router}) {
    return ChangeNotifierProvider<AuthProvider>(
      create: (_) => TestAuthProvider(user),
      child: MaterialApp.router(
        routerConfig: router,
      ),
    );
  }

  group('HistoryPage Widget Tests', () {
    late GoRouter mockRouter;

    setUp(() {
      // Setup router tiruan untuk menangani context.go() di dalam HistoryPage
      mockRouter = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(body: HistoryPage()),
          ),
          GoRoute(
            path: '/diagnosis/:id',
            builder: (context, state) => const Scaffold(body: Text('Halaman Diagnosis')),
          ),
          GoRoute(
            path: '/ecg/:id',
            builder: (context, state) => const Scaffold(body: Text('Halaman ECG Viewer')),
          ),
          GoRoute(
            path: '/report/:id',
            builder: (context, state) => const Scaffold(body: Text('Halaman Laporan')),
          ),
        ],
      );
    });

    testWidgets('Smoke Test: Komponen filter dan dropdown harus merender dengan benar', (WidgetTester tester) async {
      // 1. Siapkan mock data user dengan role Nakes
      final dummyNakes = UserModel(
        userId: 'nakes_123',
        email: 'dokter@hospital.com',
        name: 'Dr. Amelia',
        role: UserRole.nakes,
        createdAt: DateTime.now(),
      );

      // 2. Render komponen ke layar virtual test
      await tester.pumpWidget(createWidgetUnderTest(user: dummyNakes, router: mockRouter));
      await tester.pumpAndSettle();

      // 3. Validasi text field pencarian
      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('Cari nama pasien atau session ID...'), findsOneWidget);

      // 4. Validasi dropdown filter (secara default bernilai 'Semua')
      // Karena ada 2 dropdown (Status & Lead) yang default-nya 'Semua', maka harus ditemukan 2 widget.
      expect(find.text('Semua'), findsNWidgets(2));
    });

    testWidgets('RBAC Test: Akun Nakes harus bisa melihat tombol diagnosis & laporan', (WidgetTester tester) async {
      final dummyNakes = UserModel(
        userId: 'nakes_123',
        email: 'dokter@hospital.com',
        name: 'Dr. Amelia',
        role: UserRole.nakes,
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(createWidgetUnderTest(user: dummyNakes, router: mockRouter));
      await tester.pumpAndSettle();

      // Memastikan daftar list rekaman muncul
      expect(find.textContaining('rekaman EKG'), findsOneWidget);

      // Memastikan tombol 'Buka EKG Viewer' ada di setiap card
      expect(find.text('Buka EKG Viewer'), findsAtLeastNWidgets(1));

      // Memastikan tombol 'Laporan' muncul (karena nakes memiliki akses canViewAllPatients)
      expect(find.text('Laporan'), findsAtLeastNWidgets(1));
    });

    testWidgets('RBAC Test: Pasien tidak boleh melihat tombol Laporan global atau Tulis Diagnosis', (WidgetTester tester) async {
      final dummyPatient = UserModel(
        userId: 'pasien_999',
        email: 'budi@mail.com',
        name: 'Budi Santoso',
        role: UserRole.patient,
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(createWidgetUnderTest(user: dummyPatient, router: mockRouter));
      await tester.pumpAndSettle();

      // Pasien dilarang melihat tombol kelola medis seperti "Tulis Diagnosis" dan "Laporan"
      expect(find.text('Tulis Diagnosis'), findsNothing);
      expect(find.text('Laporan'), findsNothing);
    });
  });
}