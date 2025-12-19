/**
 * 認証コンテキスト
 * JWT認証状態を管理
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AppConfig } from '../config';
import { User } from '../types';
import * as authApi from '../api/auth';
import * as userApi from '../api/users';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * ユーザー情報を取得
   */
  const fetchUser = async () => {
    try {
      const token = apiClient.getToken();
      if (!token) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      const userData = await userApi.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      // トークンが無効な場合はクリア
      apiClient.clearToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * 初期化時にユーザー情報を取得
   */
  useEffect(() => {
    fetchUser();
  }, []);

  /**
   * ログイン
   */
  const login = async (username: string, password: string) => {
    try {
      const response = await authApi.login({ username, password });
      // ユーザー情報を取得
      await fetchUser();
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  /**
   * ユーザー登録
   */
  const register = async (username: string, email: string, password: string, name: string) => {
    try {
      const response = await authApi.register({ username, email, password, name });
      // ユーザー情報を取得
      await fetchUser();
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  /**
   * ログアウト
   */
  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setUser(null);
    }
  };

  /**
   * ユーザー情報を再取得
   */
  const refreshUser = async () => {
    await fetchUser();
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * useAuthフック
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

