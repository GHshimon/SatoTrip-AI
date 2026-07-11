# SatoTrip-AI 開発メモ（プロジェクト固有の注意点）

## リポジトリの罠

- **`dist/` と `node_modules/` が git 追跡されている（レガシー）**。`npm run build` や `npm install` を実行すると追跡済みファイルに差分が出る。**絶対にコミットせず** `git checkout -- dist node_modules` で復元すること。根治は `git rm -r --cached dist node_modules` の追跡解除コミット（未実施）。
- `.gitignore` はあるが、既に追跡済みのファイルには効かない。
- 過去に `.env`（実JWT鍵）と `login.json`（管理者平文PW）がコミットされた履歴が**git履歴に残存**（追跡は解除済み）。`git filter-repo` での履歴消去と鍵ローテーションが未対応。

## フロントエンド

- **`@types/react` 未導入**。クラスコンポーネントは `declare props:` パターンが必要（components/ErrorBoundary.tsx 参照）。
- Tailwind は **v3 系のビルド版**（tailwind.config.js / postcss.config.js / index.css）。Play CDN 依存は撤去済み。動的クラス結合（`bg-${x}` 型）は purge されるので禁止。
- ルーティングは App.tsx の自前ハッシュルータ。**ルート一致はクエリを除いた `path` で行う**（`/create?hobby=touring` 対応）。
- index.html に aistudiocdn の importmap が残存（Vite ビルドでは未使用のレガシー）。

## デザインシステム（旅の同人誌 × 地形図）

- トークンは `src/design/tokens.css`（CSS変数 `--st-*`）と `src/design/tokens.ts`（Canvas/SVG用の同値）。**両者は必ず同期**。出典は docs/ui-redesign/DESIGN_PROPOSAL.md §3。
- ダークモードは**新デザイン画面のみ**。`.st-theme-dark` をサブツリーに付けたときだけ反転（旧画面はライト固定）。
- **ルート紋章（src/design/crest.ts）は後方互換が最重要**。`CREST_ALGO_VERSION` を上げずに出力を変えるのは禁止。`src/design/crest.test.ts` のスナップショットが割れたら安易に更新せず、新バージョン追加で対応（発行済み紋章の見た目が変わる＝最大の運用事故）。
- Canvas コンポーネントは StrictMode の二重マウント安全に（静的1回描画 or cleanup で rAF を必ず cancel）。一覧に並ぶ紋章は rAF ループ禁止。
- `#/design-preview` にデザインシステムのショーケースあり。

## バックエンド

- **async エンドポイント内で同期のブロッキング呼び出し（Gemini SDK・requests）を直接呼ぶの禁止**。`asyncio.to_thread` へ逃がすこと。イベントループが止まると Render のヘルスチェックが失敗しインスタンスごと強制再起動→502 になる（ローカルでは絶対に再現しない）。
- Gemini モデルは `GEMINI_MODEL` 環境変数（既定 `gemini-2.5-flash`）。ハードコード禁止。`google.generativeai` パッケージは非推奨で、いずれ `google.genai` へ移行が必要。
- テーマ絞り込みで候補0件になった場合はエリアのみへフォールバックする仕様（spot_service.get_spots_for_plan）。
- 登録APIは `username` + `name` + `email` + `password` が必須。ログインは `username` + `password`。

## デプロイ構成

- **フロント**: Vercel。`VITE_API_BASE_URL` は**ビルド時に焼き込み**なので変更後は Redeploy 必須。プレビューURLには Vercel の SSO 保護がかかる（外部から curl 不可）。
- **バックエンド**: Render（`render.yaml` Blueprint、**デプロイブランチは main**）。無料プランは15分無アクセスで休眠、初回リクエストに30〜60秒。URL: https://satotrip-ai-backend.onrender.com（/health で死活確認）。
- CORS は `CORS_ORIGINS` 環境変数（カンマ区切り）。フロントのURLを追加したら Render が自動再デプロイ。
- DB は Supabase Postgres（`DATABASE_URL`）。**スポットデータは鹿児島の数件のみ**で、他エリアの生成は「スポット必須」エラーになる。全国展開にはスポット投入が必須。

## 検証環境（Claude Code セッション）

- Playwright は **scratchpad 側に `npm i playwright-core`**（リポジトリに入れると次の `npm install` で prune される）。Chromium は `/opt/pw-browsers/chromium-*/chrome-linux/chrome` を `--no-sandbox` で。
- フロントは `localhost` でアクセス（`127.0.0.1` は CORS で弾かれる）。
- このサンドボックスの送信プロキシは同一ホストへの並行接続を直列化することがある（外部APIの並行計測は不正確）。
- 本番検証で作成したテストユーザー `e2etest*@example.com` が Supabase に残っている（削除可）。
