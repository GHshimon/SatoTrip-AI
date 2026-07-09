/**
 * APIクライアント設定
 * リクエスト/レスポンスのインターセプターとエラーハンドリング
 */
import { AppConfig } from '../../config';

export interface ApiError {
  detail: string;
  status?: number;
}

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
    options: RequestInit = {}
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

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // 401エラー（認証エラー）の処理
      if (response.status === 401) {
        this.clearToken();
        // ログインページにリダイレクト（必要に応じて）
        if (window.location.hash !== '#/login') {
          window.location.hash = '#/login';
        }
        throw new Error('認証が必要です。再度ログインしてください。');
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
    } catch (error) {
      if (error instanceof Error) {
        throw { detail: error.message } as ApiError;
      }
      throw error;
    }
  }

  /**
   * GETリクエスト
   */
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * POSTリクエスト
   */
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUTリクエスト
   */
  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETEリクエスト
   */
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /**
   * ファイルアップロード（multipart/form-data）
   * Content-Type はブラウザに自動設定させるため request() を通さず個別に実装する
   */
  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(url, { method: 'POST', headers, body: formData });
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
  }

  /**
   * APIのベースURLを取得（アバター等の相対URLを絶対URL化するのに使用）
   */
  getBaseURL(): string {
    return this.baseURL;
  }
}

export const apiClient = new ApiClient();

