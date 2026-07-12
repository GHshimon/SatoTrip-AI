# スポット項目仕様（実装準備版）— 項目別ハルシネーション対策

作成日: 2026-07-11 / 位置づけ: `SPOT_DATA_QUALITY.md`（全体設計）を**項目単位で確定**し実装に渡すための仕様。
検討方法: 3視点（旅行UX / Places供給能力 / 景表法・ハルシネーション）のサブエージェント議論を統合。

---

## 0. 議論の結論（3視点の合流点と対立の解決）

### 収束したこと（3視点が一致）

1. **rating 一律4.0の全廃・null化** — 法務「自社評価ゼロでの星＝優良誤認＋景表法7条2項で根拠資料が存在し得ない」／UX「口コミ件数が無く比較材料にならず死蔵」／供給「Places由来なら`userRatingCount`込みで取得済み（が破棄中）」。→ **Places由来のみ・件数併記・出典明示、それ以外はnull。**
2. **営業時間・定休日・営業状態（閉業）の導入が最優先** — UX「時間割生成の心臓部。無いと"行っても閉まっている旅程"を量産」／法務「[S]一次ソース必須、閉店時訪問は実害直結」／供給「`regularOpeningHours`は取得済みで破棄中、`businessStatus`は**無料で追加可能**」。→ **三者が同じ結論。しかも低コスト。ここが本設計の最大の勝ち筋。**
3. **priceLevel→円の固定変換（`_PRICE_LEVEL_TO_YEN`）は廃止** — 法務「Googleは"3000円"とは言っていない。変換自体が創作的有利誤認」／供給「priceLevelは序数バンドで金額ではない。日本ではスパース。実額が要るなら`priceRange`（無料で追加可）」。→ **序数のまま保存し価格帯記号で表示。**
4. **AIは非事実系限定** — description（主観表現のみ）/ tags / category / duration_minutes（目安）だけAI許容。住所・価格・評価・電話・営業情報はAI生成を禁止。

### コスト面の重要発見（供給視点）

現行の `_DETAILS_FIELD_MASK` は `rating`/`userRatingCount`/`priceLevel`/`websiteUri`/`regularOpeningHours` を含み **既に Enterprise ティアで課金されている**。Place Details は「マスク中の最上位ティアで1リクエスト一括課金」。したがって:

- **無料で追加できる**（ティアが上がらない）: `businessStatus`(Pro), `primaryType`/`primaryTypeDisplayName`(Pro), `currentOpeningHours`(Enterprise), `priceRange`(Enterprise), `accessibilityOptions`(Pro)。
- **ティアが跳ねる**（Enterprise+Atmosphere＝課金増）: `editorialSummary`, `reservable`, `parkingOptions`, `paymentOptions`, `reviews`。**かつ日本ではスパース**。→ 費用対効果が悪く、当面採用しない。

### 残った対立: 予約要否・駐車場（要オーナー判断）

- **UX視点**: 予約要否は「体験・人気グルメ・温泉で当日詰む」ため top-3 の重要度。駐車場は「車移動主体の鹿児島で移動前提が宙に浮く」。
- **法務視点**: 予約要否・駐車場は **[D]保存断念**。「予約不要」の誤り＝入店不可の実害、「駐車場あり」の誤り＝現地で困る。AI生成は禁止。
- **供給視点**: どちらも `reservable`/`parkingOptions`（Enterprise+Atmosphere＝**課金増**）でしか取れず、**日本ではnullだらけ**。安定した一次ソースが無い。
- **本設計の解決（推奨）**: **構造化フィールドとしては持たない**（捏造も課金増も避ける）。代わりに **`website`（現状死蔵中）を復活させて「予約・詳細は公式サイトへ」導線**とし、プラン詳細に「予約可否・駐車場は各施設へご確認ください」の定型文を置く。→ 将来、予約API/アフィリエイト連携（収益化ロードマップ）を入れる段階で、その**予約パートナーを一次ソースとして**構造化する（§8）。

---

## 1. 確定フィールド仕様

分類: **[S]** 一次ソース必須（無ければ空） / **[A]** AI許容（ラベル必須・断定禁止） / **[D]** 保存断念 / **[M]** 運用メタ

| 項目 | 分類 | 出所（確定） | Placesフィールド / 課金 | 表示ラベル | 実装アクション |
|---|---|---|---|---|---|
| name | [S] | Places正規名（照合合格時） | `displayName.text` / Pro | — | 照合スコア合格時はPlaces正規名を採用（現状はAI名を優先＝要反転） |
| description | [A] | AI（主観表現のみ） | （`editorialSummary`は不採用: 課金増＋日本スパース） | 「AIが生成した参考情報です…」＋公式リンク | プロンプトからNGワード禁止（§4）。`description_source='ai'`記録 |
| area | [S/A] | Places住所から機械導出（AIは分類補助） | `formattedAddress`から導出 | — | AI area は分類ヒントのみ、保存はPlaces由来 |
| address | [S] | Places | `formattedAddress`,`shortFormattedAddress` / Pro | — | **AI住所の書込を停止**（enrich ~88行）。未取得はnull |
| lat/lng | [S] | Places→(補完)geocoding | `location` / Pro | — | 県境界(`_PREFECTURE_BOUNDS`)内チェック。AI推定座標は保存しない |
| category | [A] | AI＋型マッピング | `primaryType`(Pro,無料)で裏取り可 | — | 非事実系。継続 |
| duration_minutes | [A] | AI/カテゴリ別ヒューリスティック | （Places非公開） | 「所要時間の目安（AI推定）・約N分」 | 一律60廃止しカテゴリ別既定へ。表示に「約」「目安」 |
| tags | [A] | AI | `types`は裏取りのみ | — | 非事実系。継続 |
| image | [S] | Places写真（プロキシ） | `photos[].name` / Pro | — | 照合合格時のみ採用。`placehold.co`は「画像なし」扱い |
| **rating** | [S] | Placesのみ | `rating` / Enterprise | 「Googleの評価 ★4.2（123件）」 | **デフォルト4.0全廃・null許容**。件数無しの星は出さない |
| **rating_count**（新） | [S] | Places | `userRatingCount` / Enterprise(取得済) | ratingと常にセット | **保存カラム新設**（現在取得して捨てている） |
| price（再設計） | [S]/[D] | Places priceLevel(序数) | `priceLevel` / Enterprise | 「価格帯の目安 ¥〜¥¥（Google水準）」 | **`_PRICE_LEVEL_TO_YEN`廃止**。AI実額は保存禁止 |
| **price_range**（新・任意） | [S] | Places | `priceRange`(Enterprise,無料) | 「概算 ○〜○円（Google）」揃った時のみ | 取得できた時だけ実額表示。日本では充足率低 |
| **opening_hours**（新） | [S] | Places | `regularOpeningHours.periods` / Enterprise(取得済) | 「営業時間は変動する場合が…公式で確認」 | **保存カラム新設**（periods構造化。現在破棄中） |
| **business_status**（新） | [S] | Places | `businessStatus` / Pro(**無料追加**) | （内部制御） | `CLOSED_PERMANENTLY`は自動非公開、`TEMPORARILY`は要レビュー |
| phone | [S] | Placesのみ | `internationalPhoneNumber` / Enterprise | — | **AI生成禁止**（他人の番号捏造防止）。生成対象外 |
| website | [S] | Placesのみ | `websiteUri` / Enterprise | 「公式サイト／予約はこちら」 | **死蔵解除**。予約・詳細導線として表示に復活 |
| place_id | [S] | Places | `id` | — | 検証・再照合・dedupのキー |
| 予約要否 | [D] | （断念） | `reservable`は課金増＋null多 | 「予約可否は施設へご確認ください」 | 構造化保存しない。websiteへ誘導（§0対立の解決） |
| 駐車場 | [D] | （断念） | `parkingOptions`は課金増＋null多 | 「駐車場は施設へご確認ください」 | 同上 |
| source / verification_* | [M] | 内部 | — | — | provenance（`SPOT_DATA_QUALITY.md §3.1`）で新設 |
| source_videos | [M] | 内部 | — | — | 出所トレース。現状維持 |

---

## 2. スキーマ確定案（`backend/app/models/spot.py`）

```python
class Spot(Base):
    # --- 既存カラムは維持（name/description/area/address/category/duration_minutes/
    #     rating/image/price/tags/latitude/longitude/place_id/phone/website/source_videos） ---

    # 出所・検証（SPOT_DATA_QUALITY.md §3.1 と統合）
    source = Column(String, nullable=True, index=True)              # 'youtube'|'sns'|'csv'|'manual'|'places'
    verification_status = Column(String, nullable=False,
                                 default="unverified", index=True)   # verified|needs_review|rejected|unverified
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_score = Column(Float, nullable=True)               # 照合スコア(matched_score)
    business_status = Column(String, nullable=True)                # OPERATIONAL|CLOSED_TEMPORARILY|CLOSED_PERMANENTLY

    # 事実データ（Placesから取得済みだが現在破棄しているものを保存）
    rating_count = Column(Integer, nullable=True)                  # userRatingCount。ratingとセットでのみ表示
    price_level = Column(Integer, nullable=True)                   # priceLevel序数 0..4（金額ではない）
    price_range_min = Column(Integer, nullable=True)               # priceRange.startPrice（円、揃った時のみ）
    price_range_max = Column(Integer, nullable=True)               # priceRange.endPrice
    opening_hours = Column(JSON, nullable=True)                    # regularOpeningHours.periods をそのまま
    description_source = Column(String, nullable=True)             # 'ai'|'manual'|'places'
    field_provenance = Column(JSON, nullable=True)                 # {"address":"places","rating":"places",...}
    rejected_reason = Column(String, nullable=True)                # no_places_hit|low_score|closed|duplicate|admin
```

- 既存 `price`(Float) の扱い: **金額としての利用を停止**。`price_level`（序数フィルタ用）＋`price_range_*`（実額・任意）へ役割移行。既存 `price` は移行期間中はnull化（`place_id IS NULL` かつ AI由来のものを一括NULL、`SPOT_DATA_QUALITY.md §3.3` の移行と統合）。
- マイグレーション: `backend/scripts/migrate_spot_provenance.py` に上記カラムをまとめて追加（本番Supabaseへ `ALTER TABLE spots ADD COLUMN ...`、既存流儀に合わせidempotent）。

---

## 3. Placesフィールドマスク改修（コスト据え置き）

`backend/app/services/places_service.py`:

```python
# 追加してもEnterpriseのまま（ティア据え置き＝追加課金なし）
_DETAILS_FIELD_MASK += ",businessStatus,primaryType,primaryTypeDisplayName,currentOpeningHours,priceRange"
# accessibilityOptions(Pro,無料)は将来のバリアフリー表示用に任意で追加可
```

- `enrich_spot_with_places` / `get_place_details` の戻り値に上記を含め、`business_status` / `opening_hours(periods)` / `rating_count` / `price_level` / `price_range_*` をSpotへ保存。
- **再検証用の最小マスク関数を分離**: `get_place_business_status(place_id)` は field mask `id,businessStatus` のみ（Proティア＝定期ジョブのコストを1桁下げる。`SPOT_DATA_QUALITY.md §3.5`）。
- Text Search マスクは選別用途に縮小（`places.id,displayName,formattedAddress,location,types`）し、`rating`/`priceLevel`（Enterprise ティアのフィールド）を外す。これで Text Search は **Enterprise → Pro** に下がる（無料枠 月1,000回→月5,000回）。候補スコアリング（`_build_candidate_score`）は displayName/formattedAddress/types のみ参照するため品質影響なし。評価・価格は place_id 確定後の Details から取得する。実装済み。

---

## 4. AI生成の制約（プロンプト改修）

### AIに生成させない項目（`gemini_service.research_spot_info` のスキーマから削除）

`address` / `price` / `image` / `rating`（そもそも無い）を出力スキーマ（596-608行）から除外し、出力を **`category` / `description` / `duration_minutes` / `tags` / `area`(分類ヒント)** に縮小。プロンプトの以下を修正:

- 567行「不明な場合は…推定値で補完」→「**不明な項目は出力しない（null）。推測で事実を作らない**」。
- 600行 `address`（「推定でも可」）を**削除**。
- 603行 `price` を**削除**。
- 617-618行「住所が分からなくても…推定で埋める」を**削除**。

### descriptionのNGワード（保存時フィルタ＋プロンプト明示）

**禁止**（検証不能な事実断定＝優良誤認）: 受賞・格付け（「ミシュラン」「◯◯賞」「三ツ星」）、最上級・序列（「日本一」「県内No.1」「行列必至」）、由来・歴史断定（「元祖」「発祥」「創業◯年」「名物」）、数値的事実（「年間◯万人」「◯席」）。
**許容**（主観的な雰囲気・勧誘）: 「落ち着いた雰囲気」「散策が楽しめる」「絶景が広がる」等。

- プロンプトに上記禁止を明記。保存時に `spot_import_service` でNGワード正規表現フィルタを通し、ヒットしたら該当文を除去 or `needs_review`。

### YouTube/SNS要約

`summarize_with_gemini` / `summarize_sns_article_with_gemini` は**タイトル文字列のみ**が入力。ここで生成された `places`(店名)・`area`・座標は**候補（未検証）**に過ぎない。§5の検証を必ず通し、`summarize_with_gemini` の「推定緯度経度」（146行付近）は保存しない。

---

## 5. 時間割生成への統合（UX視点の核心）

現状 `format_places_for_prompt(database_spots, include_details=False)`（gemini_service.py:145）で、**DBスポットは name+area+tags しかプラン生成に渡っていない**＝営業時間を持たせても使われない。改修:

1. Spotに `opening_hours` / `business_status` を保存後、プラン生成に渡すスポット表現へ **曜日別営業時間・定休日** を含める（`include_details=True` 相当、または営業情報専用の簡潔フォーマット）。
2. プロンプトに**実行可能性チェック**を追加: 「各スポットの営業時間・定休日を考慮し、閉店時間中・定休日には割り当てない。`check_in_date` の曜日で営業しないスポットは除外または代替提案」。
3. `business_status != OPERATIONAL` のスポットは生成候補から除外（`spot_service.get_spots_for_plan`）。
4. 逐次加算の時刻計算（gemini_service.py:229-245）に対し、営業終了時刻を**上限制約**として渡す（最終スポットが営業時間外に押し出されるのを防ぐ）。

> 注: 8日以上先の旅程は `regularOpeningHours` + 日本の祝日カレンダーで判定し、UIに「通常営業時間ベース。祝日・臨時休業は要確認」と明示（`currentOpeningHours` は直近約7日のみ反映のため）。

---

## 6. 表示ラベル確定文言（フロント実装用）

| 箇所 | 文言 |
|---|---|
| description | 「この紹介文はAIが生成した参考情報です。正確性・最新情報は保証されません。詳細は公式サイトでご確認ください。」＋`website`リンク |
| rating | 「Googleの評価 ★4.2（123件）」＋「※ SatoTrip独自の評価ではありません」 |
| price | 「価格帯の目安：¥〜¥¥（Googleの価格水準による）」／`price_range`があれば「概算 ○〜○円（Google）」 |
| duration | 「所要時間の目安（AIによる推定）：約45分」 |
| 営業時間/定休日 | 「営業時間・定休日は変動する場合があります。訪問前に公式情報でご確認ください。」（未取得時は項目非表示） |
| 予約/駐車場 | 「予約可否・駐車場の有無は各施設へ直接ご確認ください。」 |
| プラン全体フッタ | 「本プランはAIが生成した提案です。掲載情報の正確性・最新性は保証されません。各施設の営業状況・料金・予約は公式情報をご確認ください。」（既存の免責表示を拡張） |

---

## 7. 実装計画（`SPOT_DATA_QUALITY.md §4 Phase 1` を項目仕様で具体化）

Phase 1（全国展開を安全に始める最小構成・工数M）を、本仕様で以下に確定:

| 作業 | ファイル | 工数 |
|---|---|---|
| スキーマ追加（§2の全カラム）＋移行スクリプト | `models/spot.py`, `scripts/migrate_spot_provenance.py`, `schemas/spot.py` | S |
| フィールドマスク拡張（§3、ティア据え置き）＋戻り値へ business_status/opening_hours/rating_count/price_level/price_range 追加、最小マスクの business_status 関数分離 | `services/places_service.py`, `config.py`（閾値） | M |
| 3値判定 `verify_spot_candidate()`＋enrichをPlaces先行に反転＋AI住所/価格の書込停止＋YouTube/SNS両経路へ適用 | `services/spot_import_service.py` | M |
| `research_spot_info` の出力縮小（§4）＋NGワードフィルタ | `services/gemini_service.py`, `services/spot_import_service.py` | S |
| rating一律4.0全廃＋plans.py の or 4.0/4.5 撤廃＋`_PRICE_LEVEL_TO_YEN`廃止 | `spot_import_service.py`, `api/plans.py`, `places_service.py` | S |
| 公開クエリの verified フィルタ＋business_status除外＋admin用 include_unverified | `services/spot_service.py`, `api/spots.py` | S |
| プラン生成に営業時間/定休日を渡し実行可能性チェック（§5） | `services/gemini_service.py` | M |
| フロント: rating null／price帯表示／営業時間・website表示／各ラベル（§6） | `types.ts`, `src/api/spots.ts`, `pages/FeaturePages.tsx`, `pages/PlanPages.tsx`, `pages/AdminPages.tsx` | M |
| 一括追加結果に verified/needs_review/rejected 内訳 | `schemas/spot.py`, `services/spot_bulk_service.py`, `pages/AdminPages.tsx` | S |
| 既存データ移行（AI由来 rating/price のnull化、全件unverified→鹿児島7件再検証） | `scripts/migrate_spot_provenance.py` | S |

Phase 2/3 は `SPOT_DATA_QUALITY.md §4` を踏襲（レビューUI・opening_hours表示強化・dedup強化・定期再検証・キャッシュ）。

---

## 8. 要オーナー判断（実装着手前に確認したい1点）

**予約要否・駐車場を、当面「構造化フィールドとして持たない（§0の推奨）」でよいか。**

- 推奨どおりなら: 捏造リスクゼロ・追加課金ゼロで進められ、`website`導線＋定型文で代替。
- もし「予約導線を早期に作りたい」（収益化ロードマップの宿泊/アフィリエイト予約と接続）なら: それは**予約パートナーAPIを一次ソースとする別トラック**として設計する（Placesの`reservable`は課金増＋日本スパースで非推奨）。この場合は §8 を Phase 2 に前倒しする計画を別途起こす。

この1点だけ方針をもらえれば、Phase 1 はそのまま実装に入れます。
