
/**
 * Application Configuration
 * Centralizes environment variables, feature flags, and app-wide constants.
 * 
 * 環境変数の設定:
 * - .env または .env.local ファイルを作成し、以下の変数を設定してください:
 *   - VITE_API_BASE_URL: バックエンドAPIのベースURL（デフォルト: http://localhost:8000）
 *   - VITE_IS_DEMO_MODE: デモモードフラグ（true/false、デフォルト: false）
 * 
 * 例:
 *   VITE_API_BASE_URL=http://localhost:8000
 *   VITE_IS_DEMO_MODE=false
 */
export const AppConfig = {
  // App Details
  NAME: 'SatoTrip Commercial',
  VERSION: '1.0.0',

  // API Configuration
  // Note: GEMINI_API_KEY is now handled on the backend server side for security.
  // バックエンドAPIのベースURL
  // 環境変数 VITE_API_BASE_URL で設定可能（デフォルト: http://localhost:8000）
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  GEMINI_API_KEY: '', // Deprecated: API key is now handled on backend
  
  // Feature Flags
  // デモモード: true の場合、モックデータを使用（API接続なし）
  // 環境変数 VITE_IS_DEMO_MODE で設定可能（デフォルト: false）
  IS_DEMO_MODE: import.meta.env.VITE_IS_DEMO_MODE === 'true' || false,
  
  // Local Storage Keys - Centralized to prevent typos and conflicts
  STORAGE_KEYS: {
    SAVED_PLANS: 'sato_saved_plans',
    PENDING_SPOTS: 'sato_pending_plan_spots',
    AUTH_TOKEN: 'sato_auth_token',
  },

  // Default Map Settings
  MAP: {
    DEFAULT_CENTER: [35.6895, 139.6917] as [number, number], // Tokyo
    DEFAULT_ZOOM: 13,
  }
};
