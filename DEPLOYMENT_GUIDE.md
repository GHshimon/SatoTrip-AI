# SatoTrip-AI 永久デプロイメントガイド

このガイドでは、現在の開発環境を永久的なウェブサイト（本番環境）として公開するための手順を説明します。

## 1. 推奨アーキテクチャ

本番環境では、信頼性とスケーラビリティを確保するために以下の構成を推奨します。

| コンポーネント | 推奨サービス | 役割 |
| :--- | :--- | :--- |
| **フロントエンド** | Vercel / Netlify / Cloudflare Pages | 静的ファイルのホスティング、CDN配信 |
| **バックエンド** | Render / Railway / AWS App Runner | APIサーバーの実行（Dockerコンテナ） |
| **データベース** | Supabase / Neon / AWS RDS | 永続的なデータの保存（PostgreSQL） |
| **ドメイン/SSL** | Cloudflare / Google Domains | カスタムドメインとHTTPS化 |

## 2. デプロイの準備

プロジェクトルートに本番環境用の設定ファイルを作成しました。

- `Dockerfile.frontend`: フロントエンドのビルドとNginxでの配信設定
- `Dockerfile.backend`: バックエンドのコンテナ化設定
- `docker-compose.prod.yml`: データベースを含む全サービスの統合管理設定
- `.env.production.example`: 本番環境で必要な環境変数のテンプレート

## 3. ステップバイステップの手順

### ステップ 1: データベースの準備
1. [Supabase](https://supabase.com/) または [Neon](https://neon.tech/) で無料のPostgreSQLデータベースを作成します。
2. 接続文字列（DATABASE_URL）を取得します。

### ステップ 2: バックエンドのデプロイ
1. [Render](https://render.com/) などのサービスで「Web Service」を新規作成します。
2. GitHubリポジトリを連携し、`Dockerfile.backend` を使用するように設定します。
3. 以下の環境変数を設定します：
   - `DATABASE_URL`: ステップ1で取得したURL
   - `GEMINI_API_KEY`: Google AI Studioで取得したキー
   - `JWT_SECRET_KEY`: 強力なランダム文字列（`openssl rand -hex 32` で生成可能）
   - `CORS_ORIGINS`: フロントエンドの公開URL

### ステップ 3: フロントエンドのデプロイ
1. [Vercel](https://vercel.com/) でプロジェクトをインポートします。
2. ビルド設定で以下を指定します：
   - Build Command: `npm run build`
   - Output Directory: `dist`
3. 環境変数を設定します：
   - `VITE_API_BASE_URL`: ステップ2でデプロイしたバックエンドのURL

### ステップ 4: ドメインとSSLの設定
1. 独自のドメインを取得し、各ホスティングサービスの指示に従ってDNS設定を行います。
2. すべての通信が HTTPS (SSL) で行われることを確認します。

## 4. セキュリティとメンテナンス

- **APIキーの保護**: クライアントサイド（フロントエンド）にはGemini APIキーを絶対に含めないでください。バックエンド経由で呼び出す現在の構成を維持してください。
- **定期的なバックアップ**: データベースの自動バックアップを有効にしてください。
- **監視**: [UptimeRobot](https://uptimerobot.com/) などの無料サービスを使用して、サイトの稼働状況を監視することを推奨します。

---
作成者: **Manus AI**  
作成日: 2026年2月17日
