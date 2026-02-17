<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# SatoTrip-AI

AI旅行プラン生成アプリケーション（フロントエンド + バックエンドAPI）

## プロジェクト構成

- **フロントエンド**: React + TypeScript + Vite
- **バックエンド**: FastAPI + SQLite/PostgreSQL
- **AI**: Google Gemini API

## セットアップ

### 前提条件

- Node.js (v18以上)
- Python (v3.9以上)
- npm または yarn

### フロントエンドのセットアップ

1. 依存関係をインストール:
   ```bash
   npm install
   ```

2. 環境変数を設定:
   ```bash
   # .env または .env.local ファイルを作成
   VITE_API_BASE_URL=http://localhost:8000
   VITE_IS_DEMO_MODE=false
   ```
   
   - `VITE_API_BASE_URL`: バックエンドAPIのベースURL（デフォルト: `http://localhost:8000`）
   - `VITE_IS_DEMO_MODE`: デモモードフラグ（`true`でモックデータを使用）

3. 開発サーバーを起動:
   ```bash
   npm run dev
   ```

   ブラウザで http://localhost:3000 を開きます。

### バックエンドのセットアップ

バックエンドの詳細なセットアップ手順は [backend/README.md](backend/README.md) を参照してください。

1. バックエンドディレクトリに移動:
   ```bash
   cd backend
   ```

2. 仮想環境を作成・有効化:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. 依存関係をインストール:
   ```bash
   pip install -r requirements.txt
   ```

4. 環境変数を設定:
   ```bash
   # .env ファイルを作成（backend/.env.exampleを参考）
   cp .env.example .env
   # .env ファイルを編集して必要な値を設定
   ```
   
   必須の環境変数:
   - `GEMINI_API_KEY`: Google Gemini APIキー（[取得方法](https://aistudio.google.com/app/apikey)）
   - `JWT_SECRET_KEY`: JWT署名用の秘密鍵（本番環境では強力な値に変更）

5. データベースを初期化:
   ```bash
   # データベースディレクトリを作成
   mkdir -p data
   ```

6. サーバーを起動:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   APIドキュメント:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 環境変数について

### フロントエンド

フロントエンドの環境変数は `.env` または `.env.local` ファイルで設定します。
詳細は [config.ts](config.ts) のコメントを参照してください。

### バックエンド

バックエンドの環境変数は `backend/.env` ファイルで設定します。
詳細は [backend/README.md](backend/README.md) を参照してください。

**重要**: `.env` ファイルはGitにコミットしないでください。`.gitignore` に含まれています。

## 開発

### フロントエンド

```bash
npm run dev      # 開発サーバー起動
npm run build    # 本番ビルド
npm run preview  # ビルドのプレビュー
```

### バックエンド

```bash
cd backend
uvicorn app.main:app --reload  # 開発サーバー起動（ホットリロード有効）
```

## セキュリティ

- 本番環境では必ず `JWT_SECRET_KEY` を強力な値に変更してください
- `GEMINI_API_KEY` はバックエンドでのみ使用し、フロントエンドには公開しないでください
- `.env` ファイルはGitにコミットしないでください
