"""
設定管理
環境変数から設定を読み込みます

環境変数の設定:
- .env ファイルを作成し、以下の変数を設定してください:
  - DATABASE_URL: データベース接続URL（デフォルト: sqlite:///./data/satotrip.db）
  - JWT_SECRET_KEY: JWT署名用の秘密鍵（本番環境では必須、強力な値に変更）
  - JWT_ALGORITHM: JWTアルゴリズム（デフォルト: HS256）
  - JWT_EXPIRATION_HOURS: JWTトークンの有効期限（時間、デフォルト: 24）
  - GEMINI_API_KEY: Google Gemini APIキー（必須）
  - YOUTUBE_API_KEY: YouTube Data APIキー（データ収集機能で使用、オプション）
  - OPENCAGE_API_KEY: OpenCage Geocoding APIキー（位置情報取得で使用、オプション）
  - CORS_ORIGINS: CORS許可オリジン（カンマ区切り）
  - ENVIRONMENT: 実行環境（development/production）

例:
  DATABASE_URL=sqlite:///./data/satotrip.db
  JWT_SECRET_KEY=your-secret-key-change-in-production
  GEMINI_API_KEY=your-api-key-here
  YOUTUBE_API_KEY=your-youtube-api-key-here
  OPENCAGE_API_KEY=your-opencage-api-key-here
  CORS_ORIGINS=http://localhost:3000,http://localhost:5173
  ENVIRONMENT=development
"""
from pydantic_settings import BaseSettings
from typing import List
import os
import warnings


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # Database
    # SQLite (開発環境): sqlite:///./data/satotrip.db
    # PostgreSQL (本番環境): postgresql://user:password@localhost/dbname
    DATABASE_URL: str = "sqlite:///./data/satotrip.db"
    
    # JWT認証設定
    # 本番環境では必ず強力な秘密鍵に変更してください
    # 生成方法: openssl rand -hex 32
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Gemini API設定
    # APIキーは https://aistudio.google.com/app/apikey で取得できます
    # 本番環境では必ず設定してください
    GEMINI_API_KEY: str = ""

    # YouTube Data API設定
    # APIキーは https://console.cloud.google.com/apis/credentials で取得できます
    # データ収集機能で使用（オプション）
    YOUTUBE_API_KEY: str = ""

    # OpenCage Geocoding API設定
    # APIキーは https://opencagedata.com/api で取得できます
    # 位置情報取得で使用（オプション）
    OPENCAGE_API_KEY: str = ""

    # Google Maps API設定
    # ジオコーディングで使用（オプション）
    GOOGLE_MAPS_API_KEY: str = ""

    # データ収集機能の有効/無効
    # True: データ収集機能を有効にする
    # False: データ収集機能を無効にする（デフォルト）
    DATA_COLLECTION_ENABLED: bool = False

    # 一括追加（スポット収集）設定
    # デフォルト値（UIから未指定時に使用）
    BULK_ADD_DEFAULT_MAX_RESULTS_PER_KEYWORD: int = 3
    BULK_ADD_DEFAULT_MAX_KEYWORDS: int = 20
    BULK_ADD_DEFAULT_MAX_VIDEOS: int = 30
    BULK_ADD_LOCATION_DEFAULT: bool = True
    BULK_ADD_ENABLE_BACKGROUND_JOBS: bool = True

    # サーバ側強制上限（安全装置）
    BULK_ADD_HARD_MAX_RESULTS_PER_KEYWORD: int = 10
    BULK_ADD_HARD_MAX_KEYWORDS: int = 200
    BULK_ADD_HARD_MAX_VIDEOS: int = 300

    
    # CORS設定
    # フロントエンドのオリジンをカンマ区切りで指定
    # 開発環境: http://localhost:3000,http://localhost:5173
    # 本番環境: 実際のフロントエンドURL
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # 実行環境
    # development: 開発環境（デバッグ情報を表示）
    # production: 本番環境（セキュリティ強化）
    ENVIRONMENT: str = "development"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS originsをリストに変換"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    def __init__(self, **kwargs):
        """設定の初期化とバリデーション"""
        super().__init__(**kwargs)
        self._validate_production_settings()
    
    def _validate_production_settings(self):
        """本番環境でのセキュリティ設定を検証"""
        if self.ENVIRONMENT == "production":
            # JWT_SECRET_KEYがデフォルト値でないことを確認
            if self.JWT_SECRET_KEY == "your-secret-key-change-in-production":
                raise ValueError(
                    "本番環境では JWT_SECRET_KEY を強力な値に変更してください。"
                    "生成方法: openssl rand -hex 32"
                )
            
            # GEMINI_API_KEYが設定されていることを確認
            if not self.GEMINI_API_KEY:
                raise ValueError(
                    "本番環境では GEMINI_API_KEY を設定してください。"
                    "取得方法: https://aistudio.google.com/app/apikey"
                )
            
            # SQLiteは本番環境では非推奨
            if "sqlite" in self.DATABASE_URL.lower():
                warnings.warn(
                    "本番環境ではSQLiteの使用は非推奨です。"
                    "PostgreSQLなどの本番用データベースの使用を推奨します。",
                    UserWarning
                )
        else:
            # 開発環境での警告
            if self.JWT_SECRET_KEY == "your-secret-key-change-in-production":
                warnings.warn(
                    "開発環境ではデフォルトのJWT_SECRET_KEYを使用しています。"
                    "本番環境では必ず変更してください。",
                    UserWarning
                )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# グローバル設定インスタンス
# 注意: 起動時にバリデーションが実行されます
# 本番環境では必須項目が設定されていない場合、エラーが発生します
try:
    settings = Settings()
except ValueError as e:
    # 本番環境での必須設定エラー
    import sys
    print(f"エラー: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    # その他のエラー（警告のみ）
    import warnings
    warnings.warn(f"設定の読み込み中に警告が発生しました: {e}", UserWarning)
    settings = Settings()

