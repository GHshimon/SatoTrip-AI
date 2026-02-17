"""
将来カテゴリを追加した際に既存データベースを更新するマイグレーションスクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from app.utils.database import SessionLocal, init_db
from app.models.spot import Spot
from app.utils.tag_normalizer import (
    load_tag_categories,
    categorize_tag_value,
    normalize_tag_value,
    dict_list_to_tags,
    tags_to_dict_list,
    TagSource
)


def update_tag_categories(dry_run: bool = True):
    """
    既存タグのカテゴリを更新
    
    Args:
        dry_run: Trueの場合は実際の更新を行わず、変更内容を表示するのみ
    """
    db = SessionLocal()
    
    try:
        # カテゴリ定義を読み込み
        categories = load_tag_categories()
        print(f"カテゴリ定義を読み込みました: {len(categories.get('categories', {}))}個のカテゴリ")
        
        # タグが設定されている全スポットを取得
        spots = db.query(Spot).filter(Spot.tags.isnot(None)).all()
        
        print(f"対象スポット数: {len(spots)}")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        category_updated_count = 0
        
        for spot in spots:
            try:
                current_tags = spot.tags
                
                if not current_tags:
                    skipped_count += 1
                    continue
                
                # タグを構造化タグオブジェクトに変換
                if isinstance(current_tags, list) and current_tags:
                    if isinstance(current_tags[0], dict):
                        # 既に構造化タグ形式（辞書リスト）
                        tag_objects = dict_list_to_tags(current_tags)
                    elif isinstance(current_tags[0], str):
                        # 文字列リスト形式
                        tag_objects = normalize_tags(current_tags, source=TagSource.MIGRATION)
                    else:
                        skipped_count += 1
                        continue
                else:
                    skipped_count += 1
                    continue
                
                # 各タグのカテゴリを更新
                updated_tags = []
                has_category_update = False
                
                for tag in tag_objects:
                    tag_value = tag.value
                    current_category = tag.category
                    
                    # カテゴリが未設定、または新しいカテゴリ定義で再分類が必要な場合
                    new_category = categorize_tag_value(tag_value)
                    
                    if new_category and new_category != current_category:
                        # カテゴリが更新される
                        tag.category = new_category
                        has_category_update = True
                        category_updated_count += 1
                    
                    # 正規化された値も更新
                    tag.normalized = normalize_tag_value(tag_value)
                    
                    updated_tags.append(tag)
                
                if has_category_update or not isinstance(current_tags[0], dict):
                    # 更新が必要な場合
                    new_tags = tags_to_dict_list(updated_tags) if updated_tags else None
                    
                    if not dry_run:
                        # 実際に更新
                        spot.tags = new_tags
                        db.commit()
                        updated_count += 1
                        print(f"  ✓ 更新: {spot.name} ({len(updated_tags)}個のタグ)")
                    else:
                        # ドライランの場合は表示のみ
                        print(f"  [DRY RUN] 更新予定: {spot.name}")
                        print(f"    現在: {current_tags}")
                        print(f"    更新後: {new_tags}")
                        updated_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"  ✗ エラー: スポット {spot.id} ({spot.name}) の更新に失敗: {str(e)}")
        
        print("\n=== マイグレーション結果 ===")
        print(f"更新: {updated_count}件")
        print(f"カテゴリ更新: {category_updated_count}個のタグ")
        print(f"スキップ: {skipped_count}件")
        print(f"エラー: {error_count}件")
        
        if dry_run:
            print("\n※ これはドライランです。実際の更新を行うには dry_run=False を指定してください。")
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="既存タグのカテゴリを更新")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に更新を実行（指定しない場合はドライラン）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("タグカテゴリ更新マイグレーション")
    print("=" * 60)
    
    if not args.execute:
        print("\n⚠️  ドライランモードで実行します（実際の更新は行いません）")
        print("   実際に更新するには --execute フラグを指定してください\n")
    
    update_tag_categories(dry_run=not args.execute)

