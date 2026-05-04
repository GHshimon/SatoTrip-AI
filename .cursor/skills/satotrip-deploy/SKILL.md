---
name: satotrip-deploy
description: >-
  SatoTrip-AI の本番デプロイ手順（Vercel フロント + Render バックエンド + Supabase
  PostgreSQL）。環境変数、接続文字列、ヘルスチェック、よくある障害の切り分けを含む。
  Use when deploying SatoTrip-AI to production, configuring Render/Vercel/Supabase,
  fixing DATABASE_URL or CORS, or when the user mentions デプロイ、本番、Render、Vercel、Supabase。
---

# SatoTrip-AI 本番デプロイ（エージェント向け手順）

このリポジトリの推奨構成は次のとおり。

| レイヤー | サービス | 役割 |
|----------|----------|------|
| フロント | Vercel | Vite 静的配信（`npm run build` → `dist`） |
| API | Render（Web Service） | FastAPI + Uvicorn（`backend/`） |
| DB | Supabase | PostgreSQL（接続は **Transaction プーラー推奨**） |

---

## 前提（Phase 0）

1. GitHub にリポジトリが push 可能であること。
2. アカウント: [Supabase](https://supabase.com)、[Render](https://render.com)、[Vercel](https://vercel.com)、（API 用）[Google AI Studio](https://aistudio.google.com/app/apikey)。
3. 本番では `backend/app/config.py` が `ENVIRONMENT=production` のとき **JWT_SECRET_KEY** と **GEMINI_API_KEY** を必須とする。未設定・デフォルト値のままでは起動しない。

---

## Phase 1: Supabase（データベース）

### 1.1 プロジェクト作成

1. Supabase で New project を作成する。
2. リージョンはユーザーに近いもの（例: Tokyo）を選ぶ。
3. **Database パスワード**を安全な場所に保存する（後で `DATABASE_URL` に使う）。プロジェクト Settings → Database で **Reset database password** も可能。

### 1.2 接続文字列（重要）

Render などクラウドから接続する場合、**Direct connection（ホスト `db.<ref>.supabase.co`・ポート 5432）** だけだと、IPv6 経路で **Network is unreachable** になることがある。

**推奨**: Dashboard → **Project Settings** → **Database** → **Connection string** で **URI** を選び、モードを **Transaction**（プーラー・ポート **6543**）にする。

- ホスト例: `aws-0-ap-northeast-1.pooler.supabase.com` または `aws-1-ap-northeast-1.pooler.supabase.com`（表示値をそのまま使う）。
- ユーザー名は **`postgres.<project-ref>`** 形式になることが多い。
- 末尾に付ける: `?sslmode=require`（推奨）。

**よくある誤り**

- `[YOUR-PASSWORD]` や `<POOLER-HOST>` のプレースホルダのまま保存する。
- ポート **6543** なのにホストを **`db.<ref>.supabase.co`** のままにする（プーラー用ホストと組み合わせる）。
- パスワードに `@` などがあるのに URL エンコードしない。

完成形のイメージ（値はダッシュボードの表示に合わせる）:

```text
postgresql://postgres.<PROJECT_REF>:<PASSWORD>@<POOLER_HOST>:6543/postgres?sslmode=require
```

### 1.3 テーブル作成

バックエンド起動時に `init_db()` が走り SQLAlchemy の `create_all` で **テーブルが自動作成**される。マイグレーション失敗時は Render のアプリログで DB 接続エラーを確認する。

---

## Phase 2: Render（バックエンド API）

### 2.1 サービス種別

- **Web Service**（HTTP で外部公開）。Background Worker ではない。

### 2.2 リポジトリ・ブランチ

- GitHub 連携し、本番用ブランチ（例: `main`）をデプロイ対象にする。

### 2.3 ルートディレクトリ・ビルド・起動

プロジェクトの実際の設定に合わせる。一般的な例（**Root Directory** を `backend` にする場合）:

| 項目 | 例 |
|------|-----|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Python | 3.11+（Render が提供する安定版。`requirements.txt` と整合させる） |

リポジトリルートをそのまま使う場合は Start を `cd backend && uvicorn ...` などに調整する。**バインドは `0.0.0.0`**。ポートは Render の **PORT** 環境変数に合わせる設定もあるが、このプロジェクトの慣例は **8000**（Render の「Docker のポート」またはドキュメントで PORT に合わせる）。

### 2.4 環境変数（必須一覧）

以下を Render の **Environment** に設定する。

| 変数 | 説明 |
|------|------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Phase 1 の **プーラー URI**（パスワード実値、`sslmode=require` 推奨） |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` 等で生成した長いランダム文字列（デフォルト文字列のまま禁止） |
| `GEMINI_API_KEY` | Google AI Studio で発行したキー |
| `CORS_ORIGINS` | フロントの本番オリジン。**カンマ区切り**。例: `https://your-app.vercel.app`（末尾スラッシュなしで統一） |

任意（機能を使う場合）: `YOUTUBE_API_KEY`, `OPENCAGE_API_KEY`, `GOOGLE_MAPS_API_KEY` など（`config.py` 参照）。

#### スポットエンリッチ（住所・緯度経度・画像の高精度取得）を有効化する

「都道府県を入れて一括追加」と「単体スポット作成」の両方で、店舗ごとに **Gemini (`research_spot_info`) と Google Places API (New)** を呼び、住所・緯度経度・画像・電話・URL を自動補完する。

1. **GCP**: APIs & Services → **Library** で **`Places API (New)`** を Enable する（既存の YouTube Data API v3 と同じプロジェクトで OK）。
2. **キー作成**: Credentials → 既存の API キーを編集 → **API restrictions** に `Places API (New)` を追加。**Application restrictions は None**（サーバから呼ぶため）。
3. **Render の環境変数**: `GOOGLE_MAPS_API_KEY` に上記キーを設定。
4. **挙動**: `SPOT_ENRICH_WITH_GEMINI` / `SPOT_ENRICH_WITH_PLACES` がデフォルト `True`。キーが空なら自動でスキップされ、従来動作（OpenCage フォールバック）に戻る。
5. **DB スキーマ**: `address`, `place_id`, `phone`, `website`, `source_videos` 列が必須。`init_db()` は既存テーブルにカラム追加しないため、本番では Supabase SQL Editor で `ALTER TABLE spots ADD COLUMN ...` を手動実行する。

### 2.5 ヘルスチェック

- **Health Check Path**: `/health`（**先頭・末尾にスペースを入れない**。`/health ` は失敗の原因になる）
- アプリは `GET /health` で JSON（例: `{"status":"ok"}`）を返す想定。

### 2.6 Python 依存関係

`backend/requirements.txt` に本番に必要なパッケージを含める。例:

- `psycopg2-binary`（PostgreSQL）
- `email-validator`（Pydantic の `EmailStr` 用）

コミット後にデプロイするとビルドでインストールされる。

### 2.7 デプロイ実行

- 環境変数変更後は **Save** し、自動再デプロイを待つか **Manual Deploy** を実行する。
- Free プランはコールドスタートがあり、**初回 HTTP が数十秒〜かかる**ことがある。

---

## Phase 3: Vercel（フロントエンド）

### 3.1 プロジェクトインポート

- GitHub から同一リポジトリをインポートする。

### 3.2 ビルド設定

| 項目 | 値 |
|------|-----|
| Framework Preset | Vite（または Other） |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install`（デフォルトで可） |

### 3.3 環境変数

| 変数 | 説明 |
|------|------|
| `VITE_API_BASE_URL` | Render のベース URL。**HTTPS**。例: `https://<service-name>.onrender.com`（末尾スラッシュなし） |

`config.ts` は `import.meta.env.VITE_API_BASE_URL` を参照する。変更後は再デプロイが必要。

### 3.4 確認 URL

- フロント: `https://<project>.vercel.app`
- API: `https://<service>.onrender.com/health`

---

## Phase 4: 動作確認チェックリスト

1. **バックエンド**: ブラウザまたは `curl` で `GET .../health` が **200** と `{"status":"ok"}`（タイムアウト時は 60〜120 秒待って再試行。Free の起床時間）。
2. **Supabase**: Table Editor または SQL で `public` に `users`, `plans`, `spots` などテーブルが存在するか。
3. **CORS**: フロントオリジンを `CORS_ORIGINS` に含めているか。ブラウザの開発者ツールで API が **CORS エラー**になっていないか。
4. **フロント**: サインアップ・ログイン・プラン作成がエラーなく完了するか。

---

## トラブルシューティング（ログの読み方）

| 現象 | 典型的な原因 |
|------|----------------|
| 502 / つながらない | プロセスが落ちている。Render **Logs** で `Application startup failed`、ImportError、DB 接続失敗を確認。 |
| `ModuleNotFoundError: psycopg2` | `requirements.txt` に `psycopg2-binary` を追加して再デプロイ。 |
| `email-validator is not installed` | `email-validator` を `requirements.txt` に追加。 |
| `JWT_SECRET_KEY` / `GEMINI_API_KEY` の ValueError | 本番用の値が未設定またはデフォルトのまま。 |
| DB `Network is unreachable`（IPv6） | **DATABASE_URL** を **Transaction プーラー（6543）** にし、ホストをプーラー用に修正。 |
| ヘルスチェック失敗 | Path が `/health` と完全一致か（スペースなし）。起動が遅い場合はプラン・設定を確認。 |
| フロントだけ失敗 | `VITE_API_BASE_URL` がバックエンド URL と一致しているか。 |

---

## 変更運用（継続デプロイ）

- **フロント**: `main`（または設定ブランチ）へ merge → Vercel が自動ビルド。
- **API**: 同様に push → Render が自動ビルド。環境変数のみ変更した場合も再デプロイが必要なことがある。

---

## エージェント向けメモ

- 秘密情報（API キー、`DATABASE_URL`）をチャットやコミットに貼らない。
- ユーザーに確認してほしいときは、**ダッシュボードのどの画面のどのラベルか**を具体的に示す。
- Render のログは **Application** タブの stderr/stdout と、デプロイの **Build** ログを区別して読む。
