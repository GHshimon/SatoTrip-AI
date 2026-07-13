# スポット収集セットアップ手順（前提整備）

全国拡充のスポット収集（`POST /api/spots/bulk-add-by-prefecture`）を動かすための前提設定。
収集の優先順位・ペースは `docs/design/SPOT_ROLLOUT_SCHEDULE.md`、コスト根拠は
`docs/design/SPOT_FIELD_SPEC.md §5` を参照。

## 0. 必要なもの（結論）

一括追加を動かすのに**必須**なのは次の3キー（Render の環境変数）:

| 環境変数 | 用途 | 未設定だと |
|---|---|---|
| `GEMINI_API_KEY` | 紹介文・分類などのAI補強 | 既に設定済み（プラン生成で使用中） |
| `YOUTUBE_API_KEY` | 収集の起点（動画検索） | **動画0件＝何も集まらない** |
| `GOOGLE_MAPS_API_KEY` | スポットの存在確認・営業時間・評価の取得（Places API New） | **全候補が棄却され0件**（no_places_hit） |

加えて **Cloud Billing の予算アラート**（無料枠超過の課金防止）を必ず設定すること。

準備が整ったかは管理APIで確認できる: `GET /api/spots/collection-readiness`（管理者）。
`ready: true` なら実行可能。`missing` に未設定キーが出る。

---

## 1. Google Cloud 側の準備

### 1-1. Places API（New）のキー（`GOOGLE_MAPS_API_KEY`）
1. [Google Cloud Console → APIとサービス → ライブラリ](https://console.cloud.google.com/apis/library) で
   **Places API (New)** を有効化（併せて Geocoding API / Directions API も。ルート計算で使用）。
2. [認証情報](https://console.cloud.google.com/apis/credentials) で APIキーを作成。
3. **APIキーの制限**（重要・`OWNER_TASKS.md #1`）: 「APIの制限」で許可を
   **Places API (New) / Places API / Geocoding API / Directions API** の4つに限定。
   アプリケーション制限は「なし」でよい（Render無料枠は固定IPが無く、キーはサーバー内でのみ使用）。

### 1-2. YouTube Data API v3 のキー（`YOUTUBE_API_KEY`）
1. 同じ Cloud プロジェクトで **YouTube Data API v3** を有効化。
2. APIキーを作成（Placesと別キーでも同一キーでもよいが、**別キー推奨**：用途別に制限・監視できる）。
3. 制限: 「APIの制限」で **YouTube Data API v3** のみに限定。

### 1-3. 予算アラート（必須）
1. [Cloud Billing → 予算とアラート](https://console.cloud.google.com/billing/budgets) で予算を作成。
2. 月額の上限（例: ¥1,000〜3,000）と 50%/90%/100% のアラートを設定。
   Places の Enterprise 無料枠（月1,000回）超過は即課金のため、コード側の月次ガード
   （`PLACES_MONTHLY_DETAILS_SOFT_LIMIT`）と二重の安全網にする。

---

## 2. Render 側の設定

Render ダッシュボード → `satotrip-api` → Environment に以下を追加（保存で自動再デプロイ）:

| Key | Value |
|---|---|
| `YOUTUBE_API_KEY` | 1-2 で作成したキー |
| `GOOGLE_MAPS_API_KEY` | 1-1 で作成したキー |
| `DATA_COLLECTION_ENABLED` | `true`（旧データ収集APIを使う場合に必要。一括追加には不要だが有効化推奨） |

※ `render.yaml` にも上記をプレースホルダとして記載済み（Blueprint 再適用時に入力を求められる）。

---

## 3. 準備確認（設定漏れチェック）

管理者トークンで確認:

```bash
curl -s https://satotrip-ai-backend.onrender.com/api/spots/collection-readiness \
  -H "Authorization: Bearer <管理者トークン>" | python3 -m json.tool
```

期待するレスポンス（`ready: true`）:
```json
{
  "ready": true,
  "missing": [],
  "checks": {
    "gemini_configured": true,
    "youtube_configured": true,
    "places_configured": true,
    "spot_enrich_with_places": true,
    "spot_enrich_with_gemini": true,
    "data_collection_enabled": true,
    "details_budget_ok": true
  },
  "details_budget": { "used": 0, "soft_limit": 900, "remaining": 900, "exhausted": false, "month": "YYYY-MM" },
  "total_spots": 7,
  "spots_by_verification_status": { "unverified": 7 }
}
```
`missing` にキー名が出たら、その環境変数を Render に設定する。

---

## 4. パイロット実行（1県で較正）

いきなり全国ではなく、まず1県（例: 鹿児島県の拡充、または優先順位1位の東京都）で試す:

```bash
curl -s -X POST https://satotrip-ai-backend.onrender.com/api/spots/bulk-add-by-prefecture \
  -H "Authorization: Bearer <管理者トークン>" -H 'Content-Type: application/json' \
  -d '{"prefecture":"東京都","run_async":true}'
```
または管理画面 → スポット → 一括追加 から実行。

完了後、レスポンス（または管理画面の結果）で内訳を確認:
- `verified_count / needs_review_count / rejected_count`：検証3値の内訳
- `details_budget_used / soft_limit`：今月の Places 消費と残量
- `places_hit_rate`：Places 照合ヒット率

この実測値で `SPOT_ROLLOUT_SCHEDULE.md` の「1県あたり Details 約35回」見積もりを較正する。

---

## 5. 本番展開

`SPOT_ROLLOUT_SCHEDULE.md` の優先順位（第1月: 東京/京都/大阪/北海道/沖縄…）に沿って、
週2〜3県ずつ実行。月次予算ガードが安全上限（900回）で自動停止するので、
翌月1日以降に再開する。進捗は `collection-readiness` の `spots_by_verification_status` と
各県のスポット件数で把握する。

`needs_review` のスポットは、承認キューUI（Phase 2・未実装）または既存のスポット編集で
`verified` へ昇格させる（`PUT /api/spots/{id}/verification`）。
