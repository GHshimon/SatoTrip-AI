
# Manus移行・商用開発に向けた残タスク一覧 (SatoTrip Commercial)

このドキュメントは、現在のフロントエンドプロトタイプを「Project SatoTrip」バックエンドと統合し、商用レベルのアプリケーションへ昇華させるために必要なタスクをまとめたものです。

## 1. セキュリティ & アーキテクチャ (最優先)

- [ ] **APIキーの隠蔽 (Backend Proxy)**
  - 現在: `config.ts` 経由でクライアントサイドから直接 `GoogleGenAI` を呼び出している。
  - 修正: バックエンドに `/api/generate-plan` エンドポイントを作成し、サーバー側でGemini APIを叩く構成に変更する。`config.ts` の `GEMINI_API_KEY` を空文字またはダミーにし、サーバー側環境変数のみで管理する。
- [ ] **認証基盤の統合**
  - 現在: `App.tsx` 内の `isAuthenticated` ステート（メモリ）のみ。
  - 修正: JWT (JSON Web Token) または Session Cookie を用いた永続的な認証システムを導入する。ログイン画面 (`LoginPage`) からバックエンドの `/auth/login` を叩き、トークンを安全に保持する仕組みを実装する。
- [ ] **環境変数の整理**
  - `.env` ファイルを作成し、`VITE_API_BASE_URL` や `VITE_GOOGLE_MAPS_KEY` などを管理する。`config.ts` はこれらの値を参照する形にする。

## 2. バックエンド API 連携 (Data Integration)

現在 `mockData.ts` と `localStorage` に依存しているデータを、REST API または GraphQL に置き換えます。

- [ ] **スポットデータの取得**
  - `PrefectureSpots` や `MySpots` コンポーネントで、`GET /api/spots` を使用するように `useEffect` 内のロジックを書き換える。
- [ ] **プランの保存と取得**
  - `CreatePlan` で生成されたJSONを `localStorage` ではなく `POST /api/plans` に送信する。
  - `PlanList` で `GET /api/plans` からユーザーの保存済みプランを取得する。
- [ ] **ユーザープロファイル**
  - `UserProfile` 画面で、実際のユーザー情報を表示・更新 (`PUT /api/users/me`) できるようにする。

## 3. 地図・位置情報 (Map & Geocoding)

- [ ] **正規のGeocoding実装**
  - 現在: `getSimulatedLocation` 関数で座標をシミュレーション（ランダム生成）している。
  - 修正: バックエンド側でスポット登録時に住所から正確な緯度経度を取得し、DBに保存しておく。または、Google Maps Geocoding APIを導入する。
- [ ] **ルーティングエンジンの商用化**
  - 現在: OSRM (Open Source Routing Machine) のデモサーバーを使用。
  - 修正: Google Maps Directions API (Client side or Server side) を契約するか、Mapbox等の商用プラン、あるいは自社ホスティングのOSRMサーバーに切り替える。
  - ※Google Maps JS APIを使用する場合は、課金が有効なAPIキーを設定し、`LeafletMap` から `GoogleMap` コンポーネントへの完全移行も検討する。

## 4. 管理機能 (Admin)

- [ ] **画像アップロード機能**
  - スポット追加・編集時に画像をアップロードする先 (S3, Cloudinary, Firebase Storage等) を確保し、画像URLを取得するフローを実装する。
- [ ] **AIプロンプト管理**
  - `AdminAiSettings` で変更したプロンプトをデータベースに保存し、実際の生成ロジックに反映させる仕組みを作る。

## 5. UI/UX の改善 & クリーンアップ

- [ ] **ルーティングライブラリの導入**
  - 現在: `App.tsx` 内で簡易的な `window.location.hash` ルーターを実装している。
  - 修正: `react-router-dom` を導入し、標準的なルーティング、パラメータ取得 (`useParams`)、ネストされたルート管理を行う。
- [ ] **エラーハンドリング (Error Boundary)**
  - アプリケーション全体を囲む `ErrorBoundary` を導入し、予期せぬクラッシュ時にフォールバックUIを表示する。
- [ ] **アクセシビリティ (a11y)**
  - ボタンの `aria-label` 追加、画像の `alt` 属性の精査、キーボード操作の確認を行う。

## 6. テスト & CI/CD

- [ ] **単体テスト**: Vitest / Jest の導入。
- [ ] **E2Eテスト**: Playwright / Cypress による主要フロー（ログイン→プラン作成→保存）のテスト自動化。
- [ ] **デプロイパイプライン**: GitHub Actions等を使用し、mainブランチへのプッシュで自動ビルド・デプロイを行う設定。

---
**Note:** Manus環境へ移行後、まずは「1. セキュリティ」と「5. ルーティングライブラリ」から着手することを推奨します。
