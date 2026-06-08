// lib/core/providers/auth_provider.dart

import 'package:flutter/foundation.dart';
import '../models/user_model.dart';
import '../mock/mock_data.dart';

class AuthProvider extends ChangeNotifier {
  UserModel? _currentUser;
  bool _isLoading = false;
  String? _errorMessage;

  UserModel? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _currentUser != null;
  String? get errorMessage => _errorMessage;
  UserRole? get userRole => _currentUser?.role;

  // Mock login — in production, call API and store JWT
  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    // Simulate network delay
    await Future.delayed(const Duration(milliseconds: 800));

    try {
      // Find user by email in mock data
      final user = MockData.users.where((u) => u.email == email).firstOrNull;

      if (user == null) {
        _errorMessage = 'Email tidak ditemukan';
        _isLoading = false;
        notifyListeners();
        return false;
      }

      // In mock: accept any password, or 'demo123'
      if (password != 'demo123' && password.isNotEmpty) {
        _errorMessage = 'Password salah. Gunakan: demo123';
        _isLoading = false;
        notifyListeners();
        return false;
      }

      _currentUser = user;
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = 'Terjadi kesalahan. Coba lagi.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // Quick login for demo
  Future<bool> loginAsRole(UserRole role) async {
    final creds = MockData.demoCredentials[role];
    if (creds == null) return false;
    return login(creds['email']!, creds['password']!);
  }

  void logout() {
    _currentUser = null;
    _errorMessage = null;
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}
