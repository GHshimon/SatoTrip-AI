# オーナー作業チェックリスト（コード外の手作業）

コードでは対応できない、**オーナー本人の操作が必要な項目**の一覧と手順。
完了したら `[x]` にしてコミットしてよい（このファイルは進捗管理を兼ねる）。

> スポット収集（全国拡充）の前提設定は **`docs/COLLECTION_SETUP.md`** に手順をまとめた
> （必要キー・Render設定・準備確認API `GET /api/spots/collection-readiness`・パイロット実行）。

最終更新: 2026-07-13

---

## 🔴 最優先（セキュリティ）

### 1. [ ] Places APIキーのローテーション（約10分）

旧キーは過去に写真URL経由で全ユーザーに露出済み。現在はコード側が
サーバー内プロキシ（`/api/spots/photo`）に変わっており、キーが外に出ない構造に
なっているため、**新キーへ差し替えれば完了**する。

1. [Google Cloud Console → 認証情報](https://console.cloud.google.com/apis/credentials) で新しいAPIキーを作成
2. 新キーに **API制限** を設定。許可するのは次の4つだけ:
   - Places API (New)
   - Places API
   - Geocoding API
   - Directions API
   - ※ アプリケーション制限は「なし」でよい（Render無料プランは固定IPがなく、キーはサーバー内でしか使われない）
3. Render ダッシュボード → `satotrip-api` → Environment で `GOOGLE_MAPS_API_KEY` を新キーに更新
   （`GOOGLE_PLACES_API_KEY` も設定している場合は同じく更新）。保存すると自動再デプロイ
4. 再デプロイ後、プラン詳細でスポット写真が表示されることを確認
   （過去プランのURLも応答時にプロキシへ変換されるため、旧キー削除で壊れない）
5. Cloud Console で **旧キーを削除**

### 2. [ ] 管理者パスワードの変更（約2分）

git履歴に平文パスワードが残っており、誰でも試せる状態。

1. 本番フロントで管理者アカウントでログイン
2. 設定 → プライバシーとセキュリティ → パスワードの変更（8文字以上・記号必須）
3. 注意: JWT失効機構が未実装のため、変更前に発行されたトークンは**最大24時間有効なまま**

### 3. [ ] git履歴のシークレット抹消（`git filter-repo`）

`backend/.env.production`（旧JWT鍵）と `login.json`（管理者平文PW）が履歴に残存。
1と2（キー・PWの無効化）を先に済ませれば実害は消えるので、その後落ち着いて実施でよい。

```bash
pip install git-filter-repo
git clone --mirror https://github.com/GHshimon/SatoTrip-AI.git satotrip-mirror
cd satotrip-mirror
git filter-repo --invert-paths --path backend/.env.production --path login.json
git push --force --all && git push --force --tags
```

※ 履歴が書き換わるため、実行後は各自のローカルクローンを取り直すこと。

---

## 🟡 法務（有料プラン公開の前提）

### 4. [ ] 特定商取引法表記の運営者情報を記入

`pages/LegalPages.tsx` 先頭の `OPERATOR` 定数に以下4つを記入する
（値を Claude に伝えれば代わりに記入・コミット可能）:

| 項目 | 記入内容 |
|---|---|
| `seller` 販売事業者 | 個人なら戸籍上の氏名（屋号のみは法律上不可） |
| `manager` 運営統括責任者 | 個人事業主なら販売事業者と同じでよい |
| `email` メールアドレス | 問い合わせ用。専用アドレス推奨（Gmailエイリアス等でも可） |
| `contactHours` 受付時間 | 例: 平日 10:00〜18:00 |

※ 所在地・電話番号は「請求があれば遅滞なく開示」の記載を既定にしてあるため
自宅住所の公開は不要。ただし**実際に請求されたら遅滞なく開示する運用が条件**。

---

## 🟢 インフラ設定（機能の有効化）

### 5. [ ] Stripe 本番キーの設定（決済・解約ボタンの有効化）

設定画面の決済UI（アップグレード／解約ボタン）はサーバー側の設定が済むと自動で有効になる。

1. Stripe ダッシュボードで本番APIキーを取得
2. Render → Environment に設定:
   - `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY`
   - `STRIPE_WEBHOOK_SECRET`（次のWebhook追加時に発行される）
   - ※ 価格IDの登録は不要（プラン価格はコード内定義の `price_data` 方式）
3. Stripe → Developers → Webhooks でエンドポイント
   `https://satotrip-ai-backend.onrender.com/api/payments/webhook` を追加し、
   イベント: `checkout.session.completed` / `invoice.paid` /
   `customer.subscription.deleted` / `invoice.payment_failed` を購読
4. Stripe → 設定 → Billing → カスタマーポータル を有効化（解約ボタンの遷移先）

### 6. [ ] Render に `REDIS_URL` を設定（レート制限の共有ストア）

無料の Upstash 等で Redis を作成し、Render → Environment に `REDIS_URL` を設定。
未設定でも動くが、インスタンス再起動でレート制限カウントがリセットされる。

### 7. [ ] SMTP 設定（パスワードリセットメールの送信）

Render → Environment に SMTP 系変数（`SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` /
`SMTP_PASSWORD` / `SMTP_FROM`）を設定。未設定の間、パスワードリセットメールは
送信されず、リセットリンクはサーバーログに出力される。

---

## ⚪ 掃除（任意）

### 8. [ ] Supabase のテストユーザー削除

本番検証で作成した `e2etest*@example.com` / `e2etest-atasks@example.com` が残っている。
Supabase の Table Editor から users テーブルで該当行を削除（関連データはカスケード削除）。
