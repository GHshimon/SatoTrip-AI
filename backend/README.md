# SatoTrip Backend API

FastAPIベースのバックエンドAPIサーバーです。

## 前提条件

- **Python 3.8以上**が必要です（Python 3.9以上を推奨）
- 現在のPythonバージョンを確認: `python --version`
- Python 3.7以下の場合、[Python公式サイト](https://www.python.org/downloads/)から最新版をインストールしてください

**注意**: Python 3.7以下では依存関係のインストールに失敗します。

## セットアップ

### 1. 仮想環境を作成

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. 依存関係をインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数を設定

`.env.example` ファイルを参考に `.env` ファイルを作成し、必要な値を設定してください。

```bash
# .env.example をコピー
cp .env.example .env

# .env ファイルを編集して実際の値を設定
```

#### 環境変数の説明

| 変数名 | 説明 | デフォルト値 | 必須 |
|--------|------|-------------|------|
| `DATABASE_URL` | データベース接続URL | `sqlite:///./data/satotrip.db` | いいえ |
| `JWT_SECRET_KEY` | JWT署名用の秘密鍵 | `your-secret-key-change-in-production` | 本番環境で必須 |
| `JWT_ALGORITHM` | JWTアルゴリズム | `HS256` | いいえ |
| `JWT_EXPIRATION_HOURS` | JWTトークンの有効期限（時間） | `24` | いいえ |
| `GEMINI_API_KEY` | Google Gemini APIキー | （空） | はい |
| `YOUTUBE_API_KEY` | YouTube Data APIキー | （空） | データ収集機能使用時 |
| `OPENCAGE_API_KEY` | OpenCage Geocoding APIキー | （空） | 位置情報取得使用時 |
| `DATA_COLLECTION_ENABLED` | データ収集機能の有効/無効 | `False` | いいえ |
| `CORS_ORIGINS` | CORS許可オリジン（カンマ区切り） | `http://localhost:3000,http://localhost:5173` | いいえ |
| `ENVIRONMENT` | 実行環境 | `development` | いいえ |

#### セキュリティに関する注意事項

- **本番環境では必ず `JWT_SECRET_KEY` を強力な値に変更してください**
  - 生成方法: `openssl rand -hex 32`
  - デフォルト値のまま使用すると、セキュリティリスクがあります
  
- **`GEMINI_API_KEY` は必須です**
  - 取得方法: https://aistudio.google.com/app/apikey
  - 本番環境では必ず設定してください

- **データ収集機能を使用する場合**
  - `YOUTUBE_API_KEY`: YouTube Data APIキー（取得方法: https://console.cloud.google.com/apis/credentials）
  - `OPENCAGE_API_KEY`: OpenCage Geocoding APIキー（取得方法: https://opencagedata.com/api）

- **本番環境ではPostgreSQLなどの本番用データベースの使用を推奨します**
  - SQLiteは開発環境での使用を想定しています

### 4. データベースの初期化

```bash
# データベースディレクトリを作成
mkdir -p data

# データベースは初回起動時に自動的に作成されます
```

### 5. サーバーを起動

```bash
# 開発環境（ホットリロード有効）
uvicorn app.main:app --reload --port 8000

# 本番環境
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## APIドキュメント

サーバー起動後、以下のURLでAPIドキュメントにアクセスできます:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## プロジェクト構造

```
backend/
├── app/
│   ├── main.py          # FastAPIアプリケーションエントリーポイント
│   ├── config.py        # 設定管理（環境変数）
│   ├── dependencies.py  # 依存性注入
│   ├── api/             # APIルーター
│   │   ├── auth.py           # 認証エンドポイント
│   │   ├── plans.py          # プラン管理エンドポイント
│   │   ├── spots.py           # スポット管理エンドポイント
│   │   ├── users.py           # ユーザー管理エンドポイント
│   │   └── data_collection.py # データ収集エンドポイント（管理者専用）
│   ├── models/          # データベースモデル（SQLAlchemy）
│   ├── schemas/         # Pydanticスキーマ
│   ├── services/        # ビジネスロジック
│   │   ├── auth_service.py
│   │   ├── gemini_service.py
│   │   ├── plan_service.py
│   │   ├── spot_service.py
│   │   ├── user_service.py
│   │   ├── youtube_collection_service.py  # YouTubeデータ収集
│   │   ├── geocoding_service.py          # 位置情報取得
│   │   ├── sns_collection_service.py      # SNS/Web検索
│   │   └── spot_import_service.py         # スポットインポート
│   └── utils/           # ユーティリティ関数
│       ├── database.py
│       ├── jwt_manager.py
│       ├── security.py
│       └── error_handler.py
├── requirements.txt      # Python依存関係
└── README.md            # このファイル
```

## 環境変数の検証

本番環境（`ENVIRONMENT=production`）では、以下の検証が自動的に実行されます:

- `JWT_SECRET_KEY` がデフォルト値でないことを確認
- `GEMINI_API_KEY` が設定されていることを確認
- SQLite使用時の警告

検証に失敗した場合、アプリケーションは起動しません。

## トラブルシューティング

### 環境変数が読み込まれない

- `.env` ファイルが `backend/` ディレクトリに存在することを確認
- ファイル名が `.env` であることを確認（`.env.example` ではない）
- 環境変数の名前が大文字で正しく記述されていることを確認

### データベースエラー

- `data/` ディレクトリが存在し、書き込み権限があることを確認
- `DATABASE_URL` が正しい形式であることを確認

### CORSエラー

- `CORS_ORIGINS` にフロントエンドのURLが含まれていることを確認
- カンマ区切りで複数のオリジンを指定可能

## データ収集機能

データ収集機能を使用して、YouTube動画やWeb検索から観光スポット情報を自動収集できます。

### 前提条件

1. **管理者アカウントの作成**
   - データ収集APIは管理者専用です
   - ユーザー登録後、データベースで `role` を `admin` に変更してください

2. **環境変数の設定**
   - `DATA_COLLECTION_ENABLED=True` を設定
   - `YOUTUBE_API_KEY` を設定（YouTubeデータ収集を使用する場合）
   - `OPENCAGE_API_KEY` を設定（位置情報取得を使用する場合）

3. **キーワード設定ファイル**
   - `backend/data/search_keywords.json` に都道府県ごとの検索キーワードを設定

### APIエンドポイント

#### 1. YouTubeデータ収集

```http
POST /api/admin/data-collection/youtube
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "prefecture": "鹿児島県",
  "keywords_config_path": "data/search_keywords.json",
  "max_results_per_keyword": 5
}
```

#### 2. 位置情報付与

```http
POST /api/admin/data-collection/location
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "prefecture": "鹿児島県",
  "spot_ids": null  // nullの場合は全件処理
}
```

#### 3. SNS/Web検索データ収集

```http
POST /api/admin/data-collection/sns
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "keyword": "鹿児島 観光"
}
```

#### 4. スポットインポート

```http
POST /api/admin/data-collection/import-spots
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "youtube_data": { /* YouTube収集データ */ },
  "prefecture": "鹿児島県"
}
```

### 使用例

1. **YouTubeデータ収集 → スポットインポート → 位置情報付与** の順で実行
2. 各APIは独立して使用可能
3. エラーログは `backend/logs/` ディレクトリに保存されます

### 注意事項

- データ収集処理は時間がかかる場合があります（APIレート制限のため）
- 既存のSpotと重複する場合はスキップされます（名前とエリアで判定）
- 位置情報の取得に失敗した場合でも、Spotは作成されます（位置情報は後から付与可能）

