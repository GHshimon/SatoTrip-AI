# スポットデータ品質設計書 — 全国拡充におけるAIハルシネーション対策

作成日: 2026-07-11 / 対象: スポットデータの全経路（収集・登録・表示）

## 0. 結論（サマリ）

- **設計原則**: 「事実フィールド（住所・座標・営業情報・評価・価格・営業状態）は必ず一次ソース（Google Places）から取得し、生成AIは要約・分類・タグ付けなど非事実系のみに使う」。
- 現状は **6つの登録経路すべてで生成AI由来の情報が検証なしで本番DBに直接コミット**されている。特に YouTube/SNS 経路は「動画・記事の**タイトル文字列だけ**」から生成AIがスポット名・エリア・おすすめ文を推定しており、存在しないスポットの混入リスクが最も高い。
- 収集スポットには **一律 `rating: 4.0` のデフォルト値**が付与され（`create_spot_from_data`、`import_spots_from_csv_file`）、さらにプラン生成側にも `or 4.0` / `or 4.5` のフォールバックがあり（`plans.py`）、実在しない「評価」がユーザーに表示される。**景品表示法（優良誤認）上の是正が全国展開の前提条件**。
- 対策の中核は (1) provenance（出所）カラムの追加、(2) Places 照合スコアによる **自動合格 / 要レビュー / 自動棄却の3値判定**、(3) rating の null 許容化、(4) 生成AIテキストの明示とAI由来の事実情報の保存禁止、(5) `verified_at` ベースの定期再検証。
- Phase 1（工数 M）だけで「全国展開を安全に開始できる」状態になる。

---

## 1. 現状分析: データがDBに入る全経路

### 1.1 経路図

```
[A] YouTube一括追加（管理画面のメイン経路）
 AdminPages.tsx（一括追加タブ）
  → POST /api/spots/bulk-add-by-prefecture  (api/spots.py: bulk_add_spots_by_prefecture_endpoint)
  → bulk_job_service.create_job / run_bulk_add_job（BackgroundTasks・インメモリジョブ）
  → spot_bulk_service.bulk_add_spots_by_prefecture
      → youtube_collection_service.collect_youtube_data
          → get_youtube_videos            … YouTube Search API（★取得できるのはタイトルとURLのみ）
          → summarize_with_gemini         … ★AI: タイトルだけから places/area/items/recommend を生成
      → spot_import_service.import_spots_from_youtube_data
          → parse_gemini_summary          … AI出力JSONをパース
          → create_spot_from_data         … ★rating=4.0 / duration=60 のデフォルト付与
          → enrich_spot_data
              1) gemini_service.research_spot_info  … ★AI: description/address/price/duration/tags を「推定可」で生成
              2) places_service.enrich_spot_with_places … 一次ソース（place_id/住所/座標/電話/website/rating/写真）
          → find_existing_spot / merge_spot_data → db.commit()  ← ★レビューなしで即公開
      → add_location_to_existing_spots（OpenCage geocoding。Places未ヒット分の座標補完）

[B] データ収集API（2段階版）
 AdminPages.tsx / 手動curl
  → POST /api/admin/data-collection/youtube (data_collection.py: collect_youtube_videos)
  → POST /api/admin/data-collection/import-spots (import_spots) → [A]と同じ import_spots_from_youtube_data

[C] SNS収集
  → POST /api/admin/data-collection/sns (collect_sns_data)
      → sns_collection_service.collect_trending_topics      … Google News RSS（タイトルのみ）
      → summarize_sns_article_with_gemini                   … ★AI: 記事タイトルだけから places 等を生成
  → POST /api/admin/data-collection/import-spots-from-sns
      → spot_import_service.import_spots_from_sns_data
        ★注意: この経路は enrich_spot_data を通らない＝Places照合ゼロ、rating=4.0のまま直接 db.commit()

[D] CSVインポート
  → POST /api/admin/data-collection/import-spots-from-csv
      → spot_import_service.import_spots_from_csv_file      … ★rating=4.0 / duration=60 を無条件付与

[E] 管理画面の手動作成・編集
  → POST /api/spots (api/spots.py: create_spot_endpoint)
      → enrich_spot_data（空欄フィールドを ★AI＋Places で自動補完）
  → PUT /api/spots/{spot_id} (update_spot_endpoint)
      → duration_minutes 未設定時に research_spot_info を呼び ★AI推定値を保存

[F] AIリサーチ（管理画面ボタン）
  → POST /api/spots/research (research_spot_endpoint)        … ★AI生成情報をフォームに反映
  → POST /api/spots/{spot_id}/research (research_spot)
      … ★AI出力（description/area/category/duration/price/image/rating）で既存スポットを直接 update_spot
```

### 1.2 AI生成情報（ハルシネーション可能性）の混入箇所

| # | 箇所（ファイル / 関数） | 何が起きるか |
|---|---|---|
| 1 | `youtube_collection_service.summarize_with_gemini` | プロンプトに渡るのは**動画タイトルとURLの文字列のみ**（動画内容・字幕は未取得）。AIが `places`（店名）・`area`・`items`・`recommend` を推定生成 → **存在しない店名・別の地域の店名が候補化**する既知の問題 |
| 2 | `sns_collection_service.summarize_sns_article_with_gemini` | 同上。RSSの**記事タイトルのみ**から生成。しかも経路[C]は Places 照合を一切通らない |
| 3 | `gemini_service.research_spot_info` | プロンプト自体が「正確な情報が不明な場合は、一般的な傾向や**推定値**で補完」「address は**推定でも可**」と指示。address / price / duration_minutes / description / category / tags を推定生成 |
| 4 | `spot_import_service.create_spot_from_data` | `"rating": 4.0` と `"duration_minutes": 60` を**無根拠のデフォルト値**として全収集スポットに付与 |
| 5 | `spot_import_service.import_spots_from_csv_file` | 同じく `rating=4.0` / `duration_minutes=60` を無条件付与 |
| 6 | `spot_import_service.enrich_spot_data` | AI(1)→Places(2)の順のため、**Places未ヒット時はAI推定の address/tags/price/description がそのまま保存**される。ヒット時も名称類似度の**下限スコア判定がない**（`enrich_spot_with_places` は最上位候補を無条件採用）ため誤同定した別店舗の place_id/住所/写真が付く |
| 7 | `api/spots.py: research_spot`（/{spot_id}/research） | AI出力で既存スポットのDBレコードを**直接上書き**（image は `placehold.co` ダミーに置換される設計） |
| 8 | `api/spots.py: update_spot_endpoint` | duration_minutes 未設定時にAI推定値を保存 |
| 9 | `api/plans.py`（194・250行 `or 4.0`、316行 `or 4.5`、622行 `or 4.0`） | rating が無いスポットに**プランレスポンス生成時にその場で架空の評価値を注入**しユーザーへ返す |
| 10 | `gemini_service.format_places_for_prompt`（85行） | 捏造 rating が「評価: 4.0/5.0」としてプラン生成プロンプトに混入し、AIの選定根拠を汚染 |

一次ソース側の実装状況（`places_service.py`）: Text Search＋Place Details（field mask 使用、`_DETAILS_FIELD_MASK` に `regularOpeningHours` は含むが**保存されていない**。`businessStatus` は**取得すらしていない**＝閉業検知が不可能）。候補スコアリング `_build_candidate_score`（名称0.45/県0.25/エリア0.15/型0.15）と `matched_score` は既に返しているが、**利用側が閾値判定に使っていない**。

---

## 2. リスク台帳（フィールド単位）

| フィールド | 現在の出所 | 捏造リスク | 法的リスク | ユーザー影響 | 対応方針 |
|---|---|---|---|---|---|
| `name` | AI（動画/記事タイトルから推定）→ Places 正規名は**不採用**（`enrich_spot_data` コメント参照） | **高**: 存在しない・表記違いの店名 | 中（不実表示） | 検索不能・現地に無い | Places照合スコアで存在確認、閾値未満は棄却 |
| `rating` | **一律4.0**（#4,#5）、Placesヒット時のみ実値、プラン側 `or 4.0/4.5`（#9） | **確定的に捏造**（値がある＝捏造） | **高: 景表法・優良誤認**。評価実績がないのに「4.0/5.0」を表示 | 評価順ソート（`FeaturePages.tsx`）が無意味化、信頼毀損 | **Places由来のみ保存。デフォルト値全廃・null許容** |
| 営業時間/定休日 | 未保存（Placesから取得済みだが捨てている）。AIには生成させていない | —（今後AIに生成させたら高） | 高（営業時間の誤りは実害直結） | 閉店時訪問 | **AI出力は保存禁止。Places `regularOpeningHours` のみ保存、無ければ非表示** |
| `price` | AI推定（#3）or Places priceLevel→円換算テーブル | **高**: AIの「参考価格」は根拠なし | **高**: 価格の不実表示は景表法（有利誤認）に直結 | 予算計画が狂う | AI由来priceの保存廃止。Places priceLevel は「価格帯（目安）」表示に限定 |
| `address` | AI推定（「推定でも可」#3）→ Placesヒット時のみ上書き | **高**（Places未ヒット時） | 中 | 誤った場所へ誘導 | Places `formattedAddress` のみ保存。未取得なら null |
| `latitude/longitude` | Places → 無ければ OpenCage geocoding（AI由来の name+area 文字列で検索） | 中: 誤同定・同名別地点 | 低 | 地図・距離計算・プラン動線の破綻 | Places location を正、都道府県境界（`_PREFECTURE_BOUNDS`）内チェック |
| `description` | AI生成（#1,#3。recommend/items 由来） | 中: 「同名他店の特徴混入」をプロンプトで禁止しているだけ | 中（体験・受賞歴等の捏造があれば優良誤認） | 誤期待 | AI生成と明示表示＋事実断定表現の禁止（要約・魅力紹介に限定） |
| `image` | Places写真（プロキシ経由）or `placehold.co` | 低（Places由来） | 低 | 誤同定時に別店舗の写真 | 照合スコア合格時のみ採用 |
| `duration_minutes` | AI推定 or 一律60 | 中 | 低 | プランの時間割が崩れる | 「目安」として許容（非事実系）。ただしAI推定であることを内部管理 |
| `tags` / `category` | AI生成・キーワードマッピング（`map_category_from_theme`） | 低〜中（分類ミス） | 低 | 検索・絞り込み精度低下 | AI利用継続可（非事実系）。provenance だけ記録 |
| `area` | AI推定 | 中 | 低 | エリア検索（`Spot.area.contains`）に不一致 | Places住所から機械的に導出 |
| `phone` / `website` | Places のみ | 低 | 低 | — | 現状維持（Places限定を明文化） |
| 営業状態（閉業） | **未管理** | —（閉業店の掲載は事実上の誤情報） | 中 | 閉業店へ誘導＝最悪の体験 | `business_status` カラム新設＋定期再検証 |

---

## 3. 設計方針

### 3.0 原則

1. **事実フィールドは一次ソース限定**: place_id / name(正規名) / address / lat・lng / phone / website / rating / 営業時間 / business_status / price(価格帯) は Places API の値のみ保存可。AI出力をこれらのカラムに書くコードパスを排除する。
2. **AIは非事実系限定**: description（紹介文）、tags、category、duration_minutes（目安）、テーマ分類、翻訳・要約。
3. **未検証データは公開しない**: 公開クエリは検証済みスポットのみ返す。
4. **値が無いなら無いと表示する**: デフォルト値で埋めない（rating 4.0 の全廃）。

### 3.1 出所管理（provenance）— `models/spot.py` へのカラム追加

```python
class Spot(Base):
    # --- 既存カラムは変更なし（place_id は既に unique index あり） ---

    # 出所・検証（Phase 1）
    source = Column(String, nullable=True, index=True)
    #   'youtube' | 'sns' | 'csv' | 'manual' | 'places'（初回登録経路）
    verification_status = Column(String, nullable=False, default="unverified", index=True)
    #   'verified'（自動合格） | 'needs_review'（要人手） | 'rejected'（棄却） | 'unverified'（既存データ移行用）
    verified_at = Column(DateTime(timezone=True), nullable=True)   # 最終Places照合成功日時
    verification_score = Column(Float, nullable=True)              # enrich_spot_with_places の matched_score
    business_status = Column(String, nullable=True)                # 'OPERATIONAL' | 'CLOSED_TEMPORARILY' | 'CLOSED_PERMANENTLY'

    # 事実データ・表示制御（Phase 2）
    opening_hours = Column(JSON, nullable=True)        # Places regularOpeningHours をそのまま保存（AI禁止）
    rating_count = Column(Integer, nullable=True)      # Places userRatingCount（rating表示の根拠）
    description_source = Column(String, nullable=True) # 'ai' | 'manual' | 'source_quote'（AI生成明示用）
    field_provenance = Column(JSON, nullable=True)     # {"address": "places", "price": "places", ...} フィールド別出所
    rejected_reason = Column(String, nullable=True)    # 'no_places_hit' | 'low_score' | 'closed' | 'duplicate' | 'admin'
```

- マイグレーションは既存流儀（`add_column.py` 型のスクリプト）に合わせ `backend/scripts/migrate_spot_provenance.py` を追加（本番は Supabase Postgres への `ALTER TABLE spots ADD COLUMN ...`）。
- 既存の鹿児島7件は `verification_status='unverified'` で移行し、再検証バッチ（3.5）で `verified` に昇格させる。
- `place_id` は「source_place_id」を兼ねる（既存カラム流用）。`source_videos` も出所記録として現状維持。

### 3.2 検証パイプライン（3値判定）

```
候補（AI抽出 name/area/category）
  → places_service.enrich_spot_with_places（存在確認・businessStatus・座標・matched_score）
  → 判定 verify_spot_candidate()（新設: spot_import_service.py）
      A) 自動合格 verified:
         place_idあり AND matched_score >= 0.75
         AND businessStatus == OPERATIONAL
         AND 座標が _PREFECTURE_BOUNDS[都道府県] 内
      B) 要人手レビュー needs_review:
         place_idあり AND 0.50 <= matched_score < 0.75
         または businessStatus が CLOSED_TEMPORARILY
         または 座標が県境界外
      C) 自動棄却 rejected:
         Places未ヒット（PLACES_NO_HIT） または matched_score < 0.50
         または CLOSED_PERMANENTLY
  → verified のみ公開。needs_review はレビューキューへ。rejected は保存しない
    （Phase 2以降: 監査用に rejected も status 付きで保存し公開クエリで除外）
```

閾値は `config.py` に `SPOT_VERIFY_AUTO_PASS_SCORE = 0.75` / `SPOT_VERIFY_REVIEW_SCORE = 0.50` として外出しし、運用しながら調整する（`matched_score` の重みは `_build_candidate_score` 参照）。

**既存コードへの組み込み**:

- `spot_import_service.enrich_spot_data`: 呼び出し順を **Places先行→AI後段** に反転。Places未ヒット時は AI エンリッチ自体をスキップ（棄却されるものにAIコストをかけない）。AI出力のうち `address` / `price` を enriched に書くコード（88–98行）を削除。
- `import_spots_from_youtube_data` / `import_spots_from_sns_data`: `Spot(...)` 生成前に `verify_spot_candidate()` を挟み、判定結果を `verification_status` / `verification_score` / `verified_at` / `business_status` / `source` に格納。**SNS経路にも同じ enrich＋判定を必ず通す**（現状の素通しを廃止）。
- `bulk_job_service` の結果 dict に `verified` / `needs_review` / `rejected` 件数を追加し、`BulkAddResponse`（`schemas/spot.py`）を拡張。`AdminPages.tsx` の完了サマリ（1262行付近）に3値の内訳を表示。
- `spot_service.get_spots` / `get_spots_by_area` / `get_spots_for_plan`: `Spot.verification_status.in_(("verified", "unverified"))` フィルタを追加（`unverified` は既存データ移行の経過措置。移行完了後 `verified` のみに絞る）。管理画面用には `include_unverified=true` クエリパラメータ（admin認証時のみ有効）を `api/spots.py: list_spots` に追加。
- **レビューキュー（管理画面）**: `AdminPages.tsx` のスポット管理に「承認待ち」タブを追加。表示項目: 候補name / Placesの正規名・住所・写真 / matched_score / 出所動画リンク（`source_videos`）。操作: 「承認（verified化。名称はPlaces正規名を採用可）」「棄却」。API は `PUT /api/spots/{spot_id}/verification`（body: `{status: "verified"|"rejected"}`、admin限定）を `api/spots.py` に新設。

### 3.3 rating の扱い（一律4.0の廃止・null許容）

| 修正箇所 | 変更 |
|---|---|
| `spot_import_service.create_spot_from_data`（422行） | `"rating": 4.0` → `"rating": None` |
| `spot_import_service.import_spots_from_csv_file`（1207行） | `rating=4.0` → `rating=None` |
| `api/plans.py` 194・250行（hotel_spot）、316行（matched_spot `or 4.5`）、622行（db_spots_data） | `or 4.0` / `or 4.5` を撤廃し `spot.rating`（None可）をそのまま返す |
| `gemini_service.format_places_for_prompt`（84–85行） | 変更不要（`if rating:` で None はスキップされる）。ただし rating を出す場合は `rating_count` 併記に拡張 |
| `src/api/spots.ts: transformSpotResponse`（282行） | `rating: data.rating \|\| 0` → `rating: data.rating ?? null` |
| `types.ts`（64行 Spot / 125行） | `rating: number` → `rating: number \| null` |
| `pages/FeaturePages.tsx`（532・785行のソート、693・998行の表示） | ソートは `(b.rating ?? -1) - (a.rating ?? -1)`（null末尾）。表示は `spot.rating != null` のときだけ星＋数値を描画（0 や "null" を出さない） |
| `pages/AdminPages.tsx`（257・622・641行のフォーム初期値 `rating: 0`、743行CSV出力、1044行表示） | 初期値 null、表示は「未取得」、CSVは空欄 |
| DB移行 | 既存レコードの `rating=4.0` かつ `place_id IS NULL`（＝Places由来でない）を一括 NULL 化するスクリプト |

表示ポリシー: rating は **Places由来（`rating_count` あり）に限り「Google評価 ★4.2 (123件)」形式**で出典を明示。自社に評価実績がない以上、出典なしの星表示はしない。

### 3.4 AI生成テキストの扱い

- `description` は保存時に `description_source='ai'` を記録し、フロント（`FeaturePages.tsx` のスポットカード/詳細、`PlanPages.tsx`）で「AIによる紹介文です。最新情報は公式サイトをご確認ください」と明示（`website` へのリンクを併置）。
- `research_spot_info` のプロンプトから住所・価格の推定生成を削除し、出力スキーマを `description / category / tags / duration_minutes / area(分類用)` に縮小。「不明な場合は推定値で補完」の指示を「不明な項目は null」を返すよう変更。
- `api/spots.py: research_spot`（/{spot_id}/research）は `SpotUpdate` に渡すフィールドを `description / category / duration_minutes / tags` に限定し、`price / image / rating / area` の上書きを廃止。
- 営業時間・料金・定休日: AI出力を保存するカラムを作らない。`opening_hours` は `get_place_details` が既に取得している `regularOpeningHours` を保存して表示、未取得なら**項目ごと非表示**。

### 3.5 鮮度管理（定期再検証・閉業検知）

- 再検証ジョブ `backend/scripts/reverify_spots.py`（Phase 3 で `bulk_job_service` と同型のジョブ化＋管理画面から起動）:
  - 対象: `verified` かつ `verified_at` が古い順。
  - 処理: `get_place_details(place_id)` を field mask `id,businessStatus`（最小コスト）で呼び、`CLOSED_PERMANENTLY` → `verification_status='rejected'`（`rejected_reason='closed'`）で自動非公開、`CLOSED_TEMPORARILY` → `needs_review`。成功時 `verified_at` 更新。
  - 周期: 全件 90日サイクル（1日あたり 全件数/90 件だけ処理）。
  - 優先度付け: (1) プラン採用実績のあるスポット（`plans` 参照）・お気に入り登録（`spot_favorite`）を30日サイクル、(2) 飲食（Food/Cafe/Drink は閉業回転が速い）を優先、(3) その他。
- `verified_at` はレビュー承認時・Places照合成功時にも更新する。

### 3.6 重複排除（dedup）

現状: `find_existing_spot` は place_id → name+area → name のみ。name の表記ゆれ（「黒かつ亭 天文館店」vs「黒かつ亭」）で重複する。

1. **place_id 完全一致**（既存。unique 制約あり）— 最優先。
2. **座標近傍 + 名称正規化**: place_id 不明時、`latitude/longitude` が半径 ~100m 以内（緯度経度差 0.001 度目安）かつ `places_service._normalize_name` 同士の類似度（`_name_similarity`）>= 0.85 なら同一とみなし `merge_spot_data` へ。
3. **名称正規化 + area 前方一致**: 座標も無い場合の互換フォールバック（現行 name+area 完全一致を正規化比較に置換）。
- `find_existing_spot` に上記を実装し、YouTube/SNS/CSV/手動の全経路が同関数を通るよう `import_spots_from_sns_data`（897行の直接クエリ）と `import_spots_from_csv_file`（1189行の直接クエリ）を差し替える。
- `merge_spot_data` は「検証ステータスの高い側を勝たせる」規則を追加（verified スポットに needs_review 候補をマージしても status は下げない。事実フィールドは Places 由来値を優先）。

---

## 4. 段階的実装計画

### Phase 1 — 全国展開を安全に始める最小構成（工数: M）

ゴール: 「捏造rating の全廃」「未検証スポットの非公開」「Places照合ゲート」。

| 作業 | ファイル | 工数 |
|---|---|---|
| provenance カラム追加（source / verification_status / verified_at / verification_score / business_status）＋移行スクリプト | `backend/app/models/spot.py`, `backend/scripts/migrate_spot_provenance.py`, `backend/app/schemas/spot.py` | S |
| `businessStatus` を field mask に追加し戻り値に含める | `backend/app/services/places_service.py`（`_TEXT_SEARCH_FIELD_MASK`, `_DETAILS_FIELD_MASK`, `enrich_spot_with_places`） | S |
| 3値判定 `verify_spot_candidate()` 新設、enrich を Places先行に反転、AI由来 address/price の保存停止、YouTube/SNS両経路への適用 | `backend/app/services/spot_import_service.py`, `backend/app/config.py`（閾値） | M |
| rating デフォルト4.0全廃＋plans.py のフォールバック撤廃 | `spot_import_service.py`, `backend/app/api/plans.py` | S |
| 公開クエリの verified フィルタ＋admin用 `include_unverified` | `backend/app/services/spot_service.py`, `backend/app/api/spots.py` | S |
| フロント: rating null 対応（表示・ソート・フォーム） | `types.ts`, `src/api/spots.ts`, `pages/FeaturePages.tsx`, `pages/AdminPages.tsx`, `pages/PlanPages.tsx` | M |
| 一括追加結果に verified/needs_review/rejected 内訳を表示 | `schemas/spot.py`（BulkAddResponse）, `spot_bulk_service.py`, `pages/AdminPages.tsx` | S |
| 既存データ移行: place_id なしの rating=4.0 を NULL 化、全件 `unverified` 化→鹿児島7件を再検証 | `backend/scripts/migrate_spot_provenance.py` | S |

Phase 1 完了時点で needs_review は「保存されるが非公開」のまま溜まる（レビューUIはPhase 2）。当面は既存のスポット編集画面で状態変更できる最低限のトグルだけ付ける。

### Phase 2 — レビュー運用と表示品質（工数: M〜L）

| 作業 | ファイル / API | 工数 |
|---|---|---|
| レビューキューUI（承認待ちタブ: Places正規名・写真・score・出所動画の並列表示、承認/棄却） | `pages/AdminPages.tsx`, 新API `PUT /api/spots/{id}/verification`（`api/spots.py`） | M |
| `opening_hours` / `rating_count` の保存と表示（未取得は非表示）、rating の「Google評価・件数」出典表示 | `places_service.py`, `models/spot.py`, `schemas/spot.py`, `FeaturePages.tsx` | M |
| description のAI生成明示（`description_source`＋フロント注記） | `spot_import_service.py`, `FeaturePages.tsx`, `PlanPages.tsx` | S |
| `research_spot_info` の出力縮小（住所・価格の推定廃止）、`/{spot_id}/research` の上書きフィールド限定 | `gemini_service.py`, `api/spots.py` | S |
| dedup 強化（座標近傍＋名称正規化、SNS/CSV経路の `find_existing_spot` 統一） | `spot_import_service.py` | M |
| `field_provenance` 記録と rejected の監査保存 | `spot_import_service.py`, `models/spot.py` | S |

### Phase 3 — 継続運用（工数: M〜L）

| 作業 | ファイル / API | 工数 |
|---|---|---|
| 定期再検証ジョブ（businessStatus 最小マスク、90日サイクル＋優先度付け、閉業の自動非公開） | `backend/scripts/reverify_spots.py` → `bulk_job_service` 型ジョブ化、新API `POST /api/admin/data-collection/reverify` | M |
| Places レスポンスキャッシュ（place_id キー、TTL 30日。Placesの規約上キャッシュ可能なのは place_id 恒久・その他30日目安） | 新 `models/place_cache.py` または `plan_cache.py` と同型 | M |
| 品質ダッシュボード（verified率 / needs_review滞留 / 棄却率 / 経路別ヒット率 — 既存 `kpi_metrics` を集計表示） | `pages/AdminPages.tsx`, `api/admin.py` | M |
| YouTube要約の入力強化（タイトルのみ→説明文・字幕の取得を検討）※それでも事実フィールドはPlaces限定の原則は不変 | `youtube_collection_service.py` | L |

---

## 5. コスト考慮（Places API）

課金は SKU（呼び出し種別 × field mask に含めるフィールドのティア）で決まる。概算の考え方:

```
1候補あたりの検証コスト
  = TextSearch単価 × 平均試行回数 + Details単価 × ヒット率 (+ Photo単価 × 写真取得数)
```

- 平均試行回数: `enrich_spot_with_places` は段階的クエリ（`_query_candidates` 最大4回）だが、ヒットで打ち切るため実測（`BulkAddResponse.places_search_count / places_hit_count`、既に計測済み）で 1.2〜1.5 回程度を見込む。
- 例: 1県あたり候補500件 × 47県 ≒ 23,500件 → TextSearch 約3万回 + Details 約2万回のオーダー。TextSearch/Details とも Pro ティアで数千円〜数万円規模（単価は変動するため、導入時に最新の料金表で `places_search_count` 実測値と掛け算して見積もる）。

**節約策**:

1. **フィールドマスクのティア最適化**（最重要）
   - Text Search は選別にしか使わないので `places.id, places.displayName, places.formattedAddress, places.location, places.types` に縮小（現行マスクの `rating, priceLevel` は Details 側に寄せ、TextSearch を低ティアに保つ）。
   - Details は登録確定時の1回だけフルマスク。**再検証は `id,businessStatus` の最小マスク**で別関数（`get_place_business_status`）に分離し、定期ジョブのコストを一桁下げる。
2. **検証タイミングの限定**: Places 呼び出しは (a) 登録時1回、(b) レビュー承認時（必要なら）、(c) 定期再検証のみ。ユーザーのリクエスト経路（プラン生成・スポット一覧）からは**絶対に呼ばない**（DBの検証済みデータのみ使用。現状もこの構造であり維持する）。
3. **棄却の前倒し（cheap-first）**: Phase 1 の「Places先行→AI後段」反転により、Places未ヒット候補への生成AI呼び出し（`gemini_enrich_call_count`）も削減される。
   さらに `enrich_spot_with_places` で **TextSearch のスコアが要レビュー閾値（0.50）未満の候補は Details 呼び出しをスキップ**する（実装済み）。低スコア候補はどのみち `rejected(low_score)` で DB 保存されず、Details（Enterprise ティア）の値は使われないため。誤同定の弱い候補に Enterprise 枠を消費しなくなる。
4. **TextSearch のティア最適化（実装済み）**: 上記1のとおり `rating`/`priceLevel` を外し TextSearch を Enterprise→Pro に。Enterprise 無料枠（月1,000回）を Details 専用にできる。
4. **キャッシュ**: place_id → Details レスポンスを30日キャッシュ（Phase 3）。dedup で同一 place_id の再照会を回避（`find_existing_spot` の place_id 優先が既に効く）。
5. **写真**: 現行のプロキシ（`GET /api/spots/photo`, `fetch_photo_media`）は `Cache-Control: max-age=86400` 済み。取得は1スポット1枚（`photos[0]`）を維持し、`maxWidthPx` は用途別（一覧400px/詳細800px）に出し分けて転送量を抑える。
6. **一括追加の上限**: 既存の `BULK_ADD_HARD_MAX_*`（`config.py` 96–98行）がコスト暴走の安全装置として機能しているため維持。1県あたりの想定 Places コストを管理画面の一括追加フォームに事前表示する（`max_total_videos × 平均スポット数/動画 × 単価`）。

**計測**: `kpi_metrics`（`import_spots_from_youtube_data`）に `verified_count / needs_review_count / rejected_count` を追加し、「検証コスト ÷ verified 1件」を県単位でモニタリングする。

---

## 6. 非対象（本設計で扱わないこと）

- YouTube 動画の字幕・本文取得によるAI入力の質改善（Phase 3 で検討。原則として事実はPlaces限定なので優先度低）。
- 独自のユーザーレビュー機能（rating を自社データで持つ将来案）。
- Places 以外の一次ソース（自治体オープンデータ等）の追加。スキーマ上は `source` / `field_provenance` で拡張可能にしてある。
