
import { apiClient } from './client';
import { User } from '@/types';

export interface AdminUser extends User {
    username: string;
    role: 'admin' | 'user';
    is_active: boolean;
    created_at?: string;
}

export interface SystemSettings {
    gemini_model: string;
    temperature: number;
    grounding: boolean;
    system_prompt: string;
}

/**
 * ユーザー一覧取得
 */
export async function getUsers(): Promise<AdminUser[]> {
    return apiClient.get<AdminUser[]>('/api/admin/users');
}

/**
 * ユーザーロール更新
 */
export async function updateUserRole(userId: string, role: 'admin' | 'user'): Promise<void> {
    return apiClient.put(`/api/admin/users/${userId}/role?role=${role}`, {});
}

/**
 * ユーザーステータス更新
 */
export async function updateUserStatus(userId: string, isActive: boolean): Promise<void> {
    return apiClient.put(`/api/admin/users/${userId}/status?is_active=${isActive}`, {});
}

/**
 * システム設定取得
 */
export async function getSystemSettings(): Promise<SystemSettings> {
    return apiClient.get<SystemSettings>('/api/admin/settings');
}

/**
 * システム設定更新
 */
export async function updateSystemSettings(settings: SystemSettings): Promise<SystemSettings> {
    return apiClient.put<SystemSettings>('/api/admin/settings', settings);
}

export interface AdminStats {
    plans_today: number;
    plans_change: number;
    plans_trend: 'up' | 'down';
    api_calls_24h: number;
    api_calls_change: number;
    api_calls_trend: 'up' | 'down';
    error_rate: number;
    error_rate_change: number;
    error_rate_trend: 'up' | 'down';
    total_plans: number;
    total_spots: number;
    total_users: number;
    active_users: number;
}

export interface SystemAlert {
    type: 'error' | 'warning' | 'success';
    title: string;
    message: string;
    timestamp: string;
}

export interface TrendingArea {
    area: string;
    count: number;
    change_rate: number;
}

/**
 * 統計情報取得
 */
export async function getAdminStats(): Promise<AdminStats> {
    return apiClient.get<AdminStats>('/api/admin/stats');
}

/**
 * システムアラート取得
 */
export async function getSystemAlerts(): Promise<SystemAlert[]> {
    return apiClient.get<SystemAlert[]>('/api/admin/alerts');
}

/**
 * 人気急上昇エリア取得
 */
export async function getTrendingAreas(limit: number = 3): Promise<TrendingArea[]> {
    return apiClient.get<TrendingArea[]>(`/api/admin/trending-areas?limit=${limit}`);
}
