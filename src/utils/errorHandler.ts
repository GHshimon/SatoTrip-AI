/**
 * エラーハンドリングユーティリティ
 */
import { ApiError } from '../api/client';

/**
 * APIエラーをユーザーフレンドリーなメッセージに変換
 */
export function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const apiError = error as ApiError;
    return apiError.detail || 'エラーが発生しました';
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return '予期しないエラーが発生しました';
}

/**
 * 401エラー（認証エラー）かどうかを判定
 */
export function isAuthError(error: unknown): boolean {
  if (error && typeof error === 'object' && 'status' in error) {
    const apiError = error as ApiError;
    return apiError.status === 401;
  }
  return false;
}

/**
 * エラーをログに記録
 */
export function logError(error: unknown, context?: string): void {
  const message = getErrorMessage(error);
  const logMessage = context ? `[${context}] ${message}` : message;
  console.error(logMessage, error);
}

