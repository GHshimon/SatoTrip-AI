/**
 * ユーザー管理API
 */
import { apiClient } from './client';
import { User } from '../types';

export interface UserUpdateRequest {
  name?: string;
  email?: string;
  avatar?: string;
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

