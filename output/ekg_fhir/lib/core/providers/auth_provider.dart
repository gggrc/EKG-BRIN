// lib/core/providers/auth_provider.dart

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/user_model.dart';

class AuthProvider extends ChangeNotifier {
  final _supabase = Supabase.instance.client;

  UserModel? _currentUser;
  bool _isLoading = true;
  String? _errorMessage;

  late final StreamSubscription<AuthState> _authSubscription;

  static const Map<UserRole, Map<String, String>> _demoCredentials = {
    UserRole.patient: {
      'email'   : 'demo.patient@ekgbrin.id',
      'password': 'demo123',
    },
    UserRole.nakes: {
      'email'   : 'demo.nakes@ekgbrin.id',
      'password': 'demo123',
    },
    UserRole.admin: {
      'email'   : 'demo.admin@ekgbrin.id',
      'password': 'demo123',
    },
  };

  UserModel? get currentUser   => _currentUser;
  bool get isLoading           => _isLoading;
  bool get isAuthenticated     => _currentUser != null;
  String? get errorMessage     => _errorMessage;
  UserRole? get userRole       => _currentUser?.role;

  AuthProvider() {
    _init();
  }

  Future<void> _init() async {
    // ── Tangkap OAuth error baik dari Hash Fragment maupun Standard Query ──
    if (kIsWeb) {
      final uri = Uri.base;
      String? errorDesc;

      if (uri.queryParameters.containsKey('error')) {
        errorDesc = uri.queryParameters['error_description'];
      } else if (uri.toString().contains('error=')) {
        final parsedUri = Uri.parse(uri.toString().replaceAll('#', '?'));
        errorDesc = parsedUri.queryParameters['error_description'];
      } else if (uri.fragment.isNotEmpty) {
        final fragmentParams = Uri.splitQueryString(uri.fragment);
        if (fragmentParams.containsKey('error')) {
          errorDesc = fragmentParams['error_description'];
        }
      }

      if (errorDesc != null) {
        _errorMessage = Uri.decodeComponent(errorDesc.replaceAll('+', ' ')).split('#').first;
        _isLoading    = false;
        _currentUser  = null;
        notifyListeners();
        return;
      }
    }

    try {
      final session = _supabase.auth.currentSession;
      if (session != null) {
        await _loadUserProfile(session.user);
      }
    } catch (e) {
      debugPrint('Initial session restore error: $e');
      _currentUser = null;
    }

    _authSubscription = _supabase.auth.onAuthStateChange.listen(
      (data) async {
        final event = data.event;
        final session = data.session;

        switch (event) {
          case AuthChangeEvent.signedIn:
          case AuthChangeEvent.tokenRefreshed:
          case AuthChangeEvent.userUpdated:
            if (session != null) {
              _isLoading = true;
              notifyListeners();
              await _loadUserProfile(session.user);
            }
            break;
          case AuthChangeEvent.signedOut:
            _currentUser = null;
            _errorMessage = null;
            break;
          default:
            break;
        }

        _isLoading = false;
        notifyListeners();
      },
      onError: (error) {
        debugPrint('Auth stream error: $error');
        _currentUser  = null;
        _isLoading    = false;
        
        if (error is AuthException) {
          if (error.message.contains('refresh_token_not_found') || error.statusCode == '400') {
            _errorMessage = 'Sesi Anda telah berakhir. Silakan masuk kembali.';
          } else {
            _errorMessage = error.message;
          }
        } else if (error.toString().contains('refresh_token_not_found')) {
          _errorMessage = 'Sesi Anda telah berakhir. Silakan masuk kembali.';
        } else {
          _errorMessage = 'Gagal melakukan verifikasi akun.';
        }
        notifyListeners();
      },
    );

    if (_supabase.auth.currentSession == null) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> _loadUserProfile(User supabaseUser) async {
    try {
      final existing = await _supabase
          .from('users')
          .select()
          .eq('user_id', supabaseUser.id)
          .maybeSingle();

      if (existing != null) {
        _currentUser = UserModel.fromJson(existing);
        return;
      }

      final meta      = supabaseUser.userMetadata ?? {};
      final fullName  = (meta['full_name'] ?? meta['name'] ?? '').toString().trim();
      final email     = supabaseUser.email ?? '';

      final newProfile = {
        'user_id'     : supabaseUser.id,
        'full_name'   : fullName.isNotEmpty ? fullName : 'unknown',
        'email'       : email.isNotEmpty    ? email    : 'unknown',
        'gender'      : (meta['gender']?.toString() ?? 'unknown').isNotEmpty
                          ? meta['gender'].toString()
                          : 'unknown',
        'phone_number': (meta['phone_number']?.toString() ?? '').isNotEmpty
                          ? meta['phone_number'].toString()
                          : 'unknown',
        'role'        : (meta['role']?.toString() ?? UserRole.patient.dbValue),
      };

      await _supabase.from('users').upsert(
        newProfile,
        onConflict      : 'user_id',
        ignoreDuplicates: false,
      );

      final inserted = await _supabase
          .from('users')
          .select()
          .eq('user_id', supabaseUser.id)
          .maybeSingle();

      if (inserted != null) {
        _currentUser = UserModel.fromJson(inserted);
      } else {
        throw Exception('Data profile gagal tersimpan di database.');
      }
    } on PostgrestException catch (e) {
      debugPrint('Load/upsert user profile error: ${e.message} (code: ${e.code})');
      
      if (_supabase.auth.currentSession != null) {
        final meta = supabaseUser.userMetadata ?? {};
        _currentUser = UserModel(
          userId   : supabaseUser.id,
          email    : supabaseUser.email ?? 'unknown',
          name     : (meta['full_name'] ?? meta['name'] ?? 'unknown').toString(),
          role     : UserRoleExtension.fromString(meta['role']?.toString()),
          gender   : meta['gender']?.toString() ?? 'unknown',
          phoneNumber: meta['phone_number']?.toString() ?? 'unknown',
          createdAt: DateTime.now(),
        );
      } else {
        _currentUser = null;
        _errorMessage = 'Akses ditolak (RLS Violations). Silakan login ulang.';
      }
    } catch (e) {
      debugPrint('Unexpected profile loading error: $e');
      _currentUser = null;
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading    = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _supabase.auth.signInWithPassword(
        email   : email.trim(),
        password: password,
      );
      return true;
    } on AuthException catch (e) {
      _errorMessage = _mapAuthError(e.message);
      _isLoading    = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'Terjadi kesalahan. Coba lagi.';
      _isLoading    = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> loginAsRole(UserRole role) async {
    final creds = _demoCredentials[role];
    if (creds == null) return false;
    return login(creds['email']!, creds['password']!);
  }

  Future<void> loginWithGoogle() async {
    _isLoading    = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _supabase.auth.signInWithOAuth(
        OAuthProvider.google,
        redirectTo: kIsWeb
            ? '${Uri.base.origin}/auth/callback'
            : 'io.supabase.ekgbrin://login-callback/',
        authScreenLaunchMode: LaunchMode.platformDefault,
      );
    } on AuthException catch (e) {
      _errorMessage = _mapAuthError(e.message);
      _isLoading    = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = 'Login Google gagal: $e';
      _isLoading    = false;
      notifyListeners();
    }
  }

  Future<bool> updateProfile({
    required String name,
    required String phoneNumber,
    required String gender,
  }) async {
    if (_currentUser == null) return false;
    _errorMessage = null;

    try {
      final updatedData = {
        'user_id': _currentUser!.userId,
        'full_name': name.trim().isNotEmpty ? name.trim() : 'unknown',
        'phone_number': phoneNumber.trim().isNotEmpty ? phoneNumber.trim() : 'unknown',
        'gender': gender.isNotEmpty ? gender : 'unknown',
        'email': _currentUser!.email,
        'role': _currentUser!.role.dbValue,
      };

      // 1. Eksekusi asinkron ke server Supabase
      await _supabase.from('users').upsert(
            updatedData,
            onConflict: 'user_id',
            ignoreDuplicates: false,
          );

      // 2. Manipulasi data lokal secara parsial (Analog dengan manipulasi elemen DOM tertentu saja)
      _currentUser = _currentUser!.copyWith(
        name: name.trim().isNotEmpty ? name.trim() : 'unknown',
        phoneNumber: phoneNumber.trim().isNotEmpty ? phoneNumber.trim() : 'unknown',
        gender: gender.isNotEmpty ? gender : 'unknown',
      );

      // 3. Beritahu widget yang mendengarkan agar merender ulang komponen teks yang bersangkutan saja
      notifyListeners(); 
      return true;
    } on PostgrestException catch (e) {
      debugPrint('Silent update error: ${e.message}');
      _errorMessage = 'Gagal menyimpan ke database: ${e.message}';
      return false;
    } catch (e) {
      debugPrint('Silent update unexpected error: $e');
      _errorMessage = 'Terjadi kesalahan sistem.';
      return false;
    }
  }

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();
    try {
      await _supabase.auth.signOut();
    } catch (_) {}
    _currentUser  = null;
    _errorMessage = null;
    _isLoading    = false;
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  void setError(String message) {
    _errorMessage = message;
    notifyListeners();
  }

  void clearLoading() {
    _isLoading = false;
    notifyListeners();
  }

  String _mapAuthError(String message) {
    if (message.contains('Invalid login credentials')) {
      return 'Email atau password salah.';
    }
    if (message.contains('Email not confirmed')) {
      return 'Email belum diverifikasi. Cek inbox Anda.';
    }
    if (message.contains('Too many requests')) {
      return 'Terlalu banyak percobaan. Coba lagi nanti.';
    }
    return message;
  }

  @override
  void dispose() {
    _authSubscription.cancel();
    super.dispose();
  }
}