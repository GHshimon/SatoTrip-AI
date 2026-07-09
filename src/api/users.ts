/**
 * ユーザー管理API
 */
import { apiClient } from './client';
import { User } from '../../types';

export interface UserUpdateRequest {
  name?: string;
  email?: string;
  avatar?: string;
}

export interface UserPreferences {
  notifications_enabled: boolean;
  email_notifications: boolean;
  language: string;
}

export interface UserPreferencesUpdate {
  notifications_enabled?: boolean;
  email_notifications?: boolean;
  language?: string;
}

/** 現在のユーザーの設定を取得 */
export async function getPreferences(): Promise<UserPreferences> {
  return apiClient.get<UserPreferences>('/api/users/me/preferences');
}

/** 現在のユーザーの設定を更新 */
export async function updatePreferences(data: UserPreferencesUpdate): Promise<UserPreferences> {
  return apiClient.put<UserPreferences>('/api/users/me/preferences', data);
}

/** パスワードを変更（現在のパスワード検証あり） */
export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.put<{ message: string }>('/api/users/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

/** アバター画像をアップロードして更新後のUserを返す */
export async function uploadAvatar(file: File): Promise<User> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.upload<any>('/api/users/me/avatar', formData);
  return transformUserResponse(response);
}

/** アバターの相対URL（/uploads/...）を表示用の絶対URLに変換する */
export function resolveAvatarUrl(avatar?: string): string {
  if (!avatar) return '';
  if (avatar.startsWith('http://') || avatar.startsWith('https://')) return avatar;
  if (avatar.startsWith('/uploads/')) return `${apiClient.getBaseURL()}${avatar}`;
  return avatar;
}

/**
 * 現在のユーザー情報取得
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<any>('/api/users/me');
  return transformUserResponse(response);
}

/**
 * ユーザー情報更新
 */
export async function updateUser(userData: UserUpdateRequest): Promise<User> {
  const response = await apiClient.put<any>('/api/users/me', userData);
  return transformUserResponse(response);
}

/**
 * バックエンドのレスポンスをフロントエンドのUser型に変換
 */
function transformUserResponse(data: any): User {
  return {
    id: data.id,
    name: data.name,
    avatar: data.avatar || '',
    role: data.role || 'user',
  };
}

