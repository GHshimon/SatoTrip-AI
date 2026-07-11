# Render へのバックエンドデプロイ手順

フロント(Vercel)だけでは AI 生成が動きません（接続先バックエンドが存在しないため）。
この手順で FastAPI バックエンドを Render に置くと、プレビュー URL だけで
「趣味カード → 生成 → 紋章付きしおり」の全フローが動きます。所要 15 分ほど。

## 前提

- Render アカウント（GitHub 接続済み）
- Gemini API キー（Google AI Studio で発行。**チャット等に貼ったキーは使い回さず新規発行**）
- Supabase プロジェクト（本番 DB に使う場合。一時停止していないこと）

## 手順 1: Render にバックエンドを作成

1. Render ダッシュボード → **New → Blueprint**
2. リポジトリ `GHshimon/SatoTrip-AI` を選択
3. **Branch にこのブランチ（`claude/repository-overview-dx41mh`）を指定**
   （バックエンドの修正一式がこのブランチにあります。PR #1 マージ後は `main` に変更）
4. `render.yaml` が読み込まれ、`satotrip-api` サービスが提案されるので **Apply**
5. 入力を求められる環境変数を設定:

   | 変数 | 入れる値 |
   |---|---|
   | `GEMINI_API_KEY` | Google AI Studio で新規発行したキー |
   | `DATABASE_URL` | Supabase → Settings → Database → Connection string (URI)。例 `postgresql://postgres:パスワード@db.xxxx.supabase.co:5432/postgres`（接続エラーになる場合は末尾に `?sslmode=require` を付与）。※空のままなら SQLite で動くが**再デプロイのたびにデータが消える**ので検証専用 |
   | `CORS_ORIGINS` | フロントの URL（カンマ区切り）。例: `https://sato-trip-ai-git-claude-ui-redesign-proposal-ghshimons-projects.vercel.app,https://sato-trip-ai.vercel.app` |
   | `FRONTEND_URL` | 上の代表 1 つ（例: `https://sato-trip-ai.vercel.app`） |

6. デプロイ完了後、`https://satotrip-api.onrender.com` のような URL が発行される
7. ブラウザで `https://satotrip-api.onrender.com/health` を開き `{"status":"ok"...}` が返れば成功

## 手順 2: Vercel のフロントを接続

1. Vercel ダッシュボード → sato-trip-ai プロジェクト → **Settings → Environment Variables**
2. 追加: `VITE_API_BASE_URL` = `https://satotrip-api.onrender.com`（手順1-6 の URL）
   - 環境は Preview / Production 両方にチェック
3. **Deployments → 最新のデプロイ → Redeploy**（環境変数はビルド時に焼き込まれるため再デプロイが必要）

## 手順 3: 動作確認

1. プレビュー URL を開く → 新規登録/ログイン
2. 趣味カード → 目的地を選び「しおりを編みはじめる」
3. 織物ローダーの後、紋章付きのプラン詳細が表示されれば完了

## 注意事項

- **無料プランの休眠**: 15 分アクセスが無いと休眠し、次のリクエストで起きるまで 30〜60 秒かかります。最初の 1 回だけ遅いのは正常です
- **管理者ユーザー**: 初期データ投入が必要な場合は `backend/scripts/` のシード手順を参照
- **メール送信（パスワードリセット）**: SMTP_* 環境変数を追加すると有効化されます（未設定でも他機能は動作）
- **Stripe 決済**: `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` / `STRIPE_PUBLISHABLE_KEY` を設定すると有効化されます
- **キーの扱い**: 過去にチャットへ貼り付けたテスト用 Gemini キーは必ず削除し、新しいキーだけを Render に設定してください
