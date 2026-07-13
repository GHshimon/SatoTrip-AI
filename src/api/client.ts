/**
 * APIクライアント設定
 * リクエスト/レスポンスのインターセプターとエラーハンドリング
 */
import { AppConfig } from '../../config';

export interface ApiError {
  detail: string;
  status?: number;
}

// 通常リクエストの既定タイムアウト（ms）。バックエンド無応答時に無限に待つのを防ぐ。
const DEFAULT_TIMEOUT_MS = 30000;
// タイムアウト/ネットワーク断を表すダミーステータス
const NETWORK_ERROR_STATUS = 0;

class ApiClient {
  private baseURL: string;

  constructor() {
    this.baseURL = AppConfig.API_BASE_URL;
  }

  /**
   * JWTトークンを取得
   */
  getToken(): string | null {
    return localStorage.getItem(AppConfig.STORAGE_KEYS.AUTH_TOKEN);
  }

  /**
   * JWTトークンを保存
   */
  setToken(token: string): void {
    localStorage.setItem(AppConfig.STORAGE_KEYS.AUTH_TOKEN, token);
  }

  /**
   * JWTトークンを削除
   */
  clearToken(): void {
    localStorage.removeItem(AppConfig.STORAGE_KEYS.AUTH_TOKEN);
  }

  /**
   * リクエストを送信
   */
  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = DEFAULT_TIMEOUT_MS
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // JWTトークンを自動付与
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // タイムアウト用の AbortController。指定時間で fetch を中断する。
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      // 401エラー（認証エラー）の処理
      if (response.status === 401) {
        this.clearToken();
        // ログインページにリダイレクト（必要に応じて）
        if (window.location.hash !== '#/login') {
          window.location.hash = '#/login';
        }
        // status を保持して throw（errorHandler.isAuthError が判定できるように）
        throw { detail: '認証が必要です。再度ログインしてください。', status: 401 } as ApiError;
      }

      // エラーレスポンスの処理
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`,
        }));
        const error: ApiError = {
          detail: errorData.detail || errorData.message || 'エラーが発生しました',
          status: response.status,
        };
        throw error;
      }

      // 空のレスポンス（204 No Content等）の処理
      if (response.status === 204) {
        return null as T;
      }

      return await response.json();
    } catch (error: any) {
      // タイムアウト（AbortController による中断）
      if (error?.name === 'AbortError') {
        throw {
          detail: 'リクエストがタイムアウトしました。時間をおいて再度お試しください。',
          status: NETWORK_ERROR_STATUS,
        } as ApiError;
      }
      // すでに ApiError 形式（detail を持つオブジェクト）ならそのまま伝播（status を維持）
      if (error && typeof error === 'object' && 'detail' in error) {
        throw error;
      }
      // ネットワークエラー等（TypeError: Failed to fetch など）
      if (error instanceof Error) {
        const isNetwork = error.message.includes('Failed to fetch') || error.message.includes('NetworkError');
        throw {
          detail: isNetwork ? 'サーバーに接続できませんでした。ネットワークをご確認ください。' : error.message,
          status: NETWORK_ERROR_STATUS,
        } as ApiError;
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * GETリクエスト
   */
  async get<T>(endpoint: string, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' }, timeoutMs);
  }

  /**
   * POSTリクエスト
   */
  async post<T>(endpoint: string, data?: any, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }, timeoutMs);
  }

  /**
   * PUTリクエスト
   */
  async put<T>(endpoint: string, data?: any, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }, timeoutMs);
  }

  /**
   * DELETEリクエスト（退会など確認情報が必要な場合はボディを渡せる）
   */
  async delete<T>(endpoint: string, data?: any, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
      body: data ? JSON.stringify(data) : undefined,
    }, timeoutMs);
  }

  /**
   * ファイルアップロード（multipart/form-data）
   * Content-Type はブラウザに自動設定させるため request() を通さず個別に実装する
   */
  async upload<T>(endpoint: string, formData: FormData, timeoutMs: number = 60000): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { method: 'POST', headers, body: formData, signal: controller.signal });
      if (response.status === 401) {
        this.clearToken();
        if (window.location.hash !== '#/login') window.location.hash = '#/login';
        throw { detail: '認証が必要です。再度ログインしてください。', status: 401 } as ApiError;
      }
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`,
        }));
        throw { detail: errorData.detail || 'アップロードに失敗しました', status: response.status } as ApiError;
      }
      if (response.status === 204) return null as T;
      return await response.json();
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        throw { detail: 'アップロードがタイムアウトしました。時間をおいて再度お試しください。', status: NETWORK_ERROR_STATUS } as ApiError;
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * APIのベースURLを取得（アバター等の相対URLを絶対URL化するのに使用）
   */
  getBaseURL(): string {
    return this.baseURL;
  }
}

export const apiClient = new ApiClient();

