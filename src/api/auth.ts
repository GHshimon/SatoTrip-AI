/**
 * 認証API
 */
import { apiClient } from './client';
import { AppConfig } from '../../config';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  email: string;
  role: string;
}

export interface TokenRefreshRequest {
  refresh_token: string;
}

/**
 * ログイン
 */
export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', credentials);
  // トークンを自動保存
  if (response.access_token) {
    apiClient.setToken(response.access_token);
  }
  return response;
}

/**
 * ユーザー登録
 */
export async function register(userData: RegisterRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/register', userData);
  // トークンを自動保存
  if (response.access_token) {
    apiClient.setToken(response.access_token);
  }
  return response;
}

/**
 * トークンリフレッシュ
 */
export async function refreshToken(token: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/refresh', {
    refresh_token: token,
  });
  // 新しいトークンを自動保存
  if (response.access_token) {
    apiClient.setToken(response.access_token);
  }
  return response;
}

/**
 * ログアウト
 */
export async function logout(): Promise<void> {
  try {
    await apiClient.post('/auth/logout');
  } finally {
    // トークンを削除
    apiClient.clearToken();
  }
}

/**
 * パスワードリセットを要求（登録の有無に関わらず成功扱い）
 */
export async function requestPasswordReset(email: string): Promise<void> {
  await apiClient.post('/auth/password-reset/request', { email });
}

/**
 * パスワードリセットを確定（トークン＋新パスワード）
 */
export async function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  await apiClient.post('/auth/password-reset/confirm', { token, new_password: newPassword });
}

/**
 * Googleログイン（Google Identity Services の ID トークンを送信）
 * サーバー未設定時は 503 が返る
 */
export async function googleLogin(idToken: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/google', { id_token: idToken });
  if (response.access_token) {
    apiClient.setToken(response.access_token);
  }
  return response;
}

